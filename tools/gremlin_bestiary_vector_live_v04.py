#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, os, random, resource, statistics, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tools.gremlin_bestiary_orbital_scheduler_v02 import bounded_batch_size
from tools.gremlin_bestiary_vector_species_v03 import build_species_plan, lane_width, dispatch_compression

SEED=616
ROLES=("SPIDER","RAVEN","HOUND","MOLE","OWL","ANT","MANTIS")
ROLE_WORK={"SPIDER":1200,"RAVEN":900,"HOUND":1000,"MOLE":1600,"OWL":1100,"ANT":800,"MANTIS":700}
BELZEBUB_WORK=1300
SURFACE=Path('/dev/shm/ciel_noema')
DOMAIN=b'GREMLIN-BESTIARY-LIVE/v0.1\0'

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode()

def workload(count, seed):
    rng=random.Random(seed); out=[]
    for i in range(count):
        k=rng.choice((3,3,4,4,4,5))
        routed=tuple(sorted(rng.sample(ROLES,k)))
        payload=hashlib.blake2b(f'{seed}:{i}:{rng.getrandbits(128)}'.encode(),digest_size=32).hexdigest()
        obj={'id':i,'payload':payload,'routed_roles':routed}
        obj['object_id']=hashlib.blake2b(DOMAIN+canon(obj),digest_size=32).hexdigest(); out.append(obj)
    return out

def burn(role,item):
    x=bytes.fromhex(item['payload']); salt=role.encode()
    for j in range(ROLE_WORK[role]):
        x=hashlib.blake2b(x+salt+(j&255).to_bytes(1,'little'),digest_size=32).digest()
    return role,x.hex()

def synth(item,role_outputs):
    x=hashlib.blake2b(DOMAIN+item['object_id'].encode(),digest_size=32).digest()
    for role,digest in sorted(role_outputs.items()):
        x=hashlib.blake2b(x+role.encode()+bytes.fromhex(digest),digest_size=32).digest()
    for j in range(BELZEBUB_WORK):
        x=hashlib.blake2b(x+b'BELZEBUB'+(j&255).to_bytes(1,'little'),digest_size=32).digest()
    return x.hex()

def ru():
    s=resource.getrusage(resource.RUSAGE_SELF); c=resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'cpu_s':s.ru_utime+s.ru_stime+c.ru_utime+c.ru_stime,'maxrss_kib':max(s.ru_maxrss,c.ru_maxrss)}

def pctl(xs,p):
    ys=sorted(xs)
    if not ys:return 0.0
    idx=min(len(ys)-1,max(0,math.ceil(p*len(ys))-1)); return ys[idx]

def metrics(t0,finished,r0,r1,count,qdepth,workers,extra=None):
    wall=time.perf_counter()-t0; lats=[t-t0 for t in finished]
    d={'wall_s':wall,'items_per_s':count/wall,'cpu_s':r1['cpu_s']-r0['cpu_s'],'peak_rss_kib':max(r0['maxrss_kib'],r1['maxrss_kib']),'p50_e2e_latency_ms':statistics.median(lats)*1000,'p95_e2e_latency_ms':pctl(lats,.95)*1000,'max_queue_depth':qdepth,'workers':workers}
    if extra:d.update(extra)
    return d

def baseline_serial(items):
    r0=ru(); t0=time.perf_counter(); outputs={}; finished=[]
    for item in items:
        allout={role:burn(role,item)[1] for role in ROLES}; routed={r:allout[r] for r in item['routed_roles']}
        outputs[item['object_id']]={'roles':routed,'synth':synth(item,routed)}; finished.append(time.perf_counter())
    return outputs,metrics(t0,finished,r0,ru(),len(items),1,1)

def _generalist_task(item):
    allout={role:burn(role,item)[1] for role in ROLES}; routed={r:allout[r] for r in item['routed_roles']}
    return item['object_id'],{'roles':routed,'synth':synth(item,routed)}

def _bestiary_task(item):
    routed={role:burn(role,item)[1] for role in item['routed_roles']}
    return item['object_id'],{'roles':routed,'synth':synth(item,routed)}

def parallel_items(items,workers,fn):
    r0=ru(); t0=time.perf_counter(); outputs={}; finished=[]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        fs=[ex.submit(fn,item) for item in items]; q=len(fs)
        for f in as_completed(fs):
            oid,val=f.result(); outputs[oid]=val; finished.append(time.perf_counter())
    return outputs,metrics(t0,finished,r0,ru(),len(items),q,workers)

def _item_batch(batch):
    return [_bestiary_task(item) for item in batch]

def orbital_item_batch(items,workers):
    counts={r:0 for r in ROLES}
    for item in items:
        for r in item['routed_roles']:counts[r]+=1
    chunk=bounded_batch_size(counts,len(items),workers)
    batches=[items[i:i+chunk] for i in range(0,len(items),chunk)]
    r0=ru(); t0=time.perf_counter(); outputs={}; finished=[]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        fs=[ex.submit(_item_batch,b) for b in batches]; q=len(fs)
        for f in as_completed(fs):
            now=time.perf_counter()
            for oid,val in f.result():outputs[oid]=val;finished.append(now)
    return outputs,metrics(t0,finished,r0,ru(),len(items),q,workers,{'item_batch_width':chunk,'item_batches':len(batches)})

def _role_batch(role,batch):
    return role,[(item['object_id'],burn(role,item)[1]) for item in batch]

def _synth_batch(batch):
    return [(item['object_id'],{'roles':roleout,'synth':synth(item,roleout)}) for item,roleout in batch]

def species_vector(items,workers,vector_width=8):
    by_role={r:[] for r in ROLES}
    for item in items:
        for r in item['routed_roles']:by_role[r].append(item)
    counts={r:len(v) for r,v in by_role.items()}
    plan=build_species_plan(counts,vector_width=vector_width)
    widths={p.species:p.lane_width for p in plan}
    role_batches=[]
    for r in ROLES:
        w=widths[r]
        role_batches.extend((r,by_role[r][i:i+w]) for i in range(0,len(by_role[r]),w))
    r0=ru(); t0=time.perf_counter(); role_outputs={i['object_id']:{} for i in items}; finished=[]
    synth_w=lane_width('BELZEBUB',vector_width=vector_width)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        fs=[ex.submit(_role_batch,r,b) for r,b in role_batches]
        maxq=len(fs)
        for f in as_completed(fs):
            role,vals=f.result()
            for oid,digest in vals:role_outputs[oid][role]=digest
        synth_input=[(item,role_outputs[item['object_id']]) for item in items]
        synth_batches=[synth_input[i:i+synth_w] for i in range(0,len(synth_input),synth_w)]
        sfs=[ex.submit(_synth_batch,b) for b in synth_batches]; maxq=max(maxq,len(sfs)); outputs={}
        for f in as_completed(sfs):
            now=time.perf_counter()
            for oid,val in f.result():outputs[oid]=val;finished.append(now)
    extra={'vector_width':vector_width,'species_dispatches':len(role_batches),'belzebub_lane_width':synth_w,'belzebub_batches':len(synth_batches),'dispatch_compression':dispatch_compression(plan),'species_plan':[p.__dict__ for p in plan]}
    return outputs,metrics(t0,finished,r0,ru(),len(items),maxq,workers,extra)

def integrity(items,*outputs):
    ids=[x['object_id'] for x in items]; uniq=len(set(ids)); drops=[len(set(ids)-set(o)) for o in outputs]; mismatch=0; ref=outputs[0]
    for oid in ids:
        if any(o.get(oid)!=ref.get(oid) for o in outputs[1:]):mismatch+=1
    return {'input_items':len(ids),'unique_input_ids':uniq,'duplicate_input_ids':len(ids)-uniq,'dropped_by_path':drops,'output_equivalence_mismatches':mismatch,'lineage_integrity':'PASS' if uniq==len(ids) and all(d==0 for d in drops) else 'FAIL','output_equivalence':'PASS' if mismatch==0 else 'FAIL'}

def main():
    count=2000; workers=max(1,min(5,os.cpu_count() or 1)); items=workload(count,SEED)
    raw=b'\n'.join(canon(x) for x in items)+b'\n'; raw_hash=hashlib.sha256(raw).hexdigest()
    if not SURFACE.is_dir() or not (SURFACE/'ciel_binding_status').is_file() or (SURFACE/'ciel_binding_status').read_text().strip()!='ACTIVE':raise SystemExit('NOEMA surface not ACTIVE')
    outdir=SURFACE/'gremlin'/'bestiary_vector_v03';outdir.mkdir(parents=True,exist_ok=True);(outdir/'frozen_raw.jsonl').write_bytes(raw)
    serial,sm=baseline_serial(items); general,gm=parallel_items(items,workers,_generalist_task); old,om=parallel_items(items,workers,_bestiary_task); orbital,xm=orbital_item_batch(items,workers); vector,vm=species_vector(items,workers,8)
    integ=integrity(items,serial,general,old,orbital,vector)
    receipt={'schema':'GREMLIN_BESTIARY_VECTOR_LIVE_V0_4','validation_scope':'LIVE_SAME_RUNTIME_GENERATION_CPU_REPLAY','surface':str(SURFACE),'items':count,'seed':SEED,'workers':workers,'frozen_raw_sha256':raw_hash,'legacy_serial':sm,'resource_matched_generalist':gm,'bestiary_individual':om,'bestiary_orbital_item_batch':xm,'bestiary_species_vector':vm,'speedup_vector_vs_legacy':vm['items_per_s']/sm['items_per_s'],'speedup_vector_vs_generalist':vm['items_per_s']/gm['items_per_s'],'speedup_vector_vs_old_bestiary':vm['items_per_s']/om['items_per_s'],'speedup_vector_vs_orbital_item_batch':vm['items_per_s']/xm['items_per_s'],'candidate_threshold':10.0,'candidate':bool(vm['items_per_s']/sm['items_per_s']>=10 and integ['lineage_integrity']=='PASS' and integ['output_equivalence']=='PASS'),'integrity':integ,'cpu_count_visible':os.cpu_count()}
    receipt['receipt_sha256']=hashlib.sha256(canon(receipt)).hexdigest();(outdir/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=='__main__':main()
