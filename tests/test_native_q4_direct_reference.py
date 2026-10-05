import numpy as np
import pytest

from run_native_q4_direct_reference import (
    FROZEN,
    fatigue_degradation,
    rebuild_trial_history,
    relative_inf,
    runtime_mesh_signature,
)


def test_trial_history_is_rebuilt_from_immutable_accepted_state():
    accepted = np.array([[0.4, 0.6]])
    driver = np.array([[0.3, 0.5]])
    active_a = np.array([[0.7, 0.4]])
    active_b = np.array([[0.5, 0.9]])
    trial_a, _ = rebuild_trial_history(accepted, driver, active_a)
    trial_b, _ = rebuild_trial_history(accepted, driver, active_b)
    assert np.allclose(trial_a, [[0.8, 0.6]])
    assert np.allclose(trial_b, [[0.6, 1.0]])
    # Rebuilding B after A must not accumulate A's increment.
    assert not np.allclose(trial_b, trial_a + np.maximum(active_b - driver, 0.0))


def test_carrara_asymptotic_degradation_contract():
    history = np.array([0.0, 0.5, 1.5])
    assert np.allclose(fatigue_degradation(history), [1.0, 1.0, 0.25])
    with pytest.raises(ValueError, match="non-negative"):
        fatigue_degradation(np.array([-1.0]))


def test_true_path_and_primary_gate_are_frozen():
    assert FROZEN["displacements"] == [0.08999988, 0.11999988]
    assert FROZEN["equation_closure_tolerance"] == 1.0e-3
    assert FROZEN["required_consecutive"] == 2


def test_relative_inf_uses_declared_scale_without_zero_division():
    assert relative_inf(np.array([2.0]), np.array([1.0]), 4.0) == pytest.approx(0.25)
    assert relative_inf(np.zeros(2), np.zeros(2), 0.0) == 0.0


def test_runtime_mesh_signature_matches_checkpoint_hash_recipe():
    import hashlib
    import torch
    inp = torch.tensor([[0.0, 1.0], [2.0, 3.0]], dtype=torch.float32)
    conn = torch.tensor([[0, 1, 1, 0]], dtype=torch.int64)
    expected = hashlib.sha256()
    for tensor in (inp, conn):
        array = tensor.numpy()
        expected.update(str(array.dtype).encode("ascii"))
        expected.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        expected.update(array.tobytes())
    assert runtime_mesh_signature(inp, conn) == expected.hexdigest()
