import numpy as np
import pytest

from tools.gremlin_cross_modal_relational_evidence_v01 import EvidenceProvenance
from tools.gremlin_identifiability_measurement_design_v01 import (
    rank_independent_measurements,
)
from tools.gremlin_relational_measurement_channel_catalog_v01 import (
    CATALOG,
    CUSTOM_RESPONSE_REQUIRED,
    MODEL_CONSISTENCY,
    NUISANCE_CONTROL,
    SOURCE_SENSITIVE_CONDITIONAL,
    CatalogMeasurementInstance,
    MeasurementChannelCatalogError,
    bogoliubov_dispersion_signature,
    catalog_entries,
    channel_definition,
    holonomy_shell_signature,
    radial_scalar_signature_rows,
    rank_catalog_measurements,
    spectral_chain_rule_signature,
    spectral_line_frequency_signature,
    thomas_fermi_sound_speed_signature,
)
from tools.gremlin_source_family_signature_identifiability_v01 import (
    SourceFamilySignature,
)


PROV = EvidenceProvenance(
    repository="AdrianLipa90/GREMLIN",
    branch="integrate/relational-phase-observation-v0.1",
    commit="a" * 40,
    schema="GREMLIN_RELATIONAL_MEASUREMENT_CHANNEL_CATALOG_TEST_V0_1",
    receipt="pytest:measurement-channel-catalog",
)


def _source(name, values):
    return SourceFamilySignature(
        name=name,
        values=tuple(values),
        provenance=PROV,
        normalization="unit candidate amplitude",
    )


def test_catalog_ids_are_unique_and_roles_are_typed():
    entries = catalog_entries()
    ids = [entry.channel_id for entry in entries]
    assert len(ids) == len(set(ids))
    assert len(entries) == len(CATALOG)
    assert {
        entry.role for entry in entries
    } == {
        SOURCE_SENSITIVE_CONDITIONAL,
        NUISANCE_CONTROL,
        MODEL_CONSISTENCY,
        CUSTOM_RESPONSE_REQUIRED,
    }


def test_catalog_contains_requested_cross_modal_channel_families():
    ids = {entry.channel_id for entry in catalog_entries()}
    assert {
        "ORBITAL_OMEGA_SQ",
        "EPICYCLIC_KAPPA_SQ",
        "DENSITY_GRADIENT",
        "BOGOLIUBOV_SOUND_SPEED_SQ",
        "HOLONOMY_SHELL_RADIUS",
        "TRANSVERSE_PHASE_CURVATURE",
        "SPECTRAL_LINE_FREQUENCY",
        "SPECTRAL_INTENSITY",
        "SPECTRAL_2D_CROSS_PEAK",
        "SPECTRAL_PHASE_RESOLVED",
    }.issubset(ids)


def test_radial_scalar_response_rows_match_exact_identities():
    r = 2.0
    b = 1.0
    first = np.array([4.0, -2.0])
    second = np.array([1.5, 3.0])

    rows = radial_scalar_signature_rows(r, b, first, second)

    q_omega = first / r
    q_kappa = second + 3.0 * first / r
    beta2 = (b / r) ** 2

    assert rows["ORBITAL_OMEGA_SQ"] == pytest.approx(tuple(q_omega))
    assert rows["EPICYCLIC_KAPPA_SQ"] == pytest.approx(tuple(q_kappa))
    assert rows["KOBS_GRADIENT"] == pytest.approx(
        tuple(r * r * (q_kappa - q_omega))
    )
    assert rows["TRANSVERSE_PHASE_GRADIENT"] == pytest.approx(
        tuple(b * q_omega)
    )
    assert rows["TRANSVERSE_PHASE_CURVATURE"] == pytest.approx(
        tuple(
            beta2 * q_kappa
            + (1.0 - 4.0 * beta2) * q_omega
        )
    )
    assert rows["RADIAL_HESSIAN_EIGENVALUE"] == pytest.approx(
        tuple(second)
    )
    assert rows["TANGENTIAL_HESSIAN_EIGENVALUE"] == pytest.approx(
        tuple(q_omega)
    )


def test_spectral_chain_rule_maps_loop_phase_response_to_source_space():
    d_observable_d_phi = np.array([2.0, -1.0])
    d_phi_d_source = np.array(
        [
            [1.0, 0.0, 2.0],
            [0.0, 3.0, -1.0],
        ]
    )
    expected = d_observable_d_phi @ d_phi_d_source
    assert spectral_chain_rule_signature(
        d_observable_d_phi,
        d_phi_d_source,
    ) == pytest.approx(tuple(expected))


def test_line_frequency_chain_rule_matches_oes_identity():
    jm = np.array([3.0, -1.0])
    jn = np.array([1.0, 2.0])
    hbar = 2.0
    d_phi_d_source = np.array(
        [
            [1.0, 0.0],
            [0.5, 2.0],
        ]
    )
    expected_phase_slope = -(jm - jn) / hbar
    expected = expected_phase_slope @ d_phi_d_source
    assert spectral_line_frequency_signature(
        jm,
        jn,
        hbar,
        d_phi_d_source,
    ) == pytest.approx(tuple(expected))


def test_holonomy_shell_signature_is_chain_rule():
    assert holonomy_shell_signature(
        -0.25,
        [2.0, -4.0],
    ) == pytest.approx((-0.5, 1.0))


def test_thomas_fermi_and_bogoliubov_control_signatures():
    q_cs2 = thomas_fermi_sound_speed_signature(
        2.0,
        source_to_mu_c=[1.0, 0.0],
        source_to_u_ext=[0.0, 2.0],
        source_to_u_i=[3.0, -1.0],
    )
    assert q_cs2 == pytest.approx((-1.0, -0.5))

    q_bog = bogoliubov_dispersion_signature(3.0, q_cs2)
    assert q_bog == pytest.approx((-9.0, -4.5))


def test_model_consistency_channel_cannot_be_promoted_to_source_fisher_row():
    instance = CatalogMeasurementInstance(
        instance_id="test-instance",
        channel_id="CENTRAL_CONSISTENCY_RESIDUAL",
        source_names=("source_a", "source_b"),
        source_signature=(1.0, 0.0),
        variance=1.0,
        provenance=PROV,
        response_model_id="derived-orbit-control",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:test",
    )
    with pytest.raises(
        MeasurementChannelCatalogError,
        match="MODEL_CONSISTENCY",
    ):
        instance.validate()


def test_derived_phase_channel_requires_explicit_independent_readout_evidence():
    instance = CatalogMeasurementInstance(
        instance_id="test-instance",
        channel_id="TRANSVERSE_PHASE_CURVATURE",
        source_names=("source_a", "source_b"),
        source_signature=(1.0, -1.0),
        variance=1.0,
        provenance=PROV,
        response_model_id="qhtri-independent-phase-camera-v0",
        independence_declared=True,
        independence_evidence="same orbital data only",
    )
    with pytest.raises(
        MeasurementChannelCatalogError,
        match="INDEPENDENT_READOUT",
    ):
        instance.validate()


def test_independent_phase_readout_can_be_converted_to_measurement_design_input():
    instance = CatalogMeasurementInstance(
        instance_id="test-instance",
        channel_id="TRANSVERSE_PHASE_CURVATURE",
        source_names=("source_a", "source_b"),
        source_signature=(1.0, -1.0),
        variance=0.25,
        provenance=PROV,
        response_model_id="qhtri-independent-phase-camera-v0",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:separate phase-imaging detector",
    )
    measurement = instance.to_independent_measurement()
    assert measurement.signature.name == "test-instance"
    assert measurement.signature.source_signature == pytest.approx((1.0, -1.0))
    assert measurement.variance == pytest.approx(0.25)


def test_spectral_channel_can_break_orbital_source_degeneracy():
    # Existing orbital channel sees only source_a + source_b.
    current = [
        _source("source_a", [1.0]),
        _source("source_b", [1.0]),
    ]

    # A declared spectral line response sees the difference.
    spectral_instance = CatalogMeasurementInstance(
        channel_id="SPECTRAL_LINE_FREQUENCY",
        source_names=("source_a", "source_b"),
        source_signature=(1.0, -1.0),
        variance=1.0,
        provenance=PROV,
        response_model_id="oes-line-phase-chain-rule",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:spectrometer",
    )

    ranked = rank_independent_measurements(
        current,
        [[1.0]],
        [spectral_instance.to_independent_measurement()],
        policy="RANK_THEN_NULLSPACE",
    )

    assert ranked[0][0] == "test-instance"
    assert ranked[0][1].rank_before == 1
    assert ranked[0][1].rank_after == 2
    assert ranked[0][1].rank_gain == 1


def test_reconstructed_phase_curvature_from_same_orbit_is_not_counted_by_default():
    definition = channel_definition("TRANSVERSE_PHASE_CURVATURE")
    assert definition.independence_default is False

    instance = CatalogMeasurementInstance(
        instance_id="test-instance",
        channel_id="TRANSVERSE_PHASE_CURVATURE",
        source_names=("source_a", "source_b"),
        source_signature=(1.0, -1.0),
        variance=1.0,
        provenance=PROV,
        response_model_id="derived-from-same-omega-kappa",
        independence_declared=False,
        independence_evidence="",
    )
    instance.validate()
    with pytest.raises(
        MeasurementChannelCatalogError,
        match="joint covariance block",
    ):
        instance.to_independent_measurement()


def test_bogoliubov_control_can_count_only_after_explicit_source_map_and_independence():
    definition = channel_definition("BOGOLIUBOV_SOUND_SPEED_SQ")
    assert definition.role == NUISANCE_CONTROL

    q = thomas_fermi_sound_speed_signature(
        1.0,
        source_to_mu_c=[0.0, 0.0],
        source_to_u_ext=[0.0, 0.0],
        source_to_u_i=[1.0, -1.0],
    )
    instance = CatalogMeasurementInstance(
        instance_id="test-instance",
        channel_id="BOGOLIUBOV_SOUND_SPEED_SQ",
        source_names=("source_a", "source_b"),
        source_signature=q,
        variance=0.1,
        provenance=PROV,
        response_model_id="02JP-TF-explicit-source-to-Ui",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:Bogoliubov-spectroscopy",
    )
    assert instance.to_independent_measurement().variance == pytest.approx(0.1)



def test_catalog_ranking_binds_exact_source_basis_order():
    current = [
        _source("source_a", [1.0]),
        _source("source_b", [1.0]),
    ]
    candidate = CatalogMeasurementInstance(
        instance_id="spectral-line-17",
        channel_id="SPECTRAL_LINE_FREQUENCY",
        source_names=("source_a", "source_b"),
        source_signature=(1.0, -1.0),
        variance=1.0,
        provenance=PROV,
        response_model_id="oes-line-phase-chain-rule",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:spectrometer",
    )
    ranked = rank_catalog_measurements(
        current,
        [[1.0]],
        [candidate],
        policy="RANK_THEN_NULLSPACE",
    )
    assert ranked[0][0] == "spectral-line-17"
    assert ranked[0][1] == "SPECTRAL_LINE_FREQUENCY"
    assert ranked[0][2].rank_gain == 1

    wrong_order = CatalogMeasurementInstance(
        instance_id="spectral-line-wrong-order",
        channel_id="SPECTRAL_LINE_FREQUENCY",
        source_names=("source_b", "source_a"),
        source_signature=(-1.0, 1.0),
        variance=1.0,
        provenance=PROV,
        response_model_id="oes-line-phase-chain-rule",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:spectrometer",
    )
    with pytest.raises(
        MeasurementChannelCatalogError,
        match="source basis/order",
    ):
        rank_catalog_measurements(
            current,
            [[1.0]],
            [wrong_order],
            policy="RANK_THEN_NULLSPACE",
        )


def test_multiple_instances_of_same_channel_type_remain_distinct():
    current = [
        _source("source_a", [1.0, 0.0]),
        _source("source_b", [0.0, 1.0]),
    ]
    candidates = [
        CatalogMeasurementInstance(
            instance_id="line-501nm",
            channel_id="SPECTRAL_LINE_FREQUENCY",
            source_names=("source_a", "source_b"),
            source_signature=(1.0, 1.0),
            variance=1.0,
            provenance=PROV,
            response_model_id="line-501",
            independence_declared=True,
            independence_evidence="INDEPENDENT_READOUT:spectrometer",
        ),
        CatalogMeasurementInstance(
            instance_id="line-612nm",
            channel_id="SPECTRAL_LINE_FREQUENCY",
            source_names=("source_a", "source_b"),
            source_signature=(1.0, -1.0),
            variance=1.0,
            provenance=PROV,
            response_model_id="line-612",
            independence_declared=True,
            independence_evidence="INDEPENDENT_READOUT:spectrometer",
        ),
    ]
    ranked = rank_catalog_measurements(
        current,
        np.eye(2),
        candidates,
        policy="D_OPTIMAL",
    )
    assert {row[0] for row in ranked} == {"line-501nm", "line-612nm"}
    assert all(row[1] == "SPECTRAL_LINE_FREQUENCY" for row in ranked)

def test_catalog_instance_mapping_preserves_source_neutrality():
    instance = CatalogMeasurementInstance(
        instance_id="test-instance",
        channel_id="SPECTRAL_INTENSITY",
        source_names=("source_a", "source_b"),
        source_signature=(0.5, 2.0),
        variance=2.0,
        provenance=PROV,
        response_model_id="declared-intensity-phase-jacobian-v0",
        independence_declared=True,
        independence_evidence="INDEPENDENT_READOUT:spectrometer-intensity",
    )
    mapped = instance.as_mapping()
    assert mapped["schema"] == "GREMLIN_RELATIONAL_MEASUREMENT_CHANNEL_CATALOG_V0_1"
    assert mapped["physical_source_selected"] is False
    assert mapped["catalog_definition"]["role"] == SOURCE_SENSITIVE_CONDITIONAL


@pytest.mark.parametrize(
    "call",
    [
        lambda: channel_definition("NOT_A_CHANNEL"),
        lambda: radial_scalar_signature_rows(
            0.0,
            0.0,
            [1.0],
            [1.0],
        ),
        lambda: radial_scalar_signature_rows(
            1.0,
            2.0,
            [1.0],
            [1.0],
        ),
        lambda: radial_scalar_signature_rows(
            1.0,
            0.0,
            [1.0, 2.0],
            [1.0],
        ),
        lambda: spectral_chain_rule_signature(
            [1.0, 2.0],
            [[1.0, 0.0]],
        ),
        lambda: thomas_fermi_sound_speed_signature(
            0.0,
            [1.0],
            [0.0],
            [0.0],
        ),
        lambda: CatalogMeasurementInstance(
            instance_id="duplicate-source-instance",
            channel_id="ORBITAL_OMEGA_SQ",
            source_names=("source_a", "source_a"),
            source_signature=(1.0, 2.0),
            variance=1.0,
            provenance=PROV,
            response_model_id="x",
            independence_declared=True,
            independence_evidence="INDEPENDENT_READOUT:x",
        ).validate(),
    ],
)
def test_fail_closed_domains(call):
    with pytest.raises(MeasurementChannelCatalogError):
        call()
