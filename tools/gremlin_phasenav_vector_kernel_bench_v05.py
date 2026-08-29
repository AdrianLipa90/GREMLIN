#!/usr/bin/env python3
from __future__ import annotations
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
os.environ.setdefault("OMP_NUM_THREADS","1")
os.environ.setdefault("MKL_NUM_THREADS","1")
os.environ.setdefault("NUMEXPR_NUM_THREADS","1")
import hashlib, json, math, statistics, time
from pathlib import Path
import numpy as np

SCHEMA="GREMLIN_PHASENAV_VECTOR_KERNEL_BENCH_V0_5"
OPERATOR="KCHI_TORUS_CHARACTER_FIELD"
SURFACE=Path('/dev/shm/ciel_noema')
SEED=616
DIM=36
TERMS=64
ITEMS=10000
TOL=1e-12

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':')).encode()

def make_case():
    rng=np.random.default_rng(SEED)
    theta=rng.uniform(-math.pi,math.pi,size=(ITEMS,DIM)).astype(np.float64)
    ell=rng.integers(-3,4,size=(TERMS,DIM),dtype=np.int64)
    for i in range(TERMS):
        if not np.any(ell[i]): ell[i,0]=1
    tau=rng.uniform(-math.pi,math.pi,size=TERMS).astype(np.float64)
    gain=rng.uniform(0.1,2.0,size=TERMS).astype(np.float64)
    case_hash=hashlib.sha256(theta.tobytes()+ell.tobytes()+tau.tobytes()+gain.tobytes()).hexdigest()
    return theta,ell,tau,gain,case_hash

def scalar_one(theta,ell,tau,gain):
    force=[0.0]*DIM; potential=0.0
    for q in range(TERMS):
        eps=math.fsum(int(ell[q,j])*float(theta[j]) for j in range(DIM))-float(tau[q])
        g=float(gain[q]); potential += -g*math.cos(eps); s=g*math.sin(eps)
        for j,c in enumerate(ell[q]):
            if c: force[j] += -int(c)*s
    return potential,tuple(force)

def scalar_batch(theta,ell,tau,gain):
    return [scalar_one(row,ell,tau,gain) for row in theta]

def vector_batch(theta,ell,tau,gain):
    eps=theta@ell.T-tau
    potential=-np.cos(eps)@gain
    force=-(np.sin(eps)*gain)@ell
    return potential,force

def main():
    if not SURFACE.is_dir() or not (SURFACE/'ciel_binding_status').is_file() or (SURFACE/'ciel_binding_status').read_text().strip()!='ACTIVE': raise SystemExit('NOEMA surface not ACTIVE')
    theta,ell,tau,gain,case_hash=make_case()
    scalar_one(theta[0],ell,tau,gain); vector_batch(theta[:8],ell,tau,gain)
    scalar_times=[]; scalar_ref=None
    for _ in range(3):
        t=time.perf_counter(); out=scalar_batch(theta,ell,tau,gain); scalar_times.append(time.perf_counter()-t)
        if scalar_ref is None: scalar_ref=out
    vector_times=[]; vp=vf=None
    for _ in range(7):
        t=time.perf_counter(); p,f=vector_batch(theta,ell,tau,gain); vector_times.append(time.perf_counter()-t)
        if vp is None: vp,vf=p,f
    max_p=max(abs(scalar_ref[i][0]-float(vp[i])) for i in range(ITEMS))
    max_f=max(abs(scalar_ref[i][1][j]-float(vf[i,j])) for i in range(ITEMS) for j in range(DIM))
    scalar_median=statistics.median(scalar_times); vector_median=statistics.median(vector_times); speed=scalar_median/vector_median
    receipt={
      'schema':SCHEMA,'validation_scope':'LIVE_NOEMA_SINGLE_THREAD_NUMERIC_KERNEL','operator':OPERATOR,
      'surface':str(SURFACE),'seed':SEED,'dimension':DIM,'terms':TERMS,'items':ITEMS,
      'case_sha256':case_hash,'tolerance':TOL,'scalar_times_s':scalar_times,'vector_times_s':vector_times,
      'scalar_median_s':scalar_median,'vector_median_s':vector_median,'kernel_speedup':speed,
      'max_potential_abs_error':max_p,'max_force_abs_error':max_f,
      'numerical_equivalence':'PASS' if max(max_p,max_f)<=TOL else 'FAIL',
      'kernel_candidate_threshold':10.0,
      'kernel_candidate':bool(speed>=10.0 and max(max_p,max_f)<=TOL),
      'thread_budget':'NUMPY_BLAS_SINGLE_THREAD',
      'overall_bestiary_promotion':False,
      'note':'Kernel-level result only; end-to-end Bestiary >=10x requires integration replay.'}
    receipt['receipt_sha256']=hashlib.sha256(canon(receipt)).hexdigest()
    outdir=SURFACE/'gremlin'/'bestiary_vector_kernel_v05'; outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=='__main__': main()
