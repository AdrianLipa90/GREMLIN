from __future__ import annotations

import copy
import math
import pytest

from tools.gremlin_complex_overlap_frame_bridge_v23 import (
    ComplexOverlapFrameBridgeError,
    build_complex_overlap_frame_bridge_v23,
    phase_loss_witness_v23,
    validate_complex_overlap_frame_bridge_v23,
    validate_orthonormal_frame_v23,
)

FRAME = [[1+0j,0j,0j],[0j,1+0j,0j],[0j,0j,1+0j]]
a = 0.58
b = math.sqrt(1-a*a)
PMNS = [[a,b,0j],[-b,a,0j],[0j,0j,1+0j]]
BASE = dict(
    audit_id='overlap-v23',
    frame=FRAME,
    intention=[0.5+0.1j,0.4-0.2j,math.sqrt(0.5)+0j],
    pmns=PMNS,
    symbolic_hilbert_source_ref='Theory_of_Everything:Hsymbolic orthonormal basis',
    resonance_source_ref='Theory_of_Everything:R=|<S|I>|^2',
    neutrino_fixed_point_source_ref='Reality_as_Graded_Projection:nu_e nu_mu nu_tau fixed-point species',
    pmns_source_ref='GREMLIN:v1.5 PMNS orientation',
)


def test_overlap_frame_preserves_norm_on_span_and_pmns_preserves_norm():
    r = build_complex_overlap_frame_bridge_v23(**BASE)
    assert float.fromhex(r['frame_span_norm_residual_f64_hex']) < 2e-12
    assert float.fromhex(r['pmns_norm_residual_f64_hex']) < 2e-12


def test_probability_shadow_loses_relative_phase_needed_by_mass_amplitudes():
    w = phase_loss_witness_v23(pmns=PMNS, phase_rad=0.73)
    assert w['same_probability_shadow'] is True
    assert w['mass_amplitude_delta'] > 0.1


def test_conditional_construction_removes_arbitrary_u3_but_keeps_embedding_open():
    r = build_complex_overlap_frame_bridge_v23(**BASE)
    assert r['conditional_J_matrix_freedom'].startswith('NONE_ON_BOUND')
    assert r['physical_J_identified'] is False
    assert len(r['remaining_bridge_debt']) == 2


def test_source_bound_status_closes_conditional_embedding_flag_only():
    p = dict(BASE)
    p['embedding_source_status'] = 'SOURCE_BOUND_ORTHONORMAL_NEUTRINO_TRIPLE'
    r = build_complex_overlap_frame_bridge_v23(**p)
    assert r['physical_J_identified'] is True
    assert r['remaining_bridge_debt'] == []


def test_nonorthonormal_frame_fails_closed():
    with pytest.raises(ComplexOverlapFrameBridgeError):
        validate_orthonormal_frame_v23([[1,0,0],[1,0,0],[0,0,1]])


def test_tamper_fails():
    r = build_complex_overlap_frame_bridge_v23(**BASE)
    assert validate_complex_overlap_frame_bridge_v23(r)
    t = copy.deepcopy(r)
    t['physical_J_identified'] = True
    with pytest.raises(ComplexOverlapFrameBridgeError):
        validate_complex_overlap_frame_bridge_v23(t)
