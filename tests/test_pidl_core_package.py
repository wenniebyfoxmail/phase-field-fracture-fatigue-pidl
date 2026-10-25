from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import pidl_core
from pidl_core.damage_conditioned_equilibrium import build_q4_kinematics
from pidl_core.material_properties import MaterialProperties


def test_public_package_exports_the_equilibrium_kernel() -> None:
    assert pidl_core.build_q4_kinematics is build_q4_kinematics

    points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    kinematics = pidl_core.build_q4_kinematics(points, cells)

    assert kinematics.b_matrices.shape == (1, 4, 3, 8)


def test_legacy_source_import_remains_the_same_implementation() -> None:
    from damage_conditioned_equilibrium import build_q4_kinematics as legacy_build

    assert legacy_build is build_q4_kinematics


def test_material_properties_are_exported_and_keep_the_legacy_entrypoint() -> None:
    from material_properties import MaterialProperties as legacy_properties

    material = pidl_core.MaterialProperties(210.0, 0.3, 2.0, 0.1)

    assert MaterialProperties is legacy_properties is pidl_core.MaterialProperties
    assert material() == (121.15384615384615, 80.76923076923076, 2.0, 0.1)
