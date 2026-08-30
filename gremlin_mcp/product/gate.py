from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .license import LicenseError, license_status, load_license
from .profile import ClientProfileError, load_client_profile


class ProductAuthorizationError(PermissionError):
    """Raised when a product operation is outside the configured entitlement."""


@dataclass
class ProductRuntime:
    """Fail-closed product entitlement context for the licensed MCP surface."""

    require_license: bool = True
    license_payload: dict[str, Any] | None = None
    client_profile: dict[str, Any] | None = None
    configuration_error: str | None = None

    @classmethod
    def unconfigured(cls, *, require_license: bool = True) -> "ProductRuntime":
        return cls(require_license=require_license)

    @classmethod
    def from_paths(
        cls,
        *,
        license_path: str | Path | None,
        public_key_path: str | Path | None,
        profile_path: str | Path | None = None,
        require_license: bool = True,
    ) -> "ProductRuntime":
        runtime = cls(require_license=require_license)
        if not license_path and not public_key_path:
            if require_license:
                runtime.configuration_error = "LICENSE_REQUIRED"
            return runtime
        if not license_path or not public_key_path:
            runtime.configuration_error = "LICENSE_AND_PUBLIC_KEY_MUST_BE_CONFIGURED_TOGETHER"
            return runtime
        try:
            payload = load_license(license_path, public_key_path)
            profile = load_client_profile(profile_path, payload) if profile_path else None
        except (LicenseError, ClientProfileError, OSError) as exc:
            runtime.configuration_error = str(exc)
            return runtime
        runtime.license_payload = payload
        runtime.client_profile = profile
        return runtime

    @property
    def configured(self) -> bool:
        return self.license_payload is not None and self.configuration_error is None

    @property
    def enforcement_active(self) -> bool:
        return self.require_license or self.license_payload is not None

    def _deny(self, code: str) -> None:
        raise ProductAuthorizationError(code)

    def authorize(
        self,
        *,
        tool: str,
        feature: str | None = None,
        species: str | None = None,
        provider: str | None = None,
        requested_workers: int | None = None,
        requested_sources: int | None = None,
    ) -> None:
        if not self.enforcement_active:
            return
        if self.configuration_error:
            self._deny(f"PRODUCT_CONFIGURATION_ERROR:{self.configuration_error}")
        if self.license_payload is None:
            self._deny("LICENSE_REQUIRED")

        payload = self.license_payload
        features = set(payload.get("features") or [])
        if feature and feature not in features:
            self._deny(f"FEATURE_NOT_ENTITLED:{feature}")

        profile = self.client_profile
        if profile is not None:
            allowed_tools = set(profile.get("tools") or [])
            if allowed_tools and tool not in allowed_tools:
                self._deny(f"TOOL_NOT_ALLOWED_BY_PROFILE:{tool}")
            if species is not None:
                allowed_species = set(profile.get("species") or [])
                if allowed_species and species.upper() not in allowed_species:
                    self._deny(f"SPECIES_NOT_ALLOWED_BY_PROFILE:{species.upper()}")
            if provider is not None:
                allowed_providers = set(profile.get("providers") or [])
                if allowed_providers and provider.casefold() not in allowed_providers:
                    self._deny(f"PROVIDER_NOT_ALLOWED_BY_PROFILE:{provider.casefold()}")
            if feature == "INTERNET_RESEARCH" and not bool(profile.get("internet_access")):
                self._deny("INTERNET_ACCESS_DISABLED_BY_PROFILE")
            if feature == "CUSTOM_WORKERS" and not bool(profile.get("custom_workers")):
                self._deny("CUSTOM_WORKERS_DISABLED_BY_PROFILE")

        license_limits = payload.get("limits") or {}
        max_workers = int(license_limits.get("max_workers", 0))
        max_sources = int(license_limits.get("max_sources", 0))
        if profile is not None:
            profile_limits = profile.get("limits") or {}
            max_workers = min(max_workers, int(profile_limits.get("max_workers", max_workers)))
            max_sources = min(max_sources, int(profile_limits.get("max_sources", max_sources)))
        if requested_workers is not None and int(requested_workers) > max_workers:
            self._deny(f"WORKER_LIMIT_EXCEEDED:{requested_workers}>{max_workers}")
        if requested_sources is not None and int(requested_sources) > max_sources:
            self._deny(f"SOURCE_LIMIT_EXCEEDED:{requested_sources}>{max_sources}")

    def status(self) -> dict[str, Any]:
        if self.configuration_error:
            return {
                "schema": "GREMLIN_PRODUCT_STATUS_V0_1",
                "status": "BLOCKED",
                "require_license": self.require_license,
                "enforcement_active": self.enforcement_active,
                "reason": self.configuration_error,
                "authority": {
                    "production_runtime_write": False,
                    "execution_admitted": False,
                    "canon_allowed": False,
                },
            }
        if self.license_payload is None:
            return {
                "schema": "GREMLIN_PRODUCT_STATUS_V0_1",
                "status": "UNLICENSED_RESEARCH" if not self.require_license else "BLOCKED",
                "require_license": self.require_license,
                "enforcement_active": self.enforcement_active,
                "authority": {
                    "production_runtime_write": False,
                    "execution_admitted": False,
                    "canon_allowed": False,
                },
            }
        out = {
            "schema": "GREMLIN_PRODUCT_STATUS_V0_1",
            "status": "LICENSED",
            "require_license": self.require_license,
            "enforcement_active": self.enforcement_active,
            "license": license_status(self.license_payload),
            "profile": None,
            "authority": {
                "production_runtime_write": False,
                "execution_admitted": False,
                "canon_allowed": False,
            },
        }
        if self.client_profile is not None:
            out["profile"] = {
                "client_id": self.client_profile["client_id"],
                "label": self.client_profile["label"],
                "profile_commitment": self.client_profile["profile_commitment"],
                "limits": dict(self.client_profile["limits"]),
            }
        return out
