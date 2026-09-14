from __future__ import annotations

from pathlib import Path
import hashlib
import math
import os
import re
import tempfile
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from .ferret import (
    FerretExecutionResult,
    FerretExecutionError,
    detect_human_gate,
    validate_public_network_url,
    verify_handoff_resume,
)


_CAPTCHA_PATTERNS = (
    re.compile(r"captcha", re.I),
    re.compile(r"recaptcha", re.I),
    re.compile(r"hcaptcha", re.I),
    re.compile(r"turnstile", re.I),
)

_MFA_PATTERNS = (
    re.compile(r"two[- ]factor", re.I),
    re.compile(r"2fa", re.I),
    re.compile(r"multi[- ]factor", re.I),
    re.compile(r"verification code", re.I),
    re.compile(r"one[- ]time pass", re.I),
    re.compile(r"otp", re.I),
)


class FerretBrowserSessionError(RuntimeError):
    pass


def _strict_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be in [{minimum}, {maximum}]")
    return value


def _strict_float(value: Any, field: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    out = float(value)
    if not math.isfinite(out) or not minimum <= out <= maximum:
        raise ValueError(f"{field} must be in [{minimum}, {maximum}]")
    return out


def _strict_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not allow_empty and not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _same_origin(expected_url: str, actual_url: str) -> bool:
    expected = urlsplit(expected_url)
    actual = urlsplit(actual_url)
    return (
        expected.scheme.lower(),
        (expected.hostname or "").lower(),
        expected.port or 443,
    ) == (
        actual.scheme.lower(),
        (actual.hostname or "").lower(),
        actual.port or 443,
    )


def _redacted_step(step: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(step)
    if result.get("secret") is True:
        result["value"] = "<REDACTED>"
    return result


def _private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            path.chmod(0o700)
        except OSError as exc:
            raise FerretBrowserSessionError("failed to secure FERRET artifact directory") from exc


def _private_file(path: Path) -> None:
    if os.name != "nt":
        try:
            path.chmod(0o600)
        except OSError as exc:
            raise FerretBrowserSessionError(f"failed to secure FERRET artifact: {path.name}") from exc


def _install_public_network_guard(context: Any) -> None:
    """Block HTTP and every HTTPS request whose current DNS result includes a non-public address."""
    def guard(route: Any, request: Any) -> None:
        url = getattr(request, "url", None)
        if not isinstance(url, str):
            route.abort()
            return
        parsed = urlsplit(url)
        if parsed.scheme in {"data", "blob", "about"}:
            route.continue_()
            return
        if parsed.scheme != "https":
            route.abort()
            return
        try:
            validate_public_network_url(url)
        except (TypeError, ValueError):
            route.abort()
            return
        route.continue_()

    try:
        context.route("**/*", guard)
    except Exception as exc:
        raise FerretBrowserSessionError(
            f"failed to install FERRET network guard: {type(exc).__name__}: {exc}"
        ) from exc


def collect_page_observation(
    page: Any,
    *,
    max_fields: int = 128,
    max_frames: int = 32,
) -> dict[str, Any]:
    """Collect bounded gate metadata; incomplete collection is explicit and therefore fail-closed."""
    field_limit = _strict_int(max_fields, "max_fields", minimum=0, maximum=1024)
    frame_limit = _strict_int(max_frames, "max_frames", minimum=0, maximum=256)
    errors: list[str] = []

    try:
        resolved_url = page.url
    except Exception as exc:
        raise FerretBrowserSessionError(
            f"failed to read browser URL: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(resolved_url, str) or not resolved_url.strip():
        raise FerretBrowserSessionError("browser URL is unavailable")

    try:
        title = page.title()
    except Exception as exc:
        raise FerretBrowserSessionError(
            f"failed to read browser title: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(title, str):
        raise FerretBrowserSessionError("browser title must be a string")

    try:
        body_text = page.locator("body").inner_text(timeout=1500)
    except Exception as exc:
        raise FerretBrowserSessionError(
            f"failed to read browser body: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(body_text, str):
        raise FerretBrowserSessionError("browser body text must be a string")

    fields: list[dict[str, Any]] = []
    try:
        nodes = page.locator("input, textarea, select, button").all()
    except Exception as exc:
        nodes = []
        errors.append(f"FIELD_ENUMERATION:{type(exc).__name__}")
    for node_index, node in enumerate(nodes[:field_limit]):
        try:
            fields.append(
                {
                    "tag": node.evaluate("el => el.tagName.toLowerCase()"),
                    "type": node.get_attribute("type"),
                    "name": node.get_attribute("name"),
                    "id": node.get_attribute("id"),
                    "aria_label": node.get_attribute("aria-label"),
                    "placeholder": node.get_attribute("placeholder"),
                }
            )
        except Exception as exc:
            errors.append(f"FIELD_{node_index}:{type(exc).__name__}")

    frames: list[dict[str, Any]] = []
    try:
        page_frames = list(page.frames)
    except Exception as exc:
        page_frames = []
        errors.append(f"FRAME_ENUMERATION:{type(exc).__name__}")
    for frame_index, frame in enumerate(page_frames[:frame_limit]):
        try:
            text = frame.locator("body").inner_text(timeout=1000)
            name = getattr(frame, "name", "") or ""
            url = getattr(frame, "url", "") or ""
            if not isinstance(text, str) or not isinstance(name, str) or not isinstance(url, str):
                raise TypeError("frame observation fields must be strings")
            frames.append(
                {
                    "name": name,
                    "url": url,
                    "text": " ".join(text.split())[:4000],
                }
            )
        except Exception as exc:
            errors.append(f"FRAME_{frame_index}:{type(exc).__name__}")

    return {
        "schema": "GREMLIN_FERRET_PAGE_OBSERVATION_V0_1",
        "resolved_url": resolved_url,
        "title": title,
        "body_text": " ".join(body_text.split())[:8000],
        "frames": frames,
        "fields": fields,
        "observation_complete": not errors,
        "observation_errors": errors,
        "cookies_returned": False,
        "storage_state_returned": False,
    }


def _detect_handoff(page: Any) -> str | None:
    """Detect CAPTCHA/MFA surfaces; any observation failure is a hard stop, never a clear signal."""
    observation = collect_page_observation(page)
    gate = detect_human_gate(observation)
    if gate is None:
        return None
    kind = gate.get("gate_kind")
    if kind == "CAPTCHA":
        return "CAPTCHA_USER_HANDOFF_REQUIRED"
    if kind == "MFA":
        return "MFA_USER_HANDOFF_REQUIRED"
    return "BOT_CHALLENGE_USER_HANDOFF_REQUIRED"


def persist_storage_state(context: Any, path: str | os.PathLike[str]) -> dict[str, Any]:
    """Atomically persist browser state into an owner-only file and return only non-secret metadata."""
    target = Path(path).expanduser().resolve()
    _private_directory(target.parent)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        _private_file(temp)
        try:
            context.storage_state(path=str(temp))
        except Exception as exc:
            raise FerretBrowserSessionError(
                f"failed to persist browser storage state: {type(exc).__name__}: {exc}"
            ) from exc
        if not temp.is_file():
            raise FerretBrowserSessionError("browser backend did not create storage state file")
        _private_file(temp)
        with temp.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, target)
        _private_file(target)
        if os.name != "nt":
            dir_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if temp.exists():
            temp.unlink()
    return {
        "schema": "GREMLIN_FERRET_STORAGE_STATE_RECEIPT_V0_1",
        "path": str(target),
        "sha256": _sha256_file(target),
        "bytes": target.stat().st_size,
        "mode": oct(target.stat().st_mode & 0o777),
        "secret_material_returned": False,
    }


def verify_storage_state_for_resume(
    handoff: Mapping[str, Any],
    resume: Mapping[str, Any],
    path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Verify that local browser state exactly matches the handoff resume receipt."""
    verify_handoff_resume(handoff, resume)
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise FerretBrowserSessionError("storage state file is missing")
    actual = _sha256_file(target)
    expected = resume.get("storage_state_sha256")
    if not isinstance(expected, str) or not expected:
        raise FerretBrowserSessionError("resume storage-state hash is invalid")
    if actual != expected:
        raise FerretBrowserSessionError("storage state hash mismatch")
    return {
        "schema": "GREMLIN_FERRET_STORAGE_STATE_VERIFY_V0_1",
        "status": "VERIFIED",
        "path": str(target),
        "storage_state_sha256": actual,
        "bytes": target.stat().st_size,
        "secret_material_returned": False,
    }


def wait_for_human_gate_clear(
    page: Any,
    *,
    observe: Callable[[Any], Mapping[str, Any]],
    timeout_s: float = 300.0,
    poll_ms: int = 500,
) -> dict[str, Any]:
    """Observe until a human clears a CAPTCHA/MFA gate in the same browser session."""
    timeout = _strict_float(timeout_s, "timeout_s", minimum=0.001, maximum=3600.0)
    interval = _strict_int(poll_ms, "poll_ms", minimum=1, maximum=10_000)
    if not callable(observe):
        raise ValueError("observe must be callable")
    deadline = time.monotonic() + timeout
    observations = 0
    last_gate: Mapping[str, Any] | None = None
    while True:
        try:
            observation = observe(page)
        except StopIteration as exc:
            raise FerretBrowserSessionError("observation source ended before gate cleared") from exc
        except FerretBrowserSessionError:
            raise
        except Exception as exc:
            raise FerretBrowserSessionError(
                f"browser observation failed: {type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(observation, Mapping):
            raise FerretBrowserSessionError("browser observation must be a mapping")
        observations += 1
        try:
            gate = detect_human_gate(observation)
        except (TypeError, ValueError, FerretExecutionError) as exc:
            raise FerretBrowserSessionError(f"invalid gate observation: {exc}") from exc
        except Exception as exc:
            raise FerretBrowserSessionError(f"gate state is unknown: {exc}") from exc
        if gate is None:
            return {
                "schema": "GREMLIN_FERRET_HUMAN_GATE_CLEAR_V0_1",
                "status": "HUMAN_GATE_CLEARED",
                "observations": observations,
                "automated_solution_attempted": False,
                "secret_material_returned": False,
            }
        last_gate = gate
        if time.monotonic() >= deadline:
            kind = last_gate.get("gate_kind", "UNKNOWN") if last_gate else "UNKNOWN"
            raise FerretBrowserSessionError(
                f"human gate wait timed out while gate remained active: {kind}"
            )
        page.wait_for_timeout(interval)


def open_headed_browser_for_handoff(
    url: str,
    *,
    storage_state: str | os.PathLike[str] | None = None,
):
    """Open visible Chromium for human handoff after validating the exact public network target."""
    try:
        safe_url = validate_public_network_url(url)
    except (TypeError, ValueError) as exc:
        raise FerretBrowserSessionError(f"unsafe browser target: {exc}") from exc
    state_path = None
    if storage_state is not None:
        candidate = Path(storage_state).expanduser().resolve()
        if not candidate.is_file():
            raise FerretBrowserSessionError("requested storage state file is missing")
        state_path = str(candidate)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise FerretBrowserSessionError(
            "Playwright is not installed; install Playwright and a Chromium runtime"
        ) from exc
    pw = sync_playwright().start()
    browser = None
    context = None
    try:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(storage_state=state_path)
        _install_public_network_guard(context)
        page = context.new_page()
        page.goto(safe_url, wait_until="domcontentloaded")
        resolved = validate_public_network_url(page.url)
        if not _same_origin(safe_url, resolved):
            raise FerretBrowserSessionError(f"cross-origin drift blocked: {resolved}")
    except Exception:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        pw.stop()
        raise
    return {
        "playwright": pw,
        "browser": browser,
        "context": context,
        "page": page,
        "automation_policy": "OBSERVE_AND_RESUME_ONLY_DURING_HUMAN_GATE",
        "automated_solution_attempted": False,
    }


def make_playwright_executor(
    *,
    headless: bool = True,
    executable_path: str | None = None,
    artifact_dir: str | os.PathLike[str] | None = None,
    timeout_ms: int = 20_000,
    secret_resolver: Callable[[str], str] | None = None,
):
    """Return a commitment-bound Chromium executor with public-network and human-gate firewalls."""
    if type(headless) is not bool:
        raise ValueError("headless must be boolean")
    timeout = _strict_int(timeout_ms, "timeout_ms", minimum=1_000, maximum=120_000)
    if executable_path is not None and not isinstance(executable_path, str):
        raise ValueError("executable_path must be a string or None")
    if secret_resolver is not None and not callable(secret_resolver):
        raise ValueError("secret_resolver must be callable or None")
    out_dir = Path(artifact_dir or Path.cwd() / ".ferret-artifacts").expanduser().resolve()

    def executor(preview: Mapping[str, Any]) -> FerretExecutionResult:
        if not isinstance(preview, Mapping):
            raise FerretExecutionError("preview must be a mapping")
        raw_target = preview.get("target_url")
        if not isinstance(raw_target, str):
            raise FerretExecutionError("preview target_url must be a string")
        try:
            target_url = validate_public_network_url(raw_target)
        except (TypeError, ValueError) as exc:
            raise FerretExecutionError(f"unsafe preview target: {exc}") from exc
        steps = preview.get("steps")
        if not isinstance(steps, list):
            raise FerretExecutionError("preview steps must be a list")
        _private_directory(out_dir)

        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on local runtime
            raise FerretExecutionError(
                "Playwright backend is unavailable; install playwright and a Chromium runtime"
            ) from exc

        evidence: dict[str, Any] = {
            "backend": "PLAYWRIGHT_CHROMIUM",
            "headless": headless,
            "executed_steps": [],
            "snapshots": [],
            "handoff": None,
        }

        launch_kwargs: dict[str, Any] = {"headless": headless}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path

        with sync_playwright() as pw:
            browser = pw.chromium.launch(**launch_kwargs)
            context = browser.new_context(accept_downloads=False)
            _install_public_network_guard(context)
            page = context.new_page()
            page.set_default_timeout(timeout)
            try:
                for index, step in enumerate(steps):
                    if not isinstance(step, Mapping):
                        raise FerretExecutionError(f"normalized step {index} must be a mapping")
                    action = step.get("action")
                    if not isinstance(action, str):
                        raise FerretExecutionError(f"normalized step {index} action must be a string")
                    if action == "navigate":
                        step_url = step.get("url")
                        if not isinstance(step_url, str):
                            raise FerretExecutionError(f"normalized step {index} URL must be a string")
                        safe_step_url = validate_public_network_url(step_url)
                        page.goto(safe_step_url, wait_until="domcontentloaded")
                    elif action in {"fill", "select"}:
                        selector = step.get("selector")
                        if not isinstance(selector, str):
                            raise FerretExecutionError(f"normalized step {index} selector must be a string")
                        if step.get("secret") is True:
                            secret_ref = step.get("secret_ref")
                            if not isinstance(secret_ref, str) or not secret_ref:
                                raise FerretExecutionError(f"normalized step {index} secret_ref is invalid")
                            if secret_resolver is None:
                                raise FerretExecutionError(
                                    f"normalized step {index} requires secret_resolver"
                                )
                            resolved_secret = secret_resolver(secret_ref)
                            if not isinstance(resolved_secret, str):
                                raise FerretExecutionError("secret_resolver must return a string")
                            value = resolved_secret
                        else:
                            value = step.get("value")
                            if not isinstance(value, str):
                                raise FerretExecutionError(f"normalized step {index} value must be a string")
                        locator = page.locator(selector)
                        if action == "fill":
                            locator.fill(value)
                        else:
                            locator.select_option(value)
                    elif action == "check":
                        selector = step.get("selector")
                        checked = step.get("checked")
                        if not isinstance(selector, str) or type(checked) is not bool:
                            raise FerretExecutionError(f"normalized step {index} check contract is invalid")
                        locator = page.locator(selector)
                        locator.check() if checked else locator.uncheck()
                    elif action == "upload":
                        selector = step.get("selector")
                        files = step.get("files")
                        if not isinstance(selector, str) or not isinstance(files, list) or not all(isinstance(item, str) for item in files):
                            raise FerretExecutionError(f"normalized step {index} upload contract is invalid")
                        page.locator(selector).set_input_files(files)
                    elif action == "click":
                        selector = step.get("selector")
                        if not isinstance(selector, str):
                            raise FerretExecutionError(f"normalized step {index} selector must be a string")
                        page.locator(selector).click()
                    elif action == "wait_for":
                        selector = step.get("selector")
                        if not isinstance(selector, str):
                            raise FerretExecutionError(f"normalized step {index} selector must be a string")
                        page.locator(selector).wait_for(state="visible")
                    elif action == "snapshot":
                        label_raw = step.get("label", f"snapshot-{index}")
                        if not isinstance(label_raw, str):
                            raise FerretExecutionError(f"normalized step {index} label must be a string")
                        label = re.sub(r"[^a-zA-Z0-9_.-]+", "_", label_raw)
                        shot = out_dir / f"{preview['preview_id']}-{index:02d}-{label}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        _private_file(shot)
                        evidence["snapshots"].append(
                            {
                                "path": str(shot),
                                "sha256": _sha256_file(shot),
                                "bytes": shot.stat().st_size,
                            }
                        )
                    else:
                        raise FerretExecutionError(f"unsupported normalized action: {action}")

                    if page.url:
                        try:
                            resolved_url = validate_public_network_url(page.url)
                        except (TypeError, ValueError) as exc:
                            raise FerretExecutionError(f"unsafe resolved URL: {exc}") from exc
                        if not _same_origin(target_url, resolved_url):
                            raise FerretExecutionError(f"cross-origin drift blocked: {resolved_url}")

                    handoff = _detect_handoff(page)
                    evidence["executed_steps"].append(
                        {"index": index, **_redacted_step(step), "resolved_url": page.url}
                    )
                    if handoff:
                        evidence["handoff"] = handoff
                        evidence["title"] = page.title()
                        return FerretExecutionResult(
                            status=handoff,
                            resolved_url=page.url,
                            evidence=evidence,
                        )

                evidence["title"] = page.title()
                evidence["final_url"] = page.url
                return FerretExecutionResult(
                    status="EXECUTED_AND_VERIFIED",
                    resolved_url=page.url,
                    evidence=evidence,
                )
            finally:
                context.close()
                browser.close()

    return executor
