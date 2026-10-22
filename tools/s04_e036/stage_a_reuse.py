"""Read-only reuse of Stage A evidence, scoped to actual operator semantics.

Control/scoring edits have their own production lock and tests. They do not
rewrite the old validation artifact, nor are they validated by this reuse.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from window_inputs import GP_ORDER, bound_file, read_json, sha256

PYTHON_OPERATORS = frozenset('source/' + name + '.py' for name in (
    'compute_energy', 'q4_quadrature', 'tri3_quadrature', 'fatigue_history',
    'material_properties', 'pff_model', 'cyclic_acceptance'))
FEM_FUNCTIONS = frozenset((
    'phase_field.System', 'phase_field.init.material_characteristic', 'phase_field.init.dofs',
    'phase_field.init.quadrature', 'phase_field.init.stiffness_matrix',
    'phase_field.fem.bc.set_boundaries', 'phase_field.fem.solver.params',
    'phase_field.fem.solver.step.params', 'phase_field.fem.solver.stag.params',
    'phase_field.fem.solver.newton_raphson', 'phase_field.fem.solver.step.pre_iter_update',
    'phase_field.fem.solver.stag.post_iter_update',
    'phase_field.mex.fem.assembly.equilibrium.initial',
    'phase_field.mex.fem.assembly.equilibrium.AMOR',
    'phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE',
    'e036_final_candidate', 'e036_native_candidate', 'e036_policy', 'cholmod2'))


def _digest_array(value, dtype):
    return hashlib.sha256(value.detach().cpu().numpy().astype(dtype).tobytes()).hexdigest()


def effective_physics_contract(problem):
    """Bind effective runtime values, not the hash of unrelated controller code."""
    x, cells, mat, model = problem.native_x, problem.cells, problem.mat, problem.model
    y = x[:, 1]
    ordered = hashlib.sha256(x.detach().cpu().numpy().astype('<f8').tobytes()
                             + cells.detach().cpu().numpy().astype('<i8').tobytes()).hexdigest()
    fatigue_keys = ('fatigue_on', 'loading_type', 'accum_type', 'degrad_type', 'alpha_T',
                    'history_storage', 'history_driver_mode', 'damage_history_storage',
                    'explicit_cycle_substeps', 'history_driver_reduction')
    return dict(schema='s04_e036_operator_contract_v1', ordered_mesh_sha256_f64_i64=ordered,
        node_count=len(x), cell_count=len(cells), gp_order=GP_ORDER,
        quadrature=dict(element='Q4',rule='2x2 Gauss-Legendre',reference_weights=[1.,1.,1.,1.]),
        geometry_dtype='float64', operator_readout_dtype='float64', thickness=1., stress_state='plane_strain',
        top_mask_sha256_u8=_digest_array(y == y.max(), 'uint8'),
        bottom_mask_sha256_u8=_digest_array(y == y.min(), 'uint8'),
        common_problem=problem.common,
        material=dict(E=float(mat.mat_E),nu=float(mat.mat_nu),w1=float(mat.w1),ell=float(mat.l0),
                      lame_lambda=float(mat.mat_lmbda),shear_mu=float(mat.mat_mu),eta=float(model.residual_stiffness),
                      phase_model=model.PFF_model,split=model.se_split,
                      gamma_ir=float(mat.w1 * model.irrPenalty())),
        penalty=problem.penalty, fatigue={name: problem.fatigue[name] for name in fatigue_keys},
        history_formula='A_trial=A_old+max(active_final-active_old,0); f(A_trial) detached for nodal residual',
        history_identity_fem=dict(atol=1e-10,rtol=0.))


def _same(actual, expected, name):
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError(f'Stage A {name} differs from the current semantic contract')


def _sha_map(values, required, name):
    if not isinstance(values, dict) or not required <= set(values):
        raise ValueError(f'incomplete Stage A {name}')
    if any(not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None for value in values.values()):
        raise ValueError(f'invalid Stage A {name} hash')


def validate_stage_a_reuse(validation_path, expected_path, root, problem):
    """Validate preserved evidence plus the audited old/current semantic maps."""
    validation_path, expected_path, root = map(Path, (validation_path, expected_path, root))
    validation, expected = read_json(validation_path), read_json(expected_path)
    if (validation.get('schema') != 's04_e036_fem_validation_v2'
            or validation.get('accepted') is not True or validation.get('stage_a_reexecuted') is not False
            or validation.get('stage_a_owner') != '01a1603e-8e80-7153-a753-d895b9edb7f5'
            or expected.get('schema') != 's04_e036_semantic_binding_v1'):
        raise ValueError('complete explicitly reused Stage A validation v2 is required')
    # The expected semantic binding is separately byte-bound by the new human
    # execution envelope; the original Stage A receipts remain unchanged.
    old = validation['semantic_binding']
    _same(old, expected, 'old/current semantic binding')
    _sha_map(old['python_operator_files'], PYTHON_OPERATORS, 'Python operator dependencies')
    _sha_map(old['fem_functions'], FEM_FUNCTIONS, 'actual FEM function bindings')
    _sha_map(old['fortran_sources'], set(), 'Fortran source map')
    _sha_map(old['mex_binaries'], set(), 'MEX binary map')
    if len(old['fortran_sources']) != 10 or not old['mex_binaries']:
        raise ValueError('Stage A requires all ten build sources and actual fresh MEX binaries')
    for relative, digest in old['python_operator_files'].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or sha256(path) != digest:
            raise ValueError(f'validated Python operator changed: {relative}')
    _same(effective_physics_contract(problem), old['physics_contract'], 'effective runtime values')
    artifacts = validation['evidence']
    required = {'prepare', 'disabled_transition_readback', 'frozen_c1', 'frozen_c20',
                'frozen_c60', 'frozen_c83', 'supervisor_chain', 'build_receipt', 'original_source_lock'}
    if not required <= set(artifacts):
        raise ValueError('Stage A reuse evidence is incomplete')
    for spec in artifacts.values():
        bound_file(spec, validation_path.parent)
    scopes = validation['validated_scopes']
    if (scopes.get('frozen_operator_equivalence') is not True
            or scopes.get('disabled_transition_readback') is not True):
        raise ValueError('Stage A operator and disabled-transition evidence are both required')
    return dict(accepted=True, validation_sha256=sha256(validation_path), semantic_binding_sha256=sha256(expected_path),
                stage_a_reexecuted=False, stage_a_owner=validation['stage_a_owner'], validated_scopes=scopes,
                not_validated_here=['new_PIDL_controller','new_PIDL_persistence','new_scoring'],
                scope='Operator semantic reuse only; separate production lock and tests cover new control/scoring code')
