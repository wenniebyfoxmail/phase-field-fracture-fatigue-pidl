#!/usr/bin/env python3
"""Compare one native frozen MAT state with two CPU float64 Python assemblies.

No field optimization, neural network, native solve, history commit or repair is
performed. The production energy derivative holds trial fatigue f detached; an
existing independent NumPy weak-form assembly is a second witness. Full and
free nodal forces are compared before any averaging. A failed comparison is
saved unchanged and exits nonzero; tolerances are not command-line options.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'e036_frozen_native_v1'
ATOL, RTOL = 1e-10, 1e-8
GP_ORDER = '(+,+),(-,+),(+,-),(-,-)'
MESH_DIGEST = 'c675e3fd05399cf16cc56884396f46b2af9e6b8e3c5c349e188246692d8bc174'
MATERIAL = dict(E=1., ni=.3, Gc=.01, ell=.01, res_stiff=0., alpha_T=.5, p=2.,
                penalty_irrev=421875., penalty_recov=13781.25, thickness=1.,
                stress_state='plane_strain', split_type='AMOR', diss_fct='AT1')
POLICY = dict(mode='nodal_box_kkt', joint_tol=4e-4, u_tol=1e-6, bounds_tol=1e-8,
              active_tol=1e-10, bc_tol=5e-8, history_atol=2e-6, history_rtol=2e-6)
SOURCE_PATHS = ('tools/s04_e036_fem/compare_frozen_states.py',
                'source/compute_energy.py', 'source/fatigue_history.py',
                'source/q4_quadrature.py', 'source/tri3_quadrature.py', 'source/cyclic_acceptance.py',
                'source/material_properties.py', 'source/pff_model.py',
                'tools/s04_e011_analysis/run_multicycle_cross_replay.py',
                'tools/s04_e011_analysis/audit_phase_tangent.py',
                'tools/s04_e011_analysis/localize_endpoint_tight.py',
                'tools/s04_e011_analysis/analyze_endpoint_tight.py',
                'tools/s04_e011_analysis/audit_fem_final_residuals.py',
                'tools/s04_e011_analysis/analyze_fem_staggered_endpoints.py')


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def check_hash(path, expected):
    actual = sha256(path)
    if not isinstance(expected, str) or len(expected) != 64 or actual != expected:
        raise ValueError(f'input SHA256 mismatch: {path}')
    return actual


def parse_json(text):
    def reject(value):
        raise ValueError(f'nonfinite JSON constant: {value}')
    return json.loads(text,parse_constant=reject)


def configure_threads(count):
    if type(count) is not int or not 1 <= count <= 4:
        raise ValueError('threads must be an integer in [1,4]')
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = str(count)
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['MPLBACKEND'] = 'Agg'
    import torch
    torch.set_num_threads(count)
    torch.set_num_interop_threads(count)


def _imports():
    # The imported tools have guarded CLI mains. Only the pure functions below
    # are called; none of their file/trajectory/plotting entrypoints is run.
    for directory in (ROOT / 'source', ROOT / 'tools/s04_e011_analysis'):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    import numpy as np
    return np


def read_native(path):
    """Read explicit root datasets; MATLAB v7.3 reverses numeric storage axes."""
    np = _imports()
    import h5py
    with h5py.File(path, 'r') as handle:
        def numeric(name):
            value = handle[name]
            if not isinstance(value, h5py.Dataset):
                raise ValueError(f'{name} must be a numeric dataset')
            raw = np.asarray(value)
            if raw.dtype.kind not in 'fiu':
                raise ValueError(f'{name} must be finite real numeric data')
            array = raw.transpose(tuple(reversed(range(raw.ndim)))).copy()
            # Old slot 1 is legacy storage, unused by this kernel. Preserve it
            # verbatim; only the incoming A/P/f channels define trial history.
            relevant = array[:,:,1:4] if name == 'old_history' and array.ndim == 3 else array
            if not np.isfinite(relevant).all():
                raise ValueError(f'{name} must have finite required numeric channels')
            return array

        def text(name):
            value = handle[name]
            if not isinstance(value, h5py.Dataset):
                raise ValueError(f'{name} must be a MATLAB char dataset')
            kind = value.attrs.get('MATLAB_class', b'')
            if isinstance(kind, bytes):
                kind = kind.decode('ascii')
            if kind != 'char':
                raise ValueError(f'{name} must use char, not an opaque MATLAB string object')
            return np.asarray(value, dtype='<u2').reshape(-1).tobytes().decode('utf-16-le')

        if text('schema') != SCHEMA:
            raise ValueError('unknown frozen-native schema')
        names = ('nodes', 'cells', 'u', 'd', 'old_lower', 'old_history', 'raw', 'Ru', 'Rd',
                 'trial_history', 'active_u', 'active_d', 'fixed_u', 'fixed_d',
                 'fixed_u_values', 'fixed_d_values', 'traction')
        state = {name: numeric(name) for name in names}
        for name in ('state_key', 'predecessor_key', 'material', 'provenance'):
            state[name] = parse_json(text(name + '_json'))
        state['quadrature'] = {name: numeric('quadrature/' + name)
                               for name in ('Nxi', 'dNdxi', 'gauss_W')}
    return state


def validate_state(state, common, *, production):
    np = _imports()
    points = np.asarray(state['nodes'])
    cells = np.asarray(state['cells'])
    if points.ndim != 2 or points.shape[1] != 2 or cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError('requires ordered XY nodes and Q4 connectivity')
    n, e = len(points), len(cells)
    if min(n, e) == 0 or (production and (n, e) != (86756, 86408)):
        raise ValueError('unsupported native mesh size')
    # The common digest uses float32 coordinates; assembly retains original f64.
    if points.dtype != np.float64:
        raise ValueError('native node coordinates must retain float64 precision')
    if not np.array_equal(cells, cells.astype(np.int64)):
        raise ValueError('connectivity is not integer-valued')
    cells = cells.astype(np.int64) - 1
    if cells.min() < 0 or cells.max() >= n or any(len(set(row)) != 4 for row in cells):
        raise ValueError('invalid MATLAB one-based connectivity')
    result = dict(state, nodes=points.copy(), cells=cells)
    shapes = dict(u=(2*n,), d=(n,), old_lower=(n,), old_history=(e,4,4), raw=(e,4),
                  Ru=(2*n,), Rd=(n,), trial_history=(e,4,4), traction=(2*n,))
    for name, shape in shapes.items():
        value = np.asarray(state[name])
        if len(shape) == 1:
            if value.ndim > 2 or (value.ndim == 2 and 1 not in value.shape):
                raise ValueError(f'{name} must be a vector')
            value = value.reshape(-1)
        relevant = value[:,:,1:4] if name == 'old_history' and value.ndim == 3 else value
        if value.shape != shape or value.dtype != np.float64 or not np.isfinite(relevant).all():
            raise ValueError(f'{name} must have native float64 shape {shape}')
        result[name] = value.copy()
    if not np.isfinite(points).all() or np.any(result['traction'] != 0):
        raise ValueError('requires finite geometry and the declared zero-traction problem')
    damage, lower = result['d'], result['old_lower']
    if (np.any((damage < 0) | (damage > 1)) or np.any((lower < 0) | (lower > 1))
            or np.any(damage < lower - POLICY['bounds_tol'])):
        raise ValueError('damage and predecessor lower bound violate the common physical domain')
    for name in ('old_history', 'trial_history'):
        history = result[name]
        if (np.any(history[:,:,1:3] < 0) or
                np.any((history[:,:,3] <= 0) | (history[:,:,3] > 1))):
            raise ValueError(f'{name} requires nonnegative A/P and fatigue f in (0,1]')
    for suffix, size in (('u', 2*n), ('d', n)):
        for prefix in ('active_', 'fixed_'):
            name = prefix + suffix
            value = np.asarray(state[name]).reshape(-1)
            if not np.isfinite(value).all() or not np.array_equal(value, value.astype(np.int64)):
                raise ValueError(f'{name} must be exact integer indices')
            result[name] = value.astype(np.int64) - 1
        joined = np.r_[result['active_' + suffix], result['fixed_' + suffix]]
        if not np.array_equal(np.sort(joined), np.arange(size)):
            raise ValueError(f'{suffix} DOFs must be a disjoint complete partition')
        target = np.asarray(state['fixed_' + suffix + '_values']).reshape(-1)
        if target.dtype != np.float64 or target.shape != result['fixed_' + suffix].shape or not np.isfinite(target).all():
            raise ValueError(f'invalid prescribed {suffix} values')
        result['fixed_' + suffix + '_values'] = target.copy()
        if not np.array_equal(result[suffix][result['fixed_' + suffix]], target):
            raise ValueError(f'actual {suffix} field does not match its exported prescribed values')
    if common.get('schema') != 's04_e036_common_problem_v1' or common.get('acceptance_config') != POLICY:
        raise ValueError('common acceptance policy differs from E036')
    if common.get('tol_ir') != .001 or common.get('recovery_penalty_coefficient') != 13781.25:
        raise ValueError('common penalties differ from E036')
    mesh_digest = hashlib.sha256(points.astype('<f4').tobytes() + cells.astype('<i8').tobytes()).hexdigest()
    if mesh_digest != common['ordered_mesh_sha256_f32_i64'] or (production and mesh_digest != MESH_DIGEST):
        raise ValueError('ordered mesh differs from common problem')
    expected_fixed = np.asarray(common['fixed_damage_nodes_zero_based'], dtype=np.int64)
    if not np.array_equal(np.sort(result['fixed_d']), np.sort(expected_fixed)):
        raise ValueError('damage DOFs differ from the common hard precrack')
    if common.get('fixed_damage_value') != 1. or np.any(result['fixed_d_values'] != 1.):
        raise ValueError('hard damage boundary is not exactly one')
    if production and (len(expected_fixed) != 251 or
                       not np.array_equal(np.sort(expected_fixed), np.r_[4,5,np.arange(695,944)])):
        raise ValueError('canonical hard precrack differs')
    if not isinstance(state['material'], dict):
        raise ValueError('native material, split, plane strain or unit thickness differs')
    for name, expected in MATERIAL.items():
        actual = state['material'].get(name)
        # Match the native adapter's metadata-roundoff allowance. This does
        # not change the separately fixed residual/GP comparison tolerances.
        same = (actual == expected) if isinstance(expected, str) else (
            isinstance(actual, (int, float)) and not isinstance(actual, bool)
            and np.isfinite(actual) and abs(actual-expected) <= 1e-12*max(1., abs(expected)))
        if not same:
            raise ValueError('native material, split, plane strain or unit thickness differs')
    key, oldkey = state['state_key'], state['predecessor_key']
    if production:
        for value, step, load in ((key, 4, .11999988), (oldkey, 3, .08999988)):
            if (type(value.get('cycle')) is not int or value['cycle'] not in (1,20,60,83)
                    or value.get('substep') != step or value.get('displacement') != load
                    or value.get('nominal_umax') != .12 or value.get('timing') != 'post_commit'
                    or value.get('gp_order') != GP_ORDER or not value.get('trajectory')):
                raise ValueError('state/predecessor key is outside the four declared Stage A states')
        if key['cycle'] != oldkey['cycle'] or key['trajectory'] != oldkey['trajectory']:
            raise ValueError('state and predecessor belong to different trajectories/cycles')
        y = points[:,1]; bottom, top = y == y.min(), y == y.max()
        expected_u = np.r_[np.flatnonzero(bottom|top), np.flatnonzero(bottom|top)+n]
        if not np.array_equal(np.sort(result['fixed_u']), np.sort(expected_u)):
            raise ValueError('displacement boundary DOFs differ from common SENT')
        ux, uy = result['u'][:n], result['u'][n:]
        if (np.max(abs(ux[bottom|top])) > POLICY['bc_tol'] or np.max(abs(uy[bottom])) > POLICY['bc_tol']
                or np.max(abs(uy[top]-key['displacement'])) > POLICY['bc_tol']):
            raise ValueError('actual displacement does not match physical state key')
    if not isinstance(state['provenance'], dict) or not state['provenance']:
        raise ValueError('native source/MEX/input provenance is required')
    # Compare the native reference-space quadrature independently of geometry.
    from run_multicycle_cross_replay import q4_geometry
    square = np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]])
    shape, deriv, weights, _ = q4_geometry(square, np.array([[0,1,2,3]]))
    q = state['quadrature']
    for name, expected in (('Nxi',shape.T), ('dNdxi',deriv[0].transpose(1,2,0)),
                           ('gauss_W',weights[0])):
        actual = np.asarray(q[name])
        if name == 'gauss_W':
            actual = actual.reshape(-1)
        if actual.shape != expected.shape or not np.isfinite(actual).all() or not np.allclose(actual,expected,rtol=0.,atol=1e-15):
            raise ValueError(f'native GP order/shape/weights differ: {name}')
    result['mesh_digest'] = mesh_digest
    return result


def assemble_numpy(state):
    np = _imports()
    from run_multicycle_cross_replay import q4_geometry, amor_raw
    from audit_phase_tangent import assemble
    from localize_endpoint_tight import mechanics_force
    nodes, cells, u, d = (state[k] for k in ('nodes','cells','u','d'))
    n = len(nodes)
    shape, deriv, weights, _ = q4_geometry(nodes, cells)
    raw = amor_raw(u[:n],u[n:],cells,deriv)
    rd, meta = assemble(d,raw,state['old_lower'],state['old_history'],cells,shape,deriv,weights,n)
    ru = mechanics_force(u,d,cells,shape,deriv,weights,n)-state['traction']
    return dict(Ru=ru,Rd=rd,raw=raw,P=meta['active'],A=meta['alpha'],f=meta['f'])


def assemble_energy(state):
    _imports()
    import torch
    from compute_energy import compute_energy, raw_strain_energy_density, get_psi_plus_per_elem
    from fatigue_history import update_fatigue_history, compute_fatigue_degrad
    from material_properties import MaterialProperties
    from pff_model import PFFModel
    from q4_quadrature import q4_shape_data, q4_gradient
    tensor = lambda a: torch.as_tensor(a, dtype=torch.float64, device='cpu')
    nodes, cells = tensor(state['nodes']), torch.as_tensor(state['cells'],dtype=torch.long)
    n = len(nodes)
    u,v,d = [tensor(a).clone().requires_grad_(True) for a in (state['u'][:n],state['u'][n:],state['d'])]
    oldd = tensor(state['old_lower']); old = tensor(state['old_history'])
    mat = MaterialProperties(1.,.3,1.,.01)
    pff = PFFModel('AT1','volumetric',.001,residual_stiffness=0.)
    fatigue = dict(loading_type='cyclic',accum_type='carrara',degrad_type='asymptotic',alpha_T=.5,
                   history_storage='q4_gp4',history_driver_reduction=dict(enable=True,mode='native_q4_gp4'))
    _, deriv, weights = q4_shape_data(nodes,cells)
    gu,gv = q4_gradient(u,cells,deriv),q4_gradient(v,cells,deriv)
    raw = raw_strain_energy_density(gu[...,0],gv[...,1],.5*(gu[...,1]+gv[...,0]),mat,pff)
    active = get_psi_plus_per_elem(nodes,u,v,d,mat,pff,weights.sum(1),cells,
                                  history_driver_reduction_dict=fatigue['history_driver_reduction']).detach()
    history = update_fatigue_history(old[:,:,1],active,old[:,:,2],fatigue)
    coefficient = compute_fatigue_degrad(history,fatigue).detach()
    energies = compute_energy(nodes,u,v,d,oldd,mat,pff,weights.sum(1),cells,f_fatigue=coefficient,
                              irreversibility_penalty_cfg=dict(enable=True,mode='fem_gp_q4',
                              spatial_integration='native_q4_gp4',recovery_penalty_coefficient=13781.25))
    force = torch.autograd.grad(sum(energies),(u,v,d),create_graph=False)
    fields = dict(Ru=torch.cat(force[:2])-tensor(state['traction']),Rd=force[2],raw=raw,
                  P=active,A=history,f=coefficient)
    return {k:v.detach().cpu().numpy().copy() for k,v in fields.items()}


def compare_channel(reference, candidate):
    np = _imports()
    reference, candidate = np.asarray(reference), np.asarray(candidate)
    if reference.shape != candidate.shape or not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise ValueError('comparison requires identical shapes and finite channels')
    difference = abs(candidate-reference)
    maximum = float(abs(reference).max()) if reference.size else 0.
    error = float(difference.max()) if reference.size else 0.
    tolerance = ATOL + RTOL*maximum
    return dict(shape=list(reference.shape),max_abs_reference=maximum,max_abs_difference=error,
                threshold=tolerance,passed=bool(error<=tolerance),
                worst_index=[int(x) for x in np.unravel_index(int(difference.argmax()),difference.shape)] if difference.size else None)


def compare_arrays(state, check_time=lambda: None):
    np = _imports()
    import torch
    from cyclic_acceptance import nodal_box_residual
    native = dict(Ru=state['Ru'],Rd=state['Rd'],raw=state['raw'],
                  P=state['trial_history'][:,:,2],A=state['trial_history'][:,:,1],f=state['trial_history'][:,:,3])
    check_time()
    implementations = dict(numpy=assemble_numpy(state))
    check_time()
    implementations['energy'] = assemble_energy(state)
    check_time()
    all_fields = dict(native=native,**implementations)
    for fields in all_fields.values():
        fields['Ru_free'] = fields['Ru'][state['active_u']]
        fields['Rd_free'] = fields['Rd'][state['active_d']]
        # Use the current E036 narrow-interval rule; the older audit helper
        # removed every doubly-active tolerance band and is not reused here.
        fields['Rd_box_free'] = nodal_box_residual(
            torch.from_numpy(state['d']),torch.from_numpy(fields['Rd']),
            torch.from_numpy(state['old_lower']),torch.ones_like(torch.from_numpy(state['d'])),
            POLICY['active_tol']).numpy()[state['active_d']]
    comparisons = {name:{key:compare_channel(native[key],fields[key]) for key in native}
                   for name,fields in implementations.items()}
    comparisons['numpy_vs_energy'] = {key:compare_channel(implementations['numpy'][key],
                                                         implementations['energy'][key]) for key in native}
    comparisons['native_history_identity'] = {
        'raw_slot_1':compare_channel(native['raw'],state['trial_history'][:,:,0]),
        'old_f_mapping':compare_channel(np.minimum(1.,(1./(state['old_history'][:,:,1]+.5))**2),
                                       state['old_history'][:,:,3])}
    passed = all(item['passed'] for group in comparisons.values() for item in group.values())
    return dict(passed=passed,channels=comparisons),implementations


def run(input_path, input_sha256, common_path, common_sha256, output, *, threads=1):
    output = Path(output)
    output.mkdir(exist_ok=False)  # Never overwrite an earlier success or failure.
    report = dict(schema='e036_frozen_comparison_v1',status='failed',passed=False,
                  started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  scope='frozen field software equivalence; no solve, optimization, acceptance or commit',
                  tolerance=dict(atol=ATOL,rtol=RTOL,formula='maxabsdiff <= atol + rtol*maxabsref'),
                  host=platform.node(),platform=sys.platform,threads=threads,input=str(Path(input_path).resolve()),
                  requested_input_sha256=input_sha256,common_problem=str(Path(common_path).resolve()))
    start = time.monotonic()
    def check_time():
        if time.monotonic()-start > 600:
            raise RuntimeError('ten-minute frozen comparison limit reached; no retry or continuation')
    try:
        configure_threads(threads)
        np = _imports()
        import torch
        import h5py
        report['versions'] = dict(python=sys.version,executable=sys.executable,numpy=np.__version__,
                                  torch=torch.__version__,h5py=h5py.__version__)
        report['input_sha256'] = check_hash(input_path,input_sha256)
        report['common_problem_sha256'] = check_hash(common_path,common_sha256)
        report['source_sha256'] = {name:sha256(ROOT/name) for name in SOURCE_PATHS}
        common = parse_json(Path(common_path).read_text())
        raw_state = read_native(input_path)
        if sys.platform == 'darwin' and len(raw_state['nodes']) > 64:
            raise RuntimeError('Mac is development-only: full-mesh frozen assembly must run on the authorized producer')
        state = validate_state(raw_state,common,production=True)
        report.update(state_key=state['state_key'],predecessor_key=state['predecessor_key'],
                      native_provenance=state['provenance'],ordered_mesh_sha256_f32_i64=state['mesh_digest'])
        comparison,fields = compare_arrays(state,check_time)
        with (output/'python_fields.npz').open('xb') as stream:
            np.savez_compressed(stream,**{name+'_'+key:value for name,values in fields.items() for key,value in values.items()})
        report['python_fields_sha256'] = sha256(output/'python_fields.npz')
        check_hash(input_path,input_sha256);check_hash(common_path,common_sha256)
        if report['source_sha256'] != {name:sha256(ROOT/name) for name in SOURCE_PATHS}:
            raise RuntimeError('Python source changed during comparison')
        check_time()
        report.update(comparison,status='matched' if comparison['passed'] else 'difference_exceeds_fixed_tolerance')
    except Exception as error:
        report.update(status='input_or_comparison_error',error_type=type(error).__name__,error=str(error),
                      traceback=traceback.format_exc())
    report['wall_seconds'] = time.monotonic()-start
    report['ended_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    with (output/'comparison.json').open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--input-sha256',required=True)
    parser.add_argument('--common-problem',type=Path,required=True)
    parser.add_argument('--common-problem-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=1,choices=range(1,5))
    args = parser.parse_args()
    report = run(args.input,args.input_sha256,args.common_problem,args.common_problem_sha256,args.output,threads=args.threads)
    print(json.dumps({k:report[k] for k in ('status','passed','wall_seconds')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
