from __future__ import annotations

import ast
import importlib
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
        "fem_mechanism_operator",
        "pidl_core.fem_mechanism_operator",
        "MultiScaleMeshResidualOperator",
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


def test_every_legacy_source_entrypoint_reexports_the_packaged_implementation() -> None:
    for legacy_name, packaged_name, symbol in BRIDGES:
        legacy = importlib.import_module(legacy_name)
        packaged = importlib.import_module(packaged_name)
        assert getattr(legacy, symbol) is getattr(packaged, symbol)


def test_packaged_modules_do_not_import_legacy_source_root_modules() -> None:
    legacy_names = {legacy_name for legacy_name, _, _ in BRIDGES}
    for _, packaged_name, _ in BRIDGES:
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
