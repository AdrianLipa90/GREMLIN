from gremlin_mcp.pbh_relational_tidal import (
    build_relational_source_packet,
    tidal_shape,
)


def scaled(m, s):
    return [[s*x for x in row] for row in m]


def test_consistent_tidal_fits_share_axis_and_mu():
    q = tidal_shape((0.2, -0.7, 0.68))
    packet = build_relational_source_packet([
        {
            "id": "cassini-juno-mars",
            "independent_data_layer": "major_planet_ranging",
            "tensor_3x3": scaled(q, 2.0e-13),
            "provenance": "synthetic test fixture",
        },
        {
            "id": "pluto-tno",
            "independent_data_layer": "pluto_tno_astrometry",
            "tensor_3x3": scaled(q, 2.1e-13),
            "provenance": "synthetic test fixture",
        },
    ])
    assert packet["aggregate"]["mean_axis_overlap_abs"] > 0.999999
    assert packet["aggregate"]["mean_tensor_shape_consistency"] > 0.999999
    assert packet["promotion_gate"]["mass_distance_degeneracy_unbroken"] is True
    assert packet["promotion_gate"]["PBH_identity_not_inferred_from_gravity_alone"] is True
