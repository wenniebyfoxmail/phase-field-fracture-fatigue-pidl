from __future__ import annotations

import numpy as np
import pytest

from scripts.validate_rrapinn_g4_a_replay import _equal, validate_reference_history


def test_decoded_comparison_is_exact_and_nan_policy_is_explicit():
    import torch

    assert _equal({"x": torch.tensor([1.0])}, {"x": torch.tensor([1.0])})
    assert not _equal({"x": torch.tensor([1.0])}, {"x": torch.tensor([1.0 + 1e-7])})
    left = np.asarray([1.0, np.nan])
    right = np.asarray([1.0, np.nan])
    assert np.array_equal(left, right, equal_nan=True)


def test_scalar_checkpoint_metadata_is_exact():
    assert _equal({"detected": False, "cycle": None}, {"detected": False, "cycle": None})
    assert not _equal({"detected": False}, {"detected": True})


def test_reference_history_hash_is_not_self_signed(tmp_path):
    path = tmp_path / "history.npy"
    np.save(path, np.arange(4, dtype=np.float64), allow_pickle=False)
    with pytest.raises(RuntimeError, match="hash mismatch"):
        validate_reference_history(path, ("0" * 64, (4,), "float64"))
