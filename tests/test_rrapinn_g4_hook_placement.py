from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_true_residual_export_is_before_history_refresh():
    text = (ROOT / "source" / "model_train.py").read_text(encoding="utf-8")
    hook = text.index("if _mech_diag_enabled and j in _mech_diag_steps:")
    optimizer_done = text.rindex("end = time.time()", 0, hook)
    history_refresh = text.index("hist_alpha_prev_for_driver =", hook)
    assert optimizer_done < hook < history_refresh


def test_boundary_receipt_is_separate_from_energy_fallback_trigger():
    text = (ROOT / "source" / "model_train.py").read_text(encoding="utf-8")
    observation = text.index("_boundary_observation = observe_boundary(")
    combined_trigger = text.index("if not _frac_detected and (_bdy_triggered or _E_triggered):")
    assert observation < combined_trigger
    observation_block_end = text.index("# 预警", observation)
    block = text[observation:observation_block_end]
    assert "_E_triggered" not in block
