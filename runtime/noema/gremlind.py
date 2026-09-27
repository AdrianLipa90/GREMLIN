#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, select, signal, socket, sys, threading, time, unicodedata
from pathlib import Path

SCHEMA='NOEMA_GREMLIND_V1'
RUNTIME_SOURCE_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
BUS_SCHEMA='GREMLIN_WHISPER_BUS_V0_5'
INTERVAL=0.25
STOP=threading.Event()
CIELINGO_LOCK=threading.Lock()


def canonical(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')

def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(f'.{path.name}.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n','utf-8')
    os.replace(tmp,path)

def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=canonical(obj)+b'\n'
    fd=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_APPEND, 0o600)
    try:
        os.write(fd,raw); os.fsync(fd)
    finally: os.close(fd)

def load(path: Path): return json.loads(path.read_text('utf-8'))

def verify_live(root: Path):
    required=[root/'working_state.json',root/'session/startpoint.json',root/'session/tether_guard_latest.json',root/'gremlin/imagination_binding.json']
    missing=[str(p) for p in required if not p.is_file()]
    if missing: raise RuntimeError('missing live inputs: '+','.join(missing))
    sp=load(root/'session/startpoint.json'); guard=load(root/'session/tether_guard_latest.json'); bind=load(root/'gremlin/imagination_binding.json')
    if sp.get('status')!='VERIFIED': raise RuntimeError('startpoint not VERIFIED')
    if guard.get('status')!='ACTIVE' or guard.get('guard',{}).get('tether_status')!='ACTIVE': raise RuntimeError('tether guard not ACTIVE')
    if bind.get('status')!='ACTIVE_BOUND' or bind.get('authority')!='CANDIDATE_ONLY': raise RuntimeError('GREMLIN binding invalid')
    return sp, bind

_QUERY_STOPWORDS = frozenset({
    'about','after','against','also','and','are','been','being','between','candidate','current','data','evidence','for','from','into','more','other','result','results','research','source','sources','that','their','there','these','this','through','using','with','within','would','web','www','https','http','com','org','the','was','were','has','have','had','its','our','your','you','can','may','new','software','system','systems','framework','paper','papers','title','facts','summary','query','source_ref','ref_id',
    'oraz','jest','jako','ktory','ktora','ktore','przez','dla','tego','tych','ten','ta','to','sie','nie','czy','jak','ale','lub','oraz','wynik','wyniki','zrodlo','zrodla','badanie','badania'
})
_ROLE_CUES = {
    'SPIDER': frozenset({'relation','relations','relationship','dependency','dependencies','graph','graphs','topology','isomorphism','mapping','structure','structural','bridge','connect','connection','relacja','relacje','zaleznosc','zaleznosci','struktura','mapowanie'}),
    'HOUND': frozenset({'contradiction','contradictions','limitation','limitations','failure','fail','mismatch','benchmark','verify','validate','test','tests','error','errors','inconsistency','inconsistent','inversion','breach','sprzecznosc','ograniczenie','blad','bledy','testy','walidacja'}),
    'MOLE': frozenset({'derive','derivation','mechanism','equation','formula','proof','solve','theorem','formalism','mechanizm','wyprowadz','rownanie','wzor','dowod'}),
    'RAVEN': frozenset({'memory','history','previous','prior','archive','earlier','precedent','lineage','supersede','supersedes','supersession','retroactive','chronology','pamiec','historia','poprzedni','wczesniej','archiwum'}),
    'ANT': frozenset({'alternatives','alternative','variants','variant','options','possibilities','candidate','candidates','combinations','permutations','wariant','warianty','mozliwosci','alternatywy','kombinacje'}),
    'MANTIS': frozenset({'duplicate','duplicates','redundant','redundancy','overlap','obsolete','prune','deduplicate','duplikat','duplikaty','redundancja','nakladanie'}),
}

def _norm_text(value):
    raw=unicodedata.normalize('NFKD', str(value)).casefold()
    return ''.join(ch for ch in raw if not unicodedata.combining(ch))

_HEX_ID_RE=re.compile(r'^[0-9a-f]{40,64}$')

def _tokens(value):
    text=_norm_text(value)
    out=[]
    for tok in re.findall(r'[a-z0-9][a-z0-9_-]{2,}', text):
        tok=tok.strip('_-')
        if len(tok)<4 or tok in _QUERY_STOPWORDS or tok.isdigit() or _HEX_ID_RE.fullmatch(tok):
            continue
        out.append(tok)
    return out

_SEMANTIC_SKIP_KEYS=frozenset({'path','source_ref','ref_id','url','doi','provider','provenance','source_count','id','event_id','sha256','receipt_sha256','published','updated','created_unix_ns','research_loop_id','iteration','max_iterations','next_iteration','status','authority','canon_allowed','query_execution_authority','promotion_requires_explicit_user_authorization','bundle','candidate_bundle','current_bundle','rollback_target','rollback_bundle','current_path','pointer_path','receipt_path','candidate_receipt','promotion_readiness_receipt','library_path','live_path','repo_root','module_root'})

def _semantic_skip_key(key):
    k=str(key).casefold()
    return k in _SEMANTIC_SKIP_KEYS or k.endswith(('_sha256','_hash','_digest','_id','_path','_ref','_url','_uri','_commit'))

_HEX_LITERAL_RE=re.compile(r'(?i)\b[0-9a-f]{40,64}\b')
_CONTROL_ASSIGNMENT_RE=re.compile(r'(?i)\b(?:[a-z0-9_]*(?:sha256|digest|hash)|event_id|ref_id|receipt_path|binding_sha256|authority|canon_allowed|query_execution_authority|promotion_requires_explicit_user_authorization)\s*[:=]\s*[^\s,;]+')

def _clean_semantic_string(value):
    text=_CONTROL_ASSIGNMENT_RE.sub(' ',str(value))
    text=_HEX_LITERAL_RE.sub(' ',text)
    return ' '.join(text.split())

def _event_text(payload,key=None):
    if key is not None and _semantic_skip_key(key): return ''
    if isinstance(payload,str): return _clean_semantic_string(payload)
    if isinstance(payload,dict):
        parts=[]; ordered=list(payload.items()); ordered.sort(key=lambda kv:(0 if str(kv[0]).casefold() in ('query','research_query') else 1))
        for k,v in ordered:
            text=_event_text(v,k)
            if text: parts.append(text)
        return ' '.join(parts)
    if isinstance(payload,(list,tuple)):
        return ' '.join(filter(None,(_event_text(v) for v in payload)))
    return ''

def _semantic_chunks(text,max_chars=128,max_chunks=36):
    words=str(text).split()
    chunks=[]; cur=[]; size=0
    for word in words:
        pieces=[word[i:i+max_chars] for i in range(0,len(word),max_chars)] or ['']
        for piece in pieces:
            extra=len(piece)+(1 if cur else 0)
            if cur and size+extra>max_chars:
                chunks.append(' '.join(cur)); cur=[]; size=0
                if len(chunks)>=max_chunks: return chunks
            cur.append(piece); size+=len(piece)+(1 if len(cur)>1 else 0)
    if cur and len(chunks)<max_chunks: chunks.append(' '.join(cur))
    return chunks or ['EMPTY']

def _find_event(bus: Path, event_id: str, max_lines=1000):
    if not event_id or not bus.is_file(): return None
    lines=bus.read_text('utf-8').splitlines()[-max_lines:]
    for line in reversed(lines):
        try: ev=json.loads(line)
        except (json.JSONDecodeError,TypeError,ValueError): continue
        if ev.get('event_id')==event_id: return ev
    return None

def _route_roles(text, source_count=1):
    toks=frozenset(_tokens(text)); roles=['OWL']
    for role,cues in _ROLE_CUES.items():
        if toks & cues and role not in roles: roles.append(role)
    # Cross-source research gets a structural scan and adversarial check even
    # without lexical triggers, because those roles operate on observed source structure.
    if source_count>=2 and 'SPIDER' not in roles: roles.append('SPIDER')
    if source_count>=2 and 'HOUND' not in roles: roles.append('HOUND')
    return roles[:4]

def _rank_terms(text, *, prefer_text='', exclude=(), limit=8):
    from collections import Counter
    exclude=set(exclude)
    counts=Counter(t for t in _tokens(text) if t not in exclude)
    prefer=set(_tokens(prefer_text))
    ranked=sorted(counts, key=lambda t:(-(counts[t]+(2 if t in prefer else 0)),-len(t),t))
    return ranked[:limit]

def _recent_search_queries(bus: Path, limit=12, research_loop_id=None):
    out=[]
    if not bus.is_file(): return out
    for line in bus.read_text('utf-8').splitlines()[-1500:]:
        try: ev=json.loads(line)
        except (json.JSONDecodeError,TypeError,ValueError): continue
        if ev.get('event_type')!='SEARCH_RESULT': continue
        payload=ev.get('payload',{}) if isinstance(ev.get('payload'),dict) else {}
        if research_loop_id is not None and payload.get('research_loop_id')!=research_loop_id: continue
        q=str(payload.get('query') or '').strip()
        if q and q not in out: out.append(q)
    return out[-limit:]

def _jaccard(a,b):
    A=set(_tokens(a)); B=set(_tokens(b))
    if not A and not B: return 1.0
    if not A or not B: return 0.0
    return len(A&B)/len(A|B)

def _query_candidate(source_ev, phase_payload):
    payload=source_ev.get('payload',{}) if isinstance(source_ev,dict) else {}
    text=_event_text(payload)
    query=str(payload.get('query') or payload.get('research_query') or '') if isinstance(payload,dict) else ''
    qtokens=set(_tokens(query))
    R=phase_payload.get('R') if isinstance(phase_payload,dict) else []
    chunks=_semantic_chunks(text,128,36)
    phase_index=None; phase_R=None; phase_text=''
    if isinstance(R,list) and R:
        finite=[(i,float(v)) for i,v in enumerate(R[:len(chunks)]) if isinstance(v,(int,float))]
        if finite:
            phase_index,phase_R=max(finite,key=lambda x:x[1]); phase_text=chunks[phase_index]
    global_terms=_rank_terms(text,prefer_text=phase_text,exclude=qtokens,limit=10)
    phase_terms=_rank_terms(phase_text,exclude=qtokens,limit=4) if phase_text else []
    terms=[]
    for t in phase_terms+global_terms:
        if t not in terms: terms.append(t)
    compound=set(terms)
    terms=[t for t in terms if not any(u!=t and (u.startswith(t+'-') or u.endswith('-'+t)) for u in compound)]
    phase_terms=[t for t in phase_terms if t in terms]
    source_count=1
    if isinstance(payload,dict):
        for key in ('results','sources','items'):
            if isinstance(payload.get(key),list): source_count=max(source_count,len(payload[key]))
    roles=_route_roles(' '.join([query,text]),source_count=source_count)
    source_type=source_ev.get('event_type') if isinstance(source_ev,dict) else None
    internal_audit=(source_type=='USER_TASK' and not query.strip())
    base=' '.join(terms[:4]).strip() or query.strip()
    suffix={
        'OWL':'primary evidence methodology',
        'SPIDER':'structural relation dependency',
        'HOUND':'limitations contradiction benchmark',
        'MOLE':'mechanism derivation formalism',
        'RAVEN':'prior work history precedent',
        'ANT':'alternative variants search space',
        'MANTIS':'overlap duplicate prior art',
    }
    candidates=[]
    for role in roles:
        q=' '.join(x for x in (base,suffix.get(role,'')) if x).strip()
        if query and q.casefold()==query.casefold(): q=(q+' independent evidence').strip()
        if q and q not in [x['query'] for x in candidates]:
            candidates.append({'species':role,'query':q})
    preferred='SPIDER' if source_count>=2 and any(c['species']=='SPIDER' for c in candidates) else (candidates[0]['species'] if candidates else None)
    selected=next((c['query'] for c in candidates if c['species']==preferred), candidates[0]['query'] if candidates else (base or query))
    internal_task_candidate=(base or str(payload.get('task') or payload.get('open_gate') or '')).strip() if internal_audit and isinstance(payload,dict) else None
    if internal_audit:
        selected=None
        candidates=[]
    loop_id=str(payload.get('research_loop_id') or '').strip() if isinstance(payload,dict) else ''
    iteration=int(payload.get('iteration') or 1) if isinstance(payload,dict) else 1
    max_iterations=int(payload.get('max_iterations') or 5) if isinstance(payload,dict) else 5
    max_iterations=max(1,min(12,max_iterations))
    source_bus=None
    try:
        source_bus=Path(source_ev.get('_bus_path')) if isinstance(source_ev,dict) and source_ev.get('_bus_path') else None
    except (TypeError,ValueError): source_bus=None
    bus_for_history=source_bus if source_bus and source_bus.is_file() else Path('/dev/shm/ciel_noema/gremlin/whisper/events.jsonl')
    history=[] if internal_audit else _recent_search_queries(bus_for_history,research_loop_id=(loop_id or None))
    similarities=[_jaccard(selected,h) for h in history] if selected else []
    max_similarity=max(similarities) if similarities else 0.0
    novelty=1.0 if internal_audit else max(0.0,1.0-max_similarity)
    historical_terms=set(t for h in history for t in _tokens(h))
    novel_terms=[t for t in terms if t not in historical_terms]
    if internal_audit:
        loop_action='INTERNAL_AUDIT_ONLY'
    elif iteration>=max_iterations:
        loop_action='SATURATED_MAX_DEPTH'
    elif selected and novelty>=0.30 and len(novel_terms)>=2:
        loop_action='CONTINUE'
    else:
        loop_action='SATURATED'
    return {
        'schema':'GREMLIN_RT_QUERY_SYNTH_V2',
        'route_kind':'INTERNAL_AUDIT' if internal_audit else 'WEB_RESEARCH',
        'authority':'CANDIDATE_ONLY',
        'query_execution_authority':False,
        'source_event_id':source_ev.get('event_id') if isinstance(source_ev,dict) else None,
        'source_event_type':source_ev.get('event_type') if isinstance(source_ev,dict) else None,
        'original_query':query or None,
        'research_loop_id':loop_id or None,
        'iteration':iteration,
        'next_iteration':iteration+1,
        'max_iterations':max_iterations,
        'route_species':roles,
        'phase_attention_index':phase_index,
        'phase_attention_R':phase_R,
        'phase_attention_terms':phase_terms,
        'candidate_terms':terms[:8],
        'candidates':candidates,
        'selected_query_candidate':selected,
        'selected_internal_task_candidate':internal_task_candidate,
        'selection_basis':'PHASENAV_ATTENTION_PLUS_GREMLIN_TYPED_ROLE_SYNTHESIS',
        'query_history':history,
        'max_similarity_to_history':max_similarity,
        'query_novelty':novelty,
        'novel_terms':novel_terms[:8],
        'loop_action':loop_action,
        'saturation_rule':'N/A_INTERNAL_AUDIT' if internal_audit else 'SATURATED_IF_JACCARD_NOVELTY_LT_0_30_OR_FEWER_THAN_2_NOVEL_TERMS',
    }

def make_event(sender,recipient,event_type,payload,salience=0.0,tags=None):
    body={'schema':BUS_SCHEMA,'sender':sender,'recipient':recipient,'event_type':event_type,'payload':payload,'salience':max(0.0,min(1.0,float(salience))),'tags':list(tags or []),'created_unix_ns':time.time_ns()}
    eid='gremlin:whisper:sha256:'+hashlib.sha256(canonical(body)).hexdigest()
    return {**body,'event_id':eid}

class State:
    def __init__(self, root: Path, generation: str):
        self.root=root; self.groot=root/'gremlin'; self.generation=generation
        self.bus=self.groot/'whisper/events.jsonl'; self.status=self.groot/'daemon_status.json'; self.cursor=self.groot/'whisper/gremlin.cursor.json'
        self.pid=os.getpid(); self.started=time.time_ns(); self.seq=0; self.processed=0; self.emitted=0; self.last_event_id=None; self.lock=threading.Lock()
        self.groot.mkdir(parents=True,exist_ok=True); (self.groot/'whisper').mkdir(parents=True,exist_ok=True); (self.groot/'receipts').mkdir(parents=True,exist_ok=True)
        if not self.bus.exists(): self.bus.touch(mode=0o600)
        self.offset=0
        if self.cursor.is_file():
            cursor=load(self.cursor)
            raw_offset=cursor.get('offset')
            if not isinstance(raw_offset,int) or raw_offset < 0:
                raise RuntimeError('invalid GREMLIN cursor offset')
            self.offset=raw_offset
    def snapshot(self,status='ACTIVE'):
        return {'schema':SCHEMA,'status':status,'pid':self.pid,'generation':self.generation,'authority':'CANDIDATE_ONLY','canon_allowed':False,'static_fallback':False,'heartbeat_seq':self.seq,'heartbeat_unix_ns':time.time_ns(),'interval_s':INTERVAL,'started_unix_ns':self.started,'processed_events':self.processed,'emitted_events':self.emitted,'last_event_id':self.last_event_id,'bus':str(self.bus),'socket':str(self.groot/'gremlin.sock'),'bus_wake_socket':str(self.groot/'bus_wake.sock'),'event_driven_bus_wake':True,'runtime_source_sha256':RUNTIME_SOURCE_SHA256}
    def write_status(self,status='ACTIVE'): atomic_json(self.status,self.snapshot(status))
    def publish(self,event):
        append_jsonl(self.bus,event); self.emitted+=1; self.last_event_id=event['event_id']
        # Event-driven wake for the Terminal36D/PhaseNav bridge. This does not
        # alter orbital/phase dynamics; it only removes idle polling latency.
        wake=self.root/'terminal36d'/'wake.sock'
        if wake.exists():
            s=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
            try:
                s.settimeout(0.02); s.sendto(b'1',str(wake))
            except OSError:
                pass
            finally:
                s.close()
        return event


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _purge_cielingo_modules():
    for name in list(sys.modules):
        if name == 'bridge' or name.startswith('bridge.') or name == 'cielingo_core' or name.startswith('cielingo_core.'):
            sys.modules.pop(name, None)


def _cielingo_paths(st: State, payload: dict):
    raw=payload.get('repo_root')
    if not isinstance(raw,str) or not raw.strip():
        raise RuntimeError('CIELINGO repo_root is required')
    repo_root=Path(raw).resolve(strict=True)
    live_root=(st.root/'cielingo').resolve(strict=True)
    if not _is_within(repo_root,live_root):
        raise RuntimeError('CIELINGO repo_root must stay under live NOEMA cielingo surface')
    module_root=repo_root/'src' if (repo_root/'src/bridge/cielingo_pipeline_adapter.py').is_file() else repo_root
    adapter_file=module_root/'bridge/cielingo_pipeline_adapter.py'
    if not adapter_file.is_file():
        raise RuntimeError('canonical CIELingoPipelineAdapter file missing')
    return repo_root,module_root,adapter_file


def _cielingo_receipt(st: State, payload: dict, repo_root: Path):
    raw=payload.get('receipt_path')
    if not isinstance(raw,str) or not raw.strip():
        raise RuntimeError('CIELINGO receipt_path is required')
    receipt_path=Path(raw).resolve(strict=True)
    allowed=(st.root/'cielingo/receipts').resolve(strict=True)
    if not _is_within(receipt_path,allowed):
        raise RuntimeError('CIELINGO receipt must stay under live receipt surface')
    receipt=load(receipt_path)
    if receipt.get('status')!='PASS':
        raise RuntimeError('CIELINGO receipt is not PASS')
    expected=payload.get('receipt_sha256')
    if expected and expected!=receipt.get('receipt_sha256'):
        raise RuntimeError('CIELINGO receipt SHA mismatch')
    declared=receipt.get('live_root')
    if declared and Path(str(declared)).resolve(strict=True)!=repo_root:
        raise RuntimeError('CIELINGO receipt live_root mismatch')
    branch_head=payload.get('branch_head')
    if branch_head and receipt.get('branch_head')!=branch_head:
        raise RuntimeError('CIELINGO branch head mismatch')
    return receipt_path,receipt


def _with_cielingo_adapter(st: State, repo_root: Path, module_root: Path, callback):
    with CIELINGO_LOCK:
        old_path=list(sys.path)
        try:
            _purge_cielingo_modules()
            sys.path.insert(0,str(module_root))
            from bridge.cielingo_pipeline_adapter import CIELingoPipelineAdapter
            adapter=CIELingoPipelineAdapter(repo_root=str(repo_root))
            return callback(adapter)
        finally:
            _purge_cielingo_modules()
            sys.path[:]=old_path


def _cielingo_bind(st: State, payload: dict):
    if not isinstance(payload,dict):
        raise RuntimeError('CIELINGO_BIND payload must be an object')
    repo_root,module_root,adapter_file=_cielingo_paths(st,payload)
    receipt_path,receipt=_cielingo_receipt(st,payload,repo_root)
    probe=_with_cielingo_adapter(st,repo_root,module_root,lambda adapter:{'adapter_class':type(adapter).__name__,'bridge_type':type(adapter.bridge).__name__,'processed_count':adapter.processed_count})
    base={'schema':'GREMLIN_CIELINGO_BINDING_V1','status':'BOUND','generation':st.generation,'repo_root':str(repo_root),'module_root':str(module_root),'adapter_file':str(adapter_file),'adapter_sha256':hashlib.sha256(adapter_file.read_bytes()).hexdigest(),'source_receipt_path':str(receipt_path),'source_receipt_sha256':receipt.get('receipt_sha256'),'branch_head':receipt.get('branch_head'),'probe':probe,'authority':'CANDIDATE_ONLY','canon_allowed':False,'created_unix_ns':time.time_ns()}
    binding_sha=hashlib.sha256(canonical(base)).hexdigest()
    binding={**base,'binding_sha256':binding_sha}
    atomic_json(st.groot/'cielingo_binding.json',binding)
    bind_receipt={**binding,'schema':'GREMLIN_CIELINGO_BIND_RECEIPT_V1','status':'PASS','receipt_sha256':hashlib.sha256(canonical(binding)).hexdigest()}
    receipt_out=st.groot/'receipts'/f'cielingo_bind_{binding_sha[:16]}.json'
    atomic_json(receipt_out,bind_receipt)
    return {**binding,'receipt_path':str(receipt_out),'receipt_sha256':bind_receipt['receipt_sha256']}


def _cielingo_enrich(st: State, payload: dict):
    if not isinstance(payload,dict):
        raise RuntimeError('CIELINGO_ENRICH payload must be an object')
    binding_path=st.groot/'cielingo_binding.json'
    if not binding_path.is_file():
        raise RuntimeError('CIELINGO is not bound')
    binding=load(binding_path)
    if binding.get('status')!='BOUND' or binding.get('generation')!=st.generation:
        raise RuntimeError('CIELINGO binding is stale or invalid')
    repo_root=Path(binding['repo_root']).resolve(strict=True)
    module_root=Path(binding['module_root']).resolve(strict=True)
    live_root=(st.root/'cielingo').resolve(strict=True)
    if not _is_within(repo_root,live_root) or not _is_within(module_root,live_root):
        raise RuntimeError('CIELINGO binding escaped live surface')
    engine_state=payload.get('engine_state',{})
    if not isinstance(engine_state,dict):
        raise RuntimeError('engine_state must be an object')
    intention_text=payload.get('intention_text','')
    if not isinstance(intention_text,str):
        raise RuntimeError('intention_text must be a string')
    if len(intention_text)>65536:
        raise RuntimeError('intention_text too large')
    turn_id=payload.get('turn_id')
    if turn_id is not None and not isinstance(turn_id,str):
        raise RuntimeError('turn_id must be a string or null')
    def run(adapter):
        enriched=adapter.enrich(dict(engine_state),turn_id=turn_id,intention_text=intention_text)
        state=adapter.bridge.last_state()
        draft=state.response_draft if state is not None else None
        if draft is None:
            raise RuntimeError('CIELINGO enrich produced no response draft')
        issues=draft.validate()
        if issues:
            raise RuntimeError('CIELINGO draft validation failed: '+'; '.join(issues))
        if draft.canon_allowed or draft.runtime_execution_allowed:
            raise RuntimeError('CIELINGO draft authority boundary violated')
        return {'cielingo':enriched.get('cielingo'),'lingo_frame':enriched.get('lingo_frame'),'draft_validation':issues,'missing_markers':list(draft.missing_markers),'forbidden_claims_present':list(draft.forbidden_claims_present),'canon_allowed':bool(draft.canon_allowed),'runtime_execution_allowed':bool(draft.runtime_execution_allowed)}
    result=_with_cielingo_adapter(st,repo_root,module_root,run)
    base={'schema':'GREMLIN_CIELINGO_ENRICH_RECEIPT_V1','status':'PASS','generation':st.generation,'binding_sha256':binding.get('binding_sha256'),'turn_id':turn_id,'result':result,'authority':'CANDIDATE_ONLY','canon_allowed':False,'created_unix_ns':time.time_ns()}
    receipt_sha=hashlib.sha256(canonical(base)).hexdigest()
    receipt={**base,'receipt_sha256':receipt_sha}
    receipt_path=st.groot/'receipts'/f'cielingo_enrich_{receipt_sha[:16]}.json'
    atomic_json(receipt_path,receipt)
    return {**result,'binding_sha256':binding.get('binding_sha256'),'receipt_path':str(receipt_path),'receipt_sha256':receipt_sha,'authority':'CANDIDATE_ONLY'}


def process_event(st: State, ev: dict):
    if ev.get('recipient') not in ('GREMLIN','*'): return
    if ev.get('sender')=='GREMLIN': return
    et=ev.get('event_type'); st.processed+=1; st.last_event_id=ev.get('event_id')
    # Resident daemon handles transport/attention only. Semantic claims stay candidate-only.
    if et=='PING':
        st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'PONG',{'in_reply_to':ev.get('event_id'),'generation':st.generation},0.0,['daemon']))
    elif et in ('SEARCH_RESULT','SOURCE_CHUNK','RELATION_GRAPH','RESEARCH_INPUT'):
        st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'GREMLIN_RT_INGESTED',{'in_reply_to':ev.get('event_id'),'input_type':et,'candidate_ready':True,'authority':'CANDIDATE_ONLY'},0.15,['rt','ingest']))
    elif et=='DREAM_RUN':
        st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'DREAM_WAKE',{'in_reply_to':ev.get('event_id'),'mode':'RESIDENT_EVENT_LOOP','semantic_engine':'BOUND_EXTERNALLY','authority':'CANDIDATE_ONLY'},0.60,['dream','rt']))
    elif et=='USER_TASK':
        st.publish(make_event('GREMLIN','ZOSIA','GREMLIN_RT_INGESTED',{'in_reply_to':ev.get('event_id'),'input_type':et,'candidate_ready':True,'authority':'CANDIDATE_ONLY'},0.20,['rt','task']))
    elif et=='CIELINGO_BIND':
        p=ev.get('payload',{}) if isinstance(ev.get('payload'),dict) else {}
        try:
            result=_cielingo_bind(st,p)
            st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'CIELINGO_BOUND',{'in_reply_to':ev.get('event_id'),**result},0.86,['cielingo','bind','candidate']))
        except Exception as exc:
            st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'CIELINGO_FAIL',{'in_reply_to':ev.get('event_id'),'stage':'BIND','error':type(exc).__name__,'detail':str(exc)[:400],'authority':'CANDIDATE_ONLY'},0.95,['cielingo','fail_closed']))
    elif et=='CIELINGO_ENRICH':
        p=ev.get('payload',{}) if isinstance(ev.get('payload'),dict) else {}
        try:
            result=_cielingo_enrich(st,p)
            st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'CIELINGO_ENRICHED',{'in_reply_to':ev.get('event_id'),**result},0.88,['cielingo','enrich','candidate']))
        except Exception as exc:
            st.publish(make_event('GREMLIN',ev.get('sender','ZOSIA'),'CIELINGO_FAIL',{'in_reply_to':ev.get('event_id'),'stage':'ENRICH','error':type(exc).__name__,'detail':str(exc)[:400],'authority':'CANDIDATE_ONLY'},0.95,['cielingo','fail_closed']))
    elif et=='H200_KURAMOTO_E2E_STATE':
        p=ev.get('payload',{}) if isinstance(ev.get('payload'),dict) else {}
        required=('account_current','working_state_sha256','projection_phi_sha256','projection_g_sha256','q28_receipt_sha256','q28_state_sha256')
        missing=[k for k in required if not isinstance(p.get(k),str) or not p.get(k)]
        if missing:
            st.publish(make_event('GREMLIN',ev.get('sender','H200_KURAMOTO_AUX'),'GREMLIN_H200_KURAMOTO_E2E_FAIL',{'in_reply_to':ev.get('event_id'),'missing':missing,'authority':'CANDIDATE_ONLY'},0.95,['h200','e2e','fail_closed']))
        else:
            ws=load(st.root/'working_state.json')
            if p.get('working_state_sha256')!=ws.get('working_state_sha256'):
                st.publish(make_event('GREMLIN',ev.get('sender','H200_KURAMOTO_AUX'),'GREMLIN_H200_KURAMOTO_E2E_FAIL',{'in_reply_to':ev.get('event_id'),'error':'WORKING_STATE_GENERATION_MISMATCH','authority':'CANDIDATE_ONLY'},0.95,['h200','e2e','fail_closed']))
            else:
                st.publish(make_event('GREMLIN',ev.get('sender','H200_KURAMOTO_AUX'),'GREMLIN_H200_KURAMOTO_E2E_INGESTED',{'in_reply_to':ev.get('event_id'),'projection_phi_sha256':p.get('projection_phi_sha256'),'projection_g_sha256':p.get('projection_g_sha256'),'q28_receipt_sha256':p.get('q28_receipt_sha256'),'q28_state_sha256':p.get('q28_state_sha256'),'working_state_sha256':p.get('working_state_sha256'),'phase_state_consumed':True,'authority':'CANDIDATE_ONLY'},0.72,['h200','kuramoto','e2e','q28','ingested']))
    elif et=='PHASENAV36D_RT_STATE':
        p=ev.get('payload',{}) if isinstance(ev.get('payload'),dict) else {}
        st.publish(make_event('GREMLIN','ZOSIA','GREMLIN_PHASE36D_FUSED',{'in_reply_to':ev.get('event_id'),'source_event_id':p.get('source_event_id'),'trace_sha256':p.get('trace_sha256'),'terminal_receipt_sha256':p.get('terminal_receipt_sha256'),'semantic_input_sha256':p.get('semantic_input_sha256'),'semantic_label_count':p.get('semantic_label_count'),'R':p.get('R'),'shape':p.get('shape'),'phase_state_consumed':True,'authority':'CANDIDATE_ONLY'},0.82,['gremlin','phasenav','terminal36d','fused']))
        source_ev=_find_event(st.bus,p.get('source_event_id'))
        if source_ev and source_ev.get('event_type') in ('SEARCH_RESULT','RESEARCH_PACKET','RESEARCH_INPUT','USER_TASK'):
            source_ev=dict(source_ev); source_ev['_bus_path']=str(st.bus)
            qc=_query_candidate(source_ev,p)
            if qc.get('route_kind')=='INTERNAL_AUDIT':
                st.publish(make_event('GREMLIN','ZOSIA','GREMLIN_INTERNAL_AUDIT_CANDIDATE',qc,0.78,['gremlin','internal-audit','candidate','phasenav']))
            else:
                st.publish(make_event('GREMLIN','ZOSIA','GREMLIN_RESEARCH_QUERY_CANDIDATE',qc,0.78,['gremlin','research','query-candidate','phasenav']))


def bus_loop(st: State):
    wake_path=st.groot/'bus_wake.sock'; wake_path.unlink(missing_ok=True)
    wake=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM); wake.bind(str(wake_path)); os.chmod(wake_path,0o600); wake.setblocking(False)
    try:
        while not STOP.is_set():
            try:
                size=st.bus.stat().st_size
                if st.offset>size: st.offset=0
                if size>st.offset:
                    with st.bus.open('rb') as fh:
                        fh.seek(st.offset)
                        while True:
                            line=fh.readline()
                            if not line: break
                            st.offset=fh.tell()
                            try: ev=json.loads(line.decode('utf-8')); process_event(st,ev)
                            except Exception as exc:
                                err=make_event('GREMLIN','ZOSIA','RECEIPT_INVALID',{'error':type(exc).__name__,'detail':str(exc)[:240]},0.95,['fail_closed'])
                                st.publish(err)
                    atomic_json(st.cursor,{'schema':'GREMLIN_CURSOR_V1','offset':st.offset,'updated_unix_ns':time.time_ns()})
            except Exception as exc:
                try:
                    st.publish(make_event('GREMLIN','ZOSIA','RECEIPT_INVALID',{'component':'bus_loop','error':type(exc).__name__,'detail':str(exc)[:240]},0.95,['fail_closed','bus']))
                finally:
                    STOP.set()
                    break
            ready,_,_=select.select([wake],[],[],0.05)
            if wake in ready:
                try:
                    while True: wake.recv(4096)
                except BlockingIOError:
                    pass
    finally:
        wake.close(); wake_path.unlink(missing_ok=True)


def heartbeat_loop(st: State):
    while not STOP.is_set():
        try:
            _,bind=verify_live(st.root)
            if str(bind.get('generation'))!=st.generation:
                raise RuntimeError('GREMLIN generation changed')
            with st.lock: st.seq+=1; st.write_status('ACTIVE')
        except Exception as exc:
            with st.lock:
                atomic_json(st.status,{**st.snapshot('BLOCKED'),'failure':str(exc)})
            STOP.set(); break
        STOP.wait(INTERVAL)


def socket_loop(st: State):
    path=st.groot/'gremlin.sock'; path.unlink(missing_ok=True)
    srv=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); srv.bind(str(path)); os.chmod(path,0o600); srv.listen(16); srv.settimeout(0.2)
    while not STOP.is_set():
        try: c,_=srv.accept()
        except socket.timeout: continue
        except OSError: break
        with c:
            try:
                raw=b''
                while b'\n' not in raw and len(raw)<1024*1024:
                    chunk=c.recv(65536)
                    if not chunk: break
                    raw+=chunk
                req=json.loads((raw.split(b'\n',1)[0] or b'{}').decode()) if raw else {'action':'STATUS'}
                action=str(req.get('action','STATUS')).upper()
                if action in ('PING','STATUS'):
                    resp=st.snapshot('ACTIVE')
                elif action=='PUBLISH':
                    p=req.get('event') or {}; ev=make_event(p.get('sender','ZOSIA'),p.get('recipient','GREMLIN'),p.get('event_type','RESEARCH_INPUT'),p.get('payload',{}),p.get('salience',0.0),p.get('tags',[])); st.publish(ev); resp={'status':'ACCEPTED','event':ev}
                elif action=='CIELINGO_BIND':
                    resp=_cielingo_bind(st,req.get('payload') or {})
                elif action=='CIELINGO_ENRICH':
                    resp=_cielingo_enrich(st,req.get('payload') or {})
                elif action=='POLL':
                    recipient=req.get('recipient','ZOSIA'); limit=max(1,min(100,int(req.get('limit',20)))); events=[]
                    for line in st.bus.read_text('utf-8').splitlines()[-500:]:
                        try:
                            ev=json.loads(line)
                            if ev.get('recipient') in (recipient,'*'): events.append(ev)
                        except (json.JSONDecodeError, TypeError, ValueError): continue
                    resp={'status':'ACTIVE','events':events[-limit:]}
                else: resp={'status':'BLOCKED','error':'unsupported action'}
                c.sendall(canonical(resp)+b'\n')
            except (BrokenPipeError, ConnectionResetError):
                continue
            except Exception as exc:
                try:
                    c.sendall(canonical({'status':'BLOCKED','error':type(exc).__name__,'detail':str(exc)[:240]})+b'\n')
                except (BrokenPipeError, ConnectionResetError):
                    continue
    srv.close(); path.unlink(missing_ok=True)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='/dev/shm/ciel_noema'); ns=ap.parse_args(); root=Path(ns.root)
    _,bind=verify_live(root); generation=str(bind.get('generation'))
    st=State(root,generation)
    live_bind=dict(bind); daemon=dict(live_bind.get('daemon') or {})
    daemon.update({'schema':'NOEMA_GREMLIND_BINDING_V1','status':'ACTIVE','resident':True,'pid':os.getpid(),'socket':str(root/'gremlin/gremlin.sock'),'generation':generation,'authority':'CANDIDATE_ONLY','heartbeat_interval_s':INTERVAL})
    live_bind['daemon']=daemon
    atomic_json(root/'gremlin/imagination_binding.json',live_bind)
    def stop(*_): STOP.set()
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    threads=[threading.Thread(target=heartbeat_loop,args=(st,),daemon=True),threading.Thread(target=bus_loop,args=(st,),daemon=True),threading.Thread(target=socket_loop,args=(st,),daemon=True)]
    for t in threads: t.start()
    st.write_status('ACTIVE')
    while not STOP.wait(0.2):
        if any(not t.is_alive() for t in threads): STOP.set(); break
    st.write_status('STOPPED')
    return 0

if __name__=='__main__': raise SystemExit(main())