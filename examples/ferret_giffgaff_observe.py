from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from playwright.sync_api import sync_playwright


TARGET = "https://www.giffgaff.com/complaints/new"
OUT = Path("artifacts/ferret-giffgaff-observe")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_text(value: str | None, limit: int = 200) -> str | None:
    if value is None:
        return None
    return " ".join(value.split())[:limit]


def _inventory(scope):
    fields = scope.locator("input, textarea, select, button, a").all()
    result = []
    for index, node in enumerate(fields[:160]):
        try:
            result.append(
                {
                    "tag": node.evaluate("el => el.tagName.toLowerCase()"),
                    "type": node.get_attribute("type"),
                    "name": node.get_attribute("name"),
                    "id": node.get_attribute("id"),
                    "aria_label": node.get_attribute("aria-label"),
                    "autocomplete": node.get_attribute("autocomplete"),
                    "placeholder": node.get_attribute("placeholder"),
                    "href": node.get_attribute("href"),
                    "text": _safe_text(node.inner_text()),
                }
            )
        except Exception as exc:
            result.append(
                {
                    "inventory_index": index,
                    "inventory_error": f"{type(exc).__name__}: {exc}",
                }
            )
    return result


def _frame_snapshot(page):
    frames = []
    for frame in page.frames:
        try:
            body = frame.locator("body")
            body_text = _safe_text(body.inner_text(), 5000) if body.count() else None
            frames.append(
                {
                    "name": frame.name,
                    "url": frame.url,
                    "body_text": body_text,
                    "controls": _inventory(frame),
                }
            )
        except Exception as exc:
            frames.append({"name": frame.name, "url": frame.url, "error": f"{type(exc).__name__}: {exc}"})
    return frames


def _find_guest_control(page):
    pattern = re.compile(r"continue as a guest", re.I)
    scopes = [page, *page.frames]
    seen = set()
    for scope in scopes:
        key = getattr(scope, "url", None) or id(scope)
        if key in seen:
            continue
        seen.add(key)
        for locator in (
            scope.get_by_role("button", name=pattern),
            scope.get_by_role("link", name=pattern),
            scope.get_by_text(pattern, exact=False),
        ):
            try:
                if locator.count():
                    return locator.first, getattr(scope, "url", None)
            except Exception as exc:
                scope_url = getattr(scope, "url", None)
                raise RuntimeError(
                    f"guest-control probe failed for scope {scope_url!r}: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
    return None, None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "GREMLIN_FERRET_GIFFGAFF_OBSERVE_V0_1",
        "target": TARGET,
        "mutation_performed": False,
        "submit_clicked": False,
        "guest_control_found": False,
        "guest_control_scope": None,
        "stages": [],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 1600})
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(TARGET, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        shot1 = OUT / "01-entry.png"
        page.screenshot(path=str(shot1), full_page=True)
        receipt["stages"].append(
            {
                "name": "ENTRY",
                "url": page.url,
                "title": page.title(),
                "screenshot": str(shot1),
                "screenshot_sha256": _sha256(shot1),
                "fields": _inventory(page),
                "frames": _frame_snapshot(page),
            }
        )

        guest, scope_url = _find_guest_control(page)
        if guest is not None:
            receipt["guest_control_found"] = True
            receipt["guest_control_scope"] = scope_url
            guest.click()
            page.wait_for_timeout(1800)

            shot2 = OUT / "02-guest-details.png"
            page.screenshot(path=str(shot2), full_page=True)
            receipt["stages"].append(
                {
                    "name": "GUEST_DETAILS",
                    "url": page.url,
                    "title": page.title(),
                    "screenshot": str(shot2),
                    "screenshot_sha256": _sha256(shot2),
                    "fields": _inventory(page),
                    "frames": _frame_snapshot(page),
                    "body_text": _safe_text(page.locator("body").inner_text(), 5000),
                }
            )
        else:
            receipt["observe_status"] = "GUEST_CONTROL_NOT_FOUND"

        context.close()
        browser.close()

    receipt_path = OUT / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
