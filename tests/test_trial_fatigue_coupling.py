"""Synthetic scalar callbacks only: no project network, training or FEM solve."""
import sys
from pathlib import Path
import pytest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from trial_fatigue_coupling import (
    solve_trial_fatigue_step, TrialFatigueNotConverged,
    PhysicalStepOptimizerBudget, trial_fatigue_checkpoint_contract,
    require_fresh_trial_run_directory,
    verify_initial_network, track_optimizer_work,
)
from fatigue_history import compute_fatigue_degrad


def _case(callback=None, max_outer=4):
    old = torch.tensor([[0.49, 0.6, 0.8]], dtype=torch.float64)
    prev = torch.zeros_like(old)
    damage = torch.zeros(3, dtype=torch.float64)
    fits = []
    def solve(f, outer):
        assert not f.requires_grad
        fits.append(f.clone())
    def state():
        return {"u": damage, "v": damage, "d": damage,
                "active_driver": torch.full_like(old, .1, requires_grad=True),
                "displacement": torch.tensor(0.1, dtype=torch.float64)}
    def accept(ctx):
        return {"accepted": True, "fresh_current_state": True,
                "state_token": ctx["state_token"], "metrics": {"Ru": 0., "Rd": 0.}}
    kw = dict(old_history=old, old_active_driver=prev, old_damage=damage,
              initial_f=torch.ones_like(old),
              fatigue_dict={"fatigue_on": True,"loading_type":"cyclic","accum_type":"carrara",
                            "alpha_T":.5,"history_storage":"tri3_gp3",
                            "history_driver_reduction":{"enable":True,"mode":"native_tri3_gp3"},
                            "damage_history_storage":"previous_accepted_nodal","explicit_cycle_substeps":5},
              config={"enable":True,"max_outer":max_outer,"f_atol":1e-12,"f_rtol":1e-12,
                      "epochs_per_outer":1,"max_total_rprop_epochs":4,
                      "recovery_lbfgs_max_iter":1,"recovery_lbfgs_max_eval":2},
              solve_for_coefficient=solve,evaluate_state=state,final_residual_check=callback or accept,step=4)
    return kw, fits


def test_old_history_frozen_increment_counted_once_and_coefficient_detached():
    kw, fits = _case()
    before = kw["old_history"].clone()
    result = solve_trial_fatigue_step(**kw)
    assert len(fits) == 2
    assert torch.equal(kw["old_history"], before)
    assert torch.allclose(result.history, before + .1)
    assert torch.equal(result.f_solve, result.f_commit)
    assert not result.f_commit.requires_grad
    assert not result.history.requires_grad


def test_plateau_of_f_does_not_override_failed_fresh_residual():
    def reject(ctx):
        return {"accepted":False,"fresh_current_state":True,
                "state_token":ctx["state_token"],"metrics":{"Ru":1.,"Rd":2.}}
    kw, fits = _case(reject, max_outer=3)
    before = kw["old_history"].clone()
    with pytest.raises(TrialFatigueNotConverged) as caught:
        solve_trial_fatigue_step(**kw)
    assert len(fits) == 3
    assert caught.value.records[-1]["f_converged"]
    assert torch.equal(kw["old_history"], before)


def test_stale_receipt_is_rejected_and_cannot_commit():
    kw, _ = _case(lambda ctx: {"accepted":True,"fresh_current_state":True,
                              "state_token":"previous-state","metrics":{"Ru":0.}})
    with pytest.raises(ValueError, match="fresh current trial"):
        solve_trial_fatigue_step(**kw)


def test_boolean_only_callback_cannot_fake_physical_acceptance():
    kw, _ = _case(lambda ctx: True)
    with pytest.raises(ValueError, match="explicit accepted boolean"):
        solve_trial_fatigue_step(**kw)


def test_missing_residual_callback_fails_before_solver():
    kw, fits = _case()
    kw["final_residual_check"] = None
    with pytest.raises(ValueError, match="requires a fresh"):
        solve_trial_fatigue_step(**kw)
    assert fits == []


def test_no_double_accumulation_even_when_residual_needs_many_iterations():
    def accept_late(ctx):
        assert torch.allclose(ctx["trial_history"], ctx["old_history"] + .1)
        return {"accepted":ctx["outer"] == 4,"fresh_current_state":True,
                "state_token":ctx["state_token"],"metrics":{"Ru":0.,"Rd":0.}}
    kw, fits = _case(accept_late)
    result = solve_trial_fatigue_step(**kw)
    assert len(fits) == 4
    assert torch.allclose(result.history, kw["old_history"] + .1)


def test_frozen_old_keeps_old_coefficient_but_commits_fresh_trial_history():
    def accept_late(ctx):
        assert ctx["coefficient_mode"] == "frozen_old"
        assert torch.allclose(ctx["trial_history"], ctx["old_history"] + .1)
        return {"accepted": ctx["outer"] == 3, "fresh_current_state": True,
                "state_token": ctx["state_token"], "metrics": {"Ru": 0.}}
    kw, fits = _case(accept_late)
    kw["config"]["coefficient_mode"] = "frozen_old"
    old_f = compute_fatigue_degrad(kw["old_history"], kw["fatigue_dict"])
    kw["initial_f"] = old_f.clone()
    before = kw["old_history"].clone()
    result = solve_trial_fatigue_step(**kw)
    assert len(fits) == 3
    assert all(torch.equal(fit, old_f) for fit in fits)
    assert torch.equal(result.f_solve, old_f)
    assert not torch.equal(result.f_solve, result.f_commit)
    assert not result.records[-1]["f_converged"]
    assert result.records[-1]["accepted"]
    assert torch.allclose(result.history, before + .1)
    assert torch.equal(kw["old_history"], before)


def test_frozen_old_cannot_commit_when_fresh_trial_residual_fails():
    def reject(ctx):
        return {"accepted": False, "fresh_current_state": True,
                "state_token": ctx["state_token"], "metrics": {"Ru": 1.}}
    kw, fits = _case(reject, max_outer=3)
    kw["config"]["coefficient_mode"] = "frozen_old"
    kw["initial_f"] = compute_fatigue_degrad(kw["old_history"], kw["fatigue_dict"])
    before = {key: kw[key].clone() for key in ("old_history", "old_active_driver", "old_damage")}
    with pytest.raises(TrialFatigueNotConverged) as caught:
        solve_trial_fatigue_step(**kw)
    assert len(fits) == 3
    assert all(torch.equal(fit, kw["initial_f"]) for fit in fits)
    assert all(not record["accepted"] for record in caught.value.records)
    assert all(torch.equal(kw[key], value) for key, value in before.items())


def test_trial_mode_still_requires_fixed_point_with_the_same_old_initial_f():
    kw, fits = _case()
    kw["config"]["coefficient_mode"] = "trial"
    kw["initial_f"] = compute_fatigue_degrad(kw["old_history"], kw["fatigue_dict"])
    result = solve_trial_fatigue_step(**kw)
    assert len(fits) == 2
    assert not torch.equal(fits[0], fits[1])
    assert result.records[0]["residual_accepted"]
    assert not result.records[0]["accepted"]
    assert result.records[-1]["f_converged"]
    assert torch.equal(result.f_solve, result.f_commit)


@pytest.mark.parametrize("invalid_mode", ["frozen", None, "old_history"])
def test_invalid_coefficient_mode_rejected_before_fitting(invalid_mode):
    kw, fits = _case()
    kw["config"]["coefficient_mode"] = invalid_mode
    with pytest.raises(ValueError, match="coefficient_mode"):
        solve_trial_fatigue_step(**kw)
    assert fits == []


def test_frozen_old_rejects_a_coefficient_unrelated_to_old_history():
    kw, fits = _case()
    kw["config"]["coefficient_mode"] = "frozen_old"
    with pytest.raises(ValueError, match="committed old history"):
        solve_trial_fatigue_step(**kw)
    assert fits == []


def test_observer_sees_full_independent_outer_fixed_point_and_accepted_states():
    kw, _ = _case()
    events = []
    def observe(event):
        events.append(event)
        assert set(("u", "v", "d", "active_driver", "displacement", "old_damage",
                    "old_history", "old_active_driver", "trial_history", "f_solve",
                    "f_commit", "state_token", "step", "outer")) <= event["context"].keys()
        assert all(not value.requires_grad for value in event["context"].values()
                   if torch.is_tensor(value))
        if event["event"] == "outer":
            # A storage callback cannot corrupt the controller or later events.
            event["context"]["old_history"].zero_()
            event["context"]["f_commit"].zero_()
            event["record"]["residual"]["metrics"]["Ru"] = 999.
    before = kw["old_history"].clone()
    result = solve_trial_fatigue_step(**kw, observer=observe)
    assert [event["event"] for event in events] == [
        "outer", "outer", "first_f_fixed_point", "accepted"]
    assert torch.equal(events[-1]["context"]["old_history"], before)
    assert torch.equal(events[-1]["context"]["f_commit"], result.f_commit)
    assert result.residual_receipt["metrics"]["Ru"] == 0.
    assert result.records[-1]["residual"]["metrics"]["Ru"] == 0.
    events[-1]["context"]["f_commit"].zero_()
    assert bool(torch.any(result.f_commit != 0))


def test_observer_reports_final_rejected_field_at_outer_exhaustion():
    def reject(ctx):
        return {"accepted": False, "fresh_current_state": True,
                "state_token": ctx["state_token"], "metrics": {"Ru": 1.}}
    kw, _ = _case(reject, max_outer=3)
    events = []
    with pytest.raises(TrialFatigueNotConverged):
        solve_trial_fatigue_step(**kw, observer=events.append)
    assert [event["event"] for event in events].count("first_f_fixed_point") == 1
    assert "accepted" not in [event["event"] for event in events]
    final = events[-1]
    assert final["event"] == "exhausted"
    assert final["reason"] == "max_outer"
    assert final["context"]["outer"] == 3
    assert not final["record"]["accepted"]
    assert torch.allclose(final["context"]["trial_history"], kw["old_history"] + .1)


def test_observer_reassembles_actual_field_after_partial_budget_exhaustion():
    kw, _ = _case(max_outer=3)
    original_state = kw["evaluate_state"]
    current = {"outer": 0}
    def solve(coefficient, outer):
        current["outer"] = outer
        if outer == 2:
            raise TrialFatigueNotConverged("partial optimizer budget exhausted", [])
    def state():
        value = original_state()
        value["u"] = torch.full_like(value["u"], float(current["outer"]))
        return value
    kw.update(solve_for_coefficient=solve, evaluate_state=state)
    events = []
    with pytest.raises(TrialFatigueNotConverged, match="partial optimizer budget"):
        solve_trial_fatigue_step(**kw, observer=events.append)
    final = events[-1]
    assert final["event"] == "exhausted"
    assert final["context"]["outer"] == 2
    assert torch.equal(final["context"]["u"], torch.full_like(kw["old_damage"], 2.))
    assert final["record"]["optimizer_exhausted"]
    # A numerically acceptable partial field does not turn exhaustion into acceptance.
    assert final["record"]["residual_accepted"]
    assert not final["record"]["accepted"]
    assert "accepted" not in [event["event"] for event in events]


@pytest.mark.parametrize("failure_site", ["residual", "observer"])
def test_exhaustion_diagnostic_failure_preserves_original_budget_error(failure_site):
    kw, _ = _case(max_outer=3)
    original_residual = kw["final_residual_check"]
    budget_error = TrialFatigueNotConverged("original optimizer budget exhausted", [])
    def solve(coefficient, outer):
        if outer == 2:
            raise budget_error
    def residual(context):
        if failure_site == "residual" and context["outer"] == 2:
            raise ValueError("failed exhausted residual reassembly")
        return original_residual(context)
    def observe(event):
        if failure_site == "observer" and event["event"] == "exhausted":
            raise OSError("failed exhausted snapshot write")
    kw.update(solve_for_coefficient=solve, final_residual_check=residual)
    before = kw["old_history"].clone()
    with pytest.raises(TrialFatigueNotConverged, match="original optimizer budget") as caught:
        solve_trial_fatigue_step(**kw, observer=observe)
    assert caught.value is budget_error
    assert len(caught.value.records) == 1
    assert caught.value.records[0]["outer"] == 1
    assert "failed exhausted" in caught.value.diagnostic_error
    assert torch.equal(kw["old_history"], before)


@pytest.mark.parametrize("event_name", ["outer", "first_f_fixed_point", "accepted"])
def test_observer_failure_prevents_accepted_result(event_name):
    kw, _ = _case()
    before = kw["old_history"].clone()
    def fail(event):
        if event["event"] == event_name:
            raise OSError("snapshot persistence failed")
    with pytest.raises(OSError, match="snapshot persistence"):
        solve_trial_fatigue_step(**kw, observer=fail)
    assert torch.equal(kw["old_history"], before)


def test_invalid_observer_rejected_before_fitting():
    kw, fits = _case()
    with pytest.raises(ValueError, match="observer must be callable"):
        solve_trial_fatigue_step(**kw, observer=False)
    assert fits == []


def test_optimizer_budget_is_shared_across_refreshes_and_exhaustion_cannot_commit():
    kw, _ = _case(max_outer=6)
    budget = PhysicalStepOptimizerBudget(2, 3)
    allocations = []
    def solve(f, outer):
        epochs = budget.next_rprop_epochs()
        allocations.append(epochs)
        budget.record_rprop_updates(epochs)
    def reject(ctx):
        return {"accepted":False, "fresh_current_state":True,
                "state_token":ctx["state_token"], "metrics":{"Ru":1.}}
    kw.update(solve_for_coefficient=solve, final_residual_check=reject)
    before = kw["old_history"].clone()
    with pytest.raises(TrialFatigueNotConverged, match="budget exhausted") as caught:
        solve_trial_fatigue_step(**kw)
    assert allocations == [2, 1]
    assert budget.rprop_updates == 3
    assert len(caught.value.records) == 2
    assert torch.equal(kw["old_history"], before)


def test_native_driver_mismatch_rejected_before_fitting():
    kw, fits = _case()
    kw["fatigue_dict"]["history_driver_reduction"]["mode"] = "fem_gp_tri3_g_mean"
    with pytest.raises(ValueError, match="matching native GP driver"):
        solve_trial_fatigue_step(**kw)
    assert fits == []


def test_resume_contract_preserves_acceptance_and_penalty_and_omits_callbacks():
    kw, _ = _case()
    config = dict(kw["config"], final_residual_check=kw["final_residual_check"],
                  acceptance_config={"mode":"nodal_box_kkt", "joint_tol":4e-4})
    penalty = {"enable":True, "negative_damage_recovery":13781.25}
    common = {"material":{"tol_ir":.001}, "damage_dirichlet":{"node_indices":[0, 3]}}
    original = trial_fatigue_checkpoint_contract(config, penalty, common, kw["fatigue_dict"])
    assert "final_residual_check" not in original["coupling"]
    assert original["coupling"]["history_mode"] == "trial"
    assert original["coupling"]["coefficient_mode"] == "trial"
    config["coefficient_mode"] = "frozen_old"
    assert trial_fatigue_checkpoint_contract(config, penalty, common, kw["fatigue_dict"]) != original
    config["coefficient_mode"] = "trial"
    assert original["irreversibility_penalty"] == penalty
    config["acceptance_config"]["joint_tol"] = 1e-3
    assert trial_fatigue_checkpoint_contract(config, penalty, common, kw["fatigue_dict"]) != original
    assert original["coupling"]["acceptance_config"]["joint_tol"] == 4e-4
    config["acceptance_config"]["joint_tol"] = 4e-4
    penalty["negative_damage_recovery"] = 0.
    assert trial_fatigue_checkpoint_contract(config, penalty, common, kw["fatigue_dict"]) != original
    penalty["negative_damage_recovery"] = 13781.25
    common["damage_dirichlet"]["node_indices"] = [0, 2]
    assert trial_fatigue_checkpoint_contract(config, penalty, common, kw["fatigue_dict"]) != original
    common["damage_dirichlet"]["node_indices"] = [0, 3]
    kw["fatigue_dict"]["alpha_T"] = .6
    assert trial_fatigue_checkpoint_contract(config, penalty, common, kw["fatigue_dict"]) != original


@pytest.mark.parametrize("artifact", [
    "best_models/checkpoint_step_2.pt", "best_models/trained_1NN_2.pt",
    "trial_fatigue_acceptance/step_000002_accepted.json",
    "trial_fatigue_acceptance/step_000002_rejected.json",
    "trial_fatigue_acceptance/step_000002_coefficients.npz",
])
def test_strict_resume_refused_before_loading_or_fitting(tmp_path, artifact):
    models = tmp_path / "best_models"
    models.mkdir()
    (models / "trained_1NN_initTraining.pt").write_bytes(b"staged common initial weights")
    require_fresh_trial_run_directory(models)
    output = tmp_path / artifact
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(b"prior accepted state")
    with pytest.raises(RuntimeError, match="does not support resume"):
        require_fresh_trial_run_directory(models)


def test_initial_network_bytes_require_explicit_matching_sha(tmp_path):
    import hashlib
    path = tmp_path / "initial.pt"
    path.write_bytes(b"synthetic initial artifact")
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert verify_initial_network(path, expected) == expected
    with pytest.raises(ValueError, match="initial_network_sha256"):
        verify_initial_network(path, None)
    path.write_bytes(b"changed artifact")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        verify_initial_network(path, expected)


class _FakeOptimizer:
    """Hook protocol only; no numerical optimizer or project network."""
    def __init__(self):
        self.pre, self.post = [], []
        self.state = {"global": {"func_evals": 0, "n_iter": 0}}
    def _register(self, hooks, hook):
        hooks.append(hook)
        class Handle:
            def remove(self):
                hooks.remove(hook)
        return Handle()
    def register_step_pre_hook(self, hook):
        return self._register(self.pre, hook)
    def register_step_post_hook(self, hook):
        return self._register(self.post, hook)
    def step(self, closure=None, evaluations=0):
        args = (self, closure) if closure is not None else (self,)
        kwargs = {}
        for hook in list(self.pre):
            changed = hook(self, args, kwargs)
            if changed is not None:
                args, kwargs = changed
        for _ in range(evaluations):
            self.state["global"]["n_iter"] += 1
            args[-1]()
            self.state["global"]["func_evals"] += 1
        for hook in list(self.post):
            hook(self, args, kwargs)


def test_step_hook_preserves_completed_rprop_count_on_exception():
    optimizer, budget, receipt = _FakeOptimizer(), PhysicalStepOptimizerBudget(3, 3), {}
    with pytest.raises(RuntimeError, match="injected"):
        with track_optimizer_work(optimizer, budget, receipt, "RPROP"):
            optimizer.step()
            optimizer.step()
            raise RuntimeError("injected failure after completed updates")
    assert budget.rprop_updates == 2
    assert optimizer.pre == optimizer.post == []


def test_lbfgs_closure_cap_is_hard_and_exception_counts_survive():
    optimizer, budget, receipt = _FakeOptimizer(), PhysicalStepOptimizerBudget(1, 1), {}
    called = []
    with pytest.raises(TrialFatigueNotConverged, match="closure budget"):
        with track_optimizer_work(optimizer, budget, receipt, "LBFGS", max_eval=2):
            optimizer.step(lambda: called.append(1), evaluations=4)
    assert len(called) == receipt["lbfgs_closure_calls"] == 2
    assert receipt["lbfgs_func_evals"] == 2
    assert receipt["lbfgs_iterations"] == 3
    assert optimizer.pre == optimizer.post == []
