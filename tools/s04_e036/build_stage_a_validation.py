#!/usr/bin/env python3
"""Build a reuse receipt from preserved Stage A evidence; never rerun Stage A.

Requires the Stage B read-only auditor's successful ten-job chain check, then
checks original products, operator hashes, native metadata and build identities.
No field, residual, model forward, optimizer or solver is evaluated here.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tools/s04_e036_fem'), str(Path(__file__).parent)]
from window_inputs import bound_file, read_json, sha256
from stage_a_reuse import PYTHON_OPERATORS, FEM_FUNCTIONS, effective_physics_contract


def _same(a, b, label):
    if json.dumps(a,sort_keys=True,allow_nan=False) != json.dumps(b,sort_keys=True,allow_nan=False):
        raise ValueError(f'{label} identity mismatch')


def _file_map(document, prefix=''):
    files=document['files']
    result=files if isinstance(files,dict) else {entry['path']:entry['sha256'] for entry in files}
    if len(result)!=len(files):raise ValueError('duplicate source-lock path')
    if prefix:
        if (not isinstance(prefix,str) or not prefix.endswith('/') or prefix.startswith('/')
                or '\\' in prefix or any(part in ('','.','..') for part in prefix[:-1].split('/'))):
            raise ValueError('source prefix must be an explicit safe relative directory ending in /')
        normalized={}
        for name,digest in result.items():
            if not name.startswith(prefix):continue
            relative=name[len(prefix):]
            if (not relative or '\\' in relative or relative.startswith('/')
                    or any(part in ('','.','..') for part in relative.split('/'))
                    or relative in normalized or relative in result):
                raise ValueError('source-prefix normalization collision or unsafe path')
            normalized[relative]=digest
        if not normalized:raise ValueError('source prefix matched no original files')
        result=normalized
    return result


class SavedPaths:
    """Explicit byte-identical relocation; raw receipts retain original paths."""
    def __init__(self, mappings):
        self.mappings=mappings

    def bind(self, original, digest):
        original=str(original)
        candidate=Path(original)
        if not candidate.is_file():
            normalized=original.replace('\\','/').rstrip('/')
            matches=[]
            for mapping in self.mappings:
                prefix=mapping['source_root'].replace('\\','/').rstrip('/')
                if normalized.lower().startswith(prefix.lower()+'/'):
                    relative=normalized[len(prefix)+1:]
                    target=Path(mapping['local_root']).resolve()/relative
                    if not target.resolve().is_relative_to(Path(mapping['local_root']).resolve()):
                        raise ValueError('saved path escapes its explicit relocation')
                    matches.append(target)
            if len(matches)!=1:raise ValueError(f'missing or ambiguous saved artifact relocation: {original}')
            candidate=matches[0]
        path=bound_file(dict(path=str(candidate),sha256=digest),Path.cwd())
        return dict(path=str(path),sha256=digest)

    def record(self, spec):
        bound=self.bind(spec['path'],spec['sha256'])
        return read_json(bound['path']),bound


def _metadata_contract(native_path, common):
    # Validation checks stored fields and one canonical four-node reference
    # quadrature table only. It never calls assemble_numpy/assemble_energy/run.
    import torch
    from compare_frozen_states import read_native, validate_state
    from material_properties import MaterialProperties
    from pff_model import PFFModel
    from run_paired_windows import fatigue_config
    state=validate_state(read_native(native_path),common,production=True)
    problem=SimpleNamespace(native_x=torch.as_tensor(state['nodes'],dtype=torch.float64),
        cells=torch.as_tensor(state['cells']),common=common,mat=MaterialProperties(1.,.3,1.,.01),
        model=PFFModel('AT1','volumetric',.001,residual_stiffness=0.),
        penalty=dict(enable=True,mode='fem_gp_q4',spatial_integration='native_q4_gp4',recovery_penalty_coefficient=13781.25),
        fatigue=fatigue_config(common))
    return effective_physics_contract(problem)


def build(*,audit,audit_sha256,semantic_binding,semantic_binding_sha256,original_source_lock,
          original_source_lock_sha256,path_map,output,original_source_prefix=''):
    paths=SavedPaths(read_json(path_map))
    audited=paths.bind(audit,audit_sha256);a=read_json(audited['path'])
    if (a.get('schema')!='e036-stage-a-reuse-audit-v1' or a.get('accepted') is not True
            or a.get('tasks_verified')!=10 or type(a.get('tasks_verified')) is not int
            or a.get('stage_a_reexecuted') is not False):
        raise ValueError('requires the actual successful Stage B read-only Stage A chain audit')
    auditor_path=a['audit_source_path']
    if not auditor_path.endswith('.m'):auditor_path+='.m'
    auditor=paths.bind(auditor_path,a['audit_source_sha256'])
    if sha256(ROOT/'tools/s04_e036_fem/e036_stage_b_driver.m')!=auditor['sha256']:
        raise ValueError('reuse auditor differs from this reviewed source')
    expected_spec=paths.bind(semantic_binding,semantic_binding_sha256)
    expected=read_json(expected_spec['path'])
    if expected.get('schema')!='s04_e036_semantic_binding_v1':raise ValueError('wrong semantic binding schema')
    original_lock=paths.bind(original_source_lock,original_source_lock_sha256)
    source_files=_file_map(read_json(original_lock['path']),original_source_prefix)
    for name in PYTHON_OPERATORS:
        if expected['python_operator_files'].get(name)!=source_files.get(name) or sha256(ROOT/name)!=source_files.get(name):
            raise ValueError(f'original/current Python operator identity differs: {name}')
    evidence_spec=paths.bind(a['stage_a_evidence_file'],a['stage_a_evidence_sha256'])
    e=read_json(evidence_spec['path']);_same(e,a['stage_a_evidence'],'audited original evidence manifest')
    if e.get('schema')!='e036-stage-a-evidence-v1':raise ValueError('wrong original Stage A evidence schema')
    p,pref=paths.record(e['prepare']);d,dref=paths.record(e['disabled'])
    if (p.get('status')!='prepared_build_and_mock_completed_no_native_call'
            or p['mock'].get('cases')!=28 or p['mock'].get('status')!='passed' or p['mock'].get('native_solves')!=0
            or d.get('status')!='exact_disabled_identity' or d.get('native_solves')!=2
            or d.get('recovery_solves')!=0):
        raise ValueError('actual prepare/disabled products do not pass their declared scope')
    if len(e['frozen'])!=4 or sorted(item['cycle'] for item in e['frozen'])!=[1,20,60,83]:
        raise ValueError('four distinct declared frozen comparison artifacts are required')
    runtime={item['name']:item['sha256'] for item in a['runtime_bindings']}
    if len(runtime)!=len(a['runtime_bindings']):raise ValueError('duplicate native runtime function')
    for logical,adapter in a['adapter_bindings'].items():
        if adapter['qualified_name']!='phase_field.audit.'+logical:raise ValueError('unknown native adapter alias')
        source=paths.bind(adapter['source_path'],adapter['sha256'])
        paths.bind(adapter['resolved_path'],adapter['sha256'])
        expected_source='tools/s04_e036_fem/'+logical+'.m'
        if source_files.get(expected_source)!=source['sha256']:raise ValueError('adapter differs from original validated source')
        runtime[logical]=adapter['sha256']
    for name in FEM_FUNCTIONS:
        if runtime.get(name)!=expected['fem_functions'].get(name):raise ValueError(f'FEM semantic binding differs: {name}')
    evidence=dict(prepare=pref,disabled_transition_readback=dref,supervisor_chain=evidence_spec,
                  original_source_lock=original_lock,reuse_audit=audited,reuse_auditor_source=auditor)
    for item in e['frozen']:
        n,nref=paths.record(item['native']);r,rref=paths.record(item['comparison'])
        if (n.get('cycle')!=item['cycle'] or n.get('substep')!=4 or n.get('native_solves')!=0
                or r.get('schema')!='e036_frozen_comparison_v1' or r.get('status')!='matched'
                or r.get('passed') is not True or r['state_key']['cycle']!=item['cycle']
                or r['state_key']['substep']!=4 or r['input_sha256']!=n['sha256']
                or r['tolerance']['atol']!=1e-10 or r['tolerance']['rtol']!=1e-8):
            raise ValueError('frozen native/comparison identity or numerical scope failed')
        native=paths.bind(n['path'],n['sha256'])
        common_spec=paths.bind(r['common_problem'],r['common_problem_sha256'])
        common=read_json(common_spec['path'])
        _same(common,expected['physics_contract']['common_problem'],'common problem')
        _same(_metadata_contract(native['path'],common),expected['physics_contract'],'native metadata contract')
        for name in PYTHON_OPERATORS:
            if r['source_sha256'].get(name)!=expected['python_operator_files'][name]:
                raise ValueError('comparison did not use the expected Python operator bytes')
        for prior in r['native_provenance']['binary_checks']:
            if runtime.get(prior['name'])!=prior['sha256']:raise ValueError('comparison native runtime differs')
        cycle=item['cycle'];evidence[f'frozen_c{cycle}']=rref
        evidence[f'native_c{cycle}']=nref;evidence[f'native_arrays_c{cycle}']=native
    roles={'prepare','disabled',*[f'{kind}_c{cycle}' for kind in ('native','comparison') for cycle in (1,20,60,83)]}
    if len(e['supervisors'])!=10 or {s['role'] for s in e['supervisors']}!=roles:
        raise ValueError('incomplete supervised Stage A task list')
    # The bound MATLAB auditor checked argv/config/authority chains. Preserve
    # all four immutable per-job receipts, and check termination here as well.
    labels=set()
    for s in e['supervisors']:
        if s['label'] in labels:raise ValueError('duplicate supervised Stage A attempt')
        labels.add(s['label']);r,ref=paths.record(s)
        if (r.get('stop_reason')!='completed' or r.get('watchdog_exit_code')!=0
                or r.get('watchdog_stopped') is not True or r.get('global_policy_unchanged') is not True
                or r.get('failure') not in (None,'',[])):
            raise ValueError('Stage A supervisor did not complete successfully')
        evidence['supervisor_'+s['role']]=ref
        for channel in ('supervisor_attempt','watchdog_attempt','watchdog_finished'):
            record,bound=paths.record(s[channel]);evidence[channel+'_'+s['role']]=bound
            if record['label']!=s['label'] or record['authority_sha256']!=r['authority_sha256']:
                raise ValueError('Stage A attempt/authority identity mismatch')
    build_spec=paths.bind(a['build_receipt_path'],a['build_receipt_sha256']);built=read_json(build_spec['path'])
    _same({x['relative_path']:x['sha256'] for x in built['source_records']},expected['fortran_sources'],'build source map')
    _same({x['name']:x['sha256'] for x in built['binaries']},expected['mex_binaries'],'build MEX map')
    if len(built['source_records'])!=10:raise ValueError('missing original build source')
    evidence['build_receipt']=build_spec
    result=dict(schema='s04_e036_fem_validation_v2',accepted=True,stage_a_reexecuted=False,
        stage_a_owner='01a1603e-8e80-7153-a753-d895b9edb7f5',semantic_binding=expected,evidence=evidence,
        original_source_prefix=original_source_prefix,
        validated_scopes=dict(frozen_operator_equivalence=True,disabled_transition_readback=True),
        scope='Reuse of preserved operator and disabled readback evidence; no new controller/scorer validation',
        builder_sha256=sha256(Path(__file__)))
    with Path(output).open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    return dict(path=str(Path(output).resolve()),sha256=sha256(output),stage_a_reexecuted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('audit','audit-sha256','semantic-binding','semantic-binding-sha256','original-source-lock',
                 'original-source-lock-sha256','path-map','output'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--original-source-prefix',default='',help='Explicit original manifest directory, e.g. code_04/; original bytes/hash remain unchanged')
    print(json.dumps(build(**vars(parser.parse_args())),indent=2))
