#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import time
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

SCHEMA = "GREMLIN_LOCAL_CI_PROXY_V0_1"
CONFIG_SCHEMA = "GREMLIN_LOCAL_CI_PROXY_CONFIG_V0_1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def json_sha256(value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_text(raw)


def run_cmd(argv: list[str], *, cwd: Path | None = None, timeout: int = 1800, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    stamp = utc_now()
    try:
        cp = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            timeout=timeout,
            check=False,
        )
        duration = time.monotonic() - started
        return {
            "argv": argv,
            "started_at": stamp,
            "duration_seconds": round(duration, 6),
            "returncode": cp.returncode,
            "stdout_sha256": sha256_text(cp.stdout),
            "stderr_sha256": sha256_text(cp.stderr),
            "stdout_tail": cp.stdout[-12000:],
            "stderr_tail": cp.stderr[-12000:],
            "status": "PASS" if cp.returncode == 0 else "FAIL",
        }
    except FileNotFoundError as exc:
        return {
            "argv": argv,
            "started_at": stamp,
            "duration_seconds": round(time.monotonic() - started, 6),
            "returncode": None,
            "stdout_sha256": sha256_text(""),
            "stderr_sha256": sha256_text(str(exc)),
            "stdout_tail": "",
            "stderr_tail": str(exc),
            "status": "ENVIRONMENT_FAILURE",
        }
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        return {
            "argv": argv,
            "started_at": stamp,
            "duration_seconds": round(time.monotonic() - started, 6),
            "returncode": None,
            "stdout_sha256": sha256_text(out),
            "stderr_sha256": sha256_text(err),
            "stdout_tail": out[-12000:],
            "stderr_tail": err[-12000:],
            "status": "TIMEOUT",
        }


def git(repo: Path, *args: str, timeout: int = 120) -> dict[str, Any]:
    return run_cmd(["git", "-C", str(repo), *args], timeout=timeout)


def require_git_repo(repo: Path) -> None:
    r = git(repo, "rev-parse", "--is-inside-work-tree")
    if r["returncode"] != 0 or r["stdout_tail"].strip() != "true":
        raise ValueError(f"not a git worktree: {repo}")


def resolve_commit(repo: Path, ref: str) -> str:
    r = git(repo, "rev-parse", f"{ref}^{{commit}}")
    if r["returncode"] != 0:
        raise ValueError(f"cannot resolve commit {ref!r}: {r['stderr_tail'].strip()}")
    return r["stdout_tail"].strip().splitlines()[-1]


def repo_state(repo: Path) -> dict[str, Any]:
    head = resolve_commit(repo, "HEAD")
    status = git(repo, "status", "--porcelain=v1")
    remote = git(repo, "remote", "get-url", "origin")
    return {
        "head": head,
        "dirty": bool(status["stdout_tail"].strip()),
        "origin": remote["stdout_tail"].strip() if remote["returncode"] == 0 else None,
    }


def synthetic_merge_commit(repo: Path, base_ref: str, head_ref: str) -> dict[str, str]:
    base = resolve_commit(repo, base_ref)
    head = resolve_commit(repo, head_ref)
    mt = git(repo, "merge-tree", "--write-tree", base, head)
    if mt["returncode"] != 0:
        raise RuntimeError("MERGE_CONFLICT\n" + (mt["stdout_tail"] + "\n" + mt["stderr_tail"]).strip())
    tree = mt["stdout_tail"].strip().splitlines()[0]
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "GREMLIN Local CI Proxy",
        "GIT_AUTHOR_EMAIL": "local-ci@localhost",
        "GIT_COMMITTER_NAME": "GREMLIN Local CI Proxy",
        "GIT_COMMITTER_EMAIL": "local-ci@localhost",
    })
    cc = run_cmd(
        ["git", "-C", str(repo), "commit-tree", tree, "-p", base, "-p", head, "-m", "GREMLIN local CI synthetic merge"],
        timeout=120,
        env=env,
    )
    if cc["returncode"] != 0:
        raise RuntimeError("cannot create synthetic merge commit: " + cc["stderr_tail"])
    return {"base": base, "head": head, "tree": tree, "synthetic_commit": cc["stdout_tail"].strip().splitlines()[-1]}


def load_config(path: Path) -> dict[str, Any]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")
    return cfg


def ensure_allowed(repo: Path, cfg: dict[str, Any]) -> None:
    roots = [Path(os.path.expanduser(x)).resolve() for x in cfg.get("allowed_roots", [])]
    if not roots:
        return
    rr = repo.resolve()
    if not any(rr == root or root in rr.parents for root in roots):
        raise PermissionError(f"repo path is not under an allowed root: {rr}")


def expand_profile(profile: dict[str, Any]) -> list[dict[str, Any]]:
    commands = profile.get("commands", [])
    matrix = profile.get("matrix") or {}
    if not matrix:
        return [{"matrix": {}, "commands": commands}]
    keys = list(matrix.keys())
    rows: list[dict[str, Any]] = []

    def rec(i: int, acc: dict[str, str]) -> None:
        if i == len(keys):
            rows.append({"matrix": dict(acc), "commands": commands})
            return
        k = keys[i]
        for v in matrix[k]:
            acc[k] = str(v)
            rec(i + 1, acc)
        acc.pop(k, None)

    rec(0, {})
    return rows


def subst_argv(argv: list[str], matrix: dict[str, str]) -> list[str]:
    out = []
    for token in argv:
        value = token
        for k, v in matrix.items():
            value = value.replace("{" + k + "}", v)
        out.append(value)
    return out


def classify(command_results: list[dict[str, Any]]) -> str:
    if any(r["status"] == "ENVIRONMENT_FAILURE" for r in command_results):
        return "FAIL_ENVIRONMENT"
    if any(r["status"] == "TIMEOUT" for r in command_results):
        return "FAIL_TIMEOUT"
    if any(r["status"] == "FAIL" for r in command_results):
        return "FAIL_TEST_OR_GATE"
    return "PASS"


def run_gate(cfg: dict[str, Any], *, repo: Path, profile_name: str, commit: str | None = None,
             base: str | None = None, head: str | None = None) -> dict[str, Any]:
    repo = repo.resolve()
    ensure_allowed(repo, cfg)
    require_git_repo(repo)
    profile = cfg.get("profiles", {}).get(profile_name)
    if not profile:
        raise ValueError(f"unknown profile: {profile_name}")
    if (base or head) and not (base and head):
        raise ValueError("base and head must be supplied together")
    if base and head and commit:
        raise ValueError("choose exact commit OR synthetic merge mode")

    started_at = utc_now()
    run_id = uuid.uuid4().hex
    source_state = repo_state(repo)
    merge_meta: dict[str, str] | None = None
    mode = "commit"
    target_commit = resolve_commit(repo, commit or "HEAD")
    if base and head:
        mode = "synthetic_merge"
        try:
            merge_meta = synthetic_merge_commit(repo, base, head)
            target_commit = merge_meta["synthetic_commit"]
        except RuntimeError as exc:
            receipt = {
                "schema": SCHEMA,
                "run_id": run_id,
                "started_at": started_at,
                "finished_at": utc_now(),
                "mode": mode,
                "repo": str(repo),
                "profile": profile_name,
                "source_state": source_state,
                "base_ref": base,
                "head_ref": head,
                "verdict": "FAIL_MERGE_CONFLICT",
                "error": str(exc),
                "host": host_info(),
                "commands": [],
            }
            return finalize_receipt(cfg, receipt)

    work_root = Path(os.path.expanduser(cfg.get("work_dir", "~/.gremlin/local-ci/work"))).resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    worktree = Path(tempfile.mkdtemp(prefix=f"{run_id}-", dir=str(work_root)))
    worktree.rmdir()
    added = False
    results: list[dict[str, Any]] = []
    try:
        wa = git(repo, "worktree", "add", "--detach", str(worktree), target_commit, timeout=180)
        if wa["returncode"] != 0:
            raise RuntimeError("cannot create detached worktree: " + wa["stderr_tail"])
        added = True
        rows = expand_profile(profile)
        fail_fast = bool(profile.get("fail_fast", True))
        default_timeout = int(profile.get("timeout_seconds", 1800))
        for row in rows:
            matrix = row["matrix"]
            for cmd in row["commands"]:
                argv = subst_argv([str(x) for x in cmd["argv"]], matrix)
                timeout = int(cmd.get("timeout_seconds", default_timeout))
                result = run_cmd(argv, cwd=worktree, timeout=timeout)
                result["name"] = cmd.get("name") or " ".join(argv)
                result["matrix"] = matrix
                results.append(result)
                if fail_fast and result["status"] != "PASS":
                    break
            if fail_fast and results and results[-1]["status"] != "PASS":
                break
        verdict = classify(results)
        receipt = {
            "schema": SCHEMA,
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": utc_now(),
            "mode": mode,
            "repo": str(repo),
            "profile": profile_name,
            "source_state": source_state,
            "target_commit": target_commit,
            "merge": merge_meta,
            "host": host_info(),
            "commands": results,
            "verdict": verdict,
        }
        return finalize_receipt(cfg, receipt)
    except Exception as exc:
        receipt = {
            "schema": SCHEMA,
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": utc_now(),
            "mode": mode,
            "repo": str(repo),
            "profile": profile_name,
            "source_state": source_state,
            "target_commit": target_commit,
            "merge": merge_meta,
            "host": host_info(),
            "commands": results,
            "verdict": "FAIL_PROXY_INTERNAL",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        return finalize_receipt(cfg, receipt)
    finally:
        if added:
            git(repo, "worktree", "remove", "--force", str(worktree), timeout=180)
        if worktree.exists():
            shutil.rmtree(worktree, ignore_errors=True)


def host_info() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pid": os.getpid(),
    }


def finalize_receipt(cfg: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    receipt["receipt_sha256"] = json_sha256(receipt)
    root = Path(os.path.expanduser(cfg.get("receipt_dir", "~/.gremlin/local-ci/receipts"))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    name = f"{receipt['started_at'].replace(':','').replace('+','_')}_{receipt['run_id']}.json"
    path = root / name
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(path)
    return receipt


class Handler(BaseHTTPRequestHandler):
    server_version = "GREMLINLocalCI/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, code: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(200, {"schema": SCHEMA, "status": "ok", "time": utc_now()})
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        cfg = self.server.proxy_config  # type: ignore[attr-defined]
        token = cfg.get("auth_token") or os.environ.get("GREMLIN_CI_TOKEN")
        if token and self.headers.get("Authorization") != f"Bearer {token}":
            self.send_json(401, {"error": "unauthorized"})
            return
        if self.path not in {"/v1/run", "/v1/merge"}:
            self.send_json(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > 1024 * 1024:
                raise ValueError("invalid body size")
            body = json.loads(self.rfile.read(n).decode("utf-8"))
            common = {
                "repo": Path(body["repo"]),
                "profile_name": body["profile"],
            }
            if self.path == "/v1/run":
                result = run_gate(cfg, **common, commit=body.get("commit") or "HEAD")
            else:
                result = run_gate(cfg, **common, base=body["base"], head=body["head"])
            self.send_json(200 if result["verdict"] == "PASS" else 409, result)
        except Exception as exc:
            self.send_json(400, {"error": str(exc), "type": type(exc).__name__})


def serve(cfg: dict[str, Any]) -> None:
    host = cfg.get("listen_host", "127.0.0.1")
    port = int(cfg.get("listen_port", 8765))
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("v0.1 intentionally binds only to loopback")
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.proxy_config = cfg  # type: ignore[attr-defined]
    print(json.dumps({"schema": SCHEMA, "status": "listening", "host": host, "port": port}))
    httpd.serve_forever()


def main() -> int:
    ap = argparse.ArgumentParser(description="GREMLIN local CI proxy: detached exact-head and synthetic-merge gates")
    ap.add_argument("--config", required=True, type=Path)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve")
    r = sub.add_parser("run")
    r.add_argument("--repo", required=True, type=Path)
    r.add_argument("--profile", required=True)
    r.add_argument("--commit", default="HEAD")
    m = sub.add_parser("merge")
    m.add_argument("--repo", required=True, type=Path)
    m.add_argument("--profile", required=True)
    m.add_argument("--base", required=True)
    m.add_argument("--head", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.cmd == "serve":
        serve(cfg)
        return 0
    if args.cmd == "run":
        receipt = run_gate(cfg, repo=args.repo, profile_name=args.profile, commit=args.commit)
    else:
        receipt = run_gate(cfg, repo=args.repo, profile_name=args.profile, base=args.base, head=args.head)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
