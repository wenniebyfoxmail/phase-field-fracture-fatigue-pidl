from pathlib import Path
import hashlib
import importlib.util

import pytest

spec = importlib.util.spec_from_file_location("e036_overlay", Path(__file__).with_name("build_overlay.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def source_stub():
    return mod.PRE_ITER + mod.ACCEPT + mod.COMMIT + "            if i_stag == SOL_STAG_PAR.max_iter\n"


def test_drift_and_duplicate_anchor_fail_closed():
    with pytest.raises(ValueError):
        mod.patch_solver("not the solver")
    with pytest.raises(ValueError):
        mod.patch_solver(source_stub() + mod.ACCEPT)


def test_default_keeps_native_commit_and_opt_in_requires_fresh_proposal():
    patched = mod.patch_solver(source_stub())
    assert patched.count(mod.COMMIT) == 1
    assert patched.index("e036_native_candidate") < patched.index("if stag_converged")
    assert "stag_converged = e036_audit.joint_pass" in patched
    assert "history_vars_old = e036_proposal.history" in patched
    assert patched.index("save([e036_path '.tmp']") < patched.index("history_vars_old = e036_proposal.history")
    assert "rejected_no_history_commit" in patched
    assert "history_vars_old,e036_old.history" in patched


def test_build_refuses_unknown_source_before_writing(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in mod.PINNED:
        (source / name).write_text("changed source")
    out = tmp_path / "overlay"
    with pytest.raises(ValueError, match="identity mismatch"):
        mod.build(source, out)
    assert not out.exists()


def test_local_overlay_does_not_change_input_or_overwrite_output(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    texts = {"solve_fatigue_fracture.m": source_stub(), "run_SENS_hard_recovery_native_q4_capture.m": "function result = entry(options)\nsolve_fatigue_fracture\nend\n"}
    pins = {}
    for name, text in texts.items():
        (source / name).write_text(text)
        pins[name] = hashlib.sha256((source / name).read_bytes()).hexdigest()
    monkeypatch.setattr(mod, "PINNED", pins)
    out = tmp_path / "overlay"
    receipt = mod.build(source, out)
    assert len(receipt["files"]) == 5
    for name, text in texts.items():
        assert (source / name).read_text() == text
    with pytest.raises(FileExistsError):
        mod.build(source, out)


def test_runner_default_is_disabled_and_mode_is_explicit():
    runner = mod.patch_runner("function result = entry(options)\nsolve_fatigue_fracture\nend\n")
    assert "struct('enabled',false)" in runner
    assert "Missing explicit policy" in runner
    policy = Path(__file__).with_name("e036_policy.m").read_text()
    assert "function policy=e036_policy(name,phase_semantics)" in policy
    assert "'bound_tol',1e-8,'active_tol',1e-10" in policy
