import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DT2 = ROOT / "analysis" / "toy_road_dt2_diagnostic_20260817"


def _load_analyzer():
    path = DT2 / "analyze_dt2_c5_iterates.py"
    spec = importlib.util.spec_from_file_location("dt2_analyzer", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dt2_observer_delegates_without_changing_solver_or_gate() -> None:
    begin = (DT2 / "overlay" / "begin_toy_road_c5_trace.m").read_text(encoding="utf-8")
    append = (DT2 / "overlay" / "append_toy_road_c5_stagger_row.m").read_text(encoding="utf-8")
    assert "ToyRoadC5Trace(entryInput, outputRoot)" in begin
    assert "trace.appendCompletedStagger(rowInput)" in append
    assert append.index("trace.appendCompletedStagger(rowInput)") < append.index("matfile(")
    forbidden = ("newton_raphson", "max_iter", "1e-3", "converged =", "omega", "aitken")
    for token in forbidden:
        assert token.lower() not in (begin + append).lower()


def test_dt2_observer_records_initial_and_every_completed_iterate() -> None:
    begin = (DT2 / "overlay" / "begin_toy_road_c5_trace.m").read_text(encoding="utf-8")
    append = (DT2 / "overlay" / "append_toy_road_c5_stagger_row.m").read_text(encoding="utf-8")
    for token in ("d_iterates", "d_lb", "history_pre", "active_u_dofs", "active_d_dofs", "traction"):
        assert token in begin
    for token in ("u_iterates", "d_iterates", "trace.trace_row_count", "rowInput.u", "rowInput.d"):
        assert token in append
    assert "TOY_ROAD_DT2_ITERATE_PATH" in begin + append


def test_dt2_contract_is_explicitly_nonproduction_and_binds_base_source() -> None:
    contract = (DT2 / "DT2_DIAGNOSTIC_CONTRACT.json").read_text(encoding="utf-8")
    assert '"authorization_scope": "diagnostic_only_nonproduction"' in contract
    assert '"base_source_commit": "7c56ff383187cdee2f45e1b15d707f148f386302"' in contract
    assert '"original_t2_status": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4"' in contract
    assert '"stagger_iteration_cap": 1000' in contract
    assert '"fixed_point_tolerance": 0.001' in contract


def test_dt2_launcher_is_fresh_single_process_and_does_not_authorize_t3() -> None:
    launcher = (DT2 / "launch_dt2_diagnostic.py").read_text(encoding="utf-8")
    assert "if run_root.exists()" in launcher
    assert "matlab_processes()" in launcher
    assert "subprocess.Popen" in launcher
    assert '"diagnostic_only_nonproduction"' in launcher
    assert '"serial_chain_t3_authorized": False' in launcher
    assert '"solver_modified": False' in launcher
    assert '"thresholds_modified": False' in launcher
    assert "TOY_ROAD_DT2_ITERATE_PATH" in launcher
    assert "T3_loading_history" not in launcher
    assert "run_root.mkdir(parents=True, exist_ok=False)" in launcher
    assert '[roots["receipts"], roots["matlab_startup_pref"], initial_target.parent]' in launcher
    assert "cwd=run_root" in launcher
    assert "iterate_path.parent.mkdir()" not in launcher


def test_dt2_analyzer_exposes_read_only_callable_api() -> None:
    analyzer = _load_analyzer()
    assert callable(analyzer.analyze)
