from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

SCHEMA="GREMLIN_RECURSIVE_RESIDUAL_SEALED_CONFIRMATION_V0_13"
VERSION="0.13.0"
DISCOVERY_SCHEMA="GREMLIN_RECURSIVE_RESIDUAL_DECOMPOSITION_V0_5"
RUN_INDEPENDENCE_SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_12"
_ALLOWED_NULL_POLICIES={"sample_circular_shift","run_permutation"}


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


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
        target=min(int(count),math.factorial(n_runs)-1)
        identity=tuple(range(n_runs))
        seen=set(); out=[]; attempts=0
        while len(out)<target:
            attempts+=1
            if attempts>target*100+1000:
                raise RuntimeError("could not construct unique confirmatory null ensemble")
            perm=tuple(int(x) for x in rng.permutation(n_runs))
            if perm==identity or perm in seen:
                continue
            seen.add(perm)
            out.append(component[np.asarray(perm,dtype=int)])
        return out

    raise ValueError("unsupported nuisance null policy")


def _validate_declaration(declaration:Mapping[str,Any])->None:
    if not isinstance(declaration,Mapping):
        raise ValueError("confirmatory_declaration must be mapping")
    if declaration.get("sealed_before_discovery") is not True:
        raise ValueError("confirmatory dataset was not sealed before discovery")
    if declaration.get("independent_dataset") is not True:
        raise ValueError("confirmatory dataset is not declared independent")
    if not isinstance(declaration.get("dataset_id"),str) or not declaration["dataset_id"]:
        raise ValueError("confirmatory dataset_id missing")


def confirm_recursive_selection_v13(
    discovery_result:Mapping[str,Any],
    confirm_raw_runs:Sequence[Sequence[float]],
    confirm_initial_model_runs:Sequence[Sequence[float]],
    confirm_nuisance_components:Mapping[str,Sequence[Sequence[float]]],
    confirm_nuisance_metadata:Mapping[str,Mapping[str,Any]],
    confirmatory_run_independence_result:Mapping[str,Any],
    confirmatory_declaration:Mapping[str,Any],
    *,
    confirmatory_alpha:float=0.01,
    null_count:int=1023,
)->dict[str,Any]:
    if not isinstance(discovery_result,Mapping) or discovery_result.get("schema")!=DISCOVERY_SCHEMA:
        raise ValueError("unsupported discovery result schema")
    _validate_declaration(confirmatory_declaration)
    if not (0.0<confirmatory_alpha<1.0):
        raise ValueError("confirmatory_alpha must be in (0,1)")
    if 1.0/(int(null_count)+1)>confirmatory_alpha:
        raise ValueError("null_count cannot resolve confirmatory alpha")

    raw=np.asarray(confirm_raw_runs,float)
    initial=np.asarray(confirm_initial_model_runs,float)
    if raw.shape!=initial.shape or raw.ndim!=2 or raw.shape[0]<8 or raw.shape[1]<64:
        raise ValueError("confirmation requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("confirmatory raw/initial must be finite")

    confirm_raw_sha=_sha_array(raw)
    confirm_initial_sha=_sha_array(initial)
    discovery_raw_sha=discovery_result.get("raw_sha256")
    if isinstance(discovery_raw_sha,str) and discovery_raw_sha==confirm_raw_sha:
        raise ValueError("confirmation reuses discovery RAW")

    audit=confirmatory_run_independence_result
    if not isinstance(audit,Mapping) or audit.get("schema")!=RUN_INDEPENDENCE_SCHEMA:
        raise ValueError("missing or unsupported v0.12 run-independence result")
    audit_commitments=audit.get("commitments")
    if not isinstance(audit_commitments,Mapping):
        raise ValueError("run-independence commitments missing")
    if audit_commitments.get("raw_sha256")!=confirm_raw_sha:
        raise ValueError("run-independence RAW commitment mismatch")
    if audit_commitments.get("model_sha256")!=confirm_initial_sha:
        raise ValueError("run-independence model commitment mismatch")
    audit_policy=audit.get("policy")
    if not isinstance(audit_policy,Mapping) or audit_policy.get("crossfit_valid_under_run_dependence_audit") is not True:
        raise ValueError("confirmatory run-independence audit did not validate crossfit")
    audit_sha=audit.get("analysis_sha256")
    if not isinstance(audit_sha,str) or len(audit_sha)!=64:
        raise ValueError("run-independence analysis commitment missing")

    selected=[str(x) for x in discovery_result.get("accepted_layers") or []]
    beta_map=discovery_result.get("final_joint_coefficients") or {}
    if not selected:
        return {
            "schema":SCHEMA,
            "version":VERSION,
            "status":"NO_SELECTED_LAYERS_TO_CONFIRM",
            "confirmatory_dataset_id":confirmatory_declaration["dataset_id"],
            "confirmed_layers":[],
            "failed_layers":[],
            "promotion_allowed":False,
        }

    components={}
    policies={}
    for name in selected:
        if name not in confirm_nuisance_components:
            raise ValueError(f"missing confirmatory nuisance component {name}")
        c=np.asarray(confirm_nuisance_components[name],float)
        if c.shape!=raw.shape or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid confirmatory component {name}")
        components[name]=c

        meta=confirm_nuisance_metadata.get(name)
        if not isinstance(meta,Mapping):
            raise ValueError(f"missing confirmatory nuisance metadata {name}")
        policy=meta.get("null_policy")
        if policy not in _ALLOWED_NULL_POLICIES:
            raise ValueError(f"unsupported confirmatory null policy for {name}")
        if meta.get("independent_of_confirmatory_target_fit") is not True:
            raise ValueError(f"confirmatory nuisance {name} is target-derived")
        if meta.get("frozen_before_confirmatory_test") is not True:
            raise ValueError(f"confirmatory nuisance {name} was not frozen")
        policies[name]=str(policy)

        if name not in beta_map or not math.isfinite(float(beta_map[name])):
            raise ValueError(f"missing frozen discovery coefficient for {name}")

    betas={name:float(beta_map[name]) for name in selected}

    observed={}
    null_by={}
    for name in selected:
        base=np.array(initial,copy=True)
        for other in selected:
            if other!=name:
                base += betas[other]*components[other]
        sse_base=float(np.sum((raw-base)**2))
        if sse_base<=0.0:
            raise ValueError("degenerate confirmatory base SSE")

        full=base+betas[name]*components[name]
        sse_full=float(np.sum((raw-full)**2))
        observed[name]=1.0-sse_full/sse_base

        gains=[]
        for null in _null_proxies(components[name],policies[name],int(null_count)):
            pred=base+betas[name]*null
            sse_null=float(np.sum((raw-pred)**2))
            gains.append(1.0-sse_null/sse_base)
        null_by[name]=gains

    B=min(len(v) for v in null_by.values())
    family_max_null=np.asarray([
        max(null_by[name][b] for name in selected)
        for b in range(B)
    ],dtype=float)

    scores={}
    confirmed=[]; failed=[]
    for name in selected:
        obs=float(observed[name])
        p=float((1+np.sum(family_max_null>=obs))/(B+1))
        passed=bool(obs>0.0 and p<=confirmatory_alpha)
        scores[name]={
            "fixed_discovery_coefficient":betas[name],
            "confirmatory_gain":obs,
            "familywise_monte_carlo_p":p,
            "confirmatory_alpha":float(confirmatory_alpha),
            "null_policy":policies[name],
            "familywise_null_worlds":int(B),
            "decision":"CONFIRMED" if passed else "NOT_CONFIRMED",
        }
        (confirmed if passed else failed).append(name)

    all_confirmed=bool(selected) and not failed
    out={
        "schema":SCHEMA,
        "version":VERSION,
        "status":"SEALED_CONFIRMATION_PASS" if all_confirmed else "SEALED_CONFIRMATION_FAIL",
        "confirmatory_dataset_id":confirmatory_declaration["dataset_id"],
        "confirmatory_run_independence_analysis_sha256":audit_sha,
        "discovery_raw_sha256":discovery_raw_sha,
        "confirmatory_raw_sha256":confirm_raw_sha,
        "same_raw_reused":False,
        "coefficients_refit_on_confirmation":False,
        "selected_layers":selected,
        "confirmed_layers":confirmed,
        "failed_layers":failed,
        "scores":scores,
        "confirmatory_alpha":float(confirmatory_alpha),
        "familywise_null_worlds":int(B),
        "promotion_allowed":False,
        "policy":{
            "sealed_before_discovery_required":True,
            "independent_dataset_required":True,
            "v0_12_run_independence_receipt_required":True,
            "run_independence_receipt_must_bind_exact_raw_and_model":True,
            "fixed_discovery_coefficients_required":True,
            "no_confirmatory_refit":True,
            "familywise_max_null_required":True,
            "confirmation_is_not_causal_attribution":True,
            "confirmation_is_not_physical_promotion":True,
            "time_fluctuation_claim_allowed":False,
        },
    }
    out["confirmation_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","DISCOVERY_SCHEMA","RUN_INDEPENDENCE_SCHEMA","confirm_recursive_selection_v13"]
