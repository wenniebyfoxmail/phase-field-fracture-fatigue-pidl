"""One fixed artificial end-to-end fixture; no project network or optimizer."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/s04_e036"))
import score_mechanism_matrix as s
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_shape_data
from native_q4_diagnostics import native_readout


def test_artificial_input_to_verified_scores_and_exported_figures(tmp_path, monkeypatch):
    """Actual NPZ/PT/JSON hashes, replay, Q4 metrics, contrasts and four figures.

    Only producer admission/real-network realization are replaced with tiny
    explicit fields. All serialization, readback checks and metrics are real.
    """
    x = torch.tensor([[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]], dtype=torch.float64)
    cells = torch.tensor([[0, 1, 2, 3]])
    shape, deriv, weights = q4_shape_data(x, cells)
    p = SimpleNamespace(x=x, native_x=x, cells=cells, native_shape=shape, native_dshape=deriv,
        native_weights=weights, native_area=weights.sum(1), device=torch.device("cpu"), common={"tiny": True},
        mat=MaterialProperties(1., .3, 1., .01), model=PFFModel("AT1", "volumetric", .001, residual_stiffness=0.),
        penalty=dict(enable=True, mode="fem_gp_q4", spatial_integration="native_q4_gp4", recovery_penalty_coefficient=13781.25),
        fatigue=dict(fatigue_on=True, loading_type="cyclic", accum_type="carrara", degrad_type="asymptotic", alpha_T=.5))
    old = dict(damage=torch.full((4,), .1, dtype=torch.float64), history=torch.full((1, 4), .8, dtype=torch.float64),
               active_driver=torch.zeros(1, 4, dtype=torch.float64))
    f = torch.ones(1, 4, dtype=torch.float64)
    target_fields = dict(u=.03*x[:, 0], v=.06*x[:, 1], d=torch.full((4,), .2, dtype=torch.float64))
    target_native = native_readout(p, target_fields, old, f, old["history"], f)
    target = dict(target_fields, history=target_native["gp"]["history"], active_driver=target_native["gp"]["active"],
                  f_solve=target_native["gp"]["f_commit"], f_commit=target_native["gp"]["f_commit"],
                  **{"old_"+name: value for name, value in old.items()})

    def dump(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, allow_nan=False))
        return ref(path)
    def ref(path):
        return dict(path=str(path), sha256=s.sha256(path))
    dummy = dump(tmp_path / "dummy.json", {})
    physics = dict(schema="s04_e036_mechanism_inputs_v1", trajectory="tiny", mesh=dummy, common_problem=dummy,
                   solver=s.runner.SOLVER, job_wall_seconds=300,
                   cases={name: dict(state_key=s.runner.state_key("tiny", *key), predecessor=dummy, admission=dummy,
                                    network=dict(path="unused", sha256=s.runner.NETWORK_SHA[name])) for name, key in s.CASES.items()})
    physics_ref = dump(tmp_path / "physics.json", physics)
    target_sha = dummy["sha256"]
    target_manifest = dict(schema="s04_e036_mechanism_targets_v1", physics_manifest=physics_ref,
                           targets={name: dict(snapshot=dummy, admission=dummy) for name in s.CASES})
    target_ref = dump(tmp_path / "targets.json", target_manifest)
    lock_ref = dump(tmp_path / "producer_lock.json", dict(schema="s04_e036_implementation_lock_v1",
                          files={name: s.sha256(s.ROOT / name) for name in s.SOURCE_FILES}))
    deadline = SimpleNamespace(check=lambda: None)
    class FakeEngine:
        # Four explicit nodal values, no nn.Module and no optimizer.
        def __init__(self, problem, native_old, state, key, arm, dtype, deadline, provenance):
            self.problem, self.old, self.native_old = problem, native_old, native_old
            self.key, self.arm, self.dtype, self.provenance = key, arm, dtype, provenance
            self.deadline = deadline
            self.mapping, self.weight_l2 = s.ARMS[arm] if arm in s.ARMS else ("legacy", 0.)
            self.field = SimpleNamespace(net=SimpleNamespace(state_dict=lambda: state))
            self.work = dict(rprop_updates=2000 if arm in s.ARMS else 0, lbfgs_steps=0 if arm in s.ARMS else 4,
                             lbfgs_closures=0 if arm in s.ARMS else 12, coefficient_refreshes=9, history_commits=0, snapshot_replays=0)
            self.coefficient = f.clone()
        def check(self):
            pass
        def readout(self):
            delta = self.field.net.state_dict()["delta"].double()
            fields = dict(target_fields, d=target_fields["d"] + delta)
            native = native_readout(p, fields, old, self.coefficient, old["history"], f)
            if self.arm == "legacy_witness":
                self.coefficient = native["gp"]["f_commit"].clone()
            fields = dict(fields, active_driver=native["gp"]["active"],
                          displacement=torch.tensor([self.key["displacement"]], dtype=torch.float64))
            C = 1. + float(delta.abs().max()) * 10
            return dict(fields=fields, raw_damage=fields["d"], history=native["gp"]["history"],
                        f_solve=self.coefficient.clone(), f_commit=native["gp"]["f_commit"],
                        residual=dict(accepted=False, metrics=dict(joint_score=C)), coefficient_fixed_point=False,
                        physical_accepted=False, C=C)
    monkeypatch.setattr(s.runner, "EndpointEngine", FakeEngine)
    cases = {name: dict(matrix={a: None for a in s.ARMS}, target_fit=None, C0_continuation=None) for name in s.CASES}
    for name in s.CASES:
        key = physics["cases"][name]["state_key"]
        provenance = dict(case=name, manifest_sha256=physics_ref["sha256"], theta0_sha256=s.runner.NETWORK_SHA[name],
                          predecessor_checkpoint_sha256="a"*64)
        for phase, arm, delta in [("matrix", a, v) for a, v in zip(s.ARMS, (.04, .03, .02, .01))] + [("target_fit", "legacy_witness", .002)]:
            phase_dir = tmp_path / (name + "_" + phase)
            authority = dict(approved=True, manifest_sha256=physics_ref["sha256"], mechanism_phase=phase,
                             requested_case=name, implementation_lock=lock_ref)
            if phase == "target_fit":
                authority["target_manifest"] = target_ref
            attempt_ref = dump(phase_dir / "attempt.json", dict(schema="s04_e036_mechanism_attempt_v1", phase=phase,
                manifest_sha256=physics_ref["sha256"], requested_case=name, declared_cases=list(s.CASES), execution_cases=[name],
                history_commit_count=0, provenance=dict(authority=authority, source=dict(source_kind="artificial_fixture"))))
            arm_root = phase_dir / name / arm
            arm_root.mkdir(parents=True)
            source = dict(provenance, execution_phase=phase)
            if phase == "target_fit":
                source.update(seen_target=True, target_admission=dict(snapshot_sha256=target_sha))
            engine = FakeEngine(p, old, {"delta": torch.full((4,), delta, dtype=torch.float32 if phase == "matrix" else torch.float64)},
                                key, arm, torch.float32 if phase == "matrix" else torch.float64, deadline, source)
            endpoint = arm_root / ("first_2000" if phase == "matrix" else "final")
            s.runner.publish_snapshot(endpoint, engine, engine.readout(), "first_2000" if phase == "matrix" else "lbfgs_final", endpoint=True)
            saved = {label: ref(endpoint / filename) for label, filename in
                     (("completion", "completion.json"), ("bundle", "bundle.pt"), ("fields", "fields.npz"), ("network", "network.pt"))}
            record = dict(status="complete", attempt=attempt_ref, implementation_lock=lock_ref,
                          phase_inputs=None if phase == "matrix" else target_ref, endpoint=saved, snapshots=[saved], failure=None)
            if phase == "matrix":
                cases[name]["matrix"][arm] = record
            else:
                cases[name]["target_fit"] = record
    sources_ref = dump(tmp_path / "C0_sources.json", dict(schema="s04_e036_C0_continuation_v1", physics_manifest=physics_ref,
        cases={name: {k: cases[name]["matrix"]["C0"]["endpoint"][k] for k in ("completion", "bundle")} for name in s.CASES}))
    for name in s.CASES:
        phase_dir = tmp_path / (name + "_continuation")
        authority = dict(approved=True, manifest_sha256=physics_ref["sha256"], mechanism_phase="candidate_continuation",
                         requested_case=name, implementation_lock=lock_ref, source_endpoints=sources_ref)
        attempt_ref = dump(phase_dir / "attempt.json", dict(schema="s04_e036_mechanism_attempt_v1", phase="candidate_continuation",
            manifest_sha256=physics_ref["sha256"], requested_case=name, declared_cases=list(s.CASES), execution_cases=[name],
            history_commit_count=0, provenance=dict(authority=authority, source=dict(source_kind="artificial_fixture"))))
        source = dict(case=name, manifest_sha256=physics_ref["sha256"], theta0_sha256=s.runner.NETWORK_SHA[name],
                      predecessor_checkpoint_sha256="a"*64, execution_phase="candidate_continuation")
        engine = FakeEngine(p, old, {"delta": torch.full((4,), .005, dtype=torch.float64)},
                            physics["cases"][name]["state_key"], "C0", torch.float64, deadline, source)
        engine.work.update(rprop_updates=2200, lbfgs_steps=4, lbfgs_closures=12)
        endpoint = phase_dir / name / "C0" / "float64_lbfgs" / "final"
        endpoint.parent.mkdir(parents=True)
        s.runner.publish_snapshot(endpoint, engine, engine.readout(), "lbfgs_final", endpoint=True)
        saved = {label: ref(endpoint / filename) for label, filename in
                 (("completion", "completion.json"), ("bundle", "bundle.pt"), ("fields", "fields.npz"), ("network", "network.pt"))}
        cases[name]["C0_continuation"] = dict(status="complete", attempt=attempt_ref, implementation_lock=lock_ref,
            phase_inputs=sources_ref, endpoint=saved, snapshots=[saved], failure=None)
    inventory = dict(schema="s04_e036_mechanism_score_inputs_v1", physics_manifest=physics_ref, target_manifest=target_ref,
                     cases=cases, job_wall_seconds=300)
    inv_ref = dump(tmp_path / "inventory.json", inventory)
    score_lock = dump(tmp_path / "score_lock.json", dict(schema="s04_e036_implementation_lock_v1",
        files={name: s.sha256(s.ROOT / name) for name in s.SOURCE_FILES | {"tools/s04_e036/score_mechanism_matrix.py"}}))
    score_authority = dict(mechanism_phase="score", job_wall_seconds=300, cumulative_resource_limit=None,
                           implementation_lock=score_lock, fem_validation=dummy, stage_a_semantic_binding=dummy)
    authority_ref = dump(tmp_path / "score_authority.json", score_authority)
    monkeypatch.setattr(s.runner, "check_authority", lambda *args: (score_authority, dict(source_kind="artificial_fixture")))
    monkeypatch.setattr(s.runner, "load_problem", lambda *args: (physics, tmp_path, p))
    monkeypatch.setattr(s.runner, "load_predecessor", lambda *args: (old, {}, dict(source_checkpoint=dict(sha256="a"*64))))
    monkeypatch.setattr(s.runner, "validate_stage_a_reuse", lambda *args: dict(status="artificial_fixture"))
    monkeypatch.setattr(s, "load_target", lambda *args, **kwargs: (copy.deepcopy(target), dict(snapshot_sha256=target_sha,
        native_solver_policy=dict(u_tol=1e-6, joint_tol=4e-4))))
    out = tmp_path / "score_output"
    s.main(SimpleNamespace(inventory=Path(inv_ref["path"]), authority=Path(authority_ref["path"]), out=out, device="cpu"))
    result = s.read_json(out / "scores.json")
    assert result["overall"]["status"] == "four_state_descriptive_mean"
    for state in result["states"].values():
        arm = state["matrix"]["Lplus"]["endpoint"]
        assert arm["approximation"]["J"] == pytest.approx(float(torch.tensor(.04, dtype=torch.float32)) / 3**.5)
        assert arm["approximation"]["G"] < 1e-16
        assert arm["physical_gap"]["same_old_state_exact"] is True
        assert arm["physical_gap"]["native_gp_errors"]["raw"]["absolute_rms"] == 0
        assert arm["physical_gap"]["native_gp_errors"]["active"]["absolute_rms"] > 0
        assert arm["physical_gap"]["reaction_errors"]["fresh_f_commit"]["top_xy"]["absolute_component_rms"] > 0
        assert arm["physical_accepted"] is False and arm["target_used_in_optimization"] is False
        assert state["factorial"]["effects"]["J"]["clamp_main_effect"] < 0
        assert state["target_fit"]["endpoint"]["representation_interpretation"]["capacity_sufficient_proven"] is False
    assert s.aggregate_effects({name: v for name, v in result["states"].items() if name != "c83s4"})["status"] == "unavailable"
    failed_arms = {a: v["endpoint"] for a, v in result["states"]["c1s2"]["matrix"].items()}
    failed_arms["C0"] = None
    assert s.factorial_effects(failed_arms)["status"] == "unavailable"
    for stem in ("mechanism_d", "mechanism_active", "mechanism_C_work", "mechanism_J_work"):
        assert (out / (stem + ".png")).stat().st_size > 1000
        assert (out / (stem + ".pdf")).stat().st_size > 1000
        assert "Data provenance" in (out / (stem + ".md")).read_text()
    assert s.read_json(out / "completion.json")["optimizer_updates"] == 0
