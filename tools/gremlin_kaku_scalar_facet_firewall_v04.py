from __future__ import annotations

import json
import math
from typing import Any, Mapping

from tools.gremlin_kaku_scalar_facets_v04 import (
    TAU,
    KakuScalarFacetError,
    build_affect_vad_facets_v04,
    validate_affect_vad_facets_v04,
    validate_intention_alignment_candidate_v04,
    validate_intention_target_phase_v04,
)


class KakuScalarFacetFirewallError(KakuScalarFacetError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _wrap_pi(value: float) -> float:
    return (value + math.pi) % TAU - math.pi


def validate_recomputed_affect_vad_facets_v04(packet: Mapping[str, Any]) -> bool:
    validate_affect_vad_facets_v04(packet)
    facets = packet["facets"]
    rebuilt = build_affect_vad_facets_v04(
        term=str(packet["term"]),
        valence=float.fromhex(str(facets["valence"]["value_f64_hex"])),
        arousal=float.fromhex(str(facets["arousal"]["value_f64_hex"])),
        dominance=float.fromhex(str(facets["dominance"]["value_f64_hex"])),
        confidence=float.fromhex(str(facets["confidence"]["value_f64_hex"])),
        source_ref=str(packet["source_ref"]),
        epistemic_status=str(packet["epistemic_status"]),
    )
    if _canonical(packet) != _canonical(rebuilt):
        raise KakuScalarFacetFirewallError("affect packet differs from recomputed VAD facet realization")
    return True


def validate_recomputed_intention_alignment_v04(record: Mapping[str, Any]) -> bool:
    validate_intention_alignment_candidate_v04(record)
    anchor = float.fromhex(str(record["anchor_phase_rad_f64_hex"]))
    target = float.fromhex(str(record["target_phase_rad_f64_hex"]))
    stored_delta = float.fromhex(str(record["wrapped_delta_rad_f64_hex"]))
    stored_signed = float.fromhex(str(record["signed_cosine_alignment_f64_hex"]))
    stored_lock = float.fromhex(str(record["lock_alignment_01_f64_hex"]))

    expected_delta = _wrap_pi(anchor - target)
    expected_signed = math.cos(expected_delta)
    expected_lock = 0.5 * (1.0 + expected_signed)

    if abs(stored_delta - expected_delta) > 1e-15:
        raise KakuScalarFacetFirewallError("intention wrapped delta differs from anchor-target recomputation")
    if abs(stored_signed - expected_signed) > 1e-15:
        raise KakuScalarFacetFirewallError("intention signed alignment differs from cosine recomputation")
    if abs(stored_lock - expected_lock) > 1e-15:
        raise KakuScalarFacetFirewallError("intention lock alignment differs from phase-lock recomputation")
    return True


def validate_target_phase_canonical_v04(target: Mapping[str, Any]) -> bool:
    validate_intention_target_phase_v04(target)
    phase = float.fromhex(str(target["target_phase_rad_f64_hex"]))
    if phase < 0.0 or phase >= TAU:
        raise KakuScalarFacetFirewallError("target phase is outside canonical [0,2pi) domain")
    return True
