from __future__ import annotations

from typing import Final

SCHEMA: Final = "GREMLIN_CONSTITUTIONAL_RUNTIME_SURFACE_REGISTRY_V0_1"
VERSION: Final = "0.1.0"

# Explicit policy registry. It is intentionally reviewed and versioned.
# This is not inferred from naming conventions.
SURFACES: Final[dict[str, dict[str, dict[str, object]]]] = {
    "gremlin_mcp/hive_server.py": {
        "gremlin_hive_exchange_ingest": {
            "endpoint": "gremlin_hive_exchange_ingest",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_envelope",),
        },
        "gremlin_hive_exchange_bundle_ingest": {
            "endpoint": "gremlin_hive_exchange_bundle_ingest",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_bundle",),
        },
        "gremlin_hive_sync_apply": {
            "endpoint": "gremlin_hive_sync_apply",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("apply_hive_delta",),
        },
        "gremlin_hive_place": {
            "endpoint": "gremlin_hive_place",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("place",),
        },
        "gremlin_hive_gates": {
            "endpoint": "gremlin_hive_gates",
            "consequence_class": "GOVERNANCE",
            "mutation_calls": ("update_gates",),
        },
        "gremlin_hive_dispute": {
            "endpoint": "gremlin_hive_dispute",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("dispute",),
        },
        "gremlin_hive_latch": {
            "endpoint": "gremlin_hive_latch",
            "consequence_class": "GOVERNANCE",
            "mutation_calls": ("latch",),
        },
    },
    "gremlin_mcp/hive_authority_server.py": {
        "gremlin_hive_exchange_ingest": {
            "endpoint": "gremlin_hive_exchange_ingest",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_envelope",),
        },
        "gremlin_hive_exchange_bundle_ingest": {
            "endpoint": "gremlin_hive_exchange_bundle_ingest",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_bundle",),
        },
        "gremlin_hive_sync_apply": {
            "endpoint": "gremlin_hive_sync_apply",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("apply_hive_delta",),
        },
        "gremlin_hive_place": {
            "endpoint": "gremlin_hive_place",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("place",),
        },
        "gremlin_hive_gates": {
            "endpoint": "gremlin_hive_gates",
            "consequence_class": "GOVERNANCE",
            "mutation_calls": ("update_gates",),
        },
        "gremlin_hive_dispute": {
            "endpoint": "gremlin_hive_dispute",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("dispute",),
        },
        "gremlin_hive_latch": {
            "endpoint": "gremlin_hive_latch",
            "consequence_class": "GOVERNANCE",
            "mutation_calls": ("latch",),
        },
    },
    "gremlin_mcp/server_with_hive.py": {
        "gremlin_hive_exchange_ingest": {
            "endpoint": "gremlin_hive_exchange_ingest",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_envelope",),
        },
        "gremlin_hive_exchange_bundle_ingest": {
            "endpoint": "gremlin_hive_exchange_bundle_ingest",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_bundle",),
        },
        "gremlin_hive_sync_apply": {
            "endpoint": "gremlin_hive_sync_apply",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("apply_hive_delta",),
        },
        "gremlin_hive_place": {
            "endpoint": "gremlin_hive_place",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("place",),
        },
        "gremlin_hive_gates": {
            "endpoint": "gremlin_hive_gates",
            "consequence_class": "GOVERNANCE",
            "mutation_calls": ("update_gates",),
        },
        "gremlin_hive_dispute": {
            "endpoint": "gremlin_hive_dispute",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("dispute",),
        },
        "gremlin_hive_latch": {
            "endpoint": "gremlin_hive_latch",
            "consequence_class": "GOVERNANCE",
            "mutation_calls": ("latch",),
        },
        "gremlin_hive_research_execute": {
            "endpoint": "gremlin_hive_research_execute",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("execute_research", "ingest_research_execution"),
        },
    },
    "gremlin_mcp/bestiary_memory_gateway.py": {
        "ingest_exchange_envelope_as_beast": {
            "endpoint": "bestiary_memory_gateway.ingest_exchange_envelope_as_beast",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_envelope",),
        },
        "ingest_exchange_bundle_as_beast": {
            "endpoint": "bestiary_memory_gateway.ingest_exchange_bundle_as_beast",
            "consequence_class": "APPEND_ONLY",
            "mutation_calls": ("ingest_exchange_bundle",),
        },
    },
    "gremlin_mcp/raphael.py": {
        "execute": {
            "endpoint": "raphael.execute",
            "consequence_class": "MUTATION",
            "mutation_calls": ("consume", "prepare", "apply_operation"),
        },
    },
    "gremlin_mcp/ferret.py": {
        "execute_authorized_action": {
            "endpoint": "ferret.execute_authorized_action",
            "consequence_class": "MUTATION",
            "mutation_calls": ("consume", "executor"),
        },
    },
}


def manifest() -> dict[str, object]:
    surface_count = sum(len(functions) for functions in SURFACES.values())
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "file_count": len(SURFACES),
        "surface_count": surface_count,
        "files": {
            path: {
                name: {
                    "endpoint": row["endpoint"],
                    "consequence_class": row["consequence_class"],
                    "mutation_calls": list(row["mutation_calls"]),
                }
                for name, row in functions.items()
            }
            for path, functions in SURFACES.items()
        },
        "registry_is_explicit_policy": True,
        "registry_exhaustiveness_proven": False,
    }


__all__ = ["SCHEMA", "SURFACES", "VERSION", "manifest"]
