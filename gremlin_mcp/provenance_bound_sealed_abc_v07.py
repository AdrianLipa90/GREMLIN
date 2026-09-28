from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .recursive_residual_v04 import _sha_array
from .sealed_abc_residual_v06 import sealed_abc_residual_confirmation_v06

SCHEMA="GREMLIN_PROVENANCE_BOUND_SEALED_ABC_V0_7"
VERSION="0.7.0"

_DEFAULT_TRUSTED_AUTHORITIES=(
    "NOEMA_ACQUISITION_BOUND",
    "EXTERNAL_INSTRUMENT_RAW",
    "PREACQUISITION_COMMIT",
)


def _is_sha256(value:Any)->bool:
    return (
        isinstance(value,str)
        and len(value)==64
        and all(ch in "0123456789abcdef" for ch in value.lower())
    )


def _validate_provenance(
    components:Mapping[str,np.ndarray],
    provenance_receipts:Mapping[str,Mapping[str,Any]],
    *,
    analysis_plan_sha256:str,
    trusted_authorities:Sequence[str],
)->dict[str,Any]:
    trusted=set(str(x) for x in trusted_authorities)
    if not trusted:
        raise ValueError("trusted provenance authority set is empty")

    summary={}
    for name,component in components.items():
        receipt=provenance_receipts.get(name)
        if not isinstance(receipt,Mapping):
            raise ValueError(f"missing provenance receipt for {name}")
        if receipt.get("schema")!="GREMLIN_NUISANCE_SOURCE_PROVENANCE_V0_1":
            raise ValueError(f"unsupported provenance schema for {name}")
        if receipt.get("authority") not in trusted:
            raise ValueError(f"untrusted provenance authority for {name}")
        if receipt.get("source_is_independent_acquisition") is not True:
            raise ValueError(f"source independence not established for {name}")
        if receipt.get("target_derived") is not False:
            raise ValueError(f"target-derived provenance for {name}")
        if receipt.get("construction_rule_frozen_before_target_fit") is not True:
            raise ValueError(f"construction rule not frozen before fit for {name}")
        if receipt.get("receipt_bound_before_target_fit") is not True:
            raise ValueError(f"provenance receipt not bound before fit for {name}")
        if receipt.get("bound_analysis_plan_sha256")!=analysis_plan_sha256.lower():
            raise ValueError(f"analysis-plan provenance mismatch for {name}")

        candidate_sha=_sha_array(component)
        if receipt.get("candidate_payload_sha256")!=candidate_sha:
            raise ValueError(f"candidate payload hash mismatch for {name}")
        if not _is_sha256(receipt.get("source_receipt_sha256")):
            raise ValueError(f"invalid source receipt hash for {name}")
        if receipt.get("source_capture_relation") not in {
            "SIMULTANEOUS_INDEPENDENT_SENSOR",
            "PREACQUISITION_TEMPLATE",
            "EXTERNAL_DATASET",
        }:
            raise ValueError(f"unsupported source capture relation for {name}")

        summary[name]={
            "authority":receipt["authority"],
            "candidate_payload_sha256":candidate_sha,
            "source_receipt_sha256":receipt["source_receipt_sha256"].lower(),
            "source_capture_relation":receipt["source_capture_relation"],
            "bound_analysis_plan_sha256":analysis_plan_sha256.lower(),
        }

    bundle_sha256=hashlib.sha256(
        json.dumps(summary,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    return {
        "candidates":summary,
        "provenance_bundle_sha256":bundle_sha256,
        "trusted_authorities":sorted(trusted),
    }


def provenance_bound_sealed_abc_v07(
    raw_runs:Sequence[Sequence[float]],
    initial_model_runs:Sequence[Sequence[float]],
    nuisance_components:Mapping[str,Sequence[Sequence[float]]],
    nuisance_metadata:Mapping[str,Mapping[str,Any]],
    provenance_receipts:Mapping[str,Mapping[str,Any]],
    *,
    discovery_runs:Sequence[int],
    confirmation_runs:Sequence[int],
    replication_runs:Sequence[int],
    analysis_plan_sha256:str,
    analysis_plan_frozen_before_fit:bool,
    **kwargs:Any,
)->tuple[dict[str,Any],np.ndarray,np.ndarray]:
    if not _is_sha256(analysis_plan_sha256):
        raise ValueError("analysis_plan_sha256 must be a 64-character hex digest")
    if analysis_plan_frozen_before_fit is not True:
        raise ValueError("analysis plan was not frozen before fit")

    components={
        str(name):np.asarray(value,float)
        for name,value in nuisance_components.items()
    }
    provenance=_validate_provenance(
        components,
        provenance_receipts,
        analysis_plan_sha256=analysis_plan_sha256,
        trusted_authorities=_DEFAULT_TRUSTED_AUTHORITIES,
    )

    result,model,residual=sealed_abc_residual_confirmation_v06(
        raw_runs,
        initial_model_runs,
        components,
        nuisance_metadata,
        discovery_runs=discovery_runs,
        confirmation_runs=confirmation_runs,
        replication_runs=replication_runs,
        analysis_plan_sha256=analysis_plan_sha256,
        analysis_plan_frozen_before_fit=True,
        **kwargs,
    )

    out={
        **result,
        "schema":SCHEMA,
        "version":VERSION,
        "source_provenance":provenance,
        "policy":{
            **result["policy"],
            "candidate_source_receipt_required":True,
            "candidate_payload_hash_bound":True,
            "independent_source_lineage_required":True,
            "construction_rule_frozen_before_fit_required":True,
            "provenance_authority_allowlist_versioned_in_code":True,
            "provenance_authority_trust_external":True,
            "forged_trusted_authority_receipt_not_detectable_locally":True,
        },
    }
    out["provenance_bound_confirmation_sha256"]=hashlib.sha256(
        json.dumps(out,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    return out,model,residual


__all__=["SCHEMA","VERSION","provenance_bound_sealed_abc_v07"]
