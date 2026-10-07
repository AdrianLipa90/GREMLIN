from pathlib import Path
import json
import zipfile

import pytest

from gremlin_mcp import chatgpt_clean_install as clean


def test_missing_endpoint_is_loud_blocker():
    plan = clean.build_plan(None)
    assert plan.package_ready is False
    assert plan.blocker == "REMOTE_ENDPOINT_REQUIRED"
    assert plan.host_gate.status == "EXTERNAL_REQUIRED"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/mcp",
        "https://localhost/mcp",
        "https://127.0.0.1:8766/mcp",
        "https://10.0.0.2/mcp",
        "https://example.com/api",
        "https://example.com/mcp?token=secret",
    ],
)
def test_non_clean_account_endpoint_is_rejected(url):
    assert clean.endpoint_gate(url).status == "FAIL"


def test_public_https_mcp_endpoint_is_accepted():
    assert clean.endpoint_gate("https://gremlin.example/mcp").status == "PASS"


def test_portable_mcp_manifest_uses_current_streamable_http_schema():
    manifest = clean.mcp_manifest("https://gremlin.example/mcp")
    assert manifest["$schema"] == clean.MCP_SCHEMA
    assert manifest["mcpServers"]["gremlin"] == {
        "type": "streamable-http",
        "url": "https://gremlin.example/mcp",
    }


def test_package_is_self_contained_and_inspects(tmp_path: Path):
    target = tmp_path / "gremlin.zip"
    result = clean.build_zip("https://gremlin.example/mcp", target)
    assert result["status"] == "PACKAGE_READY"
    assert result["next_required_gate"] == "CHATGPT_HOST_ADMISSION"
    assert result["host_gate"]["status"] == "EXTERNAL_REQUIRED"
    check = clean.inspect_zip(target)
    assert check["status"] == "PASS"
    with zipfile.ZipFile(target) as zf:
        assert set(clean.REQUIRED_FILES) == set(zf.namelist())
        assert b"localhost" not in zf.read("mcp.json")
        assert b"/dev/shm" not in zf.read("skills/gremlin/SKILL.md")
        mcp = json.loads(zf.read("mcp.json"))
        assert mcp["$schema"] == clean.MCP_SCHEMA
        assert mcp["mcpServers"]["gremlin"]["type"] == "streamable-http"


def test_inspection_rejects_wrong_remote_transport(tmp_path: Path):
    target = tmp_path / "bad.zip"
    files = clean.package_files("https://gremlin.example/mcp")
    mcp = json.loads(files["mcp.json"])
    mcp["mcpServers"]["gremlin"]["type"] = "http"
    files["mcp.json"] = (json.dumps(mcp) + "\n").encode()
    with zipfile.ZipFile(target, "w") as zf:
        for name, payload in files.items():
            zf.writestr(name, payload)
    result = clean.inspect_zip(target)
    assert result["status"] == "FAIL"
    assert "MCP_TRANSPORT_MUST_BE_STREAMABLE_HTTP" in result["failures"]


def test_refuses_overwrite(tmp_path: Path):
    target = tmp_path / "gremlin.zip"
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        clean.build_zip("https://gremlin.example/mcp", target)
