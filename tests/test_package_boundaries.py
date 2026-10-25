from __future__ import annotations

import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))


BRIDGES = (
    (
        "damage_conditioned_equilibrium",
        "pidl_core.damage_conditioned_equilibrium",
        "build_q4_kinematics",
    ),
    (
        "material_properties",
        "pidl_core.material_properties",
        "MaterialProperties",
    ),
    (
        "damage_state_inversion",
        "fracture_state.damage_state_inversion",
        "amplify_damage",
    ),
    (
        "spatial_degradation_reconstruction",
        "fracture_state.spatial_degradation_reconstruction",
        "reconstruct_damage",
    ),
    (
        "damage_observation_reconstruction",
        "fracture_observation.damage_observation_reconstruction",
        "at1_profile",
    ),
    (
        "fem_mechanism_assimilation",
        "fracture_assimilation.fem_mechanism_assimilation",
        "assimilate_state",
    ),
    (
        "paper_style",
        "fracture_visuals.paper_style",
        "method_style",
    ),
)


FROZEN_LEGACY_ENTRYPOINT = (
    "fem_mechanism_operator",
    "pidl_core.fem_mechanism_operator",
    "MultiScaleMeshResidualOperator",
)
D1_MATRIX_LOCK = (
    ROOT / "docs" / "experiments" / "at1_fatigue_mesh_pino_d1_matrix_lock_20260826.json"
)


def test_mutable_legacy_source_entrypoints_reexport_the_packaged_implementation() -> None:
    for legacy_name, packaged_name, symbol in BRIDGES:
        legacy = importlib.import_module(legacy_name)
        packaged = importlib.import_module(packaged_name)
        assert getattr(legacy, symbol) is getattr(packaged, symbol)


def test_frozen_legacy_operator_remains_locked_and_has_a_packaged_counterpart() -> None:
    legacy_name, packaged_name, symbol = FROZEN_LEGACY_ENTRYPOINT
    legacy = importlib.import_module(legacy_name)
    packaged = importlib.import_module(packaged_name)
    lock = json.loads(D1_MATRIX_LOCK.read_text(encoding="utf-8"))
    legacy_path = ROOT / "source" / f"{legacy_name}.py"

    assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == lock["code_sha256"][
        "operator_dependency"
    ]
    assert getattr(legacy, symbol).__name__ == getattr(packaged, symbol).__name__
    assert legacy.STATE_NAMES == packaged.STATE_NAMES


def test_packaged_modules_do_not_import_legacy_source_root_modules() -> None:
    legacy_names = {
        *(legacy_name for legacy_name, _, _ in BRIDGES),
        FROZEN_LEGACY_ENTRYPOINT[0],
    }
    packaged_names = [
        *(packaged_name for _, packaged_name, _ in BRIDGES),
        FROZEN_LEGACY_ENTRYPOINT[1],
    ]
    for packaged_name in packaged_names:
        source = (ROOT / "source" / Path(*packaged_name.split("."))).with_suffix(".py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported_names = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_from = {
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for legacy_name in legacy_names:
            assert legacy_name not in imported_names
            assert legacy_name not in imported_from
