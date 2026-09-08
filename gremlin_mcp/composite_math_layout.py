from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from typing import Any, Iterable, Mapping

from gremlin_mcp.math_token_normalize import normalize_math_tokens

SCHEMA = "GREMLIN_COMPOSITE_2D_MATH_LAYOUT_V0_1"
VERSION = "0.3.2"
_LABEL_RE = re.compile(r"^\(\d+\.\d+(?:\.\d+)?\)$")
_RELATIONS = {"=", "≈"}
_OPERATORS = {"+", "-", "*", "/", "≈", "=", "<", ">", "<=", ">="}

def _authority(): return {"production_runtime_write":False,"execution_admitted":False,"canon_allowed":False}
def _canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def _commit(d,v): return hashlib.blake2b(d+b"\0"+_canonical(v),digest_size=32).hexdigest()
def _norm(t): return str(t).strip().replace("×","*").replace("·","*").replace("⋅","*").replace("−","-").replace("–","-")
def _cx(r): return (float(r["bbox"][0])+float(r["bbox"][2]))/2
def _cy(r): return (float(r["bbox"][1])+float(r["bbox"][3]))/2
def _height(r): return max(float(r["bbox"][3])-float(r["bbox"][1]),1e-9)
def _x_overlap(a,b):
    ax0,_,ax1,_=map(float,a["bbox"]); bx0,_,bx1,_=map(float,b["bbox"]); return max(0,min(ax1,bx1)-max(ax0,bx0))/max(min(ax1-ax0,bx1-bx0),1e-9)
def _operand_like(t): return bool(str(t).strip()) and str(t).strip() not in _OPERATORS and str(t).strip() not in {"(","[","{"}
def _closing_with_script(t): return any(str(t).strip().startswith(p) for p in (")**","]**","}**",")_","]_","}_"))

def _validate(spans):
    rows=[]
    for raw in spans:
        text=str(raw.get("text") or "").strip()
        if not text: continue
        bbox=[float(v) for v in list(raw.get("bbox") or [])]
        if len(bbox)!=4 or any(not math.isfinite(v) for v in bbox): raise ValueError("span bbox must contain four finite coordinates")
        if bbox[2]<bbox[0] or bbox[3]<bbox[1]: raise ValueError("span bbox coordinates are inverted")
        size=float(raw.get("size") or max(bbox[3]-bbox[1],1.0))
        if not math.isfinite(size) or size<=0: raise ValueError("span size must be positive and finite")
        rows.append({"text":text,"bbox":bbox,"size":size})
    return rows

def _join_tokens(tokens):
    clean=list(normalize_math_tokens(tokens)["tokens"])
    if not clean:return ""
    out=clean[0];prev=clean[0]
    for token in clean[1:]:
        if token in {')',']','}'} or _closing_with_script(token): out+=token
        elif prev in {'(','[','{'}: out+=token
        elif _operand_like(prev) and _operand_like(token): out+="*"+token
        else: out+=" "+token
        prev=token
    return " ".join(out.split())

def _nearest_left_base(script,main,reference_size):
    sx0=float(script["bbox"][0]);limit=max(6.0,reference_size*.85)
    candidates=[r for r in main if float(r["bbox"][2])<=sx0+1 and sx0-float(r["bbox"][2])<=limit]
    if not candidates:return None
    return min(candidates,key=lambda r:(abs(_cy(script)-_cy(r)),max(0.0,sx0-float(r["bbox"][2]))))

def _group_scripts(rows,reference_size):
    threshold=reference_size*.84;small=sorted([dict(r) for r in rows if float(r["size"])<=threshold],key=lambda r:(float(r["bbox"][0]),_cy(r)));main=[dict(r) for r in rows if float(r["size"])>threshold];constructs=[]
    if not small or not main:return main+small,constructs
    assigned=defaultdict(list);unattached=[]
    for script in small:
        base=_nearest_left_base(script,main,reference_size)
        if base is None:unattached.append(script)
        else:assigned[id(base)].append(script)
    for base in main:
        glyphs=assigned.get(id(base),[])
        if not glyphs:continue
        sides=defaultdict(list)
        for g in glyphs:sides["SUPERSCRIPT" if _cy(g)<_cy(base) else "SUBSCRIPT"].append(g)
        for side,group in sides.items():
            centers=[_cy(r) for r in group]
            if max(centers)-min(centers)>max(2.0,reference_size*.35):unattached.extend(group);continue
            script_text="".join(_norm(r["text"]) for r in sorted(group,key=lambda r:float(r["bbox"][0])))
            if not script_text:unattached.extend(group);continue
            base["text"]=f"{_norm(base['text'])}{'**' if side=='SUPERSCRIPT' else '_'}{script_text}";constructs.append(side)
    return main+unattached,constructs

def _y_clusters(rows,tolerance):
    if not rows:return []
    ordered=sorted(rows,key=lambda r:(_cy(r),float(r["bbox"][0])));clusters=[[ordered[0]]]
    for row in ordered[1:]:
        center=statistics.mean(_cy(v) for v in clusters[-1])
        if abs(_cy(row)-center)<=tolerance: clusters[-1].append(row)
        else: clusters.append([row])
    return clusters

def _render_horizontal(rows): return _join_tokens([str(r["text"]) for r in sorted(rows,key=lambda r:(float(r["bbox"][0]),float(r["bbox"][1])))])
def _has_connector(rows): return any(_norm(r["text"]) in _OPERATORS for r in rows)

def _render_segment(rows,reference_size):
    if not rows:return None,[],"EMPTY_RELATION_SEGMENT"
    scripted,constructs=_group_scripts(rows,reference_size);clusters=_y_clusters(scripted,max(2.0,statistics.median([_height(r) for r in scripted])*.42))
    if len(clusters)==1:return _render_horizontal(clusters[0]),constructs,None
    if len(clusters)!=2:return None,constructs,"MORE_THAN_TWO_PRIMARY_VERTICAL_LEVELS"
    upper,lower=clusters
    if statistics.mean(_cy(r) for r in upper)>=statistics.mean(_cy(r) for r in lower):upper,lower=lower,upper
    if max((_x_overlap(a,b) for a in upper for b in lower),default=0)<.20:return None,constructs,"VERTICAL_LEVELS_NOT_FRACTION_ALIGNED"
    if len(upper)>1 and len(lower)>1 and not _has_connector(upper) and not _has_connector(lower):
        ux=sorted(float(r["bbox"][0]) for r in upper);lx=sorted(float(r["bbox"][0]) for r in lower);limit=max(8.0,reference_size*1.5)
        if any(b-a>limit for a,b in zip(ux,ux[1:])) and any(b-a>limit for a,b in zip(lx,lx[1:])):return None,constructs,"MULTIPLE_UNCONNECTED_VERTICAL_STACKS"
    n=_render_horizontal(upper);d=_render_horizontal(lower)
    if not n or not d:return None,constructs,"EMPTY_FRACTION_COMPONENT"
    constructs.append("STACKED_FRACTION");return f"({n})/({d})",constructs,None

def _status(*,status,linear_text,relation_count,constructs,flags,rows,page_number,equation_label):
    core={"schema":SCHEMA,"version":VERSION,"status":status,"linear_text":linear_text,"relation_count":int(relation_count),"constructs":sorted(set(constructs)),"flags":flags,"source_locator":f"page:{page_number}:eq:{equation_label}","provenance":{"page_number":int(page_number),"equation_label":str(equation_label),"spans":rows},"scope_boundary":["TOP_LEVEL_RELATIONS_MUST_BE_EXPLICIT_SPANS","COMPOSITE_SOLVER_SUPPORTS_ONE_OR_TWO_PRIMARY_VERTICAL_LEVELS_PER_RELATION_SEGMENT","SMALL_GLYPHS_BIND_TO_NEAREST_LEFT_GEOMETRIC_BASE_USING_2D_PROXIMITY","TWO_ALIGNED_PRIMARY_LEVELS_MAY_FORM_ONE_STACKED_FRACTION","MULTIPLE_UNCONNECTED_VERTICAL_STACKS_REMAIN_UNRESOLVED","LEXICAL_NORMALIZATION_RUNS_ONLY_AFTER_GEOMETRIC_RECOVERY","THREE_OR_MORE_PRIMARY_VERTICAL_LEVELS_REMAIN_UNRESOLVED","NO_SEMANTIC_OR_PHYSICAL_GUESSING","NO_OCR_REPAIR","NO_AUTOMATIC_CANON_PROMOTION"],"authority":_authority()};core["solver_commitment"]=_commit(b"GREMLIN-COMPOSITE-2D-MATH/v0.1",core);return core

def solve_composite_2d_equation(spans:Iterable[Mapping[str,Any]],*,page_number:int,equation_label:str)->dict[str,Any]:
    page=int(page_number)
    if page<1:raise ValueError("page_number must be >= 1")
    label=str(equation_label).strip()
    if not label:raise ValueError("equation_label must be non-empty")
    rows=_validate(spans)
    if not any(r["text"]==label for r in rows):return _status(status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED",linear_text=None,relation_count=0,constructs=[],flags=["EQUATION_LABEL_NOT_FOUND"],rows=rows,page_number=page,equation_label=label)
    content=[r for r in rows if r["text"]!=label];relations=sorted([r for r in content if _norm(r["text"]) in _RELATIONS],key=lambda r:float(r["bbox"][0]))
    if not relations:return _status(status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED",linear_text=None,relation_count=0,constructs=[],flags=["NO_EXPLICIT_TOP_LEVEL_RELATION"],rows=rows,page_number=page,equation_label=label)
    ref=statistics.median(float(r["size"]) for r in relations);segments=[];left=-math.inf
    for rel in relations:
        right=float(rel["bbox"][0]);segments.append([r for r in content if r not in relations and _cx(r)>left and _cx(r)<right]);left=float(rel["bbox"][2])
    segments.append([r for r in content if r not in relations and _cx(r)>left]);rendered=[];constructs=[]
    for i,segment in enumerate(segments):
        text,found,error=_render_segment(segment,ref);constructs.extend(found)
        if error or not text:return _status(status="AMBIGUOUS_COMPOSITE_2D_UNRESOLVED",linear_text=None,relation_count=len(relations),constructs=constructs,flags=[f"SEGMENT_{i}_{error or 'UNRENDERABLE'}"],rows=rows,page_number=page,equation_label=label)
        rendered.append(text)
    output=rendered[0]
    for rel,text in zip(relations,rendered[1:]):output+=f" {_norm(rel['text'])} {text}"
    return _status(status="SOLVED_COMPOSITE_2D",linear_text=output,relation_count=len(relations),constructs=constructs,flags=["GEOMETRIC_COMPOSITE_RECONSTRUCTION"],rows=rows,page_number=page,equation_label=label)
