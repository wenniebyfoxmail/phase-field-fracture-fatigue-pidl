import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fatigue_history import compute_fatigue_degrad, update_fatigue_history


def test_q4_gp_history_keeps_shape_and_accumulates_only_positive_increments():
    cfg = {
        "loading_type": "cyclic",
        "accum_type": "carrara",
        "degrad_type": "asymptotic",
        "alpha_T": 0.5,
    }
    alpha_bar = torch.zeros((2, 4), dtype=torch.float64)
    previous = torch.zeros_like(alpha_bar)
    peak_1 = torch.tensor(
        [[0.2, 0.4, 0.6, 0.8], [0.1, 0.3, 0.5, 0.7]], dtype=torch.float64
    )
    state_1 = update_fatigue_history(alpha_bar, peak_1, previous, cfg)
    assert state_1.shape == (2, 4)
    torch.testing.assert_close(state_1, peak_1)

    unloaded = torch.zeros_like(peak_1)
    state_unloaded = update_fatigue_history(state_1, unloaded, peak_1, cfg)
    torch.testing.assert_close(state_unloaded, state_1)

    peak_2 = peak_1 + torch.tensor(
        [[0.05, 0.0, 0.10, -0.20], [0.0, 0.20, -0.10, 0.30]], dtype=torch.float64
    )
    state_2 = update_fatigue_history(state_unloaded, peak_2, unloaded, cfg)
    torch.testing.assert_close(state_2, state_1 + peak_2)

    f = compute_fatigue_degrad(state_2, cfg)
    assert f.shape == (2, 4)
    assert torch.all((f > 0.0) & (f <= 1.0))


def test_q4_gp_history_round_trip_preserves_all_four_gauss_points(tmp_path):
    state = torch.arange(12, dtype=torch.float32).reshape(3, 4) / 10.0
    checkpoint = tmp_path / "gp_state.pt"
    torch.save({"hist_fat": state, "psi_plus_prev": state + 1.0}, checkpoint)
    restored = torch.load(checkpoint, weights_only=True)
    torch.testing.assert_close(restored["hist_fat"], state)
    torch.testing.assert_close(restored["psi_plus_prev"], state + 1.0)
