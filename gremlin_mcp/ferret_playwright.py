from __future__ import annotations

from pathlib import Path
import hashlib
import os
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from .ferret import FerretExecutionResult, FerretExecutionError


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


def make_playwright_executor(
    *,
    headless: bool = True,
    executable_path: str | None = None,
    artifact_dir: str | os.PathLike[str] | None = None,
    timeout_ms: int = 20_000,
):
    """Return a FERRET executor backed by Chromium via Playwright.

    The returned callable is intentionally narrow: it executes only the already-normalized,
    commitment-bound preview supplied by ``execute_authorized_action``. CAPTCHA/MFA are
    stop conditions. Cross-origin drift is fail-closed.
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
                        label = re.sub(r"[^a-zA-Z0-9_.-]+", "_", step.get("label", f"snapshot-{index}"))
                        shot = out_dir / f"{preview['preview_id']}-{index:02d}-{label}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        evidence["snapshots"].append(
                            {
                                "path": str(shot),
                                "sha256": _sha256_file(shot),
                                "bytes": shot.stat().st_size,
                            }
                        )
                    else:  # defensive, preview normalization should make this unreachable
                        raise FerretExecutionError(f"unsupported normalized action: {action}")

                    if page.url and not _same_origin(target_url, page.url):
                        raise FerretExecutionError(
                            f"cross-origin drift blocked: {page.url}"
                        )

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
