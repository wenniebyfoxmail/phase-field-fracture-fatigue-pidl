"""Artificial arrays, metadata and fake optimizers; no project NN/optimization."""
import copy
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/s04_e036"))
import run_mechanism_matrix as m
from q4_quadrature import q4_shape_data


def quad():
    x = torch.tensor([[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]], dtype=torch.float64)
    cells = torch.tensor([[0, 1, 2, 3]])
    shape, derivative, weights = q4_shape_data(x, cells)
    return SimpleNamespace(x=x, native_x=x, cells=cells, native_shape=shape,
                           native_dshape=derivative, native_weights=weights, device=torch.device("cpu"))


def manifest():
    ref = dict(path="unused", sha256="a" * 64)
    return dict(schema="s04_e036_mechanism_inputs_v1", trajectory="synthetic", mesh=ref,
                common_problem=ref, solver=copy.deepcopy(m.SOLVER), job_wall_seconds=1234,
                cases={name: dict(state_key=m.state_key("synthetic", *key), predecessor=ref,
                                  admission=ref, network=dict(path="unused", sha256=m.NETWORK_SHA[name]))
                       for name, key in m.CASES.items()})


def test_physics_manifest_never_admits_future_targets_or_replacement_network():
    doc = manifest()
    m.validate_manifest(doc)
    doc["targets"] = {}
    with pytest.raises(ValueError, match="no future target"):
        m.validate_manifest(doc)
    del doc["targets"]
    doc["cases"]["c1s2"]["network"]["sha256"] = "b" * 64
    with pytest.raises(ValueError, match="network changed"):
        m.validate_manifest(doc)


@pytest.mark.parametrize("wall", [0, -1, float("inf"), True, None])
def test_job_antihang_is_finite_independent_setting(wall):
    doc = manifest()
    doc["job_wall_seconds"] = wall
    with pytest.raises(ValueError, match="anti-hang"):
        m.validate_manifest(doc)


def test_cumulative_cap_cannot_silently_rejoin_current_program():
    doc = manifest()
    doc["solver"]["cumulative_resource_limit"] = 48
    with pytest.raises(ValueError, match="numerical program"):
        m.validate_manifest(doc)


def test_both_maps_promote_fields_but_keep_native_lower_exact():
    # A native lower that rounds down by 3e-8 must not become a tolerated heal.
    lower = torch.tensor([.50000003, 1.], dtype=torch.float64)
    for mapping in ("legacy", "nodal_clamp"):
        raw = torch.tensor([.5, 1.], dtype=torch.float32, requires_grad=True)
        field = object.__new__(m.MechanismField)
        field.problem = SimpleNamespace(native_x=torch.zeros(2, 2, dtype=torch.float64))
        field.base = SimpleNamespace(fieldCalculation=lambda _: (raw * 0, raw * 0, raw))
        field.x, field.lower, field.mapping = None, lower, mapping
        values, original = field.values()
        assert all(value.dtype == torch.float64 for value in values.values())
        assert original.dtype == torch.float64
        if mapping == "nodal_clamp":
            assert torch.equal(values["d"], lower)
            values["d"].sum().backward()
            assert torch.equal(raw.grad, torch.zeros_like(raw))
        else:
            assert float((lower[0] - values["d"][0]).detach()) > 1e-8


def test_fit_metric_uses_nodal_and_native_q4_gradient_scales():
    p = quad()
    target = {name: torch.zeros(4, dtype=torch.float64) for name in ("u", "v", "d")}
    fields = dict(target, u=.12 * p.x[:, 0])
    loss, report = m.fit_objective(fields, target, torch.full((4,), .25, dtype=torch.float64),
                                  p.native_weights, p.native_dshape, p.cells)
    assert float(loss) == pytest.approx(1 / 12 + .01**2 / 3)
    assert report["G"] == pytest.approx(.01 / math.sqrt(3))
    assert report["max_damage_error"] == 0
    assert m.fit_program_stop(dict(Q=1e-3, max_damage_error=.01))
    assert not m.fit_program_stop(dict(Q=1e-3, max_damage_error=.01000001))
    assert not m.fit_program_stop(dict(Q=.00100001, max_damage_error=0))


def test_stagnation_requires_completed_window_and_relative_best_change():
    assert not m.stalled([10.] * 10, 10, .01)
    assert m.stalled([10.] * 11, 10, .01)
    assert not m.stalled([10.] + [9.] * 10, 10, .01)


def test_closure_hard_cap_counts_calls_and_restores_all_trial_changes():
    value = torch.tensor([3.], requires_grad=True)
    work = dict(lbfgs_closures=0, lbfgs_steps=0)
    class FakeOptimizer:
        def step(self, closure):
            for _ in range(4):
                with torch.no_grad():
                    value.add_(10.)
                closure()
    with pytest.raises(m.ClosureLimit):
        m.bounded_lbfgs_step(FakeOptimizer(), [value], lambda: value.sum(), work, lambda: None, cap=3)
    assert value.item() == 3.
    assert work == dict(lbfgs_closures=3, lbfgs_steps=0)


def test_failed_optimizer_step_restores_and_never_counts_accepted_step():
    value = torch.tensor([3.], requires_grad=True)
    work = dict(lbfgs_closures=0, lbfgs_steps=0)
    class FakeOptimizer:
        def step(self, closure):
            with torch.no_grad():
                value.add_(10.)
            closure()
            raise RuntimeError("synthetic line search failure")
    with pytest.raises(RuntimeError, match="synthetic"):
        m.bounded_lbfgs_step(FakeOptimizer(), [value], lambda: value.sum(), work, lambda: None)
    assert value.item() == 3. and work["lbfgs_steps"] == 0 and work["lbfgs_closures"] == 1


class FakeEngine:
    tamper = False
    def __init__(self, problem, native_old, state, key, arm, dtype, deadline, provenance):
        self.problem, self.native_old = problem, native_old
        self.old = {k: v.clone() for k, v in native_old.items()}
        self.key, self.arm, self.dtype, self.provenance = key, arm, dtype, provenance
        self.mapping, self.weight_l2 = m.ARMS[arm]
        self.deadline = deadline
        self.field = SimpleNamespace(net=SimpleNamespace(state_dict=lambda: state))
        self.work = dict(rprop_updates=2000, lbfgs_steps=0, lbfgs_closures=0,
                         coefficient_refreshes=9, history_commits=0, snapshot_replays=0)
        self.coefficient = torch.ones(1, 4, dtype=torch.float64)
        self.events = set()
    def check(self):
        pass
    def readout(self):
        v = self.field.net.state_dict()["fixture"].to(torch.float64).clone()
        if self.tamper:
            v += 1
        fields = dict(u=v, v=v * 0, d=v * 0, active_driver=torch.zeros(1, 4, dtype=torch.float64),
                      displacement=torch.tensor([self.key["displacement"]], dtype=torch.float64))
        return dict(fields=fields, raw_damage=v * 0, history=torch.zeros(1, 4, dtype=torch.float64),
                    f_solve=self.coefficient, f_commit=self.coefficient.clone(),
                    residual=dict(accepted=False, metrics=dict(joint_score=2.)),
                    coefficient_fixed_point=True, physical_accepted=False, C=2.)
    def refresh(self, result):
        self.work["coefficient_refreshes"] += 1


def fake_engine():
    p = quad()
    p.common = {"fixture": True}
    old = dict(damage=torch.zeros(4, dtype=torch.float64), history=torch.zeros(1, 4, dtype=torch.float64),
               active_driver=torch.zeros(1, 4, dtype=torch.float64))
    return FakeEngine(p, old, {"fixture": torch.zeros(4)}, m.state_key("synthetic", 1, 2),
                      "Lplus", torch.float32, SimpleNamespace(check=lambda: None),
                      {"predecessor_checkpoint_sha256": "a" * 64})


def test_complete_diagnostic_persists_rejected_fields_without_claiming_acceptance(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "EndpointEngine", FakeEngine)
    engine = fake_engine()
    receipt = m.publish_snapshot(tmp_path / "endpoint", engine, engine.readout(), "first_2000", endpoint=True)
    assert receipt["endpoint_complete"] and receipt["readback_verified"]
    assert receipt["physical_accepted"] is False and receipt["history_commit_count"] == 0
    with np.load(tmp_path / "endpoint/fields.npz", allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
        assert metadata["network_dtype"] == "float32" and metadata["physical_operator_dtype"] == "float64"
        assert metadata["changed_function_family"] is False
        assert data["old_damage"].dtype == np.float64
    assert (tmp_path / "endpoint/completion.json").is_file()


def test_failed_exact_field_replay_never_publishes_completion(tmp_path, monkeypatch):
    engine = fake_engine()
    result = engine.readout()
    class Tampered(FakeEngine):
        tamper = True
    monkeypatch.setattr(m, "EndpointEngine", Tampered)
    with pytest.raises(ValueError, match="tensor differs"):
        m.publish_snapshot(tmp_path / "endpoint", engine, result, "first_2000", endpoint=True)
    assert not (tmp_path / "endpoint/completion.json").exists()


def test_matrix_runs_all_ten_blocks_even_if_initial_state_is_accepted(tmp_path, monkeypatch):
    engine = fake_engine()
    engine.work["rprop_updates"] = 0
    engine.work["coefficient_refreshes"] = 0
    original = engine.readout
    engine.readout = lambda: dict(original(), physical_accepted=True)
    snapshots = []
    monkeypatch.setattr(m, "publish_snapshot", lambda path, _, result, stage, **kwargs: snapshots.append((stage, kwargs)))
    def block(e, _):
        e.work["rprop_updates"] += 200
    monkeypatch.setattr(m, "rprop_block", block)
    result = m.matrix_arm(engine, tmp_path / "arm")
    assert result["work"]["rprop_updates"] == 2000
    assert result["work"]["coefficient_refreshes"] == 9
    assert snapshots[-1] == ("first_2000", dict(full_diagnostics=True, endpoint=True))


def test_immutable_old_guard_detects_any_change_without_a_network():
    obj = object.__new__(m.EndpointEngine)
    obj.old = {"damage": torch.tensor([.3], dtype=torch.float64)}
    obj.guard = m.cpu(obj.old)
    obj.field = SimpleNamespace(lower=obj.old["damage"].clone())
    obj.verify_old()
    obj.old["damage"][0] += .01
    with pytest.raises(ValueError, match="tensor differs"):
        obj.verify_old()


def test_release_contract_is_teacher_initialized_and_not_executed():
    request = m.release_contract(dict(endpoint_complete=True, metadata=dict(arm="legacy_witness")),
                                 {"accepted": False}, "observed infeasible original-map readout")
    assert request["teacher_initialized"] is True
    assert "requires separate" in request["execution_status"]


def test_case_partition_is_only_a_filter_of_the_prespecified_full_design():
    assert m.execution_cases(None) == tuple(m.CASES)
    assert m.execution_cases("c83s4") == ("c83s4",)
    with pytest.raises(ValueError, match="predetermined"):
        m.execution_cases("easier_state")
    doc = manifest()
    del doc["cases"]["c83s4"]
    with pytest.raises(ValueError, match="exact four"):
        m.validate_manifest(doc)


def continuation_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "EndpointEngine", FakeEngine)
    engine = fake_engine()
    engine.arm, engine.mapping, engine.weight_l2 = "C0", "nodal_clamp", 0.
    engine.provenance.update(manifest_sha256="b" * 64, theta0_sha256="c" * 64)
    directory = tmp_path / "prefix"
    m.publish_snapshot(directory, engine, engine.readout(), "first_2000", endpoint=True)
    def specs():
        return {name: dict(path=str(directory / file), sha256=m.sha256(directory / file))
                for name, file in (("bundle", "bundle.pt"), ("completion", "completion.json"))}
    args = (tmp_path, engine.problem, engine.native_old, engine.key, "C0", engine.deadline, engine.provenance)
    return directory, specs, args


def test_continuation_consumes_only_exact_original_matrix_prefix(tmp_path, monkeypatch):
    directory, specs, args = continuation_fixture(tmp_path, monkeypatch)
    engine, result, payload = m.load_endpoint(specs(), *args)
    assert engine.work["rprop_updates"] == 2000 and engine.work["history_commits"] == 0
    assert result["physical_accepted"] is False


@pytest.mark.parametrize("change", ["stage", "manifest", "theta0", "old_state", "lbfgs"])
def test_bound_but_wrong_continuation_provenance_is_rejected(tmp_path, monkeypatch, change):
    directory, specs, args = continuation_fixture(tmp_path, monkeypatch)
    payload = torch.load(directory / "bundle.pt", weights_only=True)
    receipt = json.loads((directory / "completion.json").read_text())
    if change == "stage":
        payload["metadata"]["stage"] = "another_stage"
    elif change == "manifest":
        payload["provenance"]["manifest_sha256"] = "d" * 64
    elif change == "theta0":
        payload["provenance"]["theta0_sha256"] = "d" * 64
    elif change == "old_state":
        payload["old_state"]["damage"][0] = .1
    else:
        payload["work"]["lbfgs_steps"] = 1
    # Simulate a separately bound, internally hashed but scientifically wrong
    # source. A valid hash does not prove the required first-2000 provenance.
    torch.save(payload, directory / "bundle.pt")
    receipt["bundle_sha256"] = m.sha256(directory / "bundle.pt")
    receipt["metadata"] = payload["metadata"]
    (directory / "completion.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        m.load_endpoint(specs(), *args)
