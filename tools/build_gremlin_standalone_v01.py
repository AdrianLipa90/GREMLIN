from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def _platform_name() -> str:
    return "windows" if sys.platform.startswith("win") else "linux"


def build(*, output_root: Path, clean: bool) -> Path:
    platform = _platform_name()
    work = output_root / "_nuitka" / platform
    final = output_root / platform / "runtime"
    if clean:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(final, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    final.parent.mkdir(parents=True, exist_ok=True)

    exe_name = "gremlin-runtime.exe" if platform == "windows" else "gremlin-runtime"
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--include-package=gremlin_mcp",
        f"--output-dir={work}",
        f"--output-filename={exe_name}",
        "gremlin_mcp/install/launcher.py",
    ]
    subprocess.run(command, check=True)

    candidates = [path for path in work.rglob("*.dist") if path.is_dir()]
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one Nuitka standalone directory, found {candidates}")
    dist = candidates[0]
    if final.exists():
        shutil.rmtree(final)
    shutil.copytree(dist, final)

    runtime = final / exe_name
    if not runtime.is_file():
        matching = list(final.glob("gremlin-runtime*"))
        if len(matching) != 1 or not matching[0].is_file():
            raise RuntimeError("Nuitka runtime executable was not found after build")
        runtime = matching[0]

    aliases = ["gremlinctl.exe", "gremlin-product-mcp.exe"] if platform == "windows" else ["gremlinctl", "gremlin-product-mcp"]
    for alias in aliases:
        destination = final / alias
        shutil.copy2(runtime, destination)
        if platform == "linux":
            destination.chmod(destination.stat().st_mode | 0o111)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one standalone GREMLIN runtime and expose product/ctl aliases")
    parser.add_argument("--output-root", default="dist", type=Path)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    path = build(output_root=args.output_root, clean=args.clean)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
