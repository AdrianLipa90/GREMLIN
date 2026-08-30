from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Callable, Protocol

from .paths import GremlinPaths


class SecretStoreError(RuntimeError):
    pass


class SecretStoreUnavailable(SecretStoreError):
    pass


class SecretStore(Protocol):
    def set(self, name: str, value: bytes) -> None: ...
    def get(self, name: str) -> bytes | None: ...
    def delete(self, name: str) -> None: ...


_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def _name(value: str) -> str:
    name = str(value).strip()
    if not _NAME_RE.fullmatch(name):
        raise ValueError("secret name must match [A-Za-z0-9._-]{1,96}")
    return name


class LinuxSecretServiceStore:
    def __init__(self, executable: str = "secret-tool") -> None:
        self.executable = executable

    def _run(self, args: list[str], *, stdin: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                [self.executable, *args],
                input=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=check,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SecretStoreUnavailable(f"Linux Secret Service operation failed: {exc}") from exc

    def set(self, name: str, value: bytes) -> None:
        key = _name(name)
        self._run(
            ["store", "--label=GREMLIN", "service", "gremlin", "account", key],
            stdin=base64.b64encode(value),
        )

    def get(self, name: str) -> bytes | None:
        key = _name(name)
        result = self._run(["lookup", "service", "gremlin", "account", key], check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        try:
            return base64.b64decode(result.stdout.strip(), validate=True)
        except Exception as exc:
            raise SecretStoreError("Secret Service returned malformed GREMLIN secret data") from exc

    def delete(self, name: str) -> None:
        key = _name(name)
        self._run(["clear", "service", "gremlin", "account", key], check=False)


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi_crypt(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise SecretStoreUnavailable("Windows DPAPI is available only on Windows")

    buffer = ctypes.create_string_buffer(data)
    in_blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    out_blob = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]

    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]

    if protect:
        ok = crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            ctypes.c_wchar_p("GREMLIN"),
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
    if not ok:
        raise SecretStoreError(f"Windows DPAPI operation failed with error {ctypes.get_last_error()}")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(out_blob.pbData, wintypes.HLOCAL))


class WindowsDpapiStore:
    """User-bound encrypted secret blobs protected by Windows DPAPI."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, name: str) -> Path:
        safe = _name(name)
        digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.dpapi"

    def set(self, name: str, value: bytes) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(name)
        encrypted = _dpapi_crypt(value, protect=True)
        temp = path.with_suffix(".tmp")
        temp.write_bytes(encrypted)
        os.replace(temp, path)

    def get(self, name: str) -> bytes | None:
        path = self._path(name)
        if not path.is_file():
            return None
        return _dpapi_crypt(path.read_bytes(), protect=False)

    def delete(self, name: str) -> None:
        path = self._path(name)
        if path.exists():
            path.unlink()


def secret_store_status(
    paths: GremlinPaths,
    *,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    if paths.platform == "windows":
        return {
            "schema": "GREMLIN_SECRET_STORE_STATUS_V0_1",
            "available": True,
            "backend": "WINDOWS_DPAPI",
        }
    executable = which("secret-tool")
    return {
        "schema": "GREMLIN_SECRET_STORE_STATUS_V0_1",
        "available": executable is not None,
        "backend": "LINUX_SECRET_SERVICE",
        "executable": executable,
    }


def resolve_secret_store(paths: GremlinPaths) -> SecretStore:
    if paths.platform == "windows":
        return WindowsDpapiStore(Path(paths.data_dir) / "secrets")
    executable = shutil.which("secret-tool")
    if not executable:
        raise SecretStoreUnavailable("secret-tool is required for GREMLIN Linux device secrets")
    return LinuxSecretServiceStore(executable)
