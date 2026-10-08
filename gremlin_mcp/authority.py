from __future__ import annotations

from typing import Any

SCHEMA = "GREMLIN_AUTHORITY_DIRECTION_V0_1"
REQUEST_SCHEMA = "GREMLIN_REQUEST_ADMISSION_V0_1"

AUTHORITY_ORDER = ("OPERATOR", "GREMLIN", "AI_CLIENT")


def gremlin_system_authority() -> dict[str, Any]:
    """Canonical GREMLIN system authority.

    This describes what GREMLIN is allowed to supervise and execute inside its
    own governed runtime. It is deliberately separate from whether one MCP/AI
    request has been admitted to cause an external effect.
    """
    return {
        "schema": SCHEMA,
        "authority_order": list(AUTHORITY_ORDER),
        "supervision_authority": "ACTIVE",
        "internal_execution": "ACTIVE",
        "internal_write": "ACTIVE",
        "external_mutation_capability": "AVAILABLE",
        "canon_promotion_capability": "AVAILABLE",
        "ai_self_authorization": False,
        "ai_override_gremlin": False,
        "mcp_self_grants_authority": False,
    }


def request_admission_state(
    *,
    external_effect_admitted: bool = False,
    canon_promotion_admitted: bool = False,
    mutation_authorized: bool = False,
    admission_basis: str = "NONE",
) -> dict[str, Any]:
    """Per-request admission state; never a statement that GREMLIN lacks capability."""
    if mutation_authorized and not external_effect_admitted:
        raise ValueError("mutation authorization requires external-effect admission")
    return {
        "schema": REQUEST_SCHEMA,
        "external_effect_admitted": bool(external_effect_admitted),
        "canon_promotion_admitted": bool(canon_promotion_admitted),
        "mutation_authorized": bool(mutation_authorized),
        "admission_basis": str(admission_basis),
        "self_granted": False,
    }


def authority_envelope(
    *,
    external_effect_admitted: bool = False,
    canon_promotion_admitted: bool = False,
    mutation_authorized: bool = False,
    admission_basis: str = "NONE",
) -> dict[str, Any]:
    return {
        "schema": "GREMLIN_AUTHORITY_ENVELOPE_V0_1",
        "system": gremlin_system_authority(),
        "request": request_admission_state(
            external_effect_admitted=external_effect_admitted,
            canon_promotion_admitted=canon_promotion_admitted,
            mutation_authorized=mutation_authorized,
            admission_basis=admission_basis,
        ),
    }


__all__ = [
    "AUTHORITY_ORDER",
    "REQUEST_SCHEMA",
    "SCHEMA",
    "authority_envelope",
    "gremlin_system_authority",
    "request_admission_state",
]
