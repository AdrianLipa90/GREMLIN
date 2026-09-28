from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v12 import _sha_array
from .residual_spectroscopy_v19 import analyze_residual_stack_v19

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_20"
VERSION="0.20.0"


def _safe_corr(a:np.ndarray,b:np.ndarray)->float:
    aa=np.asarray(a,float)-float(np.mean(a))
    bb=np.asarray(b,float)-float(np.mean(b))
    den=float(np.linalg.norm(aa)*np.linalg.norm(bb))
    return 0.0 if den==0.0 else float(np.dot(aa,bb)/den)


def _block_profiles(runs:np.ndarray,blocks:int)->tuple[np.ndarray,np.ndarray]:
    x=np.asarray(runs,float)
    if blocks<4 or x.shape[1]//blocks<8:
        raise ValueError("v0.20 requires >=8 samples per profile block")
    edges=np.linspace(0,x.shape[1],blocks+1,dtype=int)
    scale_profiles=[]
    location_profiles=[]
    for row in x:
        global_median=float(np.median(row))
        global_scale=max(
            1.4826*float(np.median(np.abs(row-global_median))),
            1e-12,
        )
        scales=[]
        locations=[]
        for left,right in zip(edges[:-1],edges[1:]):
            segment=row[left:right]
            median=float(np.median(segment))
            mad=max(
                1.4826*float(np.median(np.abs(segment-median))),
                1e-12,
            )
            scales.append(np.log(mad/global_scale))
            locations.append((median-global_median)/global_scale)
        scale_profiles.append(scales)
        location_profiles.append(locations)
    return np.asarray(scale_profiles),np.asarray(location_profiles)


def _shared_profile_stat(runs:np.ndarray,blocks:int)->tuple[float,str,dict[str,float]]:
    scale,location=_block_profiles(runs,blocks)
    scale_corr=[]
    location_corr=[]
    for i in range(len(scale)):
        for j in range(i+1,len(scale)):
            scale_corr.append(_safe_corr(scale[i],scale[j]))
            location_corr.append(_safe_corr(location[i],location[j]))

    median_scale=float(np.median(scale_corr))
    median_location=float(np.median(location_corr))
    scale_consensus=np.median(scale,axis=0)
    location_consensus=np.median(location,axis=0)
    scale_ratio=float(np.exp(np.max(scale_consensus)-np.min(scale_consensus)))
    location_span=float(np.max(location_consensus)-np.min(location_consensus))

    if median_scale>=median_location:
        statistic=median_scale
        kind="scale"
    else:
        statistic=median_location
        kind="location"

    return statistic,kind,{
        "median_pair_scale_profile_correlation":median_scale,
        "median_pair_location_profile_correlation":median_location,
        "consensus_scale_peak_to_trough_ratio":scale_ratio,
        "consensus_standardized_location_span":location_span,
    }


def shared_sample_index_confound_audit_v20(
    residual_runs:Sequence[Sequence[float]],
    *,
    blocks:int=8,
    null_count:int=199,
    alpha:float=0.005,
)->dict[str,Any]:
    residual=np.asarray(residual_runs,float)
    if residual.ndim!=2 or residual.shape[0]<8 or residual.shape[1]<64:
        raise ValueError("v0.20 shared-profile audit requires [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(residual)):
        raise ValueError("residual must be finite")
    if not (0.0<alpha<1.0):
        raise ValueError("alpha must be in (0,1)")
    if null_count<1 or 1.0/(null_count+1)>alpha:
        raise ValueError("null_count cannot resolve shared-profile alpha")

    observed,kind,details=_shared_profile_stat(residual,int(blocks))
    seed=int(_sha_array(residual)[:16],16) ^ 0x20A20
    rng=np.random.default_rng(seed)
    null=[]
    for _ in range(int(null_count)):
        shifted=np.asarray([
            np.roll(row,int(rng.integers(1,row.size)))
            for row in residual
        ])
        stat,_,_=_shared_profile_stat(shifted,int(blocks))
        null.append(stat)

    null=np.asarray(null,float)
    p=float((1+np.sum(null>=observed))/(len(null)+1))
    return {
        "status":"CALIBRATED_SHARED_SAMPLE_INDEX_SHIFT_NULL",
        "observed_shared_profile_statistic":float(observed),
        "dominant_profile_kind":kind,
        **details,
        "monte_carlo_p":p,
        "alpha":float(alpha),
        "shared_sample_index_confound":bool(p<=alpha),
        "profile_blocks":int(blocks),
        "null_ensemble_size":int(len(null)),
        "null_kind":"INDEPENDENT_CONTENT_ADDRESSED_CIRCULAR_SHIFT_PER_RUN",
        "q95_null":float(np.quantile(null,0.95)),
        "q99_null":float(np.quantile(null,0.99)),
        "seed_content_addressed":True,
        "claim_boundary":{
            "confound_is_stochastic_run_dependence":False,
            "confound_identifies_physical_cause":False,
            "pass_proves_stationarity":False,
        },
    }


def analyze_residual_stack_v20(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    sample_index_confound_alpha:float=0.005,
    sample_index_confound_null_count:int=199,
    sample_index_profile_blocks:int=8,
    **kwargs:Any,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    if raw.shape!=model.shape or raw.ndim!=2:
        raise ValueError("raw/model must be equal-shape 2D arrays")
    residual=raw-model

    confound=shared_sample_index_confound_audit_v20(
        residual,
        blocks=sample_index_profile_blocks,
        null_count=sample_index_confound_null_count,
        alpha=sample_index_confound_alpha,
    )

    if confound["shared_sample_index_confound"]:
        base=None
        classification="RAW_SHARED_SAMPLE_INDEX_CONFOUND_REQUIRES_MODELING"
        crossfit_valid=False
    else:
        base=analyze_residual_stack_v19(raw,model,**kwargs)
        classification=base["classification"]
        crossfit_valid=bool(
            base.get("policy",{}).get("crossfit_valid_after_v19",False)
        )

    out={} if base is None else dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=classification
    out["shape"]=list(raw.shape)
    out["commitments"]={
        "raw_sha256":_sha_array(raw),
        "model_sha256":_sha_array(model),
        "residual_sha256":_sha_array(residual),
    }
    out["metrics"]=dict(out.get("metrics",{}))
    out["metrics"]["shared_sample_index_confound_audit_v20"]=confound
    out["policy"]=dict(out.get("policy",{}))
    out["policy"].update({
        "shared_sample_index_audit_precedes_run_dependence_inference":True,
        "shared_profile_confound_is_not_unique_causal_attribution":True,
        "common_window_gain_or_drift_must_be_modeled_not_called_noise":True,
        "postprocessing_may_create_or_destroy_apparent_dependence":True,
        "crossfit_valid_after_v20":bool(crossfit_valid),
        "new_physics_from_residual_only":False,
        "time_fluctuation_claim_allowed":False,
    })
    out["promotion_gates"]=[
        "shared sample-index scale/location profile shift-null audit",
        *out.get("promotion_gates",[]),
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=[
    "SCHEMA",
    "VERSION",
    "shared_sample_index_confound_audit_v20",
    "analyze_residual_stack_v20",
]
