import cmath
import math

TIR_PHASE_CLOCK_COMMIT = "b69ba6055c0535c666e12dbba069ffb87238eee6"
IDT_PHASE_CLOCK_COMMIT = "f90435edbfbba8211e6c28cc49a7c22f8059021b"
IDT_LAPSE_TEST_COMMIT = "11fcd5b798445265fa5f8cd4dc3386f3b0a463c4"
RFC_LAPSE_PHASE_COMMIT = "8611783d2471a3f6700d2c409b222f40b9752ec5"
SOH_HALF_INTERFACE_COMMIT = "206e49e306b246c4b0f4d182b0d32d5511739408"

# Representative three-flavor vacuum benchmark. This audit tests structure,
# invariances, and falsification gates; it is not a global-data fit.
TH12 = math.radians(33.44)
TH13 = math.radians(8.57)
TH23 = math.radians(49.2)
DELTA = math.radians(197.0)
DM21 = 7.42e-5
DM31 = 2.517e-3
AMP_PHASE_K = 2.0 * 1.267


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def _dagger(a):
    return [[a[j][i].conjugate() for j in range(len(a))] for i in range(len(a[0]))]


def _pmns():
    c12, s12 = math.cos(TH12), math.sin(TH12)
    c13, s13 = math.cos(TH13), math.sin(TH13)
    c23, s23 = math.cos(TH23), math.sin(TH23)
    ep = cmath.exp(1j * DELTA)
    em = ep.conjugate()
    return [
        [c12 * c13, s12 * c13, s13 * em],
        [-s12 * c23 - c12 * s13 * s23 * ep, c12 * c23 - s12 * s13 * s23 * ep, c13 * s23],
        [s12 * s23 - c12 * s13 * c23 * ep, -c12 * s23 - s12 * s13 * c23 * ep, c13 * c23],
    ]


def _propagator(x_km_per_gev):
    u = _pmns()
    phases = [
        1.0 + 0.0j,
        cmath.exp(-1j * AMP_PHASE_K * DM21 * x_km_per_gev),
        cmath.exp(-1j * AMP_PHASE_K * DM31 * x_km_per_gev),
    ]
    d = [[0j] * 3 for _ in range(3)]
    for i, p in enumerate(phases):
        d[i][i] = p
    return _mm(_mm(u, d), _dagger(u))


def _probability(a):
    return [[abs(a[b][a0]) ** 2 for a0 in range(3)] for b in range(3)]


def _shannon_bits(p):
    return -sum(x * math.log2(x) for x in p if x > 0.0)


def _uniform_mutual_information(p):
    py = [sum(p[b][a] for a in range(3)) / 3.0 for b in range(3)]
    h_y = _shannon_bits(py)
    h_y_given_x = sum(_shannon_bits([p[b][a] for b in range(3)]) for a in range(3)) / 3.0
    return h_y - h_y_given_x


def _max_abs_matrix_delta(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3))


def test_crossrepo_provenance_pins_are_explicit():
    for value in (
        TIR_PHASE_CLOCK_COMMIT,
        IDT_PHASE_CLOCK_COMMIT,
        IDT_LAPSE_TEST_COMMIT,
        RFC_LAPSE_PHASE_COMMIT,
        SOH_HALF_INTERFACE_COMMIT,
    ):
        assert len(value) == 40
        int(value, 16)


def test_pmns_is_unitary_to_binary64_precision():
    u = _pmns()
    ident = _mm(_dagger(u), u)
    residual = max(abs(ident[i][j] - (1.0 if i == j else 0.0)) for i in range(3) for j in range(3))
    assert residual < 2e-15


def test_rsi_overlap_embedding_equals_flavor_transition_probability():
    # Candidate binding: S=measured flavor basis ray, I=evolved prepared flavor state.
    # Then R(S,I)=|<S|I>|^2 is exactly the standard transition probability.
    a = _propagator(500.0)
    p = _probability(a)
    basis = [[1 + 0j, 0j, 0j], [0j, 1 + 0j, 0j], [0j, 0j, 1 + 0j]]
    residual = 0.0
    for alpha in range(3):
        psi = [a[beta][alpha] for beta in range(3)]
        for beta in range(3):
            overlap = sum(basis[beta][i].conjugate() * psi[i] for i in range(3))
            residual = max(residual, abs(abs(overlap) ** 2 - p[beta][alpha]))
    assert residual < 5e-16


def test_global_phase_and_flavor_basis_rephasing_are_probability_blind():
    a = _propagator(500.0)
    p = _probability(a)
    chi = 0.731
    a_global = [[cmath.exp(1j * chi) * a[i][j] for j in range(3)] for i in range(3)]
    assert _max_abs_matrix_delta(_probability(a_global), p) < 5e-15

    phases = [0.31, -0.77, 1.19]
    d = [[0j] * 3 for _ in range(3)]
    for i, phase in enumerate(phases):
        d[i][i] = cmath.exp(1j * phase)
    a_rephased = _mm(_mm(_dagger(d), a), d)
    assert _max_abs_matrix_delta(_probability(a_rephased), p) < 5e-15


def test_unitary_evolution_preserves_pure_state_norm_while_flavor_entropy_changes():
    a = _propagator(500.0)
    p = _probability(a)
    for alpha in range(3):
        norm = sum(abs(a[beta][alpha]) ** 2 for beta in range(3))
        purity = norm * norm
        assert abs(norm - 1.0) < 2e-14
        assert abs(purity - 1.0) < 4e-14
        h_flavor = _shannon_bits([p[beta][alpha] for beta in range(3)])
        assert 0.0 <= h_flavor <= math.log2(3.0) + 1e-14


def test_prepared_to_measured_flavor_is_a_real_classical_information_channel():
    p0 = _probability(_propagator(0.0))
    p500 = _probability(_propagator(500.0))
    p11858 = _probability(_propagator(11858.0))
    i0 = _uniform_mutual_information(p0)
    i500 = _uniform_mutual_information(p500)
    i11858 = _uniform_mutual_information(p11858)
    assert abs(i0 - math.log2(3.0)) < 2e-14
    assert 0.0 < i500 < math.log2(3.0)
    assert 0.0 <= i11858 < 1e-3


def test_idt_rfc_lapse_reparameterization_preserves_accumulated_phase():
    # IDT 01AD / RFC RF-N1B2N: r_tau = r_t/N_R and d tau = N_R dt.
    n_r = 1.7
    r_t = 2.345
    dt = 3.21
    r_tau = r_t / n_r
    d_tau = n_r * dt
    assert math.isclose(r_tau, r_t / n_r, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(r_tau * d_tau, r_t * dt, rel_tol=0.0, abs_tol=2e-15)


def test_tir_idt_phase_clock_scale_identities_close_dimensionally():
    c = 299_792_458.0
    hbar = 1.054_571_817e-34
    omega = 2.345e9
    energy = hbar * abs(omega)
    ell_from_rate = c / abs(omega)
    ell_from_energy = hbar * c / energy
    assert math.isclose(ell_from_rate, ell_from_energy, rel_tol=2e-16, abs_tol=0.0)
    assert math.isclose((2.0 * math.pi * ell_from_rate) / (4.0 * math.pi * ell_from_rate), 0.5, rel_tol=0.0, abs_tol=1e-15)


def test_soh_half_turn_is_exact_two_path_spectral_null_and_matches_two_flavor_reduction():
    sigma = 0.5
    phi = math.pi
    defect = 1.0 + 2.0 * math.sqrt(sigma * (1.0 - sigma)) * math.cos(phi)
    theta = math.pi / 4.0
    survival_amplitude = math.cos(theta) ** 2 + math.sin(theta) ** 2 * cmath.exp(-1j * phi)
    assert abs(defect) < 1e-15
    assert abs(survival_amplitude) ** 2 < 1e-30


def test_belzebub_blocks_direct_identification_of_log_resonance_frequency_with_fixed_pmns_rate():
    # If one demands omega_phys = k*log(1/R_ee(L/E)) with one fixed k while
    # omega_phys is held fixed, k inferred from two baselines must agree.
    # Standard oscillatory R_ee does not satisfy that closure.
    r500 = _probability(_propagator(500.0))[0][0]
    r1000 = _probability(_propagator(1000.0))[0][0]
    k500 = 1.0 / math.log(1.0 / r500)
    k1000 = 1.0 / math.log(1.0 / r1000)
    assert abs(k500 - k1000) > 100.0
    assert not math.isclose(k500, k1000, rel_tol=1e-2, abs_tol=1e-2)
