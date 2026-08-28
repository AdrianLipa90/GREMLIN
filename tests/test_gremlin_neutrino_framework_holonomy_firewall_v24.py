from __future__ import annotations

import copy
import math
import pytest

from tools.gremlin_neutrino_framework_holonomy_firewall_v24 import (
    NeutrinoFrameworkHolonomyFirewallError,
    build_neutrino_framework_holonomy_firewall_v24,
    graded_projection_masses_v24,
    tetrahedron_ratio_masses_from_dm21_v24,
    validate_neutrino_framework_holonomy_firewall_v24,
)

BASE = dict(
    audit_id='nu-framework-v24',
    delta_m21_sq_eV2=7.42e-5,
    delta_m31_sq_eV2=2.517e-3,
    graded_ratio_squared=7.0/6.0,
    tetrahedron_ratios=(1.0,2.0,10.0),
    tetrahedron_displayed_masses_eV=(0.00501,0.01002,0.0501),
    graded_source_ref='Reality_as_Graded_Projection:m2/m1=sqrt(7/6)',
    tetrahedron_source_ref='Metatime_Monograph_v11:tetrahedron r=[1,2,10]',
)


def test_hard_ratio_conflict_is_detected():
    r = build_neutrino_framework_holonomy_firewall_v24(**BASE)
    conflict = r['ratio_conflict']
    assert conflict['mutually_exactly_compatible'] is False
    assert conflict['graded_m2_over_m1'] == pytest.approx(math.sqrt(7.0/6.0))
    assert conflict['tetrahedron_m2_over_m1'] == pytest.approx(2.0)
    assert r['absolute_scale_shared_canon_status'] == 'BLOCKED_CROSS_FRAMEWORK_CONFLICT'


def test_v22_mass_sum_and_tetrahedron_mass_sum_remain_distinct_branch_results():
    r = build_neutrino_framework_holonomy_firewall_v24(**BASE)
    sg = float.fromhex(r['graded_projection_branch']['mass_sum_eV_f64_hex'])
    st = float.fromhex(r['tir_tetrahedron_branch']['dm21_normalized_mass_sum_eV_f64_hex'])
    sd = float.fromhex(r['tir_tetrahedron_branch']['source_displayed_mass_sum_eV_f64_hex'])
    assert sg == pytest.approx(0.0983162085480, rel=1e-10)
    assert st == pytest.approx(0.0646524039254, rel=1e-10)
    assert sd == pytest.approx(0.06513, rel=1e-12)


def test_tetrahedron_ratio_predicts_dm31_equals_33_dm21():
    masses = tetrahedron_ratio_masses_from_dm21_v24(delta_m21_sq_eV2=7.42e-5, ratios=(1,2,10))
    dm31 = masses[2]**2 - masses[0]**2
    assert dm31 == pytest.approx(33.0*7.42e-5, rel=1e-14)
    assert dm31 == pytest.approx(2.4486e-3, rel=1e-14)


def test_graded_projection_branch_reproduces_v22_values():
    masses = graded_projection_masses_v24(delta_m21_sq_eV2=7.42e-5, delta_m31_sq_eV2=2.517e-3, ratio_squared=7.0/6.0)
    assert masses[0] == pytest.approx(0.0210997630318, rel=1e-10)
    assert masses[1] == pytest.approx(0.0227903488345, rel=1e-10)
    assert masses[2] == pytest.approx(0.0544260966816, rel=1e-10)


def test_receipt_tamper_fails_and_no_silent_promotion():
    r = build_neutrino_framework_holonomy_firewall_v24(**BASE)
    assert validate_neutrino_framework_holonomy_firewall_v24(r)
    t = copy.deepcopy(r)
    t['absolute_scale_shared_canon_status'] = 'PROMOTED'
    with pytest.raises(NeutrinoFrameworkHolonomyFirewallError):
        validate_neutrino_framework_holonomy_firewall_v24(t)
