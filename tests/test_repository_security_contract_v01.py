from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_security_workflow_is_fail_closed_and_recurring() -> None:
    text = (ROOT / ".github/workflows/gremlin-security-audit-v01.yml").read_text(encoding="utf-8")
    assert "pip-audit --progress-spinner=off ." in text
    assert "bandit -q -r gremlin_mcp tools client -lll -ii" in text
    assert "--report gremlin-runtime-dependency-report.json" in text
    assert "python -m pip check" in text
    assert "actions/upload-artifact@v4" in text
    assert "schedule:" in text
    assert "workflow_dispatch:" in text
    assert "contents: read" in text


def test_fail_loud_covers_contract_and_policy_surfaces() -> None:
    text = (ROOT / ".github/workflows/gremlin-fail-loud-audit-v01.yml").read_text(encoding="utf-8")
    required = (
        "'native/**'",
        "'spec/**'",
        "'config/**'",
        "'LICENSE'",
        "'AI_TRAINING_POLICY.md'",
        "'README.md'",
        "'.github/workflows/**'",
        "'.github/dependabot.yml'",
        "'SECURITY.md'",
    )
    for token in required:
        assert token in text, token


def test_readme_does_not_present_historical_sha_as_moving_current_attestation() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Current validated baseline — 2026-09-18" not in text
    assert "Validation authority is exact-head CI" in text


def _dotted(node):
    import ast

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def _python_surfaces() -> list[Path]:
    roots = ("gremlin_mcp", "tools", "client", "examples", "benchmarks")
    out: list[Path] = []
    for name in roots:
        root = ROOT / name
        if root.is_dir():
            out.extend(sorted(root.rglob("*.py")))
    return out


def test_runtime_surfaces_forbid_shell_escape_and_eval() -> None:
    import ast

    violations: list[tuple[str, int, str]] = []
    for path in _python_surfaces():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            target = _dotted(node.func)
            if target in {"os.system", "os.popen", "eval"}:
                violations.append((str(path.relative_to(ROOT)), node.lineno, target))
                continue
            if target in {
                "subprocess.run",
                "subprocess.call",
                "subprocess.check_call",
                "subprocess.check_output",
                "subprocess.Popen",
            }:
                for keyword in node.keywords:
                    if (
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        violations.append((str(path.relative_to(ROOT)), node.lineno, f"{target}:shell=True"))
    assert not violations, violations


def test_dynamic_exec_is_confined_to_validated_prototype_harness() -> None:
    import ast

    locations: list[tuple[str, int]] = []
    for path in _python_surfaces():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "exec":
                locations.append((str(path.relative_to(ROOT)), node.lineno))

    assert {path for path, _ in locations} == {"tools/gremlin_experiment_harness_v01.py"}
    assert len(locations) == 1

    harness = (ROOT / "tools/gremlin_experiment_harness_v01.py").read_text(encoding="utf-8")
    assert "_validate_generated_ast(source)" in harness
    assert '"__builtins__"' in harness
    assert "generated prototype contains forbidden syntax" in harness
    assert "attribute access outside prototype whitelist" in harness


def test_runtime_cryptography_dependency_is_on_patched_50x_line() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"cryptography>=50.0.1,<51"' in text
    assert '"cryptography>=42,<47"' not in text
