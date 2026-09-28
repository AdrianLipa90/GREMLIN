from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v04 import analyze_residual_stack_v04

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_5"
VERSION="0.5.0"


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _continuous_fourier_phase(x:np.ndarray,k:float)->complex:
    x=np.asarray(x,float)
    t=np.arange(x.size,dtype=float)
    coef=np.polyfit(t,x,1)
    y=x-np.polyval(coef,t)
    y-=y.mean()
    w=np.exp(-2j*np.pi*float(k)*t/x.size)
    z=complex(np.dot(y,w))
    return 0j if abs(z)==0.0 else z/abs(z)


def _phase_trajectory_audit(
    residual:np.ndarray,
    k:float,
    *,
    ordered_runs:bool,
    null_count:int=255,
)->dict[str,Any]:
    z=np.asarray([_continuous_fourier_phase(row,k) for row in residual],complex)
    level=float(abs(np.mean(z))) if len(z) else 0.0

    if len(z)<3 or not ordered_runs:
        return {
            "ordered_runs":bool(ordered_runs),
            "phase_level_coherence":level,
            "phase_increment_coherence":None,
            "phase_increment_mean_angle":None,
            "permutation_null_q99":None,
            "monte_carlo_p":None,
            "trajectory_ordered":False,
            "null_ensemble_size":0,
        }

    increments=z[1:]*np.conj(z[:-1])
    observed=float(abs(np.mean(increments)))
    mean_angle=float(np.angle(np.mean(increments)))

    seed=int(_sha_array(np.column_stack((residual.mean(axis=1),residual.std(axis=1))))[:16],16)
    rng=np.random.default_rng(seed)
    null=[]
    identity=np.arange(len(z))
    seen=set()
    attempts=0
    target=min(int(null_count), math.factorial(len(z))-1)
    while len(null)<target:
        attempts+=1
        if attempts>target*100+1000:
            raise RuntimeError("could not build unique phase-order permutation null")
        perm=tuple(int(v) for v in rng.permutation(len(z)))
        if perm==tuple(identity) or perm in seen:
            continue
        seen.add(perm)
        zp=z[np.asarray(perm,int)]
        inc=zp[1:]*np.conj(zp[:-1])
        null.append(float(abs(np.mean(inc))))

    null_arr=np.asarray(null,float)
    q99=float(np.quantile(null_arr,0.99)) if null else 1.0
    p=float((1+np.sum(null_arr>=observed))/(len(null_arr)+1)) if null else 1.0
    ordered=bool(observed>q99 and p<=0.01)
    return {
        "ordered_runs":True,
        "phase_level_coherence":level,
        "phase_increment_coherence":observed,
        "phase_increment_mean_angle":mean_angle,
        "permutation_null_q99":q99,
        "monte_carlo_p":p,
        "trajectory_ordered":ordered,
        "null_ensemble_size":len(null),
    }


def analyze_residual_stack_v05(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    *,
    nuisance_runs:Sequence[Sequence[float]]|None=None,
    known_template_runs:Sequence[Sequence[float]]|None=None,
    channel_runs:dict[str,Sequence[Sequence[float]]]|None=None,
    sample_spacing:float=1.0,
    ordered_runs:bool=False,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float); model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v04(
        raw,model,
        nuisance_runs=nuisance_runs,
        known_template_runs=known_template_runs,
        channel_runs=channel_runs,
        sample_spacing=sample_spacing,
    )
    residual=raw-model

    gate=base["metrics"]["crossfit_narrowband_gate"]
    k=float(gate["median_discovery_bin"])
    phase=_phase_trajectory_audit(residual,k,ordered_runs=ordered_runs)

    cls=base["classification"]
    if cls=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE":
        if not ordered_runs:
            cls="UNRESOLVED_NARROWBAND_PHASE_UNTYPED_CANDIDATE"
        elif phase["trajectory_ordered"]:
            cls="UNRESOLVED_NARROWBAND_PHASE_ORDERED_CANDIDATE"
        else:
            cls="UNRESOLVED_NARROWBAND_PHASE_UNORDERED_CANDIDATE"

    out=dict(base)
    out["schema"]=SCHEMA
    out["version"]=VERSION
    out["classification"]=cls
    out["legacy_v04_classification"]=base["classification"]
    out["metrics"]=dict(base["metrics"])
    out["metrics"]["phase_trajectory_audit"]=phase
    out["policy"]=dict(base["policy"])
    out["policy"].update({
        "phase_ordering_is_diagnostic_not_physical_attribution":True,
        "phase_unordered_does_not_mean_nonphysical":True,
        "phase_ordered_does_not_mean_new_physics":True,
        "run_order_required_for_trajectory_claim":True,
    })
    out["promotion_gates"]=list(base["promotion_gates"])+[
        "phase trajectory must remain a diagnostic subclass only",
        "ordered-run provenance required before phase-trajectory interpretation",
    ]
    out.pop("analysis_sha256",None)
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v05"]
