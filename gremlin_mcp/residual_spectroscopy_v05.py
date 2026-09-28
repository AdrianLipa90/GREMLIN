from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import numpy as np

from .residual_spectroscopy_v04 import analyze_residual_stack_v04

SCHEMA="GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_5"
VERSION="0.5.0"


def _phase_at_bin(runs:np.ndarray,k:int)->np.ndarray:
    phases=[]
    for row in runs:
        t=np.arange(row.size,dtype=float)
        y=row-np.polyval(np.polyfit(t,row,1),t)
        fft=np.fft.rfft(y-y.mean())
        kk=min(max(1,int(k)),len(fft)-1)
        phases.append(float(np.angle(fft[kk])))
    return np.asarray(phases,dtype=float)


def _fold_pairs(n_runs:int)->list[tuple[np.ndarray,np.ndarray]]:
    ids=np.arange(n_runs)
    out=[]
    for mask in (ids%2==0,ids<n_runs//2):
        a=ids[mask]; b=ids[~mask]
        if a.size>=2 and b.size>=2:
            out.extend([(a,b),(b,a)])
    return out


def _linear_run_phase_gate(
    phases:np.ndarray,
    *,
    holdout_coherence_threshold:float=0.70,
    pass_fraction_threshold:float=1.0,
    grid_size:int=721,
)->dict[str,Any]:
    ids=np.arange(len(phases),dtype=float)
    grid=np.linspace(-np.pi,np.pi,int(grid_size),dtype=float)
    directions=[]

    for train,holdout in _fold_pairs(len(phases)):
        train_matrix=np.exp(
            1j*(phases[train,None]-ids[train,None]*grid[None,:])
        )
        train_coherence=np.abs(train_matrix.mean(axis=0))
        best=int(np.argmax(train_coherence))
        slope=float(grid[best])
        holdout_coherence=float(abs(np.mean(
            np.exp(1j*(phases[holdout]-slope*ids[holdout]))
        )))
        directions.append({
            "best_run_phase_slope_rad_per_run":slope,
            "train_coherence":float(train_coherence[best]),
            "holdout_coherence":holdout_coherence,
            "pass":bool(holdout_coherence>=holdout_coherence_threshold),
        })

    pass_fraction=float(np.mean([d["pass"] for d in directions])) if directions else 0.0
    median_holdout=float(np.median(
        [d["holdout_coherence"] for d in directions]
    )) if directions else 0.0
    return {
        "directions":directions,
        "holdout_coherence_threshold":float(holdout_coherence_threshold),
        "pass_fraction_threshold":float(pass_fraction_threshold),
        "pass_fraction":pass_fraction,
        "median_holdout_coherence":median_holdout,
        "pass":bool(pass_fraction>=pass_fraction_threshold),
    }


def analyze_residual_stack_v05(
    raw_runs:Sequence[Sequence[float]],
    model_runs:Sequence[Sequence[float]],
    **kwargs:Any,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float)
    model=np.asarray(model_runs,float)
    base=analyze_residual_stack_v04(raw,model,**kwargs)

    residual=raw-model
    narrowband=base["classification"]=="UNRESOLVED_NARROWBAND_STRUCTURE_CANDIDATE"
    phase_gate=None
    classification=base["classification"]

    if narrowband:
        k=int(round(
            base["metrics"]["crossfit_narrowband_gate"]["median_discovery_bin"]
        ))
        phases=_phase_at_bin(residual,k)
        phase_gate=_linear_run_phase_gate(phases)
        if phase_gate["pass"]:
            classification="UNRESOLVED_RUN_PHASE_RELATIONAL_NARROWBAND_CANDIDATE"
        else:
            classification="UNRESOLVED_NARROWBAND_POWER_CANDIDATE_PHASE_UNRESOLVED"

    out={
        "schema":SCHEMA,
        "version":VERSION,
        "classification":classification,
        "base_v04_classification":base["classification"],
        "shape":base["shape"],
        "sample_spacing":base["sample_spacing"],
        "commitments":base["commitments"],
        "metrics":{
            **base["metrics"],
            "run_phase_relation_gate":phase_gate,
        },
        "policy":{
            **base["policy"],
            "narrowband_power_not_equal_phase_relation":True,
            "run_index_phase_relation_not_physical_time":True,
            "phase_relation_not_physical_mechanism":True,
        },
        "promotion_gates":[
            *base["promotion_gates"],
            "timestamp-aware phase-law validation before time interpretation",
        ],
    }
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","analyze_residual_stack_v05"]
