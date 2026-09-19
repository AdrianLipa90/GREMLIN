from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def _platform_name() -> str:
    return "windows" if sys.platform.startswith("win") else "linux"


def _write_entry_wrapper(work: Path) -> Path:
    """Create a neutral build entrypoint outside package directories.

    Compiling gremlin_mcp/install/launcher.py directly makes that directory a
    script search root. Because it contains secrets.py, Python/Nuitka can resolve
    an unrelated `import secrets` to gremlin_mcp/install/secrets.py as a top-level
    module, shadowing the standard-library secrets module. A wrapper in the build
    directory preserves normal package import semantics while keeping the runtime
    dispatch implementation in gremlin_mcp.install.launcher.
    """
    entry = work / "_gremlin_runtime_entry.py"
    entry.write_text(
        "from gremlin_mcp.install.launcher import main\n"
        "raise SystemExit(main())\n",
        encoding="utf-8",
    )
    return entry


def _nuitka_command(*, entry: Path, work: Path, exe_name: str) -> list[str]:
    """Build only the shipped runtime import graph, not every GREMLIN module.

    The standalone executable exposes three entry surfaces: the installation CLI,
    the licensed product MCP server, and the full GREMLIN MCP server with Hive and
    PhaseNav Bestiary runtime. Nuitka follows their static imports and the
    imports reachable from those modules. Do not use ``--include-package`` for the
    whole ``gremlin_mcp`` tree here: that also drags development/audit-only modules
    (notably SymPy and PyMuPDF) into the native C backend and can exhaust MSVC heap
    space even though those modules are not part of the shipped runtime surface.
    """
    return [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--include-module=gremlin_mcp.install.cli",
        "--include-module=gremlin_mcp.product_server",
        "--include-module=gremlin_mcp.server_with_hive",
        "--include-module=gremlin_mcp.phasenav_runtime",
        "--include-module=gremlin_mcp.workspace",
        "--include-module=tools.gremlin_client_protocol_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_phase_gates_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_numpy_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_threeway_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_analog_invariants_v01",
        "--include-module=tools.gremlin_bestiary_phasenav_live_binding_v01",
        "--include-module=tools.gremlin_geometry_phase_scheduler_v01",
        "--include-module=tools.gremlin_geometry_context_pack_v01",
        f"--output-dir={work}",
        f"--output-filename={exe_name}",
        str(entry),
    ]


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
    entry = _write_entry_wrapper(work)
    command = _nuitka_command(entry=entry, work=work, exe_name=exe_name)
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

    aliases = (
        ["gremlinctl.exe", "gremlin-product-mcp.exe", "gremlin-mcp.exe", "gremlin-workspace.exe"]
        if platform == "windows"
        else ["gremlinctl", "gremlin-product-mcp", "gremlin-mcp", "gremlin-workspace"]
    )
    for alias in aliases:
        destination = final / alias
        shutil.copy2(runtime, destination)
        if platform == "linux":
            destination.chmod(destination.stat().st_mode | 0o111)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one standalone GREMLIN runtime and expose ctl/product/full-MCP/workspace aliases")
    parser.add_argument("--output-root", default="dist", type=Path)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    path = build(output_root=args.output_root, clean=args.clean)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
