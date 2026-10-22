"""One fixed, complete artificial I/O case; no network or physical operator."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/s04_e036'))
import prepare_gap_inputs as prep


def test_complete_tiny_io_to_separate_d3_d4_and_fit_manifests(tmp_path, monkeypatch):
    root = tmp_path / 'saved'
    root.mkdir()
    mesh_sha = 'a' * 64
    trajectory = 'artificial_io_fixture_not_numerically_admitted'
    monkeypatch.setattr(prep, 'N_NODES', 4)
    monkeypatch.setattr(prep, 'N_ELEMENTS', 1)
    contract, contract_ref = prep.runner_contract()

    def record(path):
        return dict(path=str(path), sha256=prep.sha256(path))

    def raw(name, data=b'synthetic native evidence; no numerical meaning'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return record(path)

    def doc(name, value):
        return raw(name, (json.dumps(value, indent=2) + '\n').encode())

    def predecessor(name, key, source):
        path = root / (name + '.npz')
        np.savez(path, u=np.zeros(4), v=np.zeros(4), damage=np.zeros(4), history=np.zeros((1, 4)),
            active_driver=np.zeros((1, 4)), f_commit=np.ones((1, 4)),
            state_key_json=json.dumps(key), ordered_mesh_sha256_f32_i64=mesh_sha,
            source_checkpoint_sha256=source['sha256'], preparation_json='{}')
        return record(path)

    def admitted(name, key, source, pre, **extra):
        return doc(name + '.json', dict(schema='s04_e036_predecessor_admission_v1', accepted=True,
            native_residual_checked=True, checkpoint_readback_verified=True, state_key=key,
            solver_policy=prep.STANDARD_POLICY, ordered_mesh_sha256_f32_i64=mesh_sha,
            predecessor_sha256=pre['sha256'], source_checkpoint=source,
            native_residual_evidence=raw(name + '_native.mat'),
            checkpoint_readback_evidence=raw(name + '_readback.mat'), **extra))

    inventory = dict(schema='s04_e036_pidl_readiness_v1', mesh_source=raw('mesh.npz'),
        common_problem_source=doc('common.json', dict(schema='s04_e036_common_problem_v1',
                                                     ordered_mesh_sha256_f32_i64=mesh_sha)), cases={})
    exports = {}
    original_admissions = {}
    for case, (cycle, steps) in prep.CASES.items():
        oldkey = prep.predecessor_key(trajectory, cycle, steps[0])
        source = raw(case + '_old.mat', case.encode())
        prior = predecessor(case + '_old', oldkey, source)
        network = raw(case + '_network.pt', ('synthetic weights ' + case).encode())
        monkeypatch.setitem(prep.D3_NETWORK_SHA, case, network['sha256'])
        inventory['cases'][case] = dict(predecessor_key=oldkey, source_checkpoint=source,
            conversion=dict(output=prior['path'], sha256=prior['sha256']), network=network)
        old_admission = admitted(case + '_old_admission', oldkey, source, prior)
        target_map, pre_map = {}, {}
        for step in steps:
            key = prep.state_key(trajectory, cycle, step)
            checkpoint = raw(f'{case}_s{step}.mat', f'{case}:{step}'.encode())
            path = root / f'{case}_s{step}.npz'
            np.savez(path, **{name: np.zeros(4) for name in ('u', 'v', 'd', 'old_damage')},
                **{name: np.zeros((1, 4)) for name in ('history', 'active_driver', 'f_solve', 'f_commit',
                                                    'old_history', 'old_active_driver')},
                state_key_json=json.dumps(key), predecessor_key_json=json.dumps(prep.predecessor_key(trajectory, cycle, step)),
                ordered_mesh_sha256_f32_i64=mesh_sha, source_checkpoint_sha256=checkpoint['sha256'],
                predecessor_checkpoint_sha256=source['sha256'])
            snap = record(path)
            admission = doc(f'{case}_s{step}_admission.json', dict(schema='s04_e036_target_admission_v1',
                accepted=True, native_residual_checked=True, checkpoint_readback_verified=True,
                state_key=key, predecessor_key=prep.predecessor_key(trajectory, cycle, step),
                solver_policy=prep.STANDARD_POLICY, ordered_mesh_sha256_f32_i64=mesh_sha,
                snapshot_sha256=snap['sha256'], source_checkpoint=checkpoint, predecessor_checkpoint=source,
                native_residual_evidence=raw(f'{case}_s{step}_native.mat'),
                checkpoint_readback_evidence=raw(f'{case}_s{step}_readback.mat'),
                completion_evidence=raw(f'{case}_s{step}_completion.mat'), reference_role='main'))
            original_admissions[admission['path']] = admission['sha256']
            slot = f'c{cycle}/s{step}'
            target_map[slot] = dict(snapshot=snap, admission=admission)
            as_pre = predecessor(f'{case}_s{step}_as_old', key, checkpoint)
            as_admission = admitted(f'{case}_s{step}_as_old_admission', key, checkpoint, as_pre,
                                   original_target_admission=admission, new_native_calls=0, history_commits=0)
            pre_map[slot] = dict(predecessor=as_pre, admission=as_admission)
            source = checkpoint
        result = doc(case + '_run_result.json', dict(status='completed', history_commits=len(steps),
            request=dict(role='main', cycle=cycle, substeps=list(steps))))
        exports[case] = doc(case + '_targets.json', dict(schema='s04_e036_fem_targets_v1', targets=target_map,
            as_predecessors=pre_map, predecessor_admission=old_admission, run_result=result,
            input_binding=raw(case + '_input_binding.mat')))
    rows = []
    for name, (cycle, step) in contract['CASES'].items():
        network = raw(name + '_canonical.pt', ('synthetic D4 weights ' + name).encode())
        contract['NETWORK_SHA'][name] = network['sha256']
        rows.append(dict(case=name, step=5*(cycle-1)+step-1, **network, available=True, all_finite=True,
                         size=Path(network['path']).stat().st_size, parameter_count=1125211, dtypes=['torch.float32']))
    monkeypatch.setattr(prep, 'runner_contract', lambda: (contract, contract_ref))
    request = dict(schema='s04_e036_gap_input_request_v1', input_inventory=doc('inventory.json', inventory),
        network_inventory=doc('network_inventory.json', dict(cases=rows)), main_exports=exports,
        path_map=[dict(source_root=str(root), local_root=str(root), producer_root='/producer/saved')],
        producer_output_root='/producer/prepared',
        budget=dict(updates_per_block=200, max_updates_per_step=2000, max_outer=10,
                    step_wall_seconds=123, job_wall_seconds=456, cumulative_resource_limit=None),
        mechanism_job_wall_seconds=789)
    request_ref = doc('request.json', request)
    output = tmp_path / 'prepared'
    result = prep.build(request_ref['path'], request_ref['sha256'], output)
    assert result['solver_execution'] is False and result['new_native_admission'] is False
    d3, d4, fit = [json.loads((output / name).read_text()) for name in
                  ('d3_inputs.json', 'd4_inputs.json', 'd4_targets.json')]
    assert d3['schema'] == prep.SCHEMA and set(d3['cases']) == set(prep.CASES)
    assert d3['budget'] == request['budget']
    assert set(d4) == {'schema', 'trajectory', 'mesh', 'common_problem', 'cases', 'solver', 'job_wall_seconds'}
    assert 'target' not in json.dumps(d4) and 'target' not in json.dumps(d3)
    assert set(fit['targets']) == set(contract['CASES'])
    assert fit['physics_manifest']['sha256'] == prep.sha256(output / 'd4_inputs.json')
    assert fit['physics_manifest']['path'] == '/producer/prepared/d4_inputs.json'
    assert d4['cases']['c83s4']['network']['sha256'] == contract['NETWORK_SHA']['c83s4']
    mapped = json.loads((output / 'admissions/c83_s3_as_old.json').read_text())
    assert mapped['state_key']['substep'] == 3
    assert mapped['source_checkpoint']['path'].startswith('/producer/saved/')
    assert mapped['path_relocation']['scope'].startswith('path-only')
    assert all(prep.sha256(path) == digest for path, digest in original_admissions.items())
    assert len(json.loads((output / 'd3_targets_catalog.json').read_text())['targets']) == 12
    assert (output / 'prepared.json').is_file()
    # Same fixed case: removal of a real required input must publish nothing.
    Path(exports['c83']['path']).unlink()
    rejected = tmp_path / 'missing_input_attempt'
    with pytest.raises(ValueError, match='missing local bytes'):
        prep.build(request_ref['path'], request_ref['sha256'], rejected)
    assert not rejected.exists()
