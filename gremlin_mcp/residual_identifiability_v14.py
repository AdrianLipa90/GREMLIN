from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

SCHEMA="GREMLIN_BASELINE_EXTENSION_IDENTIFIABILITY_V0_14"
VERSION="0.14.0"


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _segment_phase_coherence(
    runs:np.ndarray,
    frequency_cycles_per_sample:float,
    segments:int,
)->float:
    n=runs.shape[1]
    edges=np.linspace(0,n,int(segments)+1,dtype=int)
    per_run=[]
    for row in runs:
        phasors=[]
        for a,b in zip(edges[:-1],edges[1:]):
            if b-a<8:
                raise ValueError("segment too short for phase audit")
            t=np.arange(a,b,dtype=float)
            y=np.asarray(row[a:b],float)
            y=y-float(np.mean(y))
            z=np.sum(y*np.exp(-2j*np.pi*frequency_cycles_per_sample*t))
            phasors.append(0j if abs(z)==0.0 else z/abs(z))
        per_run.append(abs(np.mean(np.asarray(phasors,complex))))
    return float(np.median(per_run))


def baseline_extension_identifiability_v14(
    baseline_runs:Mapping[str,Sequence[Sequence[float]]],
    *,
    frequency_cycles_per_sample:float,
    segment_counts:Sequence[int]=(4,8,16),
    min_endpoint_change:float=0.05,
)->dict[str,Any]:
    if not (0.0<frequency_cycles_per_sample<0.5):
        raise ValueError("frequency_cycles_per_sample must be in (0,0.5)")
    if not math.isfinite(min_endpoint_change) or min_endpoint_change<0.0:
        raise ValueError("min_endpoint_change must be finite and nonnegative")
    if not isinstance(baseline_runs,Mapping) or not baseline_runs:
        raise ValueError("baseline_runs must be a nonempty mapping")

    datasets=[]
    for label,values in baseline_runs.items():
        x=np.asarray(values,float)
        if x.ndim!=2 or x.shape[0]<8 or x.shape[1]<64 or not np.all(np.isfinite(x)):
            raise ValueError(f"invalid baseline dataset {label}")
        datasets.append((str(label),x.shape[1],x))

    datasets.sort(key=lambda item:item[1])
    lengths=[n for _,n,_ in datasets]
    if len(set(lengths))!=len(lengths):
        raise ValueError("baseline sample lengths must be unique")

    segs=tuple(sorted(set(int(s) for s in segment_counts)))
    if not segs or any(s<2 for s in segs):
        raise ValueError("segment_counts must contain integers >=2")

    table={}
    commitments={}
    for label,n,x in datasets:
        commitments[label]=_sha_array(x)
        table[label]={
            "samples":int(n),
            "coherence":{
                str(s):_segment_phase_coherence(x,frequency_cycles_per_sample,s)
                for s in segs
            },
        }

    if len(datasets)<3:
        status="INSUFFICIENT_BASELINE_EXTENSION"
        deltas={str(s):None for s in segs}
        slopes={str(s):None for s in segs}
        consistent=False
    else:
        logn=np.log(np.asarray(lengths,float))
        deltas={}
        slopes={}
        signs=[]
        for s in segs:
            vals=np.asarray([table[label]["coherence"][str(s)] for label,_,_ in datasets],float)
            delta=float(vals[-1]-vals[0])
            slope=float(np.polyfit(logn,vals,1)[0])
            deltas[str(s)]=delta
            slopes[str(s)]=slope
            if delta>=min_endpoint_change and slope>0.0:
                signs.append(1)
            elif delta<=-min_endpoint_change and slope<0.0:
                signs.append(-1)
            else:
                signs.append(0)

        if all(v==1 for v in signs):
            status="COHERENCE_STRENGTHENS_WITH_BASELINE_CANDIDATE"
            consistent=True
        elif all(v==-1 for v in signs):
            status="COHERENCE_DECAYS_WITH_BASELINE_CANDIDATE"
            consistent=True
        else:
            status="BASELINE_EXTENSION_AMBIGUOUS"
            consistent=False

    out={
        "schema":SCHEMA,
        "version":VERSION,
        "status":status,
        "frequency_cycles_per_sample":float(frequency_cycles_per_sample),
        "frequency_was_frozen_before_baseline_audit":True,
        "baseline_order":[label for label,_,_ in datasets],
        "sample_lengths":lengths,
        "segment_counts":list(segs),
        "coherence_table":table,
        "endpoint_changes":deltas,
        "log_length_slopes":slopes,
        "segment_trend_consistent":bool(consistent),
        "commitments":commitments,
        "policy":{
            "absolute_coherence_threshold_is_authoritative":False,
            "single_window_deterministic_line_claim_allowed":False,
            "high_q_stochastic_resonance_remains_possible":True,
            "baseline_strengthening_proves_deterministic_line":False,
            "baseline_decay_proves_stochastic_origin":False,
            "independent_physical_replication_still_required":True,
            "new_physics_established":False,
            "time_fluctuation_claim_allowed":False,
        },
    }
    out["analysis_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out


__all__=["SCHEMA","VERSION","baseline_extension_identifiability_v14"]
