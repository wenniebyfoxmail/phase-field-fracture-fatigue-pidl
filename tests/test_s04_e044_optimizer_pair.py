from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "tools" / "s04_e011_analysis" / "run_c20_optimizer_pair.py"


def test_runner_declares_strict_budget_and_frozen_history_contract():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "objective_plus_backward" in source
    assert "frozen_history" in source
    assert "line_search_fn=\"strong_wolfe\"" in source
    assert "calls >= max_evaluations" in source


def test_runner_uses_same_saved_start_for_both_arms():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "start_parameters = clone_parameters(field.net)" in source
    assert "restore_parameters(field.net, start_parameters)" in source
    assert "trained_1NN" not in source
