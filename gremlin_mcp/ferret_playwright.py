from __future__ import annotations

from pathlib import Path
import hashlib
import os
import re
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from .ferret import (
    FerretExecutionResult,
    FerretExecutionError,
    detect_human_gate,
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


def _detect_handoff(page: Any) -> str | None:
    """Detect obvious CAPTCHA/MFA surfaces; never attempts to solve or bypass them."""
    try:
        html = page.content()
    except Exception:
        html = ""
    try:
        title = page.title()
    except Exception:
        title = ""
    text = f"{title}\n{html[:250_000]}"
    if any(pattern.search(text) for pattern in _CAPTCHA_PATTERNS):
        return "CAPTCHA_USER_HANDOFF_REQUIRED"
    if any(pattern.search(text) for pattern in _MFA_PATTERNS):
        return "MFA_USER_HANDOFF_REQUIRED"
    return None


def _redacted_step(step: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(step)
    if result.get("secret"):
        result["value"] = "<REDACTED>"
    return result


def persist_storage_state(context: Any, path: str | os.PathLike[str]) -> dict[str, Any]:
    """Persist Playwright storage state locally and emit only non-secret receipt metadata."""
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        context.storage_state(path=str(target))
    except Exception as exc:
        raise FerretBrowserSessionError(
            f"failed to persist browser storage state: {type(exc).__name__}: {exc}"
        ) from exc
    if not target.is_file():
        raise FerretBrowserSessionError("browser backend did not create storage state file")
    try:
        target.chmod(0o600)
    except OSError as exc:
        raise FerretBrowserSessionError("failed to set owner-only storage-state permissions") from exc
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
    """Verify that the local browser state exactly matches the handoff resume receipt."""
    verify_handoff_resume(handoff, resume)
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise FerretBrowserSessionError("storage state file is missing")
    actual = _sha256_file(target)
    expected = str(resume.get("storage_state_sha256", "")).strip().lower()
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
    """Observe until a human clears a CAPTCHA/MFA gate in the same browser session.

    FERRET never clicks, answers, injects challenge tokens, calls solver services, or otherwise
    automates the verification challenge in this loop.
    """
    timeout = float(timeout_s)
    interval = int(poll_ms)
    if not (0.001 <= timeout <= 3600.0):
        raise ValueError("timeout_s must be in [0.001, 3600]")
    if not (1 <= interval <= 10_000):
        raise ValueError("poll_ms must be in [1, 10000]")
    deadline = time.monotonic() + timeout
    observations = 0
    last_gate: Mapping[str, Any] | None = None
    while True:
        try:
            observation = observe(page)
        except StopIteration as exc:
            raise FerretBrowserSessionError("observation source ended before gate cleared") from exc
        except Exception as exc:
            raise FerretBrowserSessionError(
                f"browser observation failed: {type(exc).__name__}: {exc}"
            ) from exc
        observations += 1
        gate = detect_human_gate(observation)
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
            kind = str(last_gate.get("gate_kind", "UNKNOWN")) if last_gate else "UNKNOWN"
            raise FerretBrowserSessionError(
                f"human gate wait timed out while gate remained active: {kind}"
            )
        page.wait_for_timeout(interval)


def collect_page_observation(
    page: Any,
    *,
    max_fields: int = 128,
    max_frames: int = 32,
) -> dict[str, Any]:
    """Collect bounded gate metadata without returning cookies or browser storage secrets."""
    fields: list[dict[str, Any]] = []
    try:
        nodes = page.locator("input, textarea, select, button").all()
    except Exception:
        nodes = []
    for node in nodes[: max(0, int(max_fields))]:
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
        except Exception:
            continue

    frames: list[dict[str, Any]] = []
    try:
        page_frames = list(page.frames)
    except Exception:
        page_frames = []
    for frame in page_frames[: max(0, int(max_frames))]:
        try:
            text = frame.locator("body").inner_text(timeout=1000)
        except Exception:
            text = ""
        frames.append(
            {
                "name": getattr(frame, "name", "") or "",
                "url": getattr(frame, "url", "") or "",
                "text": " ".join(str(text).split())[:4000],
            }
        )

    try:
        title = page.title()
    except Exception:
        title = ""
    try:
        body_text = page.locator("body").inner_text(timeout=1500)
    except Exception:
        body_text = ""
    return {
        "schema": "GREMLIN_FERRET_PAGE_OBSERVATION_V0_1",
        "resolved_url": str(getattr(page, "url", "")),
        "title": str(title),
        "body_text": " ".join(str(body_text).split())[:8000],
        "frames": frames,
        "fields": fields,
        "cookies_returned": False,
        "storage_state_returned": False,
    }


def open_headed_browser_for_handoff(
    url: str,
    *,
    storage_state: str | os.PathLike[str] | None = None,
):
    """Open visible Chromium for the human side of a FERRET handoff.

    No stealth flags, solver APIs, token injection, or anti-bot evasion are used. The caller owns
    the lifecycle of the returned Playwright/browser/context/page objects.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise FerretBrowserSessionError(
            "Playwright is not installed; install Playwright and a Chromium runtime"
        ) from exc
    state_path = None
    if storage_state is not None:
        candidate = Path(storage_state).expanduser().resolve()
        if not candidate.is_file():
            raise FerretBrowserSessionError("requested storage state file is missing")
        state_path = str(candidate)
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(storage_state=state_path)
        page = context.new_page()
        page.goto(str(url), wait_until="domcontentloaded")
    except Exception:
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
):
    """Return a FERRET executor backed by Chromium via Playwright.

    The executor runs only the already-normalized, commitment-bound preview supplied by
    ``execute_authorized_action``. CAPTCHA/MFA are stop conditions and cross-origin drift is
    fail-closed.
    """
    timeout = int(timeout_ms)
    if not 1_000 <= timeout <= 120_000:
        raise ValueError("timeout_ms must be in [1000, 120000]")
    out_dir = Path(artifact_dir or Path.cwd() / ".ferret-artifacts")

    def executor(preview: Mapping[str, Any]) -> FerretExecutionResult:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - depends on local runtime
            raise FerretExecutionError(
                "Playwright backend is unavailable; install playwright and a Chromium runtime"
            ) from exc

        target_url = str(preview["target_url"])
        steps = list(preview["steps"])
        out_dir.mkdir(parents=True, exist_ok=True)
        evidence: dict[str, Any] = {
            "backend": "PLAYWRIGHT_CHROMIUM",
            "headless": bool(headless),
            "executed_steps": [],
            "snapshots": [],
            "handoff": None,
        }

        launch_kwargs: dict[str, Any] = {"headless": bool(headless)}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path

        with sync_playwright() as pw:
            browser = pw.chromium.launch(**launch_kwargs)
            context = browser.new_context(accept_downloads=False)
            page = context.new_page()
            page.set_default_timeout(timeout)
            try:
                for index, step in enumerate(steps):
                    action = step["action"]
                    if action == "navigate":
                        page.goto(step["url"], wait_until="domcontentloaded")
                    elif action == "fill":
                        page.locator(step["selector"]).fill(step["value"])
                    elif action == "select":
                        page.locator(step["selector"]).select_option(step["value"])
                    elif action == "check":
                        locator = page.locator(step["selector"])
                        locator.check() if step.get("checked", True) else locator.uncheck()
                    elif action == "upload":
                        page.locator(step["selector"]).set_input_files(step["files"])
                    elif action == "click":
                        page.locator(step["selector"]).click()
                    elif action == "wait_for":
                        page.locator(step["selector"]).wait_for(state="visible")
                    elif action == "snapshot":
                        label = re.sub(
                            r"[^a-zA-Z0-9_.-]+",
                            "_",
                            step.get("label", f"snapshot-{index}"),
                        )
                        shot = out_dir / f"{preview['preview_id']}-{index:02d}-{label}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        evidence["snapshots"].append(
                            {
                                "path": str(shot),
                                "sha256": _sha256_file(shot),
                                "bytes": shot.stat().st_size,
                            }
                        )
                    else:
                        raise FerretExecutionError(f"unsupported normalized action: {action}")

                    if page.url and not _same_origin(target_url, page.url):
                        raise FerretExecutionError(f"cross-origin drift blocked: {page.url}")

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
