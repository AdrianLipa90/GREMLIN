from gremlin_mcp.pbh_relational_tidal import (
    build_relational_source_packet,
    tensor_diagnostics,
    tidal_shape,
)


def scaled(m, s):
    return [[s * x for x in row] for row in m]


def test_ideal_point_mass_tensor_passes_eigenshape_gate():
    q = tidal_shape((0.2, -0.7, 0.68))
    d = tensor_diagnostics(scaled(q, 2.0e-13))
    assert d["passes"]["all"] is True
    assert d["point_mass_shape_residual"] < 1e-10
    assert d["transverse_eigenvalue_split_over_mu"] < 1e-10
    assert d["mu_fit"] > 0.0


def test_trace_free_non_point_tensor_fails_shape_gate():
    t = [
        [1.0, 0.0, 0.0],
        [0.0, 0.5, 0.0],
        [0.0, 0.0, -1.5],
    ]
    d = tensor_diagnostics(t)
    assert d["passes"]["trace_free_compatible"] is True
    assert d["passes"]["all"] is False
    assert (
        d["passes"]["point_mass_shape"] is False
        or d["passes"]["transverse_degeneracy"] is False
    )


def test_traceful_tensor_fails_trace_gate():
    t = [
        [2.0, 0.0, 0.0],
        [0.0, -0.5, 0.0],
        [0.0, 0.0, -0.5],
    ]
    d = tensor_diagnostics(t)
    assert d["passes"]["trace_free_compatible"] is False
    assert d["passes"]["all"] is False


def test_packet_requires_each_layer_to_have_point_mass_shape():
    q = tidal_shape((0.2, -0.7, 0.68))
    bad = [
        [1.0e-13, 0.0, 0.0],
        [0.0, 0.5e-13, 0.0],
        [0.0, 0.0, -1.5e-13],
    ]
    packet = build_relational_source_packet([
        {
            "id": "layer-a",
            "independent_data_layer": "major_planet_ranging",
            "tensor_3x3": scaled(q, 2.0e-13),
            "provenance": "synthetic operator test fixture",
        },
        {
            "id": "layer-b",
            "independent_data_layer": "tno_astrometry",
            "tensor_3x3": bad,
            "provenance": "synthetic operator test fixture",
        },
    ])
    assert packet["status"] == "RELATIONAL_TENSOR_ONLY"
    assert packet["aggregate"]["all_point_mass_shape_pass"] is False
