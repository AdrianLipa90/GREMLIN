from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .joint_family_null_v15 import joint_family_round_v15

SCHEMA_SEAL="GREMLIN_CANDIDATE_BANK_SEAL_V0_16"
SCHEMA_TARGET="GREMLIN_TARGET_ACCESS_RECEIPT_V0_16"
SCHEMA_RESULT="GREMLIN_SEALED_CANDIDATE_BANK_RESULT_V0_16"
VERSION="0.16.0"

_ALLOWED_SOURCE_TYPES={
    "instrument_channel",
    "environment_channel",
    "clock_channel",
    "preregistered_template",
    "known_systematic_template",
}
_ALLOWED_PROVENANCE_AUTHORITIES={
    "GIT_COMMIT",
    "NOEMA_APPEND_ONLY_RECEIPT",
    "EXTERNAL_TIMESTAMPED_MANIFEST",
}


def _sha_array(x:np.ndarray)->str:
    a=np.ascontiguousarray(np.asarray(x,dtype=np.float64))
    h=hashlib.sha256(); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def _canonical_sha(payload:Mapping[str,Any])->str:
    return hashlib.sha256(
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()


def _validate_hex64(value:Any,name:str)->str:
    if (
        not isinstance(value,str)
        or len(value)!=64
        or any(ch not in "0123456789abcdef" for ch in value.lower())
    ):
        raise ValueError(f"{name} must be a 64-character hex digest")
    return value.lower()


def _canonical_bank_payload(
    candidate_components:Mapping[str,Sequence[Sequence[float]]],
    candidate_metadata:Mapping[str,Mapping[str,Any]],
    analysis_plan_sha256:str,
)->dict[str,Any]:
    plan=_validate_hex64(analysis_plan_sha256,"analysis_plan_sha256")
    names=sorted(str(name) for name in candidate_components)
    if not names:
        raise ValueError("candidate bank is empty")

    entries=[]
    for name in names:
        c=np.asarray(candidate_components[name],float)
        if c.ndim!=2 or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid candidate array {name}")
        m=candidate_metadata.get(name)
        if not isinstance(m,Mapping):
            raise ValueError(f"missing candidate metadata {name}")
        if m.get("frozen_before_fit") is not True:
            raise ValueError(f"candidate {name} was not frozen before fit")
        if m.get("independent_of_target_fit") is not True:
            raise ValueError(f"candidate {name} is target-derived by declaration")
        if m.get("source_type") not in _ALLOWED_SOURCE_TYPES:
            raise ValueError(f"unsupported source_type for {name}")
        if not isinstance(m.get("source_id"),str) or not m["source_id"]:
            raise ValueError(f"missing source_id for {name}")
        if m.get("null_policy") not in {"run_permutation","sample_circular_shift"}:
            raise ValueError(f"unsupported null_policy for {name}")
        source_commitment=_validate_hex64(
            m.get("source_commitment_sha256"),
            f"source_commitment_sha256 for {name}",
        )
        entries.append({
            "name":name,
            "component_sha256":_sha_array(c),
            "shape":list(c.shape),
            "metadata":{
                "frozen_before_fit":True,
                "independent_of_target_fit":True,
                "source_type":str(m["source_type"]),
                "source_id":str(m["source_id"]),
                "source_commitment_sha256":source_commitment,
                "null_policy":str(m["null_policy"]),
            },
        })

    return {
        "analysis_plan_sha256":plan,
        "candidate_entries":entries,
    }


def seal_candidate_bank_v16(
    candidate_components:Mapping[str,Sequence[Sequence[float]]],
    candidate_metadata:Mapping[str,Mapping[str,Any]],
    *,
    analysis_plan_sha256:str,
    sealed_unix_ns:int,
    provenance_authority:str,
    provenance_evidence_id:str,
    provenance_evidence_sha256:str,
    external_verification_receipt_sha256:str,
)->dict[str,Any]:
    if provenance_authority not in _ALLOWED_PROVENANCE_AUTHORITIES:
        raise ValueError("unsupported provenance authority")
    if not isinstance(provenance_evidence_id,str) or not provenance_evidence_id:
        raise ValueError("missing provenance evidence id")
    if not isinstance(sealed_unix_ns,int) or sealed_unix_ns<=0:
        raise ValueError("sealed_unix_ns must be positive integer")

    payload=_canonical_bank_payload(
        candidate_components,candidate_metadata,analysis_plan_sha256
    )
    seal={
        "schema":SCHEMA_SEAL,
        "version":VERSION,
        **payload,
        "sealed_unix_ns":int(sealed_unix_ns),
        "provenance":{
            "authority":provenance_authority,
            "evidence_id":provenance_evidence_id,
            "evidence_sha256":_validate_hex64(
                provenance_evidence_sha256,"provenance_evidence_sha256"
            ),
            "external_verification_receipt_sha256":_validate_hex64(
                external_verification_receipt_sha256,
                "external_verification_receipt_sha256",
            ),
        },
        "claim_boundary":{
            "seal_proves_external_timestamp_truth":False,
            "seal_proves_causal_independence":False,
        },
    }
    seal["candidate_bank_sha256"]=_canonical_sha(payload)
    seal["seal_sha256"]=_canonical_sha(seal)
    return seal


def validate_target_access_receipt_v16(
    receipt:Mapping[str,Any],
    *,
    raw:np.ndarray,
    initial_model:np.ndarray,
)->dict[str,Any]:
    if not isinstance(receipt,Mapping) or receipt.get("schema")!=SCHEMA_TARGET:
        raise ValueError("unsupported target access receipt")
    if receipt.get("externally_verified") is not True:
        raise ValueError("target access receipt is not externally verified")
    raw_sha=_sha_array(raw)
    model_sha=_sha_array(initial_model)
    if receipt.get("raw_sha256")!=raw_sha:
        raise ValueError("target raw commitment mismatch")
    if receipt.get("initial_model_sha256")!=model_sha:
        raise ValueError("target model commitment mismatch")
    t=receipt.get("target_first_access_unix_ns")
    if not isinstance(t,int) or t<=0:
        raise ValueError("invalid target_first_access_unix_ns")
    _validate_hex64(
        receipt.get("external_verification_receipt_sha256"),
        "target external verification receipt",
    )
    return dict(receipt)


def sealed_joint_family_round_v16(
    raw_runs:Sequence[Sequence[float]],
    initial_model_runs:Sequence[Sequence[float]],
    candidate_components:Mapping[str,Sequence[Sequence[float]]],
    candidate_metadata:Mapping[str,Mapping[str,Any]],
    *,
    bank_seal:Mapping[str,Any],
    target_access_receipt:Mapping[str,Any],
    null_count:int=127,
    familywise_alpha:float=0.05,
    min_holdout_gain:float=0.0,
    min_individual_null_margin:float=0.0,
)->dict[str,Any]:
    raw=np.asarray(raw_runs,float)
    initial=np.asarray(initial_model_runs,float)
    if raw.shape!=initial.shape or raw.ndim!=2:
        raise ValueError("raw/initial shape mismatch")

    if not isinstance(bank_seal,Mapping) or bank_seal.get("schema")!=SCHEMA_SEAL:
        raise ValueError("unsupported candidate bank seal")
    if bank_seal.get("provenance",{}).get("authority") not in _ALLOWED_PROVENANCE_AUTHORITIES:
        raise ValueError("unsupported seal provenance authority")

    target_receipt=validate_target_access_receipt_v16(
        target_access_receipt,raw=raw,initial_model=initial
    )

    sealed_payload=_canonical_bank_payload(
        candidate_components,
        candidate_metadata,
        str(bank_seal.get("analysis_plan_sha256")),
    )
    actual_bank_sha=_canonical_sha(sealed_payload)
    if actual_bank_sha!=bank_seal.get("candidate_bank_sha256"):
        raise ValueError("candidate bank differs from sealed bank")

    seal_copy={k:v for k,v in dict(bank_seal).items() if k!="seal_sha256"}
    if _canonical_sha(seal_copy)!=bank_seal.get("seal_sha256"):
        raise ValueError("candidate bank seal hash mismatch")

    seal_time=bank_seal.get("sealed_unix_ns")
    access_time=target_receipt["target_first_access_unix_ns"]
    if not isinstance(seal_time,int) or seal_time>=access_time:
        raise ValueError("candidate bank was not sealed before target access")

    raw_sha=_sha_array(raw)
    exact_target_matches=[]
    for entry in sealed_payload["candidate_entries"]:
        if entry["component_sha256"]==raw_sha:
            exact_target_matches.append(entry["name"])
    if exact_target_matches:
        raise ValueError(
            "candidate bank contains exact target RAW commitment: "
            + ",".join(exact_target_matches)
        )

    joint_meta={
        entry["name"]:{
            "null_policy":entry["metadata"]["null_policy"]
        }
        for entry in sealed_payload["candidate_entries"]
    }
    joint=joint_family_round_v15(
        raw,
        initial,
        candidate_components,
        joint_meta,
        null_count=null_count,
        familywise_alpha=familywise_alpha,
        min_holdout_gain=min_holdout_gain,
        min_individual_null_margin=min_individual_null_margin,
    )

    result={
        "schema":SCHEMA_RESULT,
        "version":VERSION,
        "status":"ADMISSIBLE_BANK_JOINT_NULL_EVALUATED",
        "candidate_bank_sha256":actual_bank_sha,
        "bank_seal_sha256":bank_seal["seal_sha256"],
        "target_raw_sha256":raw_sha,
        "target_initial_model_sha256":_sha_array(initial),
        "seal_precedes_target_access":True,
        "exact_target_hash_match_rejected":True,
        "joint_family_result":joint,
        "policy":{
            "external_provenance_receipt_required":True,
            "bank_hash_bound_to_exact_arrays_and_metadata":True,
            "exact_raw_copy_rejected_defense_in_depth":True,
            "near_copy_independence_inferred_from_values":False,
            "external_timestamp_truth_proven_by_code":False,
            "causal_independence_proven_by_code":False,
            "physical_attribution":False,
        },
    }
    result["analysis_sha256"]=_canonical_sha(result)
    return result


__all__=[
    "SCHEMA_SEAL",
    "SCHEMA_TARGET",
    "SCHEMA_RESULT",
    "seal_candidate_bank_v16",
    "validate_target_access_receipt_v16",
    "sealed_joint_family_round_v16",
]
