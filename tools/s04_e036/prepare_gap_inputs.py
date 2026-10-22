#!/usr/bin/env python3
"""Pure-I/O manifests from complete main FEM-B exports; never admit or solve.

Reads hashes, JSON, NPZ headers and small identity metadata only. Original
receipts remain unchanged. Producer-path admissions are explicit derivatives.
"""
from __future__ import annotations

import argparse
import ast
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile

import numpy as np

from window_inputs import CASES, SCHEMA, read_json, sha256, state_key, predecessor_key, validate_budget

ROOT = Path(__file__).resolve().parents[2]
N_NODES, N_ELEMENTS = 86756, 86408
STANDARD_POLICY = dict(u_tol=1e-6, joint_tol=4e-4)
D3_NETWORK_SHA = {
    'c1': '653222915cb35dccd2fb2abfd25928e12e3a7dd53a128afc9cfec27a7727686b',
    'c83': '02417bddab7e413de8fe7b2a07b86682d9f526d49221c2de976b8a2baeb813ae',
    'c20s4': 'e0acd981b8c6d69be9b88d676088b8a026448ee24f28ec231ecdd5c266edd69f',
    'c60s4': 'b2de308fac8282d48fe3a2d4d77004b03702f47bc04363e249651540f9946b30',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def same(first, second, reason):
    require(json.dumps(first, sort_keys=True, allow_nan=False) ==
            json.dumps(second, sort_keys=True, allow_nan=False), reason)


def digest_ok(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def native_path(value):
    require(isinstance(value, str) and bool(value), 'explicit absolute source path required')
    value = value.replace('\\', '/').rstrip('/')
    require(value.startswith('/') or re.match(r'^[A-Za-z]:/', value), 'absolute source path required')
    require('..' not in value.split('/'), 'parent traversal is forbidden')
    return value


class PathBindings:
    """An explicit source→local bytes→producer route, with no remote IO."""
    def __init__(self, mappings):
        require(isinstance(mappings, list) and bool(mappings), 'explicit path mappings required')
        self.routes, self.records, self.destinations = [], {}, {}
        for entry in mappings:
            require(set(entry) == {'source_root', 'local_root', 'producer_root'}, 'invalid path-map fields')
            source = native_path(entry['source_root'])
            local = Path(entry['local_root'])
            producer = native_path(entry['producer_root'])
            require(local.is_absolute() and producer.startswith('/'), 'local/producer roots must be absolute POSIX paths')
            self.routes.append((source, local.resolve(), producer))

    def bind(self, spec):
        require(isinstance(spec, dict) and set(spec) == {'path', 'sha256'} and digest_ok(spec['sha256']),
                'every file requires an explicit path and actual SHA256')
        source = native_path(spec['path'])
        matched = []
        for prefix, local, producer in self.routes:
            # Windows paths are case insensitive; POSIX paths are not.
            a, b = (source.casefold(), prefix.casefold()) if re.match(r'^[A-Za-z]:/', prefix) else (source, prefix)
            if a == b or a.startswith(b + '/'):
                suffix = source[len(prefix):].lstrip('/')
                path = (local / suffix).resolve()
                require(path.is_relative_to(local), 'mapped local path escaped its root')
                matched.append((path, str(PurePosixPath(producer) / suffix)))
        require(len(matched) == 1, 'missing or ambiguous explicit path mapping: ' + source)
        local, producer = matched[0]
        require(local.is_file() and sha256(local) == spec['sha256'], 'missing local bytes or SHA mismatch: ' + str(local))
        prior = self.destinations.setdefault(producer, spec['sha256'])
        require(prior == spec['sha256'], 'different bytes map to one producer destination')
        record = dict(source_path=source, local_path=str(local), producer_path=producer, sha256=spec['sha256'])
        self.records[(source, spec['sha256'])] = record
        return local, dict(path=producer, sha256=spec['sha256'])

    def relocate_refs(self, value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256'}:
                return self.bind(value)[1]
            return {key: self.relocate_refs(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.relocate_refs(item) for item in value]
        return value


def runner_contract():
    """Read literal declarations without importing a torch/NN runner."""
    path = ROOT / 'tools/s04_e036/run_mechanism_matrix.py'
    values = {}
    for item in ast.parse(path.read_text()).body:
        if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
            name = item.targets[0].id
            if name in {'CASES', 'NETWORK_SHA', 'SOLVER'}:
                value = item.value
                if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'dict' and not value.args:
                    values[name] = {k.arg: ast.literal_eval(k.value) for k in value.keywords}
                else:
                    values[name] = ast.literal_eval(value)
    require(set(values) == {'CASES', 'NETWORK_SHA', 'SOLVER'}, 'runner has no inspectable frozen literal contract')
    return values, dict(path=str(path), sha256=sha256(path))


def npz_identity(path, key, mesh_sha, source_sha, *, predecessor=False, prior_sha=None):
    """Validate headers and short identity strings without loading field arrays."""
    nodal = ('u', 'v', 'damage') if predecessor else ('u', 'v', 'd', 'old_damage')
    gp = ('history', 'active_driver', 'f_commit') if predecessor else (
        'history', 'active_driver', 'f_solve', 'f_commit', 'old_history', 'old_active_driver')
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'duplicate NPZ fields')
        for name in nodal + gp:
            with archive.open(name + '.npy') as stream:
                version = np.lib.format.read_magic(stream)
                require(version in {(1, 0), (2, 0)}, 'unsupported NPY header')
                shape, _, dtype = (np.lib.format.read_array_header_1_0(stream) if version == (1, 0)
                                   else np.lib.format.read_array_header_2_0(stream))
                require(shape == ((N_NODES,) if name in nodal else (N_ELEMENTS, 4)) and dtype == np.dtype('float64'),
                        'native float64 NPZ header/support differs: ' + name)
        def short(name):
            info = archive.getinfo(name + '.npy')
            require(info.file_size <= 262144, 'identity metadata is not small')
            with archive.open(info) as stream:
                value = np.lib.format.read_array(stream, allow_pickle=False)
            require(value.shape == () and value.dtype.kind in 'US', 'identity metadata must be one string')
            return str(value.item())
        same(json.loads(short('state_key_json')), key, 'NPZ physical state differs')
        require(short('ordered_mesh_sha256_f32_i64') == mesh_sha and short('source_checkpoint_sha256') == source_sha,
                'NPZ source/mesh differs')
        if not predecessor:
            same(json.loads(short('predecessor_key_json')), predecessor_key(key['trajectory'], key['cycle'], key['substep']),
                 'target predecessor key differs')
            require(short('predecessor_checkpoint_sha256') == prior_sha, 'target predecessor source differs')


class Builder:
    def __init__(self, paths, producer_root):
        self.paths, self.files, self.derivatives = paths, {}, []
        self.producer_root = native_path(producer_root)
        require(self.producer_root.startswith('/'), 'producer output must be an absolute POSIX directory')

    def add_json(self, name, value):
        require(name not in self.files and '..' not in PurePosixPath(name).parts, 'duplicate or unsafe generated file')
        content = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
        import hashlib
        self.files[name] = content
        return dict(path=str(PurePosixPath(self.producer_root) / name), sha256=hashlib.sha256(content).hexdigest())

    def admission(self, spec, name, key, mesh, snapshot_sha, *, predecessor=False):
        path, original = self.paths.bind(spec)
        doc = read_json(path)
        schema = 's04_e036_predecessor_admission_v1' if predecessor else 's04_e036_target_admission_v1'
        require(doc.get('schema') == schema and all(doc.get(k) is True for k in
                ('accepted', 'native_residual_checked', 'checkpoint_readback_verified')), 'actual accepted native admission required')
        same(doc['state_key'], key, 'admission physical state differs')
        same(doc['solver_policy'], STANDARD_POLICY, 'main F1 policy must remain standard')
        require(doc['ordered_mesh_sha256_f32_i64'] == mesh, 'admission mesh differs')
        require(doc['predecessor_sha256' if predecessor else 'snapshot_sha256'] == snapshot_sha, 'admission input SHA differs')
        for required in ('source_checkpoint', 'native_residual_evidence', 'checkpoint_readback_evidence'):
            self.paths.bind(doc[required])
        if not predecessor:
            require(doc.get('reference_role') == 'main', 'tightening/oracle cannot replace main F1')
            self.paths.bind(doc['predecessor_checkpoint'])
            self.paths.bind(doc['completion_evidence'])
        relocated = self.paths.relocate_refs(doc)
        require('path_relocation' not in doc, 'do not repeatedly rewrite an admission derivative')
        relocated['path_relocation'] = dict(original_admission=original,
            scope='path-only derivative; original numerical admission unchanged; no new native check')
        result = self.add_json(name, relocated)
        self.derivatives.append(dict(original=original, derivative=result))
        return doc, result


def build(request_path, request_sha256, output):
    request_path, output = Path(request_path).resolve(), Path(output).resolve()
    require(digest_ok(request_sha256) and sha256(request_path) == request_sha256, 'request SHA mismatch')
    require(not output.exists(), 'fresh output required; never replace inputs')
    request = read_json(request_path)
    require(set(request) == {'schema', 'input_inventory', 'network_inventory', 'main_exports', 'path_map',
        'producer_output_root', 'budget', 'mechanism_job_wall_seconds'}, 'request fields differ')
    require(request['schema'] == 's04_e036_gap_input_request_v1' and set(request['main_exports']) == set(CASES),
            'four complete main exports required')
    validate_budget(request['budget'])
    wall = request['mechanism_job_wall_seconds']
    require(type(wall) in (int, float) and math.isfinite(wall) and wall > 0, 'explicit finite D4 job wall time required')
    paths = PathBindings(request['path_map'])
    builder = Builder(paths, request['producer_output_root'])
    inventory_path, inventory_ref = paths.bind(request['input_inventory'])
    networks_path, networks_ref = paths.bind(request['network_inventory'])
    inventory, networks = read_json(inventory_path), read_json(networks_path)
    require(inventory.get('schema') == 's04_e036_pidl_readiness_v1' and set(inventory['cases']) == set(CASES),
            'existing four-case input inventory required')
    contract, contract_ref = runner_contract()
    rows = networks['cases']
    require(isinstance(rows, list) and len(rows) == 4 and {row['case'] for row in rows} == set(contract['CASES']),
            'exact canonical four-network inventory required')
    network_refs = {}
    for row in rows:
        cycle, substep = contract['CASES'][row['case']]
        require(row.get('available') is True and row.get('all_finite') is True and row.get('parameter_count') == 1125211
            and row.get('dtypes') == ['torch.float32'] and row['step'] == 5 * (cycle - 1) + substep - 1
            and row['sha256'] == contract['NETWORK_SHA'][row['case']], 'canonical D4 network identity/inspection differs')
        local, ref = paths.bind(dict(path=row['path'], sha256=row['sha256']))
        require(local.stat().st_size == row['size'], 'network size differs from inspected inventory')
        network_refs[row['case']] = ref
    _, mesh_ref = paths.bind(inventory['mesh_source'])
    common_path, common_ref = paths.bind(inventory['common_problem_source'])
    common = read_json(common_path)
    require(common.get('schema') == 's04_e036_common_problem_v1', 'common problem schema differs')
    mesh = common['ordered_mesh_sha256_f32_i64']
    trajectory = inventory['cases']['c1']['predecessor_key']['trajectory']
    d3_cases, targets, d4_predecessors, main_refs = {}, {}, {}, {}
    for case, (cycle, steps) in CASES.items():
        export_path, export_ref = paths.bind(request['main_exports'][case])
        export = read_json(export_path)
        require(set(export) == {'schema', 'targets', 'run_result', 'input_binding', 'predecessor_admission', 'as_predecessors'}
                and export['schema'] == 's04_e036_fem_targets_v1', 'complete actual main-B export schema required')
        expected_slots = {f'c{cycle}/s{s}' for s in steps}
        require(set(export['targets']) == expected_slots and set(export['as_predecessors']) == expected_slots,
                'main export is incomplete or from another window')
        run_path, _ = paths.bind(export['run_result'])
        report = read_json(run_path)
        require(report.get('status') == 'completed' and report.get('history_commits') == len(steps), 'main B run is not completed')
        req = report['request']
        require(req['role'] == 'main' and req['cycle'] == cycle and np.atleast_1d(req['substeps']).tolist() == list(steps),
                'run result requested another comparison')
        paths.bind(export['input_binding'])
        prior = inventory['cases'][case]
        oldkey = predecessor_key(trajectory, cycle, steps[0])
        same(prior['predecessor_key'], oldkey, 'inventory predecessor differs')
        converted = dict(path=prior['conversion']['output'], sha256=prior['conversion']['sha256'])
        pre_path, pre_ref = paths.bind(converted)
        pre_doc, pre_adm = builder.admission(export['predecessor_admission'], f'admissions/{case}_old.json',
                                           oldkey, mesh, pre_ref['sha256'], predecessor=True)
        require(pre_doc['source_checkpoint']['sha256'] == prior['source_checkpoint']['sha256'], 'main B admitted another predecessor')
        paths.bind(prior['source_checkpoint'])
        npz_identity(pre_path, oldkey, mesh, pre_doc['source_checkpoint']['sha256'], predecessor=True)
        require(prior['network']['sha256'] == D3_NETWORK_SHA[case], 'canonical D3 network changed')
        network = paths.bind({k: prior['network'][k] for k in ('path', 'sha256')})[1]
        d3_cases[case] = dict(predecessor=pre_ref, admission=pre_adm, network=network)
        last_source = pre_doc['source_checkpoint']['sha256']
        for substep in steps:
            slot, key = f'c{cycle}/s{substep}', state_key(trajectory, cycle, substep)
            target = export['targets'][slot]
            require(set(target) == {'snapshot', 'admission'}, 'target references differ')
            snap_path, snap_ref = paths.bind(target['snapshot'])
            doc, adm_ref = builder.admission(target['admission'], f'admissions/c{cycle}_s{substep}.json',
                                             key, mesh, snap_ref['sha256'])
            same(doc['predecessor_key'], predecessor_key(trajectory, cycle, substep), 'target prior key differs')
            require(doc['predecessor_checkpoint']['sha256'] == last_source, 'F1 source chain is broken')
            npz_identity(snap_path, key, mesh, doc['source_checkpoint']['sha256'], prior_sha=last_source)
            targets[slot] = dict(snapshot=snap_ref, admission=adm_ref)
            last_source = doc['source_checkpoint']['sha256']
            if cycle in (1, 83) and substep in (1, 3):
                pre = export['as_predecessors'][slot]
                require(set(pre) == {'predecessor', 'admission'}, 'F1 predecessor export differs')
                path, ref = paths.bind(pre['predecessor'])
                pd, pa = builder.admission(pre['admission'], f'admissions/c{cycle}_s{substep}_as_old.json',
                                           key, mesh, ref['sha256'], predecessor=True)
                require(pd['source_checkpoint']['sha256'] == last_source and pd.get('new_native_calls') == 0
                        and pd.get('history_commits') == 0 and pd['original_target_admission'] == target['admission'],
                        'D4 old state is not the same main F1 endpoint')
                npz_identity(path, key, mesh, last_source, predecessor=True)
                d4_predecessors[f'c{cycle}s{substep+1}'] = dict(predecessor=ref, admission=pa)
        main_refs[case] = export_ref
    d3 = dict(schema=SCHEMA, trajectory=trajectory, mesh=mesh_ref, common_problem=common_ref,
              cases=d3_cases, budget=request['budget'])
    d3_ref = builder.add_json('d3_inputs.json', d3)
    d4 = dict(schema='s04_e036_mechanism_inputs_v1', trajectory=trajectory, mesh=mesh_ref, common_problem=common_ref,
        cases={name: dict(state_key=state_key(trajectory, *pair), **d4_predecessors[name], network=network_refs[name])
               for name, pair in contract['CASES'].items()}, solver=contract['SOLVER'], job_wall_seconds=wall)
    d4_ref = builder.add_json('d4_inputs.json', d4)
    builder.add_json('d4_targets.json', dict(schema='s04_e036_mechanism_targets_v1', physics_manifest=d4_ref,
        targets={name: targets[f'c{cycle}/s{substep}'] for name, (cycle, substep) in contract['CASES'].items()}))
    builder.add_json('d3_targets_catalog.json', dict(schema='s04_e036_d3_targets_catalog_v1', training_manifest=d3_ref,
        targets={f'{case}/s{s}': targets[f'c{cycle}/s{s}'] for case, (cycle, steps) in CASES.items() for s in steps},
        reference_tightening={f'c{cycle}/s{s}': None for cycle in (1, 83) for s in (2, 4)},
        status='target catalog only; final scoring needs actual run receipt and production implementation lock'))
    for value in paths.records.values():
        require(sha256(value['local_path']) == value['sha256'], 'input changed while preparing manifests')
    require(all(str(PurePosixPath(builder.producer_root) / name) not in paths.destinations
                for name in builder.files), 'generated producer output would overwrite a source artifact')
    receipt = dict(schema='s04_e036_gap_inputs_preparation_v1', status='prepared_from_actual_complete_main_B_exports',
        request=dict(path=str(request_path), sha256=request_sha256), input_inventory=inventory_ref,
        network_inventory=networks_ref, main_exports=main_refs, mechanism_runner_contract=contract_ref,
        input_bindings=list(paths.records.values()), admission_derivatives=builder.derivatives,
        solver_execution=False, new_native_admission=False, stage_a_validation='separately required; not generated here',
        publication_rule='prepared.json is completion marker; producer must verify all local-to-producer SHA after transfer')
    output.mkdir(parents=True, exist_ok=False)
    for name, content in builder.files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(content)
    receipt['generated_files'] = {name: dict(path=str(output / name), producer_path=str(PurePosixPath(builder.producer_root) / name),
        sha256=sha256(output / name)) for name in builder.files}
    with (output / 'prepared.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = build(args.request, args.request_sha256, args.out)
    print(json.dumps(dict(status=result['status'], generated_files=len(result['generated_files']), solver_execution=False)))
