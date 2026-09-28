from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v04 import analyze_residual_stack_v04

SCHEMA="GREMLIN_RECURSIVE_RESIDUAL_DECOMPOSITION_V0_4"
VERSION="0.4.0"

_ALLOWED_SOURCE_TYPES={
    "instrument_channel",
    "environment_channel",
    "clock_channel",
    "preregistered_template",
    "known_systematic_template",
}
_ALLOWED_NULL_POLICIES={"sample_circular_shift","run_permutation"}


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _canonical_sha(payload:Mapping[str,Any])->str:
    return hashlib.sha256(
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()


def _fit(target:np.ndarray,components:Sequence[np.ndarray],runs:np.ndarray)->np.ndarray:
    if not components:
        return np.zeros(0,dtype=float)
    y=target[runs].reshape(-1)
    X=np.stack([c[runs].reshape(-1) for c in components],axis=1)
    return np.linalg.lstsq(X,y,rcond=None)[0]


def _model(initial:np.ndarray,components:Sequence[np.ndarray],beta:np.ndarray)->np.ndarray:
    out=np.array(initial,dtype=float,copy=True)
    for component,coefficient in zip(components,beta):
        out+=float(coefficient)*component
    return out


def _fold_pairs(n_runs:int)->list[tuple[np.ndarray,np.ndarray]]:
    ids=np.arange(n_runs)
    out=[]
    for mask in (ids%2==0,ids<n_runs//2):
        a=ids[mask]; b=ids[~mask]
        out.extend([(a,b),(b,a)])
    return out


def _null_proxies(component:np.ndarray,policy:str,count:int)->list[np.ndarray]:
    n_runs,n_samples=component.shape
    seed=int(_sha_array(component)[:16],16)
    rng=np.random.default_rng(seed)

    if policy=="sample_circular_shift":
        out=[]
        for _ in range(count):
            proxy=np.empty_like(component)
            for i in range(n_runs):
                shift=int(rng.integers(1,n_samples))
                proxy[i]=np.roll(component[i],shift)
            out.append(proxy)
        return out

    if policy=="run_permutation":
        max_unique=math.factorial(n_runs)-1
        target=min(count,max_unique)
        identity=tuple(range(n_runs))
        seen=set()
        out=[]
        attempts=0
        while len(out)<target:
            attempts+=1
            if attempts>target*100+1000:
                raise RuntimeError("could not construct unique run-permutation null ensemble")
            perm=tuple(int(x) for x in rng.permutation(n_runs))
            if perm==identity or perm in seen:
                continue
            seen.add(perm)
            out.append(component[np.asarray(perm,dtype=int)])
        return out

    raise ValueError("unsupported nuisance null policy")


def _flat_corr(a:np.ndarray,b:np.ndarray)->float:
    aa=np.asarray(a,float).reshape(-1); bb=np.asarray(b,float).reshape(-1)
    aa-=aa.mean(); bb-=bb.mean()
    den=float(np.linalg.norm(aa)*np.linalg.norm(bb))
    return 0.0 if den==0.0 else float(np.dot(aa,bb)/den)


def _candidate_stats(
    raw:np.ndarray,
    initial:np.ndarray,
    accepted:Sequence[np.ndarray],
    candidate:np.ndarray,
    null_policy:str,
    null_count:int,
)->dict[str,Any]:
    target=raw-initial
    pairs=_fold_pairs(raw.shape[0])

    gains=[]
    coefficients=[]
    base_sse=[]
    for train,holdout in pairs:
        beta_base=_fit(target,accepted,train)
        base=_model(initial,accepted,beta_base)
        sse_base=float(np.sum((raw[holdout]-base[holdout])**2))
        if sse_base<=0.0:
            raise ValueError("degenerate zero holdout SSE")
        base_sse.append(sse_base)

        beta=_fit(target,[*accepted,candidate],train)
        pred=_model(initial,[*accepted,candidate],beta)
        sse=float(np.sum((raw[holdout]-pred[holdout])**2))
        gains.append(1.0-sse/sse_base)
        coefficients.append(float(beta[-1]))

    null_gains=[]
    for null in _null_proxies(candidate,null_policy,null_count):
        fold=[]
        for (train,holdout),sse_base in zip(pairs,base_sse):
            beta=_fit(target,[*accepted,null],train)
            pred=_model(initial,[*accepted,null],beta)
            sse=float(np.sum((raw[holdout]-pred[holdout])**2))
            fold.append(1.0-sse/sse_base)
        null_gains.append(float(min(fold)))

    signs=[int(np.sign(x)) for x in coefficients if abs(x)>1e-12]
    sign_consistent=bool(signs) and all(x==signs[0] for x in signs)
    observed=float(min(gains))
    q90=float(np.quantile(null_gains,0.90))
    return {
        "holdout_gains":[float(x) for x in gains],
        "crossfit_coefficients":[float(x) for x in coefficients],
        "coefficient_sign_consistent":sign_consistent,
        "conservative_holdout_gain":observed,
        "null_conservative_gains":null_gains,
        "individual_null_q90_gain":q90,
        "gain_over_individual_null_q90":observed-q90,
        "null_policy":null_policy,
        "null_ensemble_size":len(null_gains),
    }


def _validate_metadata(metadata:Mapping[str,Mapping[str,Any]],names:Sequence[str])->None:
    for name in names:
        m=metadata.get(name)
        if not isinstance(m,Mapping):
            raise ValueError(f"missing nuisance metadata for {name}")
        if m.get("frozen_before_fit") is not True:
            raise ValueError(f"nuisance {name} was not frozen before target fit")
        if m.get("independent_of_target_fit") is not True:
            raise ValueError(f"nuisance {name} is target-derived")
        if m.get("source_type") not in _ALLOWED_SOURCE_TYPES:
            raise ValueError(f"unsupported nuisance source_type for {name}")
        if m.get("null_policy") not in _ALLOWED_NULL_POLICIES:
            raise ValueError(f"unsupported nuisance null_policy for {name}")
        if not isinstance(m.get("source_id"),str) or not m["source_id"]:
            raise ValueError(f"missing nuisance source_id for {name}")


def recursive_residual_decomposition_v04(
    raw_runs:Sequence[Sequence[float]],
    initial_model_runs:Sequence[Sequence[float]],
    nuisance_components:Mapping[str,Sequence[Sequence[float]]],
    nuisance_metadata:Mapping[str,Mapping[str,Any]],
    *,
    sample_spacing:float=1.0,
    min_holdout_gain:float=0.01,
    min_gain_over_individual_null:float=0.005,
    familywise_alpha:float=0.01,
    null_count:int=255,
    max_candidates:int=64,
    alias_abs_correlation:float=0.97,
    max_layers:int=8,
)->tuple[dict[str,Any],np.ndarray,np.ndarray]:
    raw=np.asarray(raw_runs,float); initial=np.asarray(initial_model_runs,float)
    if raw.shape!=initial.shape or raw.ndim!=2 or raw.shape[0]<8 or raw.shape[1]<64:
        raise ValueError("v0.4 requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("raw/initial must be finite")
    if not nuisance_components:
        raise ValueError("at least one frozen nuisance component is required")
    if not (0.0<familywise_alpha<1.0):
        raise ValueError("familywise_alpha must be in (0,1)")
    if null_count<31:
        raise ValueError("null_count must be >=31")
    if len(nuisance_components)>max_candidates:
        raise ValueError("candidate family too large for greedy v0.4; use a preregistered bank test")
    if max_layers<1:
        raise ValueError("max_layers must be positive")

    names=sorted(str(name) for name in nuisance_components)
    _validate_metadata(nuisance_metadata,names)
    components={}
    for name in names:
        c=np.asarray(nuisance_components[name],float)
        if c.shape!=raw.shape or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid nuisance component {name}")
        components[name]=c

    alias_pairs=[]
    for i,left in enumerate(names):
        for right in names[i+1:]:
            corr=abs(_flat_corr(components[left],components[right]))
            if corr>=alias_abs_correlation:
                alias_pairs.append({"left":left,"right":right,"abs_correlation":corr})

    stage0_packet=analyze_residual_stack_v04(raw,initial,sample_spacing=sample_spacing)
    stage0={
        "stage_index":0,
        "accepted_component":None,
        "accepted_components":[],
        "joint_coefficients":{},
        "classification":stage0_packet["classification"],
        "analysis_sha256":stage0_packet["analysis_sha256"],
        "commitments":stage0_packet["commitments"],
        "previous_stage_sha256":None,
    }
    stage0["stage_sha256"]=_canonical_sha(stage0)

    stages=[stage0]
    accepted=[]
    selection_rounds=[]

    for round_index in range(max_layers):
        remaining=[name for name in names if name not in accepted]
        if not remaining:
            break
        accepted_arrays=[components[name] for name in accepted]

        stats={}
        for name in remaining:
            stats[name]=_candidate_stats(
                raw,initial,accepted_arrays,components[name],
                str(nuisance_metadata[name]["null_policy"]),
                null_count,
            )

        B=min(len(stats[name]["null_conservative_gains"]) for name in remaining)
        family_max_null=np.asarray([
            max(stats[name]["null_conservative_gains"][b] for name in remaining)
            for b in range(B)
        ],dtype=float)
        family_threshold=float(np.quantile(family_max_null,1.0-familywise_alpha))

        passing=[]
        scored={}
        for name in remaining:
            s=stats[name]
            if s["conservative_holdout_gain"]<min_holdout_gain:
                decision="NO_CONSERVATIVE_HOLDOUT_GAIN"
            elif s["gain_over_individual_null_q90"]<min_gain_over_individual_null:
                decision="FAIL_INDIVIDUAL_NULL_MARGIN"
            elif s["coefficient_sign_consistent"] is not True:
                decision="CROSSFIT_COEFFICIENT_SIGN_INSTABILITY"
            elif s["conservative_holdout_gain"]<=family_threshold:
                decision="FAIL_FAMILYWISE_MAX_NULL"
            else:
                decision="PASS"
                passing.append((
                    s["conservative_holdout_gain"]-family_threshold,
                    s["gain_over_individual_null_q90"],
                    s["conservative_holdout_gain"],
                    name,
                ))
            scored[name]={
                **s,
                "familywise_max_null_threshold":family_threshold,
                "familywise_alpha":float(familywise_alpha),
                "family_size":len(remaining),
                "decision":decision,
            }

        selection_rounds.append({
            "round_index":round_index+1,
            "familywise_alpha":float(familywise_alpha),
            "familywise_max_null_threshold":family_threshold,
            "familywise_null_worlds":int(B),
            "candidate_scores":scored,
        })

        if not passing:
            break

        passing.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]))
        chosen=passing[0][3]
        accepted.append(chosen)

        accepted_arrays=[components[name] for name in accepted]
        beta=_fit(raw-initial,accepted_arrays,np.arange(raw.shape[0]))
        current_model=_model(initial,accepted_arrays,beta)
        packet=analyze_residual_stack_v04(raw,current_model,sample_spacing=sample_spacing)

        stage={
            "stage_index":len(stages),
            "accepted_component":chosen,
            "accepted_components":list(accepted),
            "joint_coefficients":{name:float(v) for name,v in zip(accepted,beta)},
            "selection_score":scored[chosen],
            "classification":packet["classification"],
            "analysis_sha256":packet["analysis_sha256"],
            "commitments":packet["commitments"],
            "previous_stage_sha256":stages[-1]["stage_sha256"],
        }
        stage["stage_sha256"]=_canonical_sha(stage)
        stages.append(stage)

    accepted_arrays=[components[name] for name in accepted]
    final_beta=_fit(raw-initial,accepted_arrays,np.arange(raw.shape[0]))
    final_model=_model(initial,accepted_arrays,final_beta)
    final_residual=raw-final_model
    final_packet=analyze_residual_stack_v04(raw,final_model,sample_spacing=sample_spacing)

    alias_with_accepted=[
        pair for pair in alias_pairs
        if pair["left"] in accepted or pair["right"] in accepted
    ]
    if not accepted:
        status="NO_NUISANCE_LAYER_ACCEPTED"
    elif alias_with_accepted:
        status="PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
    else:
        status="PASS"

    result={
        "schema":SCHEMA,
        "version":VERSION,
        "status":status,
        "raw_sha256":_sha_array(raw),
        "initial_model_sha256":_sha_array(initial),
        "accepted_layers":accepted,
        "final_joint_coefficients":{name:float(v) for name,v in zip(accepted,final_beta)},
        "selection_rounds":selection_rounds,
        "stages":stages,
        "alias_pairs":alias_pairs,
        "attribution_ambiguous":bool(alias_with_accepted),
        "final_packet":final_packet,
        "policy":{
            "minimum_runs":8,
            "max_candidates_per_family":int(max_candidates),
            "familywise_max_null_required":True,
            "familywise_alpha":float(familywise_alpha),
            "null_count_requested":int(null_count),
            "candidate_must_be_frozen_before_fit":True,
            "target_derived_nuisance_forbidden":True,
            "joint_refit_after_acceptance":True,
            "mapping_order_authoritative":False,
            "destructive_denoising":False,
            "interpretation_last":True,
            "physical_mechanism_from_decomposition_only":False,
            "time_fluctuation_claim_allowed":False,
        },
    }
    result["decomposition_sha256"]=_canonical_sha(result)
    return result,final_model,final_residual


__all__=["SCHEMA","VERSION","recursive_residual_decomposition_v04"]
