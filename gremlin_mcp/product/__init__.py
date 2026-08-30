"""GREMLIN product licensing and client-profile layer."""

from .gate import ProductAuthorizationError, ProductRuntime
from .keycodec import LICENSE_KEY_PREFIX, decode_license_key, encode_license_key, verify_license_key
from .license import (
    LICENSE_ENVELOPE_SCHEMA,
    LICENSE_PAYLOAD_SCHEMA,
    LicenseError,
    issue_license,
    load_license,
    verify_license,
)
from .profile import CLIENT_PROFILE_SCHEMA, ClientProfileError, load_client_profile

__all__ = [
    "CLIENT_PROFILE_SCHEMA",
    "LICENSE_ENVELOPE_SCHEMA",
    "LICENSE_KEY_PREFIX",
    "LICENSE_PAYLOAD_SCHEMA",
    "ClientProfileError",
    "LicenseError",
    "ProductAuthorizationError",
    "ProductRuntime",
    "decode_license_key",
    "encode_license_key",
    "issue_license",
    "load_client_profile",
    "load_license",
    "verify_license",
    "verify_license_key",
]
