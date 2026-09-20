import math
from types import SimpleNamespace

import numpy as np
import pytest

from tools.gremlin_cognitive_action_principle_v01 import (
    CognitiveActionError,
    energy_balance_rate,
    euler_lagrange_residual,
    holonomic_tangent_residual,
    hybrid_action,
    inertial_phase_residual,
    overdamped_phase_velocity,
    permission_projector,
    permission_tangent_residual,
    phase_force,
    phase_potential,
    project_velocity,
    quadratic_action_model,
    quadratic_energy,
    quadratic_lagrangian,
    rayleigh_dissipation,
    trapezoidal_action,
    v012_collective_to_action,
)


def _model(damping=None):
    m = np.diag([2.0, 3.0, 4.0])
    g = np.array([
        [0.0, 0.5, 0.0],
        [-0.5, 0.0, 0.2],
        [0.0, -0.2, 0.0],
    ])
    k = np.array([
        [4.0, 1.0, 0.0],
        [1.0, 5.0, 0.3],
        [0.0, 0.3, 6.0],
    ])
    return quadratic_action_model(m, g, k, damping)


def test_local_euler_lagrange_reproduces_mgk_equation():
    model = _model()
    q = np.array([0.2, -0.1, 0.3])
    v = np.array([0.4, 0.5, -0.2])
    a = -np.linalg.solve(
        model.metric,
        model.connection_curvature @ v + model.stiffness @ q,
    )
    residual = euler_lagrange_residual(model, q, v, a)
    assert residual == pytest.approx(np.zeros(3), abs=1e-12)


def test_connection_changes_lagrangian_but_not_energy():
    model = _model()
    zero_g = quadratic_action_model(
        model.metric,
        np.zeros((3, 3)),
        model.stiffness,
    )
    q = np.array([0.3, 0.1, -0.4])
    v = np.array([-0.2, 0.7, 0.5])
    assert quadratic_lagrangian(model, q, v) != pytest.approx(
        quadratic_lagrangian(zero_g, q, v)
    )
    assert quadratic_energy(model, q, v) == pytest.approx(
        quadratic_energy(zero_g, q, v)
    )


def test_rayleigh_dissipation_and_energy_balance_are_nonpositive_without_drive():
    d = np.diag([1.0, 2.0, 0.5])
    model = _model(d)
    v = np.array([0.2, -0.3, 0.4])
    r = rayleigh_dissipation(model, v)
    rate = energy_balance_rate(model, v)
    assert r > 0.0
    assert rate == pytest.approx(-2.0 * r)
    assert rate < 0.0


def test_external_drive_enters_energy_balance_as_power():
    model = _model(np.diag([1.0, 0.0, 0.0]))
    v = np.array([2.0, 0.0, 0.0])
    qext = np.array([3.0, 0.0, 0.0])
    assert energy_balance_rate(model, v, external_force=qext) == pytest.approx(2.0)


def test_linear_potential_force_and_holonomic_multiplier_sign():
    model = quadratic_action_model(
        np.eye(2),
        np.zeros((2, 2)),
        np.zeros((2, 2)),
    )
    q = np.zeros(2)
    v = np.zeros(2)
    f = np.array([1.5, -0.5])
    a = f.copy()
    assert euler_lagrange_residual(
        model, q, v, a, potential_force=f
    ) == pytest.approx(np.zeros(2))

    j = np.array([[1.0, 0.0]])
    lam = np.array([2.0])
    a = np.array([2.0, 0.0])
    assert euler_lagrange_residual(
        model,
        q,
        v,
        a,
        constraint_jacobian=j,
        multipliers=lam,
    ) == pytest.approx(np.zeros(2))


def test_permission_projector_enforces_tangent_subspace():
    p = permission_projector(np.diag([1.0, 0.0, 1.0]))
    v = np.array([2.0, 5.0, -3.0])
    assert project_velocity(p, v) == pytest.approx([2.0, 0.0, -3.0])
    assert permission_tangent_residual(p, v) == pytest.approx([0.0, 5.0, 0.0])


def test_invalid_permission_projector_fails_closed():
    with pytest.raises(CognitiveActionError):
        permission_projector([[1.0, 0.2], [0.2, 0.0]])


def test_holonomic_tangent_residual():
    j = np.array([[1.0, -1.0, 0.0]])
    assert holonomic_tangent_residual(j, [0.5, 0.5, 9.0]) == pytest.approx([0.0])
    assert holonomic_tangent_residual(j, [0.5, -0.5, 9.0]) == pytest.approx([1.0])


def test_phase_force_is_negative_gradient_of_phase_potential():
    theta = np.array([0.2, -0.5, 1.0])
    couplings = np.array([
        [0.0, 1.0, 0.3],
        [1.0, 0.0, 0.7],
        [0.3, 0.7, 0.0],
    ])
    force = phase_force(theta, couplings)
    eps = 1e-6
    grad = []
    for i in range(theta.size):
        e = np.zeros(theta.size)
        e[i] = eps
        grad.append(
            (phase_potential(theta + e, couplings) - phase_potential(theta - e, couplings))
            / (2.0 * eps)
        )
    assert force == pytest.approx(-np.asarray(grad), abs=2e-9)


def test_inertial_phase_residual_and_overdamped_limit():
    theta = np.array([0.1, -0.2, 0.7])
    couplings = np.array([
        [0.0, 0.8, 0.2],
        [0.8, 0.0, 0.4],
        [0.2, 0.4, 0.0],
    ])
    inertia = np.array([2.0, 3.0, 4.0])
    damping = np.array([1.0, 1.5, 2.0])
    drive = np.array([0.3, -0.1, 0.2])

    omega = overdamped_phase_velocity(
        theta,
        damping=damping,
        couplings=couplings,
        drive=drive,
    )
    assert inertial_phase_residual(
        theta,
        omega,
        np.zeros(3),
        inertia=inertia,
        damping=damping,
        couplings=couplings,
        drive=drive,
    ) == pytest.approx(np.zeros(3), abs=1e-12)


def test_trapezoidal_continuous_action_plus_declared_jump_terms():
    continuous = trapezoidal_action(
        [0.0, 1.0, 2.0],
        [0.0, 2.0, 0.0],
    )
    assert continuous == pytest.approx(2.0)
    assert hybrid_action(continuous, [0.5, -0.25]) == pytest.approx(2.25)


def test_v012_collective_matrices_map_exactly_to_local_action():
    mats = SimpleNamespace(
        mass=np.diag([2.0, 3.0, 4.0]),
        gyroscopic=np.array([
            [0.0, 0.2, 0.0],
            [-0.2, 0.0, 0.1],
            [0.0, -0.1, 0.0],
        ]),
        stiffness=np.diag([8.0, 27.0, 64.0]),
    )
    model = v012_collective_to_action(mats)
    assert model.metric == pytest.approx(mats.mass)
    assert model.connection_curvature == pytest.approx(mats.gyroscopic)
    assert model.stiffness == pytest.approx(mats.stiffness)


@pytest.mark.parametrize(
    "builder",
    [
        lambda: quadratic_action_model(np.diag([1.0, 0.0]), np.zeros((2, 2)), np.eye(2)),
        lambda: quadratic_action_model(np.eye(2), np.array([[0.0, 1.0], [0.0, 0.0]]), np.eye(2)),
        lambda: quadratic_action_model(np.eye(2), np.zeros((2, 2)), np.array([[1.0, 2.0], [0.0, 1.0]])),
        lambda: quadratic_action_model(np.eye(2), np.zeros((2, 2)), np.eye(2), np.diag([1.0, -1.0])),
    ],
)
def test_invalid_quadratic_structures_fail_closed(builder):
    with pytest.raises(CognitiveActionError):
        builder()
