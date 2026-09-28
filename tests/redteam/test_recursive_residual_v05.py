from collections import OrderedDict

import numpy as np

from gremlin_mcp.recursive_residual_v05 import recursive_residual_decomposition_v05


def _meta(names, null_policy="run_permutation"):
    return {
        name: {
            "frozen_before_fit": True,
            "independent_of_target_fit": True,
            "source_type": "instrument_channel",
            "source_id": f"redteam-v05:{name}",
            "null_policy": null_policy,
        }
        for name in names
    }


def _seed10029_case():
    rng = np.random.default_rng(10029)
    runs, n = 8, 64
    true = rng.normal(size=(runs, n))
    raw = 0.5 * true + rng.normal(size=(runs, n))
    candidates = OrderedDict([("true", true)])
    for j in range(7):
        candidates[f"noise{j:02d}"] = rng.normal(size=(runs, n))
    return raw, candidates


def test_v05_global_alpha_ledger_kills_seed10029_false_second_layer():
    raw, candidates = _seed10029_case()
    result, _, _ = recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        global_familywise_alpha=0.01,
        null_count=1023,
        max_layers=8,
    )
    assert result["accepted_layers"] == ["true"]
    assert result["policy"]["uniform_round_alpha_budget"] == 0.00125
    assert result["policy"]["shared_synchronized_null_worlds"] is True


def test_v05_fails_closed_if_null_resolution_cannot_support_alpha_budget():
    raw, candidates = _seed10029_case()
    try:
        recursive_residual_decomposition_v05(
            raw,
            np.zeros_like(raw),
            candidates,
            _meta(candidates),
            global_familywise_alpha=0.01,
            null_count=255,
            max_layers=8,
        )
    except ValueError as exc:
        assert "cannot resolve round alpha" in str(exc)
    else:
        raise AssertionError("under-resolved null ensemble was accepted")


def test_v05_mapping_order_is_not_authoritative():
    raw, candidates = _seed10029_case()
    a, _, _ = recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        global_familywise_alpha=0.01,
        null_count=1023,
        max_layers=8,
    )
    rev = OrderedDict(reversed(list(candidates.items())))
    b, _, _ = recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        rev,
        _meta(rev),
        global_familywise_alpha=0.01,
        null_count=1023,
        max_layers=8,
    )
    assert a["accepted_layers"] == b["accepted_layers"]
    assert (
        a["final_packet"]["commitments"]["residual_sha256"]
        == b["final_packet"]["commitments"]["residual_sha256"]
    )


def test_v05_pure_noise_family_does_not_accept_layer():
    rng = np.random.default_rng(404)
    raw = rng.normal(size=(8, 64))
    candidates = {
        f"noise{j:02d}": rng.normal(size=raw.shape)
        for j in range(8)
    }
    result, _, _ = recursive_residual_decomposition_v05(
        raw,
        np.zeros_like(raw),
        candidates,
        _meta(candidates),
        global_familywise_alpha=0.01,
        null_count=1023,
        max_layers=8,
    )
    assert result["accepted_layers"] == []


def test_v05_target_derived_candidate_fails_before_null_worlds():
    raw, candidates = _seed10029_case()
    metadata = _meta(candidates)
    metadata["true"]["independent_of_target_fit"] = False
    try:
        recursive_residual_decomposition_v05(
            raw,
            np.zeros_like(raw),
            candidates,
            metadata,
            global_familywise_alpha=0.01,
            null_count=1023,
            max_layers=8,
        )
    except ValueError as exc:
        assert "target-derived" in str(exc)
    else:
        raise AssertionError("target-derived nuisance accepted")
