from __future__ import annotations

import pytest

from gremlin_mcp.product.gate import ProductAuthorizationError, ProductRuntime


def test_require_license_rejects_falsey_non_boolean_values() -> None:
    for value in ("", 0, None):
        with pytest.raises(ProductAuthorizationError, match="INVALID_REQUIRE_LICENSE:BOOLEAN_REQUIRED"):
            ProductRuntime(require_license=value)  # type: ignore[arg-type]


def test_require_license_rejects_truthy_non_boolean_values() -> None:
    for value in ("false", 1, [True]):
        with pytest.raises(ProductAuthorizationError, match="INVALID_REQUIRE_LICENSE:BOOLEAN_REQUIRED"):
            ProductRuntime(require_license=value)  # type: ignore[arg-type]


def test_unconfigured_runtime_cannot_disable_enforcement_via_falsey_string() -> None:
    with pytest.raises(ProductAuthorizationError, match="INVALID_REQUIRE_LICENSE:BOOLEAN_REQUIRED"):
        ProductRuntime.unconfigured(require_license="")  # type: ignore[arg-type]


def test_direct_runtime_rejects_non_dict_entitlement_and_profile() -> None:
    with pytest.raises(ProductAuthorizationError, match="license_payload"):
        ProductRuntime(require_license=True, license_payload=[])  # type: ignore[arg-type]
    with pytest.raises(ProductAuthorizationError, match="client_profile"):
        ProductRuntime(require_license=True, client_profile=[])  # type: ignore[arg-type]


def test_valid_explicit_unlicensed_research_mode_remains_available_only_with_real_false() -> None:
    runtime = ProductRuntime.unconfigured(require_license=False)
    assert runtime.enforcement_active is False
    assert runtime.status()["status"] == "UNLICENSED_RESEARCH"
    runtime.authorize(tool="gremlin_route")
