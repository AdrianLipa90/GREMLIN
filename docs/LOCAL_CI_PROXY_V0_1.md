# GREMLIN Local CI Proxy v0.1

Repository-local replacement for GitHub Actions merge gating.

The proxy tests an exact commit in a detached temporary worktree or synthesizes a merge commit with `git merge-tree --write-tree` and `git commit-tree`. It does not create a branch or mutate the checked-out branch during validation.

## Canonical commands

Exact commit:

```text
python3 tools/gremlin_ci_proxy.py --config config/local-ci.json run --repo /path/to/GREMLIN --profile gremlin-pytest-current --commit HEAD
```

Synthetic merge:

```text
python3 tools/gremlin_ci_proxy.py --config config/local-ci.json merge --repo /path/to/GREMLIN --profile gremlin-pytest-current --base main --head <candidate-ref>
```

Focused residual-redteam gate:

```text
python3 tools/gremlin_ci_proxy.py --config config/local-ci.json run --repo /path/to/GREMLIN --profile gremlin-redteam-current --commit HEAD
```

Verdicts are `PASS`, `FAIL_TEST_OR_GATE`, `FAIL_ENVIRONMENT`, `FAIL_TIMEOUT`, `FAIL_MERGE_CONFLICT`, or `FAIL_PROXY_INTERNAL`.

Receipts include target commit, command exit codes, stdout/stderr hashes, bounded output tails and host fingerprint.

This is local GREMLIN T0/T1 evidence. It must not be relabelled as GitHub exact-head CI. Promotion requires PASS for the exact candidate tree being admitted.
