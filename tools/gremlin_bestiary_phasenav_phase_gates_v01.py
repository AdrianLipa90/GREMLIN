from __future__ import annotations

from dataclasses import dataclass
import cmath, hashlib, json, math
from typing import Iterable, Mapping, Sequence

try:
    import numpy as np
except ImportError:  # optional accelerated path; scalar reference remains dependency-free
    np = None  # type: ignore[assignment]

DIM = 36
TAU = 2.0 * math.pi
CONTRACT_ID = "GREMLIN_BESTIARY_PHASENAV_PHASE_GATES_V0_1"
SPECIES = (
    "HUMMINGBIRD","OCTOPUS","SPIDER","RAVEN","HOUND","MOLE","OWL","ANT","MANTIS",
    "FOX","BEAVER","BAT","CANARY","SERPENT","CHAMELEON","BELZEBUB","GREMLIN","FERRET",
)
REALIZATION_MODE = {
    "HUMMINGBIRD":"HYBRID","OCTOPUS":"HYBRID","SPIDER":"ANALOG_CORE_HYBRID_CONTROL",
    "RAVEN":"ANALOG_CORE_HYBRID_CONTROL","HOUND":"ANALOG_CORE_HYBRID_CONTROL",
    "MOLE":"ANALOG_CORE_HYBRID_CONTROL","OWL":"HYBRID","ANT":"HYBRID","MANTIS":"HYBRID",
    "FOX":"ANALOG_CORE_HYBRID_CONTROL","BEAVER":"ANALOG_CORE_HYBRID_CONTROL",
    "BAT":"ANALOG_CORE_HYBRID_CONTROL","CANARY":"ANALOG_CORE_HYBRID_CONTROL",
    "SERPENT":"ANALOG_CORE_HYBRID_CONTROL","CHAMELEON":"HYBRID","BELZEBUB":"HYBRID",
    "GREMLIN":"HYBRID","FERRET":"HYBRID_AUTHORITY_BOUNDARY",
}

class PhaseGateError(ValueError):
    pass

def _finite(x: object, field: str) -> float:
    try: y = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc: raise PhaseGateError(f"{field} must be finite") from exc
    if not math.isfinite(y): raise PhaseGateError(f"{field} must be finite")
    return y

def _wrap(x: float) -> float: return x % TAU

def _v36(values: Sequence[float], field: str = "vector") -> tuple[float, ...]:
    out = tuple(_finite(v, field) for v in values)
    if len(out) != DIM: raise PhaseGateError(f"{field} must contain exactly {DIM} values")
    return out

def _theta36(values: Sequence[float]) -> tuple[float, ...]:
    vals = _v36(values, "theta")
    if any(v < 0.0 or v >= TAU for v in vals): raise PhaseGateError("theta coordinates must lie in [0, 2pi)")
    return vals

def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

def _carrier36(label: str) -> tuple[float, ...]:
    seed = label.encode(); raw = b""; counter = 0
    while len(raw) < DIM * 8:
        raw += hashlib.sha512(seed + counter.to_bytes(4,"little")).digest(); counter += 1
    return tuple(TAU * (int.from_bytes(raw[i*8:(i+1)*8],"little") / float(2**64)) for i in range(DIM))

def circular_delta(a: float, b: float) -> float:
    return (a - b + math.pi) % TAU - math.pi

def torus_distance(a: Sequence[float], b: Sequence[float]) -> float:
    aa, bb = _theta36(a), _theta36(b)
    return math.sqrt(sum(circular_delta(x,y)**2 for x,y in zip(aa,bb)))

def phase_coherence(a: Sequence[float], b: Sequence[float]) -> float:
    aa, bb = _theta36(a), _theta36(b)
    z = sum(cmath.exp(1j*circular_delta(x,y)) for x,y in zip(aa,bb)) / DIM
    return abs(z)

def phase_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    aa, bb = _theta36(a), _theta36(b)
    z = sum(cmath.exp(1j*circular_delta(x,y)) for x,y in zip(aa,bb)) / DIM
    return 0.5 * (1.0 + z.real)

def circular_mean(states: Sequence[Sequence[float]], weights: Sequence[float] | None = None) -> tuple[float, ...]:
    if not states: raise PhaseGateError("at least one state required")
    vecs = [_theta36(s) for s in states]
    ws = [1.0]*len(vecs) if weights is None else [_finite(w,"weight") for w in weights]
    if len(ws) != len(vecs) or any(w < 0 for w in ws) or sum(ws) <= 0: raise PhaseGateError("invalid weights")
    total = sum(ws); out = []
    for i in range(DIM):
        z = sum(w*cmath.exp(1j*v[i]) for w,v in zip(ws,vecs)) / total
        if abs(z) < 1e-15: raise PhaseGateError("undefined antipodal circular mean")
        out.append(_wrap(cmath.phase(z)))
    return tuple(out)

@dataclass(frozen=True)
class PhaseState36:
    theta: tuple[float, ...]
    def __init__(self, theta: Sequence[float]) -> None: object.__setattr__(self,"theta",_theta36(theta))
    @property
    def payload(self) -> dict[str, object]:
        return {"schema":"GREMLIN_PHASENAV_T36_STATE_V0_1","contract_id":CONTRACT_ID,"space":"T^36",
                "basis_semantics":"UNASSIGNED_36D_COORDINATE_ORDER_PRESERVED","theta":list(self.theta)}
    @property
    def state_id(self) -> str: return f"gremlin:t36:sha256:{_sha(self.payload)}"

@dataclass(frozen=True)
class PhaseGate36:
    species: str
    phase_bias: tuple[float, ...]
    drive_gain: float = 0.30
    neighbor_coupling: float = 0.12
    harmonic_gain: float = 0.04
    dt: float = 0.20
    def __init__(self, species: str, phase_bias: Sequence[float] | None = None, drive_gain: float=.30,
                 neighbor_coupling: float=.12, harmonic_gain: float=.04, dt: float=.20) -> None:
        name = str(species).strip().upper()
        if name not in SPECIES: raise PhaseGateError(f"unknown species: {species!r}")
        object.__setattr__(self,"species",name)
        object.__setattr__(self,"phase_bias",_theta36(phase_bias if phase_bias is not None else _carrier36(name)))
        for field,value in (("drive_gain",drive_gain),("neighbor_coupling",neighbor_coupling),("harmonic_gain",harmonic_gain),("dt",dt)):
            x = _finite(value,field)
            if x < 0 or (field=="dt" and x <= 0): raise PhaseGateError(f"invalid {field}")
            object.__setattr__(self,field,x)
    @property
    def gate_id(self) -> str:
        p={"species":self.species,"phase_bias":list(self.phase_bias),"drive_gain":self.drive_gain,
           "neighbor_coupling":self.neighbor_coupling,"harmonic_gain":self.harmonic_gain,"dt":self.dt,
           "carrier_semantics":"DETERMINISTIC_ROUTING_CARRIER_NOT_SEMANTIC_AXIS_BINDING",
           "realization_mode":REALIZATION_MODE[self.species]}
        return f"gremlin:phase-gate:sha256:{_sha(p)}"
    def step(self, state: PhaseState36, target: Sequence[float] | None = None) -> PhaseState36:
        if not isinstance(state,PhaseState36): raise PhaseGateError("PhaseState36 required")
        bias = self.phase_bias if target is None else _theta36(target); t=state.theta; out=[]
        for i in range(DIM):
            drive=self.drive_gain*math.sin(circular_delta(bias[i],t[i]))
            coupling=.5*self.neighbor_coupling*(math.sin(circular_delta(t[(i-1)%DIM],t[i]))+math.sin(circular_delta(t[(i+1)%DIM],t[i])))
            harmonic=self.harmonic_gain*math.sin(2*circular_delta(bias[i],t[i]))
            out.append(_wrap(t[i]+self.dt*(drive+coupling+harmonic)))
        return PhaseState36(out)
    def step_batch(self, states: Sequence[PhaseState36], target: Sequence[float] | None = None) -> tuple[PhaseState36,...]:
        """Dependency-free scalar reference batch."""
        return tuple(self.step(s,target=target) for s in states)

    def step_batch_vectorized(self, states: Sequence[PhaseState36], target: Sequence[float] | None = None) -> tuple[PhaseState36,...]:
        """NumPy batch-first realization of the same PhaseNav phase gate.

        This is an accelerated numerical realization only.  It does not change
        semantic identity, authority, or the phase-gate equations.
        """
        if np is None:
            raise PhaseGateError("NumPy is required for vectorized phase-gate execution")
        if not states:
            return tuple()
        if not all(isinstance(s, PhaseState36) for s in states):
            raise PhaseGateError("step_batch_vectorized requires PhaseState36 inputs")
        theta = np.asarray([s.theta for s in states], dtype=np.float64)
        if theta.shape != (len(states), DIM) or not np.isfinite(theta).all():
            raise PhaseGateError("invalid vectorized T^36 batch")
        bias = np.asarray(self.phase_bias if target is None else _theta36(target), dtype=np.float64)
        delta = (bias[None, :] - theta + math.pi) % TAU - math.pi
        left_delta = (np.roll(theta, 1, axis=1) - theta + math.pi) % TAU - math.pi
        right_delta = (np.roll(theta, -1, axis=1) - theta + math.pi) % TAU - math.pi
        drive = self.drive_gain * np.sin(delta)
        coupling = 0.5 * self.neighbor_coupling * (np.sin(left_delta) + np.sin(right_delta))
        harmonic = self.harmonic_gain * np.sin(2.0 * delta)
        out = np.mod(theta + self.dt * (drive + coupling + harmonic), TAU)
        if out.shape != theta.shape or not np.isfinite(out).all():
            raise PhaseGateError("vectorized phase gate produced invalid output")
        return tuple(PhaseState36(row.tolist()) for row in out)

    def vectorized_max_error(self, states: Sequence[PhaseState36], target: Sequence[float] | None = None) -> float:
        scalar = self.step_batch(states, target=target)
        vector = self.step_batch_vectorized(states, target=target)
        if len(scalar) != len(vector):
            raise PhaseGateError("scalar/vector batch length mismatch")
        if not scalar:
            return 0.0
        return max(
            abs(circular_delta(a, b))
            for s_ref, s_vec in zip(scalar, vector)
            for a, b in zip(s_ref.theta, s_vec.theta)
        )

def _result(species: str, operation: str, data: Mapping[str,object], parents: Iterable[str]) -> dict[str,object]:
    body={"schema":"GREMLIN_PHASENAV_SPECIES_RESULT_V0_1","contract_id":CONTRACT_ID,"species":species,
          "operation":operation,"realization_mode":REALIZATION_MODE[species],"parents":list(parents),
          "data":dict(data),"external_effects":False,"canon_allowed":False}
    body["receipt_sha256"]=_sha(body); return body

def hummingbird_capture(s: PhaseState36) -> dict[str,object]:
    return _result("HUMMINGBIRD","APPEND_ONLY_CAPTURE",{"state_id":s.state_id,"theta":list(s.theta)},[s.state_id])

def octopus_route(s: PhaseState36, candidates: Sequence[str], *, max_species:int=4, min_score:float=.15) -> dict[str,object]:
    if max_species < 1: raise PhaseGateError("max_species must be positive")
    scored=[]
    for raw in candidates:
        n=str(raw).strip().upper()
        if n not in SPECIES or n in {"HUMMINGBIRD","OCTOPUS","BELZEBUB","GREMLIN","FERRET"}: continue
        score=phase_similarity(s.theta,_carrier36(n))
        if score >= min_score: scored.append((score,n))
    scored.sort(key=lambda x:(-x[0],x[1]))
    return _result("OCTOPUS","BOUNDED_PHASE_ROUTE",{"routes":[{"species":n,"score":q} for q,n in scored[:max_species]]},[s.state_id])

def spider_scan(states: Sequence[PhaseState36], *, threshold:float=.80) -> dict[str,object]:
    if len(states)<2: raise PhaseGateError("SPIDER requires at least two states")
    edges=[]
    for i in range(len(states)):
        for j in range(i+1,len(states)):
            c=phase_coherence(states[i].theta,states[j].theta)
            if c>=threshold: edges.append({"left":i,"right":j,"coherence":c})
    return _result("SPIDER","RELATION_COHERENCE_GRAPH",{"edges":edges,"threshold":threshold},[s.state_id for s in states])

def raven_recall(query:PhaseState36,memory:Sequence[PhaseState36],*,k:int=3)->dict[str,object]:
    if k<1 or not memory: raise PhaseGateError("RAVEN requires memory and positive k")
    scored=[(phase_similarity(query.theta,s.theta),i,s.state_id) for i,s in enumerate(memory)]
    scored.sort(key=lambda x:(-x[0],x[1]))
    return _result("RAVEN","PHASE_SIMILARITY_RECALL",{"matches":[{"index":i,"score":q,"state_id":sid} for q,i,sid in scored[:k]]},[query.state_id,*[s.state_id for s in memory]])

def hound_scan(s:PhaseState36,baseline:PhaseState36)->dict[str,object]:
    r=[abs(circular_delta(x,y)) for x,y in zip(s.theta,baseline.theta)]
    rms=math.sqrt(sum(x*x for x in r)/DIM); m=max(r)
    return _result("HOUND","PHASE_RESIDUAL_SCAN",{"rms_residual":rms,"max_residual":m,"max_index":r.index(m)},[s.state_id,baseline.state_id])

def mole_relax(s:PhaseState36,target:PhaseState36,*,steps:int=16)->dict[str,object]:
    if steps<1 or steps>10000: raise PhaseGateError("invalid MOLE step count")
    gate=PhaseGate36("MOLE",drive_gain=.75,neighbor_coupling=.02,harmonic_gain=.08,dt=.25)
    before=torus_distance(s.theta,target.theta); cur=s; trace=[]
    for _ in range(steps): cur=gate.step(cur,target=target.theta); trace.append(cur.state_id)
    return _result("MOLE","LOCAL_PHASE_RELAXATION",{"before_distance":before,"after_distance":torus_distance(cur.theta,target.theta),"steps":steps,"final_state_id":cur.state_id,"trace":trace},[s.state_id,target.state_id])

def owl_audit(claim:PhaseState36,evidence:Sequence[PhaseState36],*,coordinate_tolerance:float=math.pi/3)->dict[str,object]:
    if not evidence: raise PhaseGateError("OWL requires evidence")
    support=[phase_similarity(claim.theta,e.theta) for e in evidence]; center=circular_mean([e.theta for e in evidence])
    unsupported=sum(abs(circular_delta(a,b))>coordinate_tolerance for a,b in zip(claim.theta,center))/DIM
    return _result("OWL","EPISTEMIC_PHASE_AUDIT",{"mean_support":sum(support)/len(support),"minimum_support":min(support),"unsupported_fraction":unsupported},[claim.state_id,*[e.state_id for e in evidence]])

def ant_enumerate(s:PhaseState36,*,axes:Sequence[int]=(0,1,2),delta:float=.125,budget:int=64)->dict[str,object]:
    axes=tuple(dict.fromkeys(int(a) for a in axes))
    if not axes or any(a<0 or a>=DIM for a in axes) or budget<1: raise PhaseGateError("invalid ANT request")
    d=abs(_finite(delta,"delta")); ids=[]
    for code in range(3**len(axes)):
        digits=[]; n=code
        for _ in axes: digits.append(n%3-1); n//=3
        if all(x==0 for x in digits): continue
        th=list(s.theta)
        for axis,sign in zip(axes,digits): th[axis]=_wrap(th[axis]+sign*d)
        ids.append(PhaseState36(th).state_id)
        if len(ids)>=budget: break
    return _result("ANT","BOUNDED_PHASE_ENUMERATION",{"variant_ids":ids,"axes":list(axes),"delta":d,"budget":budget},[s.state_id])

def mantis_prune(states:Sequence[PhaseState36],*,epsilon:float=1e-6)->dict[str,object]:
    if epsilon<0: raise PhaseGateError("epsilon must be non-negative")
    kept=[]; dropped=[]
    for idx,s in enumerate(states):
        match=next((j for j,k in enumerate(kept) if torus_distance(s.theta,k.theta)<=epsilon),None)
        if match is None: kept.append(s)
        else: dropped.append({"index":idx,"duplicate_of_kept_index":match})
    return _result("MANTIS","PHASE_DUPLICATE_PRUNE",{"kept_state_ids":[s.state_id for s in kept],"dropped":dropped,"epsilon":epsilon},[s.state_id for s in states])

def fox_plan(start:PhaseState36,goal:PhaseState36,*,steps:int=8)->dict[str,object]:
    if steps<1 or steps>1024: raise PhaseGateError("invalid FOX step count")
    path=[start]+[PhaseState36([_wrap(a+(k/steps)*circular_delta(b,a)) for a,b in zip(start.theta,goal.theta)]) for k in range(1,steps+1)]
    ds=[torus_distance(s.theta,goal.theta) for s in path]
    return _result("FOX","GEODESIC_PHASE_PLAN",{"path_state_ids":[s.state_id for s in path],"goal_distances":ds,"monotone":all(b<=a+1e-12 for a,b in zip(ds,ds[1:]))},[start.state_id,goal.state_id])

def beaver_construct(parts:Sequence[PhaseState36],weights:Sequence[float]|None=None)->dict[str,object]:
    theta=circular_mean([p.theta for p in parts],weights); c=PhaseState36(theta)
    return _result("BEAVER","CANDIDATE_PHASE_CONSTRUCTION",{"candidate_state_id":c.state_id,"theta":list(c.theta),"part_residuals":[torus_distance(c.theta,p.theta) for p in parts]},[p.state_id for p in parts])

def _centroid_phase(s:PhaseState36)->float:
    z=sum(cmath.exp(1j*x) for x in s.theta)/DIM
    return 0.0 if abs(z)<1e-15 else _wrap(cmath.phase(z))

def _unwrap(values:Sequence[float])->list[float]:
    if not values:return []
    out=[values[0]]
    for x in values[1:]: out.append(out[-1]+circular_delta(x,_wrap(out[-1])))
    return out

def bat_scan(history:Sequence[PhaseState36])->dict[str,object]:
    if len(history)<4: raise PhaseGateError("BAT requires at least four samples")
    p=_unwrap([_centroid_phase(s) for s in history]); mean=sum(p)/len(p); sig=[x-mean for x in p]; n=len(sig)
    powers=[]
    for k in range(1,n//2+1):
        z=sum(sig[t]*cmath.exp(-2j*math.pi*k*t/n) for t in range(n)); powers.append((abs(z)**2/(n*n),k))
    power,h=max(powers); total=sum(x for x,_ in powers)
    return _result("BAT","WEAK_PHASE_SPECTRAL_SCAN",{"dominant_harmonic":h,"dominant_power":power,"power_fraction":0.0 if total==0 else power/total},[s.state_id for s in history])

def canary_watch(history:Sequence[PhaseState36],*,slack:float=.01,threshold:float=.5)->dict[str,object]:
    if len(history)<3: raise PhaseGateError("CANARY requires at least three samples")
    speeds=[torus_distance(a.theta,b.theta)/math.sqrt(DIM) for a,b in zip(history,history[1:])]
    base=speeds[0]; c=peak=0.0
    for speed in speeds[1:]: c=max(0.0,c+(speed-base)-slack); peak=max(peak,c)
    return _result("CANARY","PHASE_CUSUM_SENTINEL",{"baseline_speed":base,"peak_cusum":peak,"threshold":threshold,"verdict":"BLOCK_CANDIDATE" if peak>threshold else "PASS"},[s.state_id for s in history])

def _phase_entropy(theta:Sequence[float],bins:int=12)->float:
    counts=[0]*bins
    for x in _theta36(theta): counts[min(bins-1,int((x/TAU)*bins))]+=1
    probs=[c/DIM for c in counts if c]
    return -sum(p*math.log(p) for p in probs)/math.log(bins)

def serpent_sense(history:Sequence[PhaseState36],reference:Sequence[PhaseState36]|None=None)->dict[str,object]:
    if len(history)<2: raise PhaseGateError("SERPENT requires at least two samples")
    last,prev=history[-1],history[-2]; d=[circular_delta(a,b) for a,b in zip(last.theta,prev.theta)]
    temp=math.sqrt(sum(x*x for x in d)/DIM)
    rough=sum(abs(circular_delta(last.theta[(i+1)%DIM],last.theta[i])) for i in range(DIM))/DIM
    centroid=abs(sum(cmath.exp(1j*x) for x in last.theta)/DIM); entropy=_phase_entropy(last.theta)
    drift=sum(abs(x) for x in d)/DIM
    lock=sum(math.cos(circular_delta(last.theta[(i+1)%DIM],last.theta[i])) for i in range(DIM))/DIM
    novelty=0.0 if not reference else min(torus_distance(last.theta,r.theta) for r in reference)/math.sqrt(DIM)
    taste=(centroid,entropy,rough/math.pi,drift/math.pi,(lock+1)/2,novelty/math.pi)
    parents=[s.state_id for s in history]+([] if reference is None else [s.state_id for s in reference])
    return _result("SERPENT","LATENT_FIELD_TASTE_TEMPERATURE",{"temperature":temp,"taste_signature":list(taste),"novelty":novelty},parents)

def _chameleon_profile(profile_id:str)->tuple[tuple[int,...],tuple[float,...]]:
    label=str(profile_id).strip()
    if not label: raise PhaseGateError("profile_id required")
    keys=[(hashlib.sha256(f"{label}:{i}".encode()).digest(),i) for i in range(DIM)]
    return tuple(i for _,i in sorted(keys)),_carrier36("CHAMELEON:"+label)

def chameleon_skin(s:PhaseState36,profile_id:str)->PhaseState36:
    p,o=_chameleon_profile(profile_id); return PhaseState36([_wrap(s.theta[src]+o[i]) for i,src in enumerate(p)])

def chameleon_unskin(s:PhaseState36,profile_id:str)->PhaseState36:
    p,o=_chameleon_profile(profile_id); original=[0.0]*DIM
    for i,src in enumerate(p): original[src]=_wrap(s.theta[i]-o[i])
    return PhaseState36(original)

def chameleon_transform(s:PhaseState36,profile_id:str)->dict[str,object]:
    sk=chameleon_skin(s,profile_id)
    return _result("CHAMELEON","REVERSIBLE_PHASE_SKIN_NOT_CRYPTOGRAPHY",{"profile_id":profile_id,"skinned_state_id":sk.state_id,"theta":list(sk.theta),"cryptographic_claim":False},[s.state_id])

def belzebub_synthesize(states:Sequence[PhaseState36])->dict[str,object]:
    if not states: raise PhaseGateError("BELZEBUB requires candidates")
    _,mi=min((sum(torus_distance(s.theta,o.theta) for o in states),i) for i,s in enumerate(states))
    medoid=states[mi]; ranked=sorted(states,key=lambda s:torus_distance(s.theta,medoid.theta)); kept=ranked[:max(1,math.ceil(.75*len(ranked)))]
    c=PhaseState36(circular_mean([s.theta for s in kept]))
    return _result("BELZEBUB","DEFENSIVE_PHASE_SYNTHESIS",{"medoid_state_id":medoid.state_id,"kept_state_ids":[s.state_id for s in kept],"candidate_state_id":c.state_id,"theta":list(c.theta)},[s.state_id for s in states])

def gremlin_aggregate(states:Sequence[PhaseState36])->dict[str,object]:
    if not states: raise PhaseGateError("GREMLIN requires verified heads")
    a=PhaseState36(circular_mean([s.theta for s in states]))
    return _result("GREMLIN","VERIFIED_HEAD_AGGREGATION_CANDIDATE",{"aggregate_state_id":a.state_id,"theta":list(a.theta),"mean_disagreement":sum(torus_distance(a.theta,s.theta) for s in states)/len(states)},[s.state_id for s in states])

def ferret_authorize(*,explicit_authorization:bool,scope_match:bool,receipt_valid:bool,action_commitment:str)->dict[str,object]:
    c=str(action_commitment).strip()
    if not c: raise PhaseGateError("action_commitment required")
    admitted=bool(explicit_authorization and scope_match and receipt_valid)
    return _result("FERRET","AUTHORITY_BOUNDARY_ONLY",{"action_commitment":c,"verdict":"ADMITTED" if admitted else "BLOCK","external_action_executed":False},[])

def species_manifest()->dict[str,object]:
    return {"contract_id":CONTRACT_ID,"dimension":DIM,"space":"T^36",
            "species":[{"name":n,"realization_mode":REALIZATION_MODE[n],"carrier_sha256":_sha(list(_carrier36(n)))} for n in SPECIES],
            "semantic_axis_assignment":False,"fully_analog_physical_claim":False,"external_effects":False}


def phase_gate_vectorization_manifest() -> dict[str, object]:
    return {
        "schema": "GREMLIN_BESTIARY_PHASENAV_VECTOR_GATE_MANIFEST_V0_1",
        "contract_id": CONTRACT_ID,
        "dimension": DIM,
        "space": "T^36",
        "numpy_available": np is not None,
        "scalar_reference": True,
        "vectorized_batch_realization": np is not None,
        "semantic_identity_modified": False,
        "authority_modified": False,
        "physical_analog_claim": False,
    }


def run_full_bestiary_reference_sweep() -> dict[str, object]:
    """Exercise every declared species on one deterministic frozen fixture.

    The sweep is a conformance harness, not a claim that all specialist
    semantics are physically analog.  FERRET is deliberately exercised in a
    blocked state.
    """
    base = PhaseState36([_wrap(0.10 + 0.017 * i) for i in range(DIM)])
    near = PhaseState36([_wrap(x + 0.02) for x in base.theta])
    mid = PhaseState36([_wrap(x + 0.21 * math.sin(i + 1.0)) for i, x in enumerate(base.theta)])
    far = PhaseState36([_wrap(2.4 + 0.071 * i) for i in range(DIM)])
    history = tuple(
        PhaseState36([_wrap(x + 0.03 * t + 0.04 * math.sin(2.0 * math.pi * 3 * t / 16.0)) for x in base.theta])
        for t in range(16)
    )

    receipts: dict[str, dict[str, object]] = {}
    receipts["HUMMINGBIRD"] = hummingbird_capture(base)
    receipts["OCTOPUS"] = octopus_route(base, [n for n in SPECIES if n not in {"HUMMINGBIRD","OCTOPUS","BELZEBUB","GREMLIN","FERRET"}], max_species=4, min_score=0.0)
    receipts["SPIDER"] = spider_scan([base, near, far], threshold=0.8)
    receipts["RAVEN"] = raven_recall(base, [far, near, base], k=2)
    receipts["HOUND"] = hound_scan(mid, base)
    receipts["MOLE"] = mole_relax(base, near, steps=8)
    receipts["OWL"] = owl_audit(base, [near, mid])
    receipts["ANT"] = ant_enumerate(base, axes=(0,1), delta=0.10, budget=5)
    receipts["MANTIS"] = mantis_prune([base, PhaseState36(base.theta), near], epsilon=1e-12)
    receipts["FOX"] = fox_plan(base, near, steps=4)
    receipts["BEAVER"] = beaver_construct([base, near])
    receipts["BAT"] = bat_scan(history)
    receipts["CANARY"] = canary_watch(history, slack=0.001, threshold=4.0)
    receipts["SERPENT"] = serpent_sense(history, reference=[base, near])
    receipts["CHAMELEON"] = chameleon_transform(base, "reference-sweep-v0.1")
    receipts["BELZEBUB"] = belzebub_synthesize([base, near, mid])
    receipts["GREMLIN"] = gremlin_aggregate([base, near])
    receipts["FERRET"] = ferret_authorize(
        explicit_authorization=False,
        scope_match=True,
        receipt_valid=True,
        action_commitment="reference-sweep-no-effect",
    )

    missing = [name for name in SPECIES if name not in receipts]
    if missing:
        raise PhaseGateError(f"full Bestiary sweep missing species: {missing}")
    if any(rec.get("external_effects") is not False or rec.get("canon_allowed") is not False for rec in receipts.values()):
        raise PhaseGateError("Bestiary sweep crossed candidate-only authority boundary")

    return {
        "schema": "GREMLIN_BESTIARY_FULL_REFERENCE_SWEEP_V0_1",
        "contract_id": CONTRACT_ID,
        "species_count": len(SPECIES),
        "species": list(SPECIES),
        "receipt_sha256_by_species": {name: str(receipts[name]["receipt_sha256"]) for name in SPECIES},
        "ferret_verdict": receipts["FERRET"]["data"]["verdict"],
        "external_effects": False,
        "canon_allowed": False,
        "physical_analog_claim": False,
        "receipt_sha256": _sha({
            "contract_id": CONTRACT_ID,
            "species": list(SPECIES),
            "receipt_sha256_by_species": {name: str(receipts[name]["receipt_sha256"]) for name in SPECIES},
        }),
    }
