"""One reviewed R001 -> R002 recovery; no implicit retry or state synthesis.

Only copy hash-verified complete accepted states. Never recompute consumed
steps, promote trial payloads, delete a source lock or amend the failed run.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from hybrid_history import trial_history
from hybrid_producer_common import write_json, append_event, object_sha
from hybrid_state_contract import verify_expected, verify_transition
from hybrid_transaction import StateStore

SOURCE_ROOT = '/mnt/data2/drtao/wennie/S04-E027-SYNMEM-R001'
SOURCE_CODE = 'e8ac73f6ead57fbb0c795d862abc682c9435901f'
COUNTS = dict(base_low=106, base_high=106, space_low=40, space_high=1)
TASK_START = 1792532920


def read(path):
    return json.loads(Path(path).read_text())


def verify_recovery(spec, continuation, output):
    """Read-only manifest and authority admission, before the R002 reservation."""
    c = continuation
    source = Path(c['source_root'])
    if (str(source) != SOURCE_ROOT or str(Path(output)) != SOURCE_ROOT[:-1]+'2'
            or c['source_code'] != SOURCE_CODE or c['prior_attempts'] != 253
            or c['deadline_epoch'] != TASK_START + spec['budget']['wall_seconds']
            or c['counts'] != COUNTS or c['revision_index'] != 1
            or not c.get('hq_authorization') or not c.get('independent_recovery_review')
            or type(c['prior_output_bytes']) is not int or c['prior_output_bytes'] < 36612446):
        raise RuntimeError('outside one exact cumulative-budget recovery authority')
    manifest_path = Path(c['manifest_path'])
    if manifest_path != Path('/mnt/data2/drtao/wennie/pf_synmem_stage_e8ac73f6_20261020/retrieval_manifest.json'):
        raise RuntimeError('unapproved recovery manifest path')
    data = manifest_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != c['manifest_sha256']:
        raise RuntimeError('recovery manifest digest mismatch')
    manifest = json.loads(data)
    expected = set()
    for entry in manifest['files']:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() in expected:
            raise RuntimeError('unsafe or duplicate recovery member')
        path = source/relative
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise RuntimeError('recovery symlink is forbidden')
        payload = path.read_bytes()
        if len(payload) != entry['bytes'] or hashlib.sha256(payload).hexdigest() != entry['sha256']:
            raise RuntimeError('changed recovery member: '+str(relative))
        expected.add(relative.as_posix())
    if any(p.is_symlink() for p in source.rglob('*')):
        raise RuntimeError('recovery tree contains an extra symlink')
    actual = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    if actual != expected or len(expected) != manifest['file_count']:
        raise RuntimeError('recovery file set differs')
    if (read(source/'spec.json') != spec or read(source/'receipt.json')['code_commit'] != SOURCE_CODE
            or read(source/'progress.json')['attempted_steps'] != c['prior_attempts']
            or read(source/'supervisor_terminal.json')['state'] != 'failed'
            or read(source/'supervisor_terminal.json')['error'] != "FileNotFoundError(2, 'No such file or directory')"
            or list(source.glob('*/failure.json')) or (source/'result.json').exists()
            or (source/'current_match.json').exists() or list(source.glob('future*.npz'))):
        raise RuntimeError('R001 is not the reviewed control-only incomplete attempt')
    for pid in (read(source/'receipt.json')['pid'], read(source/'process.json')['pid']):
        if Path('/proc', str(pid)).exists():
            raise RuntimeError('original producer PID exists; reconcile before recovery')
    return source


def validate_prefix(t, source, count):
    """Validate the complete causal chain and fresh certificates, without solve."""
    source = Path(source)
    if object_sha(read(source/'pair_contract.json')) != object_sha(asdict(t.pair)):
        raise RuntimeError('recovery pair contract differs')
    if read(source/'schedule.json') != [asdict(s) for s in t.schedule]:
        raise RuntimeError('recovery schedule differs')
    with np.load(source/'mesh.npz', allow_pickle=False) as m:
        for key, value in dict(points=t.mesh.points, cells=t.mesh.cells, crack=t.mesh.crack,
                               dofs=t.dofs, unit=t.unit).items():
            if not np.array_equal(m[key], value):
                raise RuntimeError('recovery mesh/boundary differs')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise RuntimeError('recovery trajectory contains symlink')
    if (source/'failure.json').exists():
        raise RuntimeError('cannot resume a scientific failure')
    latest, lm = StateStore(source/'latest.npz').load()
    if latest.load_index != count or count > t.origin:
        raise RuntimeError('unexpected recovered prefix length')
    paths = sorted((source/'states').glob('state*.npz'))
    expected = [f'state{i:04d}.npz' for i in range(count+1)]
    if [p.name for p in paths] not in (expected, expected[:-1]):
        raise RuntimeError('recovery snapshots have gaps or extras')
    states = []
    for index in range(count+1):
        path = source/'states'/f'state{index:04d}.npz'
        if not path.exists():
            if index != count: raise RuntimeError('missing interior accepted state')
            path = source/'latest.npz'
        state, meta = StateStore(path).load()
        verify_expected(state, meta, t.context(state, index))
        if index == 0:
            if state.fingerprint() != t.old.fingerprint():
                raise RuntimeError('different declared initial state')
        else:
            old, om, _ = states[-1]
            verify_transition(old, om, state, meta)
            cert, settings = meta['certificate'], t.settings
            damage, force = cert['damage'], cert['mechanics']
            scalars = [damage[k] for k in ('primal_inf','kkt_scaled_inf','kkt_l2','projected_inf')]
            scalars += [force[k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')]
            scalars += [cert['fatigue_residual']]
            if (not np.isfinite(scalars).all() or min(scalars) < 0
                    or damage['primal_inf'] > settings.bound_tolerance
                    or max(damage['kkt_scaled_inf'],damage['projected_inf']) > settings.damage_tolerance
                    or force['force_scaled'] > settings.force_tolerance
                    or force['force_l2'] > settings.force_tolerance*settings.force_scale
                    or force['force_l2']+damage['kkt_l2'] > settings.joint_residual_sum_tolerance
                    or force['boundary_inf'] > settings.bound_tolerance
                    or cert['fatigue_residual'] > settings.fatigue_tolerance
                    or state.version != old.version + 1
                    or np.any(state.damage < old.damage) or np.any(state.accumulated < old.accumulated)
                    or not np.array_equal(state.opaque, old.opaque)):
                raise RuntimeError('recovered accepted-state validity failed')
            load = t.schedule[index-1]
            if (state.load_id != f'{load.trajectory_id}:{load.step}:{load.prescribed_load:.17g}'
                    or not np.array_equal(state.displacement[t.dofs], t.unit*load.prescribed_load)):
                raise RuntimeError('recovered load differs')
            with np.load(path, allow_pickle=False) as payload:
                psi = payload['evidence_psi_raw_commit_gp']
            gp = (t.backend.gp @ state.damage).reshape(state.fatigue.shape)
            expected_history = trial_history(old, gp, psi, alpha_t=t.spec['material']['alpha_t'],
                                             power=t.spec['material']['power'])
            for key in ('accumulated','driver','fatigue'):
                if not np.array_equal(getattr(state,key),getattr(expected_history,key)):
                    raise RuntimeError('recovered history field differs: '+key)
        states.append((state,meta,path))
    if latest.fingerprint() != states[-1][0].fingerprint() or lm != states[-1][1]:
        raise RuntimeError('latest does not equal terminal accepted snapshot')
    rows = [json.loads(s) for s in (source/'steps.jsonl').read_text().splitlines()]
    if len(rows) not in (count, count-1):
        raise RuntimeError('recovery event ledger is incomplete beyond final commit')
    for index, row in enumerate(rows,1):
        if (row['load'] != asdict(t.schedule[index-1])
                or row['state_id'] != states[index][0].fingerprint()
                or row['certificate'] != states[index][1]['certificate']):
            raise RuntimeError('recovery event differs from accepted payload')
    return states, rows


def recover_prefixes(trajectories, continuation, output):
    """Reconcile all four prefixes before admitting any new step; source read-only."""
    prepared = []
    for pair in trajectories:
        for t in pair:
            if t.path.name in COUNTS:
                source=Path(continuation['source_root'])/t.path.name
                states,rows=validate_prefix(t,source,COUNTS[t.path.name])
                prepared.append((t,source,states,rows))
    if len(prepared)!=4 or sum(len(s)-1 for _,_,s,_ in prepared)!=253:
        raise RuntimeError('accepted prefix debit differs from 253 consumed attempts')
    reports=[]
    for t,source,states,rows in prepared:
        for name in ('steps.jsonl','work_trace.jsonl'):
            shutil.copy2(source/name,t.path/name)
        for index,(_,_,path) in enumerate(states):
            shutil.copy2(path,t.state_path(index))
        shutil.copy2(source/'latest.npz',t.store.path)
        t.old,meta=t.store.load()
        verify_expected(t.old,meta,t.context(t.old,t.old.load_index))
        recovered_log = len(rows)<t.old.load_index
        if recovered_log:
            append_event(t.path/'steps.jsonl',dict(load=asdict(t.schedule[t.old.load_index-1]),
                state_id=t.old.fingerprint(),wall_seconds=None,
                f_min=float(t.old.fatigue.min()),A_max=float(t.old.accumulated.max()),
                certificate=meta['certificate'],recovered_durable_commit=True,
                note='Original latest.npz was accepted; SIGTERM preceded snapshot/event. No new solve; whole-step wall unavailable.'))
        reports.append(dict(trajectory=t.path.name,accepted_prefix=t.old.load_index,
                            state_id=t.old.fingerprint(),recovered_terminal_log=recovered_log))
    write_json(Path(output)/'recovery_receipt.json',dict(source=continuation['source_root'],
               prior_attempts=253,reused_accepted_states=253,new_solves_for_recovery=0,
               trajectories=reports,source_modified=False))
