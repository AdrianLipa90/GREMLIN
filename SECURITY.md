# Security Policy

GREMLIN uses fail-closed runtime and repository contracts, but security defects must be treated separately from ordinary correctness bugs.

## Supported surface

Security review covers the current `main` branch and current release candidates. Historical branches and archived experiment snapshots may contain obsolete code and are not security-supported deployment surfaces.

## Reporting

Do not publish working exploit details, credentials, private tokens, or sensitive customer data in a public issue.

Use GitHub private vulnerability reporting when it is available for this repository. If that surface is unavailable, contact the repository owner through GitHub and disclose only enough information to establish a private reporting channel.

A useful report includes the affected commit, file or entrypoint, reproducible preconditions, impact, and the smallest safe proof of concept.

## Automated gates

The repository runs:

- repository-wide compile, test, wheel-build and isolated-wheel smoke validation;
- `pip-audit` against the installed project dependency graph;
- high-severity Bandit SAST over GREMLIN Python runtime/tool surfaces;
- scheduled Dependabot checks for Python and GitHub Actions dependencies.

Security scanning supplements, but does not replace, exact-head functional validation, NOEMA admission checks, authorization boundaries, or manual review of high-consequence changes.
