from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

SCHEMA="GREMLIN_JOINT_FAMILY_NULL_WORLD_V0_15"
VERSION="0.15.0"
_ALLOWED_NULL_POLICIES={"run_permutation","sample_circular_shift"}


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _fold_pairs(n_runs:int)->list[tuple[np.ndarray,np.ndarray]]:
    ids=np.arange(n_runs)
    out=[]
    for mask in (ids%2==0,ids<n_runs//2):
        a=ids[mask]; b=ids[~mask]
        out.extend([(a,b),(b,a)])
    return out


def _fit(target:np.ndarray,components:Sequence[np.ndarray],runs:np.ndarray)->np.ndarray:
    if not components:
        return np.zeros(0,float)
    y=target[runs].reshape(-1)
    X=np.stack([c[runs].reshape(-1) for c in components],axis=1)
    return np.linalg.lstsq(X,y,rcond=None)[0]


def _model(initial:np.ndarray,components:Sequence[np.ndarray],beta:np.ndarray)->np.ndarray:
    out=np.array(initial,float,copy=True)
    for c,b in zip(components,beta):
        out += float(b)*c
    return out


def _family_seed(candidates:Mapping[str,np.ndarray])->int:
    hashes=sorted(_sha_array(v) for v in candidates.values())
    h=hashlib.sha256("|".join(hashes).encode()).hexdigest()
    return int(h[:16],16)


def _world_transforms(
    *,
    n_runs:int,
    n_samples:int,
    count:int,
    seed:int,
)->list[dict[str,Any]]:
    rng=np.random.default_rng(seed)
    out=[]
    identity=tuple(range(n_runs))
    for _ in range(int(count)):
        while True:
            perm=tuple(int(v) for v in rng.permutation(n_runs))
            if perm!=identity:
                break
        shifts=rng.integers(1,n_samples,size=n_runs,dtype=np.int64)
        out.append({
            "run_permutation":np.asarray(perm,dtype=int),
            "sample_circular_shift":np.asarray(shifts,dtype=int),
        })
    return out


def _apply_world(component:np.ndarray,policy:str,world:Mapping[str,Any])->np.ndarray:
    if policy=="run_permutation":
        return component[np.asarray(world["run_permutation"],int)]
    if policy=="sample_circular_shift":
        shifts=np.asarray(world["sample_circular_shift"],int)
        return np.asarray([
            np.roll(component[i],int(shifts[i]))
            for i in range(component.shape[0])
        ])
    raise ValueError("unsupported null policy")


def _conservative_gain(
    raw:np.ndarray,
    initial:np.ndarray,
    accepted:Sequence[np.ndarray],
    candidate:np.ndarray,
)->tuple[float,list[float],list[float]]:
    target=raw-initial
    gains=[]; coeff=[]
    for train,holdout in _fold_pairs(raw.shape[0]):
        beta_base=_fit(target,accepted,train)
        base=_model(initial,accepted,beta_base)
        sse_base=float(np.sum((raw[holdout]-base[holdout])**2))
        if sse_base<=0.0:
            raise ValueError("degenerate holdout SSE")
        beta=_fit(target,[*accepted,candidate],train)
        pred=_model(initial,[*accepted,candidate],beta)
        sse=float(np.sum((raw[holdout]-pred[holdout])**2))
        gains.append(1.0-sse/sse_base)
        coeff.append(float(beta[-1]))
    return float(min(gains)),gains,coeff


def joint_family_round_v15(
    raw_runs:Sequence[Sequence[float]],
    initial_model_runs:Sequence[Sequence[float]],
    candidate_components:Mapping[str,Sequence[Sequence[float]]],
    candidate_metadata:Mapping[str,Mapping[str,Any]],
    *,
    accepted_components:Mapping[str,Sequence[Sequence[float]]]|None=None,
    null_count:int=127,
    familywise_alpha:float=0.05,
    min_holdout_gain:float=0.0,
    min_individual_null_margin:float=0.0,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float)
    initial=np.asarray(initial_model_runs,float)
    if raw.shape!=initial.shape or raw.ndim!=2 or raw.shape[0]<8 or raw.shape[1]<64:
        raise ValueError("raw/initial must be equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("raw/initial must be finite")
    if not candidate_components:
        raise ValueError("candidate family is empty")
    if not (0.0<familywise_alpha<1.0):
        raise ValueError("familywise_alpha must be in (0,1)")
    if null_count<31:
        raise ValueError("null_count must be >=31")

    accepted_map=accepted_components or {}
    accepted_names=sorted(accepted_map)
    accepted=[]
    for name in accepted_names:
        a=np.asarray(accepted_map[name],float)
        if a.shape!=raw.shape:
            raise ValueError(f"accepted component shape mismatch: {name}")
        accepted.append(a)

    names=sorted(str(n) for n in candidate_components)
    candidates={}
    policies={}
    for name in names:
        c=np.asarray(candidate_components[name],float)
        if c.shape!=raw.shape or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid candidate {name}")
        meta=candidate_metadata.get(name)
        if not isinstance(meta,Mapping):
            raise ValueError(f"missing metadata {name}")
        policy=meta.get("null_policy")
        if policy not in _ALLOWED_NULL_POLICIES:
            raise ValueError(f"unsupported null policy {name}")
        candidates[name]=c
        policies[name]=str(policy)

    observed={}
    fold_gains={}
    coefficients={}
    for name in names:
        obs,fg,cf=_conservative_gain(raw,initial,accepted,candidates[name])
        observed[name]=obs; fold_gains[name]=fg; coefficients[name]=cf

    worlds=_world_transforms(
        n_runs=raw.shape[0],
        n_samples=raw.shape[1],
        count=int(null_count),
        seed=_family_seed(candidates),
    )
    null=np.empty((len(names),len(worlds)),float)
    for b,world in enumerate(worlds):
        for j,name in enumerate(names):
            proxy=_apply_world(candidates[name],policies[name],world)
            null[j,b]=_conservative_gain(raw,initial,accepted,proxy)[0]

    family_max=np.max(null,axis=0)
    scores={}
    passing=[]
    for j,name in enumerate(names):
        obs=float(observed[name])
        individual_q90=float(np.quantile(null[j],0.90))
        p=float((1+np.sum(family_max>=obs))/(len(worlds)+1))
        nonzero=[int(np.sign(x)) for x in coefficients[name] if abs(x)>1e-12]
        sign_ok=bool(nonzero) and all(x==nonzero[0] for x in nonzero)
        if obs<min_holdout_gain:
            decision="NO_CONSERVATIVE_HOLDOUT_GAIN"
        elif obs-individual_q90<min_individual_null_margin:
            decision="FAIL_INDIVIDUAL_NULL_MARGIN"
        elif not sign_ok:
            decision="CROSSFIT_COEFFICIENT_SIGN_INSTABILITY"
        elif p>familywise_alpha:
            decision="FAIL_JOINT_FAMILY_MAX_NULL"
        else:
            decision="PASS"
            passing.append(name)
        scores[name]={
            "conservative_holdout_gain":obs,
            "fold_holdout_gains":[float(x) for x in fold_gains[name]],
            "crossfit_coefficients":[float(x) for x in coefficients[name]],
            "individual_null_q90":individual_q90,
            "familywise_monte_carlo_p":p,
            "decision":decision,
        }

    out={
        "schema":SCHEMA,
        "version":VERSION,
        "status":"PASSING_CANDIDATES_PRESENT" if passing else "NO_CANDIDATE_PASSES",
        "candidate_names":names,
        "passing_candidates":passing,
        "familywise_alpha":float(familywise_alpha),
        "joint_null_worlds":int(len(worlds)),
        "joint_null_seed_is_content_addressed":True,
        "same_world_transform_shared_within_null_policy":True,
        "scores":scores,
        "family_max_null_quantiles":{
            "q50":float(np.quantile(family_max,0.50)),
            "q90":float(np.quantile(family_max,0.90)),
            "q95":float(np.quantile(family_max,0.95)),
            "q99":float(np.quantile(family_max,0.99)),
        },
        "policy":{
            "candidate_specific_unsynchronized_family_null_forbidden":True,
            "dependency_preserving_joint_worlds_required":True,
            "mapping_order_authoritative":False,
            "physical_attribution":False,
        },
    }
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","joint_family_round_v15"]
