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


def _inventory(page):
    fields = page.locator("input, textarea, select, button").all()
    result = []
    for node in fields[:120]:
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
                    "text": _safe_text(node.inner_text()),
                }
            )
        except Exception:
            continue
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "GREMLIN_FERRET_GIFFGAFF_OBSERVE_V0_1",
        "target": TARGET,
        "mutation_performed": False,
        "submit_clicked": False,
        "stages": [],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 1600})
        page = context.new_page()
        page.set_default_timeout(15000)
        page.goto(TARGET, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

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
            }
        )

        guest = page.get_by_role("button", name=re.compile(r"continue as a guest", re.I))
        if guest.count() == 0:
            guest = page.get_by_text(re.compile(r"continue as a guest", re.I), exact=False)
        if guest.count() == 0:
            raise RuntimeError("Continue as a guest control was not found")

        guest.first.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1200)

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
                "body_text": _safe_text(page.locator("body").inner_text(), 5000),
            }
        )

        context.close()
        browser.close()

    receipt_path = OUT / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
