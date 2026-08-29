#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, random, resource, statistics, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

SEED=616
ROLES=("SPIDER","RAVEN","HOUND","MOLE","OWL","ANT","MANTIS")
ROLE_WORK={"SPIDER":1200,"RAVEN":900,"HOUND":1000,"MOLE":1600,"OWL":1100,"ANT":800,"MANTIS":700}
BELZEBUB_WORK=1300
SURFACE=Path("/dev/shm/ciel_noema")
DOMAIN=b"GREMLIN-BESTIARY-LIVE/v0.1\0"

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()

def workload(count, seed):
    rng=random.Random(seed)
    out=[]
    for i in range(count):
        k=rng.choice((3,3,4,4,4,5))
        routed=tuple(sorted(rng.sample(ROLES,k)))
        payload=hashlib.blake2b(f"{seed}:{i}:{rng.getrandbits(128)}".encode(),digest_size=32).hexdigest()
        obj={"id":i,"payload":payload,"routed_roles":routed}
        obj["object_id"]=hashlib.blake2b(DOMAIN+canon(obj),digest_size=32).hexdigest()
        out.append(obj)
    return out

def burn(role, item):
    loops=ROLE_WORK[role]
    x=bytes.fromhex(item["payload"])
    salt=role.encode()
    for j in range(loops):
        x=hashlib.blake2b(x+salt+(j&255).to_bytes(1,"little"),digest_size=32).digest()
    return role, x.hex()

def synth(item, role_outputs):
    x=hashlib.blake2b(DOMAIN+item["object_id"].encode(),digest_size=32).digest()
    for role,digest in sorted(role_outputs.items()):
        x=hashlib.blake2b(x+role.encode()+bytes.fromhex(digest),digest_size=32).digest()
    for j in range(BELZEBUB_WORK):
        x=hashlib.blake2b(x+b"BELZEBUB"+(j&255).to_bytes(1,"little"),digest_size=32).digest()
    return x.hex()

def ru():
    s=resource.getrusage(resource.RUSAGE_SELF)
    c=resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"cpu_s":s.ru_utime+s.ru_stime+c.ru_utime+c.ru_stime,"maxrss_kib":max(s.ru_maxrss,c.ru_maxrss)}

def pctl(xs,p):
    ys=sorted(xs)
    if not ys: return 0.0
    idx=min(len(ys)-1,max(0,math.ceil(p*len(ys))-1))
    return ys[idx]

def metrics(start, finished, r0, r1, count, qdepth, workers):
    wall=time.perf_counter()-start
    lats=[t-start for t in finished]
    return {"wall_s":wall,"items_per_s":count/wall,"cpu_s":r1["cpu_s"]-r0["cpu_s"],"peak_rss_kib":max(r0["maxrss_kib"],r1["maxrss_kib"]),"p50_e2e_latency_ms":statistics.median(lats)*1000,"p95_e2e_latency_ms":pctl(lats,.95)*1000,"max_queue_depth":qdepth,"workers":workers}

def baseline_serial(items):
    r0=ru(); t0=time.perf_counter(); outputs={}; finished=[]
    for item in items:
        allout={role:burn(role,item)[1] for role in ROLES}
        routed={r:allout[r] for r in item["routed_roles"]}
        outputs[item["object_id"]]={"roles":routed,"synth":synth(item,routed)}
        finished.append(time.perf_counter())
    r1=ru()
    return outputs,metrics(t0,finished,r0,r1,len(items),1,1)

def _generalist_task(item):
    allout={role:burn(role,item)[1] for role in ROLES}
    routed={r:allout[r] for r in item["routed_roles"]}
    return {"object_id":item["object_id"],"roles":routed,"synth":synth(item,routed)}

def _bestiary_task(item):
    routed={role:burn(role,item)[1] for role in item["routed_roles"]}
    return {"object_id":item["object_id"],"roles":routed,"synth":synth(item,routed)}

def parallel(items, workers, fn):
    r0=ru(); t0=time.perf_counter(); outputs={}; finished=[]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures=[ex.submit(fn,item) for item in items]
        qdepth=len(futures)
        for fut in as_completed(futures):
            res=fut.result(); outputs[res["object_id"]]={"roles":res["roles"],"synth":res["synth"]}; finished.append(time.perf_counter())
    r1=ru()
    return outputs,metrics(t0,finished,r0,r1,len(items),qdepth,workers)

def integrity(items, *outputs):
    ids=[x["object_id"] for x in items]; uniq=len(set(ids)); drops=[len(set(ids)-set(o)) for o in outputs]; mismatch=0; ref=outputs[0]
    for oid in ids:
        if any(o.get(oid)!=ref.get(oid) for o in outputs[1:]): mismatch+=1
    return {"input_items":len(ids),"unique_input_ids":uniq,"duplicate_input_ids":len(ids)-uniq,"dropped_by_path":drops,"output_equivalence_mismatches":mismatch,"lineage_integrity":"PASS" if uniq==len(ids) and all(d==0 for d in drops) else "FAIL","output_equivalence":"PASS" if mismatch==0 else "FAIL"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--items",type=int,default=2000); ap.add_argument("--seed",type=int,default=SEED); ap.add_argument("--workers",type=int,default=max(1,min(5,os.cpu_count() or 1))); ap.add_argument("--surface",default=str(SURFACE)); a=ap.parse_args()
    root=Path(a.surface)
    if root != SURFACE or not root.is_dir(): raise SystemExit("live benchmark requires /dev/shm/ciel_noema")
    status=root/"ciel_binding_status"
    if not status.is_file() or status.read_text().strip()!="ACTIVE": raise SystemExit("NOEMA surface binding not ACTIVE")
    items=workload(a.items,a.seed); raw_bytes=b"\n".join(canon(x) for x in items)+b"\n"; raw_hash=hashlib.sha256(raw_bytes).hexdigest()
    benchdir=root/"gremlin"/"bestiary_live_v01"; benchdir.mkdir(parents=True,exist_ok=True); (benchdir/"frozen_raw.jsonl").write_bytes(raw_bytes)
    serial,sm=baseline_serial(items); matched,mm=parallel(items,a.workers,_generalist_task); zoo,zm=parallel(items,a.workers,_bestiary_task); integ=integrity(items,serial,matched,zoo)
    legacy_speed=zm["items_per_s"]/sm["items_per_s"]; matched_speed=zm["items_per_s"]/mm["items_per_s"]
    receipt={"schema":"GREMLIN_BESTIARY_LIVE_WALLCLOCK_V0_2","validation_scope":"LIVE_SAME_RUNTIME_GENERATION_CPU_REPLAY","surface":str(root),"items":a.items,"seed":a.seed,"workers":a.workers,"frozen_raw_sha256":raw_hash,"legacy_monolithic_serial":sm,"resource_matched_generalist":mm,"bestiary":zm,"speedup_vs_legacy_serial":legacy_speed,"speedup_vs_resource_matched_generalist":matched_speed,"candidate_threshold":10.0,"candidate":bool(legacy_speed>=10.0 and integ["lineage_integrity"]=="PASS" and integ["output_equivalence"]=="PASS"),"integrity":integ,"cpu_count_visible":os.cpu_count(),"note":"resource-matched comparison isolates routing/specialization from extra worker parallelism"}
    receipt["receipt_sha256"]=hashlib.sha256(canon(receipt)).hexdigest(); (benchdir/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n"); print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__": main()
