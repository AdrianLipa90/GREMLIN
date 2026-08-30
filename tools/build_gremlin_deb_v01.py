from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


_LDD_ARROW = re.compile(r"=>\s+(/\S+)")
_LDD_DIRECT = re.compile(r"^\s*(/\S+)\s+")


def _system_libraries(binary: Path, *, private_runtime: Path) -> set[Path]:
    result = subprocess.run(["ldd", str(binary)], check=True, stdout=subprocess.PIPE, text=True)
    libraries: set[Path] = set()
    private_root = private_runtime.resolve()
    for line in result.stdout.splitlines():
        match = _LDD_ARROW.search(line) or _LDD_DIRECT.search(line)
        if not match:
            if "not found" in line:
                raise RuntimeError(f"unresolved shared library for {binary}: {line.strip()}")
            continue
        path = Path(match.group(1)).resolve()
        try:
            path.relative_to(private_root)
            continue
        except ValueError:
            pass
        libraries.add(path)
    return libraries


def _owner_package(path: Path) -> str:
    candidates = [path, Path(os.path.realpath(path))]
    errors: list[str] = []
    for candidate in candidates:
        result = subprocess.run(
            ["dpkg-query", "-S", str(candidate)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            package = result.stdout.split(": ", 1)[0].strip()
            return package.split(":", 1)[0]
        errors.append(result.stderr.strip())
    raise RuntimeError(f"could not map shared library to Debian package: {path}; {'; '.join(errors)}")


def _dependencies(runtime: Path, control_center: Path) -> list[str]:
    binaries = [runtime / "gremlin-runtime", control_center]
    libraries: set[Path] = set()
    for binary in binaries:
        if not binary.is_file():
            raise ValueError(f"expected executable is missing: {binary}")
        libraries.update(_system_libraries(binary, private_runtime=runtime))
    packages = {_owner_package(path) for path in libraries}
    packages.add("libsecret-tools")
    return sorted(packages)


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise ValueError(f"source directory is missing: {source}")
    shutil.copytree(source, destination, dirs_exist_ok=True)


def build(*, dist_root: Path, version: str, output: Path, architecture: str = "amd64") -> Path:
    runtime = dist_root / "linux" / "runtime"
    control_center = dist_root / "linux" / "control-center" / "gremlin-control-center"
    resources = dist_root / "linux" / "resources"
    desktop = Path("packaging/linux/gremlin.desktop")
    for required in (runtime, resources):
        if not required.exists():
            raise ValueError(f"required build input is missing: {required}")
    if not control_center.is_file():
        raise ValueError(f"control center binary is missing: {control_center}")
    if not desktop.is_file():
        raise ValueError(f"desktop file is missing: {desktop}")

    deps = _dependencies(runtime, control_center)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f"output already exists: {output}")

    with tempfile.TemporaryDirectory(prefix="gremlin-deb-") as tmp:
        root = Path(tmp) / "root"
        debian = root / "DEBIAN"
        runtime_dst = root / "usr/lib/gremlin/runtime"
        bin_dst = root / "usr/bin"
        resources_dst = root / "usr/share/gremlin"
        applications_dst = root / "usr/share/applications"
        for directory in (debian, runtime_dst, bin_dst, resources_dst, applications_dst):
            directory.mkdir(parents=True, exist_ok=True)

        _copy_tree(runtime, runtime_dst)
        shutil.copy2(control_center, bin_dst / "gremlin-control-center")
        _copy_tree(resources, resources_dst)
        shutil.copy2(desktop, applications_dst / "gremlin.desktop")

        for name in ("gremlinctl", "gremlin-product-mcp"):
            target = Path("/usr/lib/gremlin/runtime") / name
            os.symlink(str(target), bin_dst / name)

        installed_kib = sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) // 1024
        control = "\n".join(
            [
                "Package: gremlin",
                f"Version: {version}",
                "Section: utils",
                "Priority: optional",
                f"Architecture: {architecture}",
                "Maintainer: Adrian Lipa / Intention Lab",
                f"Installed-Size: {installed_kib}",
                f"Depends: {', '.join(deps)}",
                "Description: GREMLIN AI Research Orchestrator",
                " Licensed GREMLIN MCP runtime, native Control Center and",
                " installation/diagnostics tooling for local AI orchestration.",
                "",
            ]
        )
        (debian / "control").write_text(control, encoding="utf-8")
        subprocess.run(
            ["dpkg-deb", "--root-owner-group", "--build", str(root), str(output)],
            check=True,
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a GREMLIN Debian package from prebuilt release artifacts")
    parser.add_argument("--dist-root", type=Path, default=Path("dist"))
    parser.add_argument("--version", default="0.5.0~preview1-1")
    parser.add_argument("--architecture", default="amd64")
    parser.add_argument("--output", type=Path, default=Path("dist/installer/gremlin_0.5.0~preview1-1_amd64.deb"))
    args = parser.parse_args()
    print(build(dist_root=args.dist_root, version=args.version, output=args.output, architecture=args.architecture))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
