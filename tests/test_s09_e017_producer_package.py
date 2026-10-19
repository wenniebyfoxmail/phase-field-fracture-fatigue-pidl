"""Artificial-fixture tests for the disabled S09-E017 producer package."""

# ruff: noqa: E402

import ast
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import s09_e017_producer_package as package


CONFIG_PATH = ROOT / "docs/research/S09/S09-E017/final_run_package_config_20261019.json"
SOURCE_PATH = ROOT / "source/s09_e017_producer_package.py"
RUNNER_PATH = ROOT / "scripts/run_s09_e017_producer.py"


def config_fixture():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class ArtificialAdapter:
    artificial_fixture = True

    def __init__(self, *, stop=None):
        self.counters = package.RuntimeCounters()
        self.stop = stop
        self._next_id = 1000

    def preflight(self):
        if self.stop == "preflight":
            raise package.FirstStop("IDENTITY_MISMATCH", None, 0, "artificial")
        return {
            "artificial_fixture": True,
            "identities_valid": True,
            "resources_valid": True,
            "scientific_assets_read": False,
        }

    def prepare_arm(self, arm):
        if self.stop == f"prepare:{arm}":
            raise package.FirstStop("PARAMETER_FREEZE_DRIFT", arm, 0, "artificial")
        names = {
            "D_DIRECT": ("direct_damage_head.weight", "direct_damage_head.bias"),
            "F_AMP": ("amplitude_residual.weight", "amplitude_residual.bias"),
            "F_AMP_SHAPE": (
                "amplitude_residual.weight",
                "amplitude_residual.bias",
                "shape_logits.weight",
                "shape_logits.bias",
            ),
        }[arm]
        ids = tuple(range(self._next_id, self._next_id + len(names)))
        self._next_id += len(names)
        self.counters.optimizer_constructions += 1
        return package.ArmStart(
            arm=arm,
            shared_state_sha256="a" * 64,
            trainable_names=names,
            frozen_names=("shared_trunk.weight", "non_damage_heads.weight"),
            parameter_object_ids=ids,
            optimizer_state_entries=0,
        )

    def evaluate(self, arm, update):
        self.counters.evaluations += 1
        self.counters.model_forwards += len(package.EXPECTED_CYCLES)
        return {
            "arm": arm,
            "update": update,
            "cycles": [
                {
                    "cycle": cycle,
                    "decision_vectors": {
                        "A": [0.1, 0],
                        "S": [0, 0.1, 0.2, 0.3, 0.4, 0.5],
                        "R": [0.1, 0.2],
                        "P": [0.1, 0.2, 0.3, 0.4],
                    },
                    "shape_raw_na_reason": None,
                    "shape_decision_imputed": False,
                    "finite": True,
                }
                for cycle in package.EXPECTED_CYCLES
            ],
        }

    def update(self, arm, update):
        if self.stop == f"update:{arm}:{update}":
            raise package.FirstStop("NONFINITE_VALUE", arm, update, "artificial")
        active = package.ACTIVE_GROUPS[arm]
        self.counters.model_forwards += len(package.EXPECTED_CYCLES)
        self.counters.autograd_collections += len(active)
        self.counters.backward_passes += len(active)
        self.counters.optimizer_steps += 1
        return {
            "arm": arm,
            "update": update,
            "active_groups": list(active),
            "finite": True,
            "hard_constraint_violations": 0,
            "raw_losses": {name: 0.1 for name in active},
            "raw_gradients": {name: [0.0] for name in active},
            "scaled_gradients": {name: [0.0] for name in active},
            "projected_gradients": {name: [0.0] for name in active},
            "frozen_scales": {name: 1.0 for name in active},
            "pairwise_geometry": [],
            "permutation": list(active),
            "projection_log": [],
            "preclip_norm": 0.0,
            "postclip_norm": 0.0,
            "raw_group_dot_realised_update": {name: 0.0 for name in active},
        }

    def checkpoint(self, arm, update):
        assert update == 64
        return f"artificial:{arm}:{update}".encode()

    def audit(self):
        return {
            "artificial_fixture": True,
            "hard_constraint_violations": 0,
            "factorisation_roundtrip_failures": 0,
            "scientific_claim": None,
        }


def test_config_freezes_mapping_physics_arms_budget_resources_and_disabled_launch():
    config = config_fixture()
    package.validate_package_config(config)
    assert config["mapping"]["autoregressive"] is False
    assert config["physics"]["beta"] == 0.25
    assert tuple(config["arms"]) == package.ARM_ORDER
    assert config["budget"]["total_update_cap"] == 192
    assert config["producer"]["reserved_memory_cap_bytes"] == 20 * 1024**3
    assert config["launch"]["wrapper_enabled"] is False


@pytest.mark.parametrize(
    ("mutation", "error", "match"),
    [
        (lambda c: c.update(execution_authorized=True), PermissionError, "disabled"),
        (
            lambda c: c["data"].update(cycles=list(reversed(c["data"]["cycles"]))),
            ValueError,
            "cycle order",
        ),
        (lambda c: c["physics"].update(beta=1.0), ValueError, "physics boundary"),
        (lambda c: c["budget"].update(total_update_cap=193), ValueError, "budget"),
        (
            lambda c: c["producer"].update(cuda_visible_devices="0"),
            ValueError,
            "producer envelope",
        ),
        (
            lambda c: c["bindings"].update(packet_loader="other:load"),
            ValueError,
            "binding",
        ),
        (
            lambda c: c["source"].update(producer_package_reviewed_commit="b" * 40),
            ValueError,
            "premature",
        ),
    ],
)
def test_config_fails_closed_on_identity_scope_or_authority_drift(
    mutation, error, match
):
    config = config_fixture()
    mutation(config)
    with pytest.raises(error, match=match):
        package.validate_package_config(config)


def test_binding_targets_are_real_source_symbols_without_resolving_or_importing_them():
    for reference in package.REAL_BINDINGS.values():
        module, name = reference.split(":", 1)
        if module == "torch.optim":
            assert name == "AdamW"
            continue
        path = ROOT / "source" / f"{module}.py"
        assert path.is_file(), reference
        tree = ast.parse(path.read_text(encoding="utf-8"))
        top_level = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        assert name in top_level, reference


def test_package_import_is_stdlib_only_and_has_no_eager_scientific_calls():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"torch", "numpy", "subprocess", "socket", "requests"})
    assert "importlib" in imported


def test_disabled_candidate_rejects_before_binding_resolution(monkeypatch):
    called = []
    monkeypatch.setattr(
        package.importlib, "import_module", lambda name: called.append(name)
    )
    with pytest.raises(PermissionError, match="execution_authorized is false"):
        package.resolve_real_bindings(
            config_fixture(), cli_flag=True, observed_commit="0" * 40
        )
    assert called == []


def test_disabled_launch_wrapper_stops_without_scientific_import_or_asset_arguments():
    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER_PATH),
            "--resolved-config",
            str(CONFIG_PATH),
            "--execute-reviewed-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "execution_authorized is false" in result.stderr
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert source.index("assert_launch_enabled(") < source.index(
        "resolve_real_bindings("
    )
    assert "--packet-dir" in source and "--initial-checkpoint" in source


def test_artificial_fixture_executes_exact_three_arm_budget_and_writes_closed_evidence(
    tmp_path
):
    adapter = ArtificialAdapter()
    output = tmp_path / "fixture"
    receipt = package.run_artificial_fixture(
        config=config_fixture(), adapter=adapter, output_root=output
    )
    assert receipt["terminal_state"] == "ARTIFICIAL_FIXTURE_COMPLETED"
    assert receipt["scientific_result_created"] is False
    assert receipt["completed_updates"] == {arm: 64 for arm in package.ARM_ORDER}
    assert receipt["last_complete_evaluation"] == {arm: 64 for arm in package.ARM_ORDER}
    assert adapter.counters.optimizer_constructions == 3
    assert adapter.counters.optimizer_steps == 192
    assert adapter.counters.evaluations == 18
    assert adapter.counters.autograd_collections == 704
    assert (output / "completion_receipt.json").is_file()
    inventory = json.loads((output / "inventory.json").read_text())
    assert "arms/F_AMP/metrics.jsonl" in inventory["files"]
    assert "arms/F_AMP_SHAPE/checkpoint_update64.fixture" in inventory["files"]


def test_first_stop_is_global_preserves_progress_and_does_not_retry(tmp_path):
    adapter = ArtificialAdapter(stop="update:F_AMP:4")
    receipt = package.run_artificial_fixture(
        config=config_fixture(), adapter=adapter, output_root=tmp_path / "stopped"
    )
    assert receipt["terminal_state"] == "ARTIFICIAL_FIXTURE_STOPPED"
    assert receipt["first_stop"]["reason"] == "NONFINITE_VALUE"
    assert receipt["first_stop"]["arm"] == "F_AMP"
    assert receipt["completed_updates"] == {
        "D_DIRECT": 64,
        "F_AMP": 3,
        "F_AMP_SHAPE": 0,
    }
    assert receipt["retry"] is False and receipt["alternate_gpu"] is False
    assert adapter.counters.optimizer_steps == 67


def test_preflight_stop_occurs_before_arm_optimizer_or_forward(tmp_path):
    adapter = ArtificialAdapter(stop="preflight")
    receipt = package.run_artificial_fixture(
        config=config_fixture(), adapter=adapter, output_root=tmp_path / "preflight"
    )
    assert receipt["first_stop"]["reason"] == "IDENTITY_MISMATCH"
    assert adapter.counters.optimizer_constructions == 0
    assert adapter.counters.model_forwards == 0
    assert adapter.counters.autograd_collections == 0
    assert adapter.counters.optimizer_steps == 0


def test_start_validation_rejects_cross_arm_parameter_aliasing_before_forward(tmp_path):
    class AliasedAdapter(ArtificialAdapter):
        def prepare_arm(self, arm):
            start = super().prepare_arm(arm)
            return replace(start, parameter_object_ids=(1,))

    adapter = AliasedAdapter()
    receipt = package.run_artificial_fixture(
        config=config_fixture(), adapter=adapter, output_root=tmp_path / "alias"
    )
    assert receipt["terminal_state"] == "ARTIFICIAL_FIXTURE_STOPPED"
    assert adapter.counters.model_forwards == 0
    assert adapter.counters.optimizer_steps == 0


def test_evidence_writer_is_canonical_hash_bound_and_write_once(tmp_path):
    writer = package.EvidenceWriter(tmp_path)
    value = {"finite": True, "count": 0}
    digest = writer.write_json("receipt.json", value)
    assert digest == package.sha256_bytes(package.canonical_json(value))
    assert (tmp_path / "receipt.json").read_bytes() == package.canonical_json(value)
    with pytest.raises(ValueError, match="already exists"):
        writer.write_json("receipt.json", value)
