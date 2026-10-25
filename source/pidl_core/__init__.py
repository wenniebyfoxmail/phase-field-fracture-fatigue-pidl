"""Stable, lightweight public interface for reusable PIDL mechanics kernels.

Only modules whose dependencies and behaviour are independently tested belong
here.  Experiment runners and dataset-specific adapters remain outside this
package so they do not become implicit package requirements.
"""

from .damage_conditioned_equilibrium import (
    EquilibriumResult,
    Q4Kinematics,
    assemble_amor_stiffness,
    build_q4_kinematics,
    element_to_nodal_damage,
    equilibrium_internal_force,
    plane_strain_tensors,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
    tensile_energy,
)
from .material_properties import MaterialProperties

__all__ = [
    "EquilibriumResult",
    "MaterialProperties",
    "Q4Kinematics",
    "assemble_amor_stiffness",
    "build_q4_kinematics",
    "element_to_nodal_damage",
    "equilibrium_internal_force",
    "plane_strain_tensors",
    "sens_displacement_boundary_conditions",
    "solve_amor_equilibrium",
    "tensile_energy",
]
