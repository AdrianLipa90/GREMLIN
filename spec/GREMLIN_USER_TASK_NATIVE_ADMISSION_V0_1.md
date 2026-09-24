# Native user-task admission boundary v0.1

GREMLIN's repository-level contract and NOEMA's host runtime are deliberately separate.

The repository defines the deterministic user-task gateway and reference admission semantics. The host runtime decides when to invoke that contract. The validated NOEMA binding invokes a native GREMLIN + PhaseNav preflight at STARTPROMPT and stores the result in the turn state.

The key boundary is context isolation. A continuation/deictic prompt such as `Kontynuuj` may use `current_task` and `active_path` to recover routing context. An explicit new task is task-only for specialist membership, even when stale context exists.

PhaseNav may provide scheduling/locality/order information but cannot add or remove specialists selected by the deterministic semantic admission mask.

The native admission path never grants write, send, merge, deploy, publication, canon-promotion or other external-effect authority. Those actions remain under the host's normal explicit authorization boundary.

The GREMLIN-vs-bypass shadow telemetry remains a separate observational channel. It is useful for benchmarks but does not control the native execution membership.
