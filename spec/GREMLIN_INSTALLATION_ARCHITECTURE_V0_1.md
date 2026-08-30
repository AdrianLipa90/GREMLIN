# GREMLIN Installation Architecture v0.1

Status: IMPLEMENTATION CANDIDATE

Branch: `feat/gremlin-installation-control-center-v0.1`

## 1. Product boundary

GREMLIN installation is split into four independently testable layers:

```text
platform installer
  -> GREMLIN Control Center
  -> gremlinctl
  -> GREMLIN product runtime / MCP
```

The installer owns files under the application installation root. User configuration, product state, cache, diagnostics and activation material live outside that root so upgrades can replace program files without replacing customer state.

## 2. Windows layout

Default per-user installation requires no administrator elevation:

```text
%LOCALAPPDATA%\Programs\GREMLIN\
    gremlin-product-mcp.exe
    gremlinctl.exe
    gremlin-control-center.exe
    runtime\
    resources\
        issuer-public.pem
        profiles\
```

User configuration:

```text
%APPDATA%\GREMLIN\
    config.toml
    license.json
    client-profile.json
    integrations.json
```

User state:

```text
%LOCALAPPDATA%\GREMLIN\
    state\gremlin-worker.sqlite3
    logs\
    cache\
    data\diagnostics\
```

Optional machine policy:

```text
%ProgramData%\GREMLIN\policy.toml
```

## 3. Linux layout

Program files installed by the `.deb` package:

```text
/usr/bin/gremlin-product-mcp
/usr/bin/gremlinctl
/usr/bin/gremlin-control-center
/usr/lib/gremlin/
/usr/share/gremlin/
    issuer-public.pem
    profiles/
/usr/share/applications/gremlin.desktop
```

Per-user paths follow XDG environment variables with standard fallbacks:

```text
$XDG_CONFIG_HOME/gremlin/        or ~/.config/gremlin/
$XDG_STATE_HOME/gremlin/         or ~/.local/state/gremlin/
$XDG_CACHE_HOME/gremlin/         or ~/.cache/gremlin/
$XDG_DATA_HOME/gremlin/          or ~/.local/share/gremlin/
```

Machine policy:

```text
/etc/gremlin/policy.toml
```

## 4. Operational configuration

Canonical user configuration schema:

```toml
schema = "GREMLIN_CONFIG_V0_1"

[runtime]
transport = "stdio"
state = "auto"

[network]
internet = true
local_http = false

[research]
max_workers = 4
max_sources = 24

[logging]
level = "info"
```

Ordinary configuration resolution:

```text
defaults
  < user config
  < environment overrides
  < CLI overrides
```

Machine policy is then applied as a restrictive layer. v0.1 supports restrictive internet/local-HTTP switches, worker/source ceilings and a forced transport. Signed product entitlements and client profiles remain independent capability gates.

Effective capability remains an intersection:

```text
signed product entitlement
  INTERSECT client profile
  INTERSECT machine policy
  INTERSECT requested runtime configuration
```

## 5. Runtime dependencies

Customer installers ship a standalone GREMLIN runtime. End users do not need a Python interpreter, pip, venv, `mcp` package or `cryptography` package.

Reference build strategy:

```text
GREMLIN Python runtime
  -> Nuitka standalone distribution
  -> platform package
```

Standalone directory mode is the default runtime packaging target because it provides deterministic startup, direct inspection of shipped components and straightforward installer upgrades.

Linux shared-library dependencies are derived during package construction with Debian tooling (`dpkg-shlibdeps`/debhelper) instead of maintaining a handwritten runtime dependency list.

Windows runtime DLL dependencies are collected into the standalone distribution and audited in CI before the Inno Setup stage.

## 6. Native Control Center

`gremlin-control-center` is a native Rust/egui application. It calls stable `gremlinctl` interfaces rather than importing the Python runtime.

Initial tabs:

```text
Overview
License
Integrations
Settings
Diagnostics
```

The first working skeleton consumes:

```text
gremlinctl doctor --json
```

This establishes one diagnostics/configuration authority for both command-line support and the GUI.

Target first-run flow:

```text
Welcome
  -> Activate or import license
  -> Detect MCP clients
  -> Select integrations
  -> Apply configuration atomically
  -> MCP handshake test
  -> Ready
```

## 7. Licensing, device activation and MCP authentication

These are separate product boundaries:

```text
product license
    determines licensed capability

device activation
    binds an installation to an issued entitlement

MCP authentication
    authenticates a principal connecting to a running network service
```

The existing Ed25519 signed product entitlement remains the product-license layer.

Device activation target design:

```text
installation generates device Ed25519 keypair
  -> sends device public key + license identifier to activation service
  -> activation service applies seat/device policy
  -> returns signed GREMLIN_DEVICE_CERT_V0_1
```

The design uses installation keys rather than hardware serial-number fingerprinting.

Private device keys and refresh credentials are stored through OS secret storage:

```text
Windows: Windows Credential Manager / DPAPI-backed credential storage
Linux: Secret Service compatible keyring (libsecret)
```

The configuration directory stores non-secret product configuration and signed public entitlement documents.

## 8. MCP integration model

Local desktop/IDE operation defaults to `stdio`:

```text
AI client
  -> starts gremlin-product-mcp
  -> stdio MCP session
```

This path avoids persistent ports and background daemons.

Local Streamable HTTP remains an advanced option and is constrained to loopback by the product MCP v0.1 boundary. Remote/Enterprise MCP adds its own authenticated transport layer in a later milestone.

Integration adapters expose a common contract:

```text
discover()
inspect()
install()
verify()
remove()
restore_backup()
```

Configuration changes to third-party MCP clients use:

```text
read
  -> validate
  -> backup
  -> merge GREMLIN entry
  -> atomic replace
  -> reread
  -> validate
  -> MCP handshake
```

Adapters never replace an entire third-party configuration with a GREMLIN-only file.

## 9. `gremlinctl` v0.1

Implemented commands:

```text
gremlinctl paths
gremlinctl init
gremlinctl config show
gremlinctl doctor
```

`paths` is the canonical Windows/XDG resolver used by packaging and UI code.

`init` creates per-user directories and a default config only when it is absent.

`doctor` emits sanitized PASS/WARN/FAIL diagnostics and exits nonzero only on FAIL.

Planned command families:

```text
gremlinctl license status|activate|import|deactivate
gremlinctl integrations list|install|remove|verify
gremlinctl mcp test
gremlinctl diagnostics collect
gremlinctl update check|install
```

## 10. Installer behavior

### Windows

Target artifact:

```text
GREMLIN-Setup-<version>-x64.exe
```

Reference installer: Inno Setup, per-user install, `PrivilegesRequired=lowest`.

Installer responsibilities:

```text
verify packaged payload
copy immutable program files
register uninstaller
create Start Menu shortcut
initialize user directories/config without overwrite
launch Control Center
```

### Debian/Ubuntu

Target artifact:

```text
gremlin_<version>_amd64.deb
```

Package responsibilities:

```text
install immutable binaries/resources
install desktop entry/icon
register shared-library dependencies
leave per-user configuration to first-run gremlinctl/Control Center
```

The package avoids creating home-directory files from root package-maintainer scripts.

## 11. Upgrade boundary

Program updates replace only immutable application files.

Persistent customer state remains under canonical config/state/data paths. Update packages do not overwrite:

```text
config.toml
license.json / device certificate
client-profile.json
integrations.json
SQLite state
logs/diagnostics except normal retention policy
```

A future signed update manifest binds platform, architecture, version, download digest and release signature.

## 12. v0.1 gates

Installation architecture v0.1 requires:

- Windows path-contract tests;
- Linux XDG path-contract tests;
- configuration precedence tests;
- restrictive machine-policy tests;
- sanitized doctor tests;
- packaged `gremlinctl` entrypoint;
- native Control Center `cargo check`;
- Control Center diagnostics bridge to `gremlinctl`;
- packaging templates for Windows and Debian-family Linux.
