#!/usr/bin/env python3
"""Read-only conversion of completed E036 FEM windows to scorer inputs.

No native evaluation is performed here. Hash-bound native residual vectors are
reduced again, and proposal/checkpoint/predecessor arrays are compared exactly.
The scorer independently reassembles the fields in its native Q4 operator.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 's04_e036'))
from prepare_predecessor import _mat_array as arr, _mat_integer as integer, _mat_text as text, _mat_object
from window_inputs import sha256, state_key

MESH_SHA = 'c675e3fd05399cf16cc56884396f46b2af9e6b8e3c5c349e188246692d8bc174'


def require(test, message):
    if not test:
        raise ValueError(message)


def record(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha256(path))


def equal(a, b, label):
    require(np.array_equal(a, b), f'{label} differs from exact saved source')


def scalar(h, name):
    a = arr(h, name)
    require(a.size == 1, f'{name} must be scalar')
    return float(a.item())


def key_from_mat(h, prefix):
    key = {name: text(h, f'{prefix}/{name}') for name in ('trajectory', 'timing', 'gp_order')}
    key.update({name: integer(h, f'{prefix}/{name}') for name in ('cycle', 'substep')})
    key.update({name: scalar(h, f'{prefix}/{name}') for name in ('nominal_umax', 'displacement')})
    require(key == state_key(key['trajectory'], key['cycle'], key['substep']), 'noncanonical physical state key')
    return key


def reduce_residual(u, d, lower, ru, rd, free_u, free_d, joint_tol, u_tol):
    """The exact native nodal-box rule; narrow noncollapsed boxes retain raw."""
    require(np.isfinite(u).all() and np.isfinite(d).all() and np.isfinite(lower).all()
            and np.isfinite(ru).all() and np.isfinite(rd).all(), 'nonfinite state/residual')
    require(np.all((lower >= 0) & (lower <= 1)) and np.all((d >= 0) & (d <= 1) & (d >= lower - 1e-8)),
            'physical/healing feasibility failed')
    q = rd[free_d].copy()
    lo = d[free_d] <= lower[free_d] + 1e-10
    hi = d[free_d] >= 1 - 1e-10
    both = lo & hi
    q[lo & ~both] = np.minimum(q[lo & ~both], 0)
    q[hi & ~both] = np.maximum(q[hi & ~both], 0)
    q[lower[free_d] == 1] = 0
    ur, dr, kr = map(float, (np.linalg.norm(ru[free_u]), np.linalg.norm(rd[free_d]), np.linalg.norm(q)))
    criterion = max((ur + kr) / joint_tol, ur / u_tol)
    require(criterion <= 1, 'saved fresh native residual fails declared policy')
    return dict(u_free_l2=ur, d_raw_free_l2=dr, d_nodal_box_l2=kr, criterion=criterion)


def source_arrays(path, kind):
    import h5py
    with h5py.File(path, 'r') as h:
        if kind == 'stored_u0':
            return arr(h, 'common/u').reshape(-1), arr(h, 'common/d').reshape(-1), arr(h, 'common/history')
        if kind == 'request28_post_commit':
            require(all(integer(h, 'request28_snapshot/' + x) == 1 for x in
                        ('damage_committed', 'history_committed', 'cyclemax_updated')), 'source not committed')
            uv = arr(h, 'request28_snapshot/u_node')
            return uv.T.reshape(-1), arr(h, 'request28_snapshot/d_node').reshape(-1), arr(h, 'request28_snapshot/history_vars_old')
        require(kind == 'verified_window_step', 'unsupported predecessor schema')
        d = arr(h, 'p_field').reshape(-1)
        equal(d, arr(h, 'p_field_old').reshape(-1), 'predecessor lower')
        return arr(h, 'displ').reshape(-1), d, arr(h, 'history_vars_old')


def checked_policy(h, role, prefix='e036_audit'):
    jt, ut = (4e-6, 1e-8) if role == 'tightening' else (4e-4, 1e-6)
    expected = {'joint_tol': jt, 'u_tol': ut, 'bound_tol': 1e-8, 'active_tol': 1e-10, 'history_tol': 1e-10}
    for name, value in expected.items():
        require(scalar(h, prefix + '/policy/' + name) == value, 'actual native policy differs')
    material = {'E': 1, 'ni': .3, 'Gc': .01, 'ell': .01, 'res_stiff': 0, 'alpha_T': .5,
                'p': 2, 'penalty_irrev': 421875, 'penalty_recov': 13781.25}
    for name, value in material.items():
        require(scalar(h, prefix + '/policy/expected_material/' + name) == value, 'native material policy differs')
    return dict(u_tol=ut, joint_tol=jt)


def convert_step(folder, predecessor_path, predecessor_kind, support, role, output, window_row):
    import h5py
    paths = {name: folder / filename for name, filename in dict(proposal='proposal.mat',
             checkpoint='step_checkpoint.mat', readback='readback.mat', completion='completion.mat').items()}
    if role=='nodal_oracle':
        paths['initial_candidate']=folder/'initial_candidate.mat'
    refs = {name: record(path) for name, path in paths.items()}
    prior_ref = record(predecessor_path)
    bound_names=('proposal','checkpoint','readback','initial_candidate') if role=='nodal_oracle' else ('proposal','checkpoint','readback')
    for name in bound_names:
        require(refs[name]['sha256']==window_row[name+'_sha256'],'step is not bound to completed window row: '+name)
    with h5py.File(paths['completion'], 'r') as h:
        key = key_from_mat(h, 'completion/state_key')
        require(key==window_row['state_key'],'completion physical key differs from requested window row')
        require(integer(h, 'completion/history_commits') == 1, 'completion must record one commit')
        version = (key['cycle'] - 1) * 5 + key['substep']
        require(integer(h, 'completion/version') == version and integer(h, 'completion/pre_version') == version - 1,
                'completion version differs')
        for name in bound_names:
            require(text(h, f'completion/{name}_sha256') == refs[name]['sha256'], 'completion hash differs')
        if role=='nodal_oracle':
            require(text(h,'completion/initial_candidate')=='initial_candidate.mat','unexpected oracle initial filename')
            for name in ('declared_initial_fields_sha256','initial_source_snapshot_sha256','initial_source_completion_sha256'):
                require(text(h,'completion/'+name)==window_row[name],'oracle source differs from window row')
            binding=support.get('oracle_binding')
            require(isinstance(binding,dict) and binding.get('initial_fields_sha256')==window_row['declared_initial_fields_sha256']
                and binding.get('initial_source_snapshot_sha256')==window_row['initial_source_snapshot_sha256']
                and binding.get('initial_source_completion_sha256')==window_row['initial_source_completion_sha256'],
                'oracle source differs from persisted input authority')
    with h5py.File(paths['proposal'], 'r') as h:
        require(text(h, 'e036_status') == 'validated_proposal_before_native_assignment', 'unaccepted proposal')
        old_key = key_from_mat(h, 'e036_old/state_key')
        expected_c, expected_s = key['cycle'], key['substep'] - 1
        if expected_s == 0 and expected_c > 1:
            expected_c, expected_s = expected_c - 1, 5
        require(old_key == state_key(key['trajectory'], expected_c, expected_s), 'wrong predecessor key')
        policy = checked_policy(h, role)
        u, d = arr(h, 'e036_proposal/u').reshape(-1), arr(h, 'e036_proposal/d').reshape(-1)
        hist, raw = arr(h, 'e036_proposal/history'), arr(h, 'e036_proposal/raw')
        old_u, lower, old_hist = arr(h, 'e036_old/u').reshape(-1), arr(h, 'e036_old/lower').reshape(-1), arr(h, 'e036_old/history')
        n, e = len(support['nodes']), len(support['cells'])
        require(u.shape == (2*n,) and d.shape == lower.shape == (n,) and hist.shape == old_hist.shape == (e,4,4),
                'native field support differs')
        for a in (u, d, hist, raw, old_u, lower, old_hist):
            require(a.dtype == np.float64 and np.isfinite(a).all(), 'native arrays must be finite float64')
        equal(d, arr(h, 'e036_proposal/lower').reshape(-1), 'proposal lower')
        for name, a in (('u', u), ('d', d)):
            equal(a, arr(h, 'e036_audit/' + name).reshape(-1), 'audit ' + name)
        equal(raw, arr(h, 'e036_audit/raw'), 'audit raw')
        equal(raw, hist[:,:,0], 'current kernel raw history channel')
        equal(hist[:,:,3], arr(h, 'e036_audit/f_commit'), 'commit coefficient')
        f_solve = arr(h, 'e036_audit/f_solve')
        require(np.max(np.abs(f_solve - hist[:,:,3])) <= 1e-10 and
                np.max(np.abs(arr(h, 'e036_audit/history234_solve') - hist[:,:,1:4])) <= 1e-10,
                'solve/commit history mismatch')
        require(all(integer(h, 'e036_audit/' + x) == 1 for x in ('joint_pass','feasible')), 'native audit rejected')
        require(integer(h, 'e036_audit/old_version') == integer(h, 'e036_old/version') ==
                integer(h, 'e036_proposal/pre_version') == version-1 and
                integer(h, 'e036_proposal/version') == version, 'proposal version differs')
        require(np.all(old_hist[:,:,1:3] >= 0) and np.all(hist[:,:,:3] >= 0), 'negative history/driver')
        driver = (1 - d[support['cells']] @ support['Nxi'])**2 * raw
        expected_A = old_hist[:,:,1] + np.maximum(driver - old_hist[:,:,2], 0)
        for actual, expected, label in ((hist[:,:,2], driver, 'active driver'),
                (hist[:,:,1], expected_A, 'single history update'),
                (hist[:,:,3], np.minimum(1, (1/(expected_A+.5))**2), 'fatigue coefficient'),
                (old_hist[:,:,3], np.minimum(1, (1/(old_hist[:,:,1]+.5))**2), 'old fatigue coefficient')):
            require(np.max(np.abs(actual-expected)) <= 1e-10, label + ' differs')
        ru, rd = arr(h, 'e036_audit/ru').reshape(-1), arr(h, 'e036_audit/rd').reshape(-1)
        require(ru.shape == u.shape and rd.shape == d.shape, 'native residual shape differs')
        metrics = reduce_residual(u,d,lower,ru,rd,support['free_u'],support['free_d'],**policy)
        for name, value in metrics.items():
            require(np.isclose(scalar(h, 'e036_audit/' + name), value, atol=1e-13, rtol=1e-12),
                    'saved native residual reduction differs')
    # The old fields must come from the named immutable source, not a replacement.
    su, sd, sh = source_arrays(predecessor_path, predecessor_kind)
    for a,b,label in ((old_u,su,'old u'),(lower,sd,'old d'),(old_hist,sh,'old history')):
        equal(a,b,label)
    check_bc(u,d,key,support)
    with h5py.File(paths['checkpoint'], 'r') as h:
        require(integer(h, 'SOL_CYCL_VAR/n_cycle') == key['cycle'] and integer(h, 'i_step_completed') == key['substep'],
                'checkpoint physical key differs')
        for name, expected in (('displ',u),('p_field',d),('p_field_old',d),('history_vars_old',hist)):
            actual=arr(h,name)
            equal(actual.reshape(-1) if expected.ndim==1 else actual,expected,'checkpoint '+name)
    with h5py.File(paths['readback'], 'r') as h:
        require(text(h, 'readback/status') == 'accepted_step_readback_matches_proposal', 'readback rejected')
        for name in ('proposal','checkpoint'):
            require(text(h, 'readback/' + name + '_sha256') == refs[name]['sha256'], 'readback hash differs')
        require(integer(h, 'readback/cycle') == key['cycle'] and integer(h,'readback/substep') == key['substep'] and
                integer(h,'readback/version') == version, 'readback key differs')
    arrays=dict(u=u[:n],v=u[n:],d=d,history=hist[:,:,1],active_driver=hist[:,:,2],f_solve=f_solve,
                f_commit=hist[:,:,3],old_damage=lower,old_history=old_hist[:,:,1],old_active_driver=old_hist[:,:,2])
    output.mkdir(parents=True, exist_ok=False)
    snapshot=output/'snapshot.npz'
    np.savez(snapshot,**arrays,state_key_json=json.dumps(key,sort_keys=True),
             predecessor_key_json=json.dumps(old_key,sort_keys=True),ordered_mesh_sha256_f32_i64=MESH_SHA,
             source_checkpoint_sha256=refs['checkpoint']['sha256'],predecessor_checkpoint_sha256=prior_ref['sha256'])
    admission=dict(schema='s04_e036_nodal_oracle_admission_v1' if role=='nodal_oracle' else 's04_e036_target_admission_v1',accepted=True,native_residual_checked=True,
         checkpoint_readback_verified=True,state_key=key,predecessor_key=old_key,solver_policy=policy,
         snapshot_sha256=sha256(snapshot),ordered_mesh_sha256_f32_i64=MESH_SHA,
         source_checkpoint=refs['checkpoint'],predecessor_checkpoint=prior_ref,
         native_residual_evidence=refs['proposal'],checkpoint_readback_evidence=refs['readback'],
         completion_evidence=refs['completion'],native_residual_reduction=metrics,
         reference_role=role,
         converter_scope='saved native vectors reduced again; no new assembly/solve; scorer independently reassembles')
    if role=='nodal_oracle':
        initial_ref=refs['initial_candidate']
        with h5py.File(initial_ref['path'],'r') as h:
            require(key_from_mat(h,'projection/state_key')==key and
                    text(h,'projection/predecessor_checkpoint_sha256')==prior_ref['sha256'],
                    'oracle initial state/predecessor differs')
            iu,id_=arr(h,'initial_fields/u').reshape(-1),arr(h,'initial_fields/d').reshape(-1)
            pu,pd=arr(h,'projection/projected_u').reshape(-1),arr(h,'projection/projected_d').reshape(-1)
            equal(iu,arr(h,'projection/raw_u').reshape(-1),'oracle raw u')
            equal(id_,arr(h,'projection/raw_d').reshape(-1),'oracle raw d')
            expected_d=np.minimum(np.maximum(id_,lower),1);expected_d[support['fixed_d']]=1
            expected_u=iu.copy();expected_u[np.r_[support['bot'],support['top']]]=0
            expected_u[n+support['bot']]=0;expected_u[n+support['top']]=key['displacement']
            equal(pu,expected_u,'oracle projected u');equal(pd,expected_d,'oracle projected d')
            projection_metrics=dict(u_max_abs_change=float(np.max(abs(pu-iu))),u_l2_change=float(np.linalg.norm(pu-iu)),
                d_max_abs_change=float(np.max(abs(pd-id_))),d_l2_change=float(np.linalg.norm(pd-id_)))
            for name,value in projection_metrics.items():
                require(np.isclose(scalar(h,'projection/'+name),value,atol=1e-13,rtol=1e-12),'oracle projection metric differs')
            admission['oracle_source_snapshot_sha256']=text(h,'projection/source_snapshot_sha256')
            admission['oracle_source_completion_sha256']=text(h,'projection/source_completion_sha256')
            for field,declared in (('source_snapshot_sha256','initial_source_snapshot_sha256'),
                                   ('source_completion_sha256','initial_source_completion_sha256')):
                require(text(h,'projection/'+field)==text(h,'initial_fields/'+field)==window_row[declared],
                        'oracle recorded source is not bound to completed window/authority')
        require(sha256(initial_ref['path'])==initial_ref['sha256'],'oracle initial record changed')
        admission['initial_candidate_evidence']=initial_ref
        admission['initial_projection']=projection_metrics
    admission_path=output/'admission.json';admission_path.write_text(json.dumps(admission,indent=2)+'\n')
    for name,path in paths.items():
        require(sha256(path)==refs[name]['sha256'],'source changed during conversion')
    require(sha256(predecessor_path)==prior_ref['sha256'],'predecessor changed during conversion')
    return dict(snapshot=record(snapshot),admission=record(admission_path))


def export_as_predecessor(target, output):
    """Repackage an accepted main F1 endpoint; no native call or new commit."""
    snapshot,admission=Path(target['snapshot']['path']),Path(target['admission']['path'])
    require(sha256(snapshot)==target['snapshot']['sha256'] and sha256(admission)==target['admission']['sha256'],
            'F1 target export changed before predecessor conversion')
    receipt=json.loads(admission.read_text())
    require(receipt['schema']=='s04_e036_target_admission_v1' and receipt['reference_role']=='main' and
            all(receipt[k] is True for k in ('accepted','native_residual_checked','checkpoint_readback_verified')),
            'only an accepted main F1 endpoint becomes a D4 predecessor')
    su,sd,sh=source_arrays(receipt['source_checkpoint']['path'],'verified_window_step')
    with np.load(snapshot,allow_pickle=False) as z:
        key=json.loads(str(z['state_key_json'].item()));n=len(z['d'])
        require(key==receipt['state_key'] and np.all(z['d']>=z['old_damage']),
                'main F1 endpoint must have exact no-healing for predecessor reuse')
        arrays=dict(u=z['u'].copy(),v=z['v'].copy(),damage=z['d'].copy(),history=z['history'].copy(),
                    active_driver=z['active_driver'].copy(),f_commit=z['f_commit'].copy())
    for name,expected in dict(u=su[:n],v=su[n:],damage=sd,history=sh[:,:,1],active_driver=sh[:,:,2],f_commit=sh[:,:,3]).items():
        require(arrays[name].dtype==np.float64,'F1 predecessor conversion must retain native float64')
        equal(arrays[name],expected,'as-predecessor '+name)
    for name in ('source_checkpoint','native_residual_evidence','checkpoint_readback_evidence','completion_evidence'):
        r=receipt[name];require(sha256(r['path'])==r['sha256'],'F1 native evidence changed before predecessor conversion')
    output.mkdir(parents=True,exist_ok=False);npz=output/'predecessor.npz'
    preparation=dict(schema='s04_e036_predecessor_preparation_v1',source_kind='verified-main-F1-step',
        native_timing='post_commit',state_key=key,inputs=target,status='same_verified_endpoint_repackaged',
        new_native_calls=0,history_commits=0)
    np.savez(npz,**arrays,state_key_json=json.dumps(key,sort_keys=True),
        ordered_mesh_sha256_f32_i64=MESH_SHA,source_checkpoint_sha256=receipt['source_checkpoint']['sha256'],
        preparation_json=json.dumps(preparation,sort_keys=True))
    result=dict(schema='s04_e036_predecessor_admission_v1',accepted=True,native_residual_checked=True,
        checkpoint_readback_verified=True,predecessor_sha256=sha256(npz),state_key=key,
        ordered_mesh_sha256_f32_i64=MESH_SHA,solver_policy=receipt['solver_policy'],
        source_checkpoint=receipt['source_checkpoint'],native_residual_evidence=receipt['native_residual_evidence'],
        checkpoint_readback_evidence=receipt['checkpoint_readback_evidence'],completion_evidence=receipt['completion_evidence'],
        original_target_admission=target['admission'],new_native_calls=0,history_commits=0,
        admission_basis='verified accepted main F1 endpoint; exact source arrays and existing fresh final native check/readback reused; no new zero-increment assembly')
    path=output/'admission.json';path.write_text(json.dumps(result,indent=2)+'\n')
    return dict(predecessor=record(npz),admission=record(path))


def load_support(path):
    import h5py
    with h5py.File(path,'r') as h:
        p='authority/binding/'
        nodes=arr(h,p+'nodes');raw_cells=arr(h,p+'cells');cells=raw_cells.astype(np.int64)-1
        require(nodes.shape==(86756,2) and cells.shape==(86408,4) and np.array_equal(raw_cells,cells+1), 'wrong mesh shape')
        digest=hashlib.sha256(nodes.astype('<f4').tobytes()+cells.astype('<i8').tobytes()).hexdigest()
        require(digest==MESH_SHA,'ordered mesh differs')
        Nxi=arr(h,p+'Nxi');require(Nxi.shape==(4,4),'Q4 shape functions differ')
        # Check GP order explicitly; do not trust a copied label.
        a=1/np.sqrt(3);xi=np.array([a,-a,a,-a]);eta=np.array([a,a,-a,-a])
        expected=np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])/4
        require(np.max(abs(Nxi-expected))<=1e-14,'Q4 basis/GP order differs')
        free_u=arr(h,p+'active_u').reshape(-1).astype(int)-1
        free_d=arr(h,p+'active_d').reshape(-1).astype(int)-1
        fixed_d=np.array([4,5,*range(695,944)])
        bot=np.flatnonzero(nodes[:,1]==nodes[:,1].min());top=np.flatnonzero(nodes[:,1]==nodes[:,1].max())
        fixed_u=np.r_[bot,top,bot+len(nodes),top+len(nodes)]
        equal(np.sort(free_u),np.setdiff1d(np.arange(2*len(nodes)),fixed_u),'free mechanical DOFs')
        equal(np.sort(free_d),np.setdiff1d(np.arange(len(nodes)),fixed_d),'free phase DOFs')
        oracle_binding=None
        authority=_mat_object(h,'authority')
        if 'initial_fields_sha256' in authority:
            oracle_binding={name:text(h,'authority/'+name) for name in
                ('initial_fields_sha256','initial_source_snapshot_sha256','initial_source_completion_sha256')}
    return dict(nodes=nodes,cells=cells,Nxi=Nxi,free_u=free_u,free_d=free_d,bot=bot,top=top,fixed_d=fixed_d,
                oracle_binding=oracle_binding)


def check_bc(u,d,key,support):
    n=len(d);bot,top=support['bot'],support['top']
    require(np.all(d[support['fixed_d']]==1) and np.max(abs(u[np.r_[bot,top]]))<=5e-8 and
            np.max(abs(u[n+bot]))<=5e-8 and np.max(abs(u[n+top]-key['displacement']))<=5e-8,'native BC mismatch')


def convert_predecessor(folder, source, source_kind, npz_path, support, output):
    """Bind an existing float64 NPZ to actual saved native admission/readback."""
    import h5py
    refs = {name: record(folder / filename) for name, filename in dict(
        native='native_admission.mat', packet='admitted_predecessor.mat', report='admission_report.mat').items()}
    source_ref, npz_ref = record(source), record(npz_path)
    su, sd, sh = source_arrays(source, source_kind)
    with h5py.File(refs['packet']['path'], 'r') as h:
        key = key_from_mat(h, 'pre/state_key')
        for name, expected in (('u',su),('d',sd),('lower',sd),('history',sh)):
            actual = arr(h,'pre/'+name)
            equal(actual.reshape(-1) if expected.ndim == 1 else actual,expected,'admitted preimage '+name)
        for name in ('accepted','native_residual_checked','checkpoint_readback_verified'):
            require(integer(h,'pre/admission/'+name)==1,'native predecessor admission rejected')
        require(text(h,'pre/admission/predecessor_sha256')==source_ref['sha256'],'wrong admitted source bytes')
    with h5py.File(refs['report']['path'], 'r') as h:
        require(text(h,'report/status')=='admitted_current_native_predecessor' and
                text(h,'report/packet_sha256')==refs['packet']['sha256'] and
                integer(h,'report/native_solves')==integer(h,'report/history_commits')==0,
                'native admission readback report differs')
        require(text(h,'report/source/sha256')==source_ref['sha256'],'admission source hash differs')
    with h5py.File(refs['native']['path'], 'r') as h:
        policy=checked_policy(h,'main',prefix='audit')
        equal(su,arr(h,'audit/u').reshape(-1),'admission u')
        equal(sd,arr(h,'audit/d').reshape(-1),'admission d')
        raw=arr(h,'audit/raw')
        driver=(1-sd[support['cells']] @ support['Nxi'])**2*raw
        require(np.max(abs(driver-sh[:,:,2]))<=1e-10,'predecessor saved active driver differs')
        require(np.max(abs(sh[:,:,3]-np.minimum(1,(1/(sh[:,:,1]+.5))**2)))<=1e-10,
                'predecessor saved fatigue law differs')
        ru,rd=arr(h,'audit/ru').reshape(-1),arr(h,'audit/rd').reshape(-1)
        require(ru.shape==su.shape and rd.shape==sd.shape,'admission residual support differs')
        metrics=reduce_residual(su,sd,sd,ru,rd,support['free_u'],support['free_d'],**policy)
        for name,value in metrics.items():
            require(np.isclose(scalar(h,'audit/'+name),value,atol=1e-13,rtol=1e-12),'admission residual reduction differs')
        require(integer(h,'audit/joint_pass')==integer(h,'audit/feasible')==1,'native admission rejected')
    check_bc(su,sd,key,support)
    n=len(sd)
    with np.load(npz_path,allow_pickle=False) as z:
        require(json.loads(str(z['state_key_json'].item()))==key and str(z['source_checkpoint_sha256'].item())==source_ref['sha256']
                and str(z['ordered_mesh_sha256_f32_i64'].item())==MESH_SHA,'NPZ provenance differs')
        for name,expected in dict(u=su[:n],v=su[n:],damage=sd,history=sh[:,:,1],active_driver=sh[:,:,2],f_commit=sh[:,:,3]).items():
            require(z[name].dtype==np.float64,'predecessor NPZ must retain float64')
            equal(z[name],expected,'NPZ '+name)
    receipt=dict(schema='s04_e036_predecessor_admission_v1',accepted=True,native_residual_checked=True,
        checkpoint_readback_verified=True,predecessor_sha256=npz_ref['sha256'],state_key=key,
        ordered_mesh_sha256_f32_i64=MESH_SHA,source_checkpoint=source_ref,
        native_residual_evidence=refs['native'],checkpoint_readback_evidence=refs['packet'],
        native_report=refs['report'],solver_policy=policy,native_residual_reduction=metrics,
        scope='existing predecessor; no solve, recovery, history update or projection')
    for r in (*refs.values(),source_ref,npz_ref):
        require(sha256(r['path'])==r['sha256'],'admission input changed during verification')
    with output.open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    return record(output)


def read_window_rows(path, request, trajectory):
    """Decode MATLAB struct-array references; bind every requested published row."""
    import h5py
    steps=np.atleast_1d(request['substeps']).tolist();count=len(steps)
    with h5py.File(path,'r') as h:
        require(text(h,'result/status')=='completed' and integer(h,'result/history_commits')==count,
                'saved window is not completed')
        require(integer(h,'result/request/cycle')==request['cycle'] and
                text(h,'result/request/role')==request['role'] and
                arr(h,'result/request/substeps').reshape(-1).tolist()==steps,'saved window request differs')
        rows=_mat_object(h,'result/rows')
        require(isinstance(rows,h5py.Group),'saved rows must be a native MATLAB struct array')
        def field_path(name,index):
            require(name in rows,'completed window row lacks '+name)
            value=rows[name]
            if isinstance(value,h5py.Dataset) and h5py.check_dtype(ref=value.dtype) is not None:
                refs=np.asarray(value).reshape(-1)
                require(len(refs)==count and bool(refs[index]),'native row reference count differs')
                return h[refs[index]].name
            require(count==1,'multirow MATLAB struct requires one field reference per row')
            return value.name
        result=[]
        for index,step in enumerate(steps):
            key=key_from_mat(h,field_path('state_key',index))
            require(key==state_key(trajectory,request['cycle'],step),'window row physical key differs')
            require(integer(h,field_path('history_commits',index))==1,'window row must commit exactly once')
            row=dict(state_key=key,**{name+'_sha256':text(h,field_path(name+'_sha256',index))
                for name in ('proposal','checkpoint','readback')})
            if request['role']=='nodal_oracle':
                require(text(h,field_path('initial_candidate',index))=='initial_candidate.mat','unknown oracle initial filename')
                row.update({name:text(h,field_path(name,index)) for name in ('initial_candidate_sha256',
                    'declared_initial_fields_sha256','initial_source_snapshot_sha256','initial_source_completion_sha256')})
            result.append(row)
    require(len({json.dumps(r['state_key'],sort_keys=True) for r in result})==count,'duplicate window rows')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-result',required=True,type=Path);p.add_argument('--run-result-sha256',required=True)
    p.add_argument('--window',required=True,type=Path);p.add_argument('--predecessor',required=True,type=Path)
    p.add_argument('--predecessor-npz',type=Path,help='existing converted input; required for main windows')
    p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    require(sha256(args.run_result)==args.run_result_sha256,'run result hash differs')
    report=json.loads(args.run_result.read_text());request=report['request']
    require(report['status']=='completed','only completed windows may export')
    steps=np.atleast_1d(request['substeps']).tolist();cycle=request['cycle'];role=request['role']
    require((role=='main' and ((cycle in (1,83) and steps==[1,2,3,4,5]) or (cycle in (20,60) and steps==[4]))) or
            (role in ('tightening','nodal_oracle') and cycle in (1,83) and steps in ([2],[4])),'undeclared target request')
    require(report['history_commits']==len(steps),'window commit count differs')
    require(sha256(args.window/'window_result.mat')==report['window_result_sha256'],'window result differs')
    spec=report['admission']['source'];require(sha256(args.predecessor)==spec['sha256'],'wrong incoming source')
    rows=read_window_rows(args.window/'window_result.mat',request,spec['state_key']['trajectory'])
    support=load_support(args.window/'input_binding.mat');kind=spec['kind'];previous=args.predecessor
    require(not args.output.exists(),'never replace exports');args.output.mkdir(parents=True)
    predecessor_admission=None
    if role=='main':
        require(args.predecessor_npz is not None,'main windows require their pre-existing predecessor NPZ')
        predecessor_admission=convert_predecessor(args.window.parent/'predecessor',previous,kind,
            args.predecessor_npz,support,args.output/'predecessor_admission.json')
    targets={};as_predecessors={}
    for step,row in zip(steps,rows):
        folder=args.window/f'c{cycle:04d}_s{step:02d}'
        target=convert_step(folder,previous,kind,support,role,args.output/f'c{cycle}_s{step}',row)
        targets[f'c{cycle}/s{step}']=target
        if role=='main':
            as_predecessors[f'c{cycle}/s{step}']=export_as_predecessor(target,args.output/f'c{cycle}_s{step}'/'as_predecessor')
        previous=folder/'step_checkpoint.mat';kind='verified_window_step'
    (args.output/'targets.json').write_text(json.dumps(dict(schema='s04_e036_fem_oracle_targets_v1' if role=='nodal_oracle' else 's04_e036_fem_targets_v1',targets=targets,
        run_result=record(args.run_result),input_binding=record(args.window/'input_binding.mat'),
        predecessor_admission=predecessor_admission,as_predecessors=as_predecessors),indent=2)+'\n')


if __name__=='__main__':
    main()
