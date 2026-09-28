from pathlib import Path
import zipfile

import pytest

from gremlin_mcp import chatgpt_clean_install as clean


def test_missing_endpoint_is_loud_blocker():
    plan = clean.build_plan(None)
    assert plan.ready is False
    assert plan.blocker == "REMOTE_ENDPOINT_REQUIRED"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/mcp",
        "https://localhost/mcp",
        "https://127.0.0.1:8766/mcp",
        "https://10.0.0.2/mcp",
        "https://example.com/api",
    ],
)
def test_non_clean_account_endpoint_is_rejected(url):
    assert clean.endpoint_gate(url).status == "FAIL"


def test_public_https_mcp_endpoint_is_accepted():
    assert clean.endpoint_gate("https://gremlin.example/mcp").status == "PASS"


def test_package_is_self_contained_and_inspects(tmp_path: Path):
    target = tmp_path / "gremlin.zip"
    result = clean.build_zip("https://gremlin.example/mcp", target)
    assert result["status"] == "READY"
    check = clean.inspect_zip(target)
    assert check["status"] == "PASS"
    with zipfile.ZipFile(target) as zf:
        assert set(clean.REQUIRED_FILES) <= set(zf.namelist())
        assert b"localhost" not in zf.read("mcp.json")
        assert b"/dev/shm" not in zf.read("skills/gremlin/SKILL.md")


def test_refuses_overwrite(tmp_path: Path):
    target = tmp_path / "gremlin.zip"
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        clean.build_zip("https://gremlin.example/mcp", target)
