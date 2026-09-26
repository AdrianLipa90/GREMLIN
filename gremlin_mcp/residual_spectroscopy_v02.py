from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

SCHEMA = "GREMLIN_RESIDUAL_PRESERVING_SPECTROSCOPY_V0_2"
VERSION = "0.2.0"

def _sha_array(x: np.ndarray) -> str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64)); h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes()); return h.hexdigest()

def _safe_corr(a: np.ndarray,b: np.ndarray) -> float:
    a=np.asarray(a,float); b=np.asarray(b,float)
    if a.shape!=b.shape: raise ValueError("correlation inputs must have equal shape")
    aa=a-a.mean(); bb=b-b.mean(); den=float(np.linalg.norm(aa)*np.linalg.norm(bb))
    return 0.0 if den==0.0 else float(np.dot(aa,bb)/den)

def _linear_drift_r2(x: np.ndarray) -> tuple[float,float]:
    x=np.asarray(x,float); t=np.arange(x.size,dtype=float); tc=t-t.mean(); xc=x-x.mean(); den=float(np.dot(tc,tc))
    slope=0.0 if den==0.0 else float(np.dot(tc,xc)/den); pred=slope*tc; ss=float(np.dot(xc,xc))
    r2=0.0 if ss==0.0 else max(0.0,min(1.0,float(np.dot(pred,pred)/ss)))
    scale=float(np.std(x)); norm=0.0 if scale==0.0 else slope*x.size/scale
    return norm,r2

def _block_mean_scaling(x: np.ndarray) -> float|None:
    x=np.asarray(x,float); n=x.size; xs=[]; ys=[]; m=1
    while m<=n//16:
        k=n//m
        if k<8: break
        blocks=x[:k*m].reshape(k,m).mean(axis=1); s=float(np.std(blocks,ddof=1)) if k>1 else 0.0
        if s>0.0: xs.append(math.log(m)); ys.append(math.log(s))
        m*=2
    return None if len(xs)<2 else float(np.polyfit(xs,ys,1)[0])

def _analysis_spectrum(x: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    t=np.arange(x.size,dtype=float); coef=np.polyfit(t,x,1); y=x-np.polyval(coef,t); y-=y.mean()
    fft=np.fft.rfft(y); p=np.abs(fft)**2
    if p.size>1: p[0]=0.0
    total=float(p.sum()); q=np.zeros_like(p) if total==0.0 else p/total
    return fft,q

def _run_features(x: np.ndarray) -> dict[str,Any]:
    x=np.asarray(x,float)
    if x.ndim!=1 or x.size<64 or not np.all(np.isfinite(x)): raise ValueError("each residual run must be finite 1D with >=64 samples")
    xc=x-x.mean(); lag1=_safe_corr(xc[:-1],xc[1:]); slope,r2=_linear_drift_r2(x); fft,q=_analysis_spectrum(x)
    k=int(np.argmax(q)); peak=float(q[k]) if q.size else 0.0; med=float(np.median(q[1:])) if q.size>1 else 0.0
    sd=float(np.std(x,ddof=1)); mean_z=0.0 if sd==0.0 else abs(float(x.mean()))/(sd/math.sqrt(x.size))
    return {"mean":float(x.mean()),"std":sd,"mean_offset_z":mean_z,"lag1":lag1,"drift_normalized_slope":slope,"drift_r2":r2,"block_mean_log_slope":_block_mean_scaling(x),"peak_bin":k,"peak_fraction":peak,"peak_to_median_ratio":0.0 if med==0.0 else peak/med,"fft":fft,"norm_psd":q}

def _channel_coherence(residual: np.ndarray,channel: np.ndarray,bin_index: int)->float:
    if bin_index<=0: return 0.0
    rf=[]; cf=[]
    for r,c in zip(residual,channel):
        rr,_=_analysis_spectrum(r); cc,_=_analysis_spectrum(c)
        if bin_index>=len(rr) or bin_index>=len(cc): return 0.0
        rf.append(rr[bin_index]); cf.append(cc[bin_index])
    r=np.asarray(rf,complex); c=np.asarray(cf,complex); den=float(np.sqrt(np.sum(abs(r)**2)*np.sum(abs(c)**2)))
    return 0.0 if den==0.0 else float(abs(np.sum(r*np.conj(c)))/den)

def analyze_residual_stack(raw_runs: Sequence[Sequence[float]],model_runs: Sequence[Sequence[float]],*,nuisance_runs: Sequence[Sequence[float]]|None=None,known_template_runs: Sequence[Sequence[float]]|None=None,channel_runs: Mapping[str,Sequence[Sequence[float]]]|None=None,sample_spacing: float=1.0)->dict[str,Any]:
    raw=np.asarray(raw_runs,float); model=np.asarray(model_runs,float)
    if raw.shape!=model.shape or raw.ndim!=2 or raw.shape[0]<2 or raw.shape[1]<64: raise ValueError("raw/model must be equal-shape 2D arrays with >=2 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(model)): raise ValueError("raw/model must be finite")
    if not math.isfinite(sample_spacing) or sample_spacing<=0: raise ValueError("sample_spacing must be positive finite")
    residual=raw-model; feats=[_run_features(r) for r in residual]
    psd=np.stack([f["norm_psd"] for f in feats]); stacked=np.median(psd,axis=0); consensus=int(np.argmax(stacked))
    med_floor=float(np.median(stacked[1:])) if stacked.size>1 else 0.0
    stacked_ratio=0.0 if med_floor==0.0 else float(stacked[consensus]/med_floor)
    support=float(np.mean([f["norm_psd"][consensus]>6.0*np.median(f["norm_psd"][1:]) for f in feats])) if consensus>0 else 0.0
    phases=np.array([np.angle(f["fft"][consensus]) for f in feats]) if consensus>0 else np.zeros(len(feats))
    phase_coh=float(abs(np.mean(np.exp(1j*phases)))) if consensus>0 else 0.0
    freq=consensus/(raw.shape[1]*sample_spacing)
    lag1=float(np.median([abs(f["lag1"]) for f in feats])); drift_r2=float(np.median([f["drift_r2"] for f in feats])); drift_slope=float(np.median([abs(f["drift_normalized_slope"]) for f in feats])); mean_z=float(np.median([f["mean_offset_z"] for f in feats])); peak_fraction=float(stacked[consensus]) if stacked.size else 0.0
    ss=[f["block_mean_log_slope"] for f in feats if f["block_mean_log_slope"] is not None]; scale_slope=float(np.median(ss)) if ss else None
    nuisance_corr=0.0
    if nuisance_runs is not None:
        n=np.asarray(nuisance_runs,float)
        if n.shape!=raw.shape: raise ValueError("nuisance_runs must match raw shape")
        nuisance_corr=float(np.median([abs(_safe_corr(residual[i],n[i])) for i in range(raw.shape[0])]))
    known_corr=0.0
    if known_template_runs is not None:
        k=np.asarray(known_template_runs,float)
        if k.shape!=raw.shape: raise ValueError("known_template_runs must match raw shape")
        known_corr=float(np.median([abs(_safe_corr(residual[i],k[i])) for i in range(raw.shape[0])]))
    channel_coh={}
    if channel_runs:
        for name,vals in channel_runs.items():
            c=np.asarray(vals,float)
            if c.shape!=raw.shape: raise ValueError(f"channel {name} must match raw shape")
            channel_coh[str(name)]=_channel_coherence(residual,c,consensus)
    if known_corr>=0.75: cls="KNOWN_MODEL_STRUCTURE_CANDIDATE"
    elif nuisance_corr>=0.70: cls="SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE"
    elif drift_r2>=0.70 and drift_slope>=1.0: cls="SYSTEMATIC_DRIFT_CANDIDATE"
    elif mean_z>=5.0 and stacked_ratio<10.0: cls="PERSISTENT_OFFSET_CANDIDATE"
    elif stacked_ratio>=12.0 and support>=0.50: cls="UNRESOLVED_STRUCTURED_CANDIDATE"
    elif lag1<=0.20 and stacked_ratio<=6.0 and mean_z<4.0 and drift_r2<0.5: cls="STOCHASTIC_BACKGROUND_COMPATIBLE"
    else: cls="UNRESOLVED_RESIDUAL"
    out={"schema":SCHEMA,"version":VERSION,"classification":cls,"shape":list(raw.shape),"sample_spacing":float(sample_spacing),"commitments":{"raw_sha256":_sha_array(raw),"model_sha256":_sha_array(model),"residual_sha256":_sha_array(residual)},"metrics":{"consensus_peak_bin":consensus,"consensus_frequency":freq,"stacked_peak_to_median_ratio":stacked_ratio,"individual_run_support_fraction":support,"cross_run_phase_coherence":phase_coh,"stacked_peak_power_fraction":peak_fraction,"median_abs_lag1":lag1,"median_mean_offset_z":mean_z,"median_drift_r2":drift_r2,"median_abs_normalized_drift_slope":drift_slope,"median_block_mean_log_slope":scale_slope,"median_abs_nuisance_correlation":nuisance_corr,"median_abs_known_template_correlation":known_corr,"cross_channel_coherence":channel_coh},"per_run":[{k:v for k,v in f.items() if k not in ("fft","norm_psd")} for f in feats],"policy":{"raw_preserved":True,"residual_preserved":True,"analysis_copy_allowed":True,"destructive_denoising":False,"interpretation_last":True,"new_physics_from_residual_only":False,"time_fluctuation_claim_allowed":False},"promotion_gates":["independent-run persistence","cross-channel coherence","instrument/environment/clock controls","sampling/jitter/alias controls","known-physics template controls","independent replication before physical interpretation"]}
    out["analysis_sha256"]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest(); return out

__all__=["SCHEMA","VERSION","analyze_residual_stack"]
