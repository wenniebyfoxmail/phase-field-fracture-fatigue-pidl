"""Synthetic saved-receipt fixtures only; metadata reader is mocked explicitly."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/s04_e036'))
import build_stage_a_validation as builder
from stage_a_reuse import PYTHON_OPERATORS,FEM_FUNCTIONS
from window_inputs import sha256


def test_explicit_saved_path_relocation_is_hashed_and_cannot_escape(tmp_path):
    path=tmp_path/'f.json';path.write_text('{}')
    resolver=builder.SavedPaths([dict(source_root='C:\\source',local_root=str(tmp_path))])
    assert resolver.bind('C:\\source\\f.json',sha256(path))['path']==str(path)
    with pytest.raises(ValueError,match='SHA256'):
        resolver.bind('C:\\source\\f.json','0'*64)
    with pytest.raises(ValueError,match='escapes'):
        resolver.bind('C:\\source\\..\\outside.json','0'*64)


def _inputs(tmp_path,monkeypatch):
    def save(name,doc):
        path=tmp_path/name;path.write_text(json.dumps(doc));return dict(path=str(path),sha256=sha256(path))
    source_map={name:sha256(builder.ROOT/name) for name in PYTHON_OPERATORS}
    adapters={}
    for name in ('e036_final_candidate','e036_native_candidate','e036_policy'):
        relative='tools/s04_e036_fem/'+name+'.m';path=builder.ROOT/relative
        source_map[relative]=sha256(path)
        adapters[name]=dict(qualified_name='phase_field.audit.'+name,source_path=str(path),resolved_path=str(path),sha256=sha256(path))
    original_lock=save('source_lock.json',dict(files=source_map))
    runtime={name:('a'*64 if name not in adapters else adapters[name]['sha256']) for name in FEM_FUNCTIONS}
    fortran={f'fixture_{i}.f90':'b'*64 for i in range(10)};mex={'fixture':'c'*64}
    common=save('common.json',dict(synthetic_fixture=True))
    contract=dict(common_problem=dict(synthetic_fixture=True))
    expected=save('semantic.json',dict(schema='s04_e036_semantic_binding_v1',
        python_operator_files={name:source_map[name] for name in PYTHON_OPERATORS},fem_functions=runtime,
        fortran_sources=fortran,mex_binaries=mex,physics_contract=contract))
    monkeypatch.setattr(builder,'_metadata_contract',lambda *_:contract)
    e=dict(schema='e036-stage-a-evidence-v1',prepare=save('prepare.json',dict(status='prepared_build_and_mock_completed_no_native_call',
        mock=dict(cases=28,status='passed',native_solves=0))),disabled=save('disabled.json',dict(status='exact_disabled_identity',native_solves=2,recovery_solves=0)),frozen=[],supervisors=[])
    for cycle in (1,20,60,83):
        raw=tmp_path/f'raw_{cycle}.mat';raw.write_bytes(b'synthetic placeholder, metadata reader is mocked')
        n=save(f'native_{cycle}.json',dict(cycle=cycle,substep=4,native_solves=0,path=str(raw),sha256=sha256(raw)))
        r=save(f'comparison_{cycle}.json',dict(schema='e036_frozen_comparison_v1',status='matched',passed=True,
            state_key=dict(cycle=cycle,substep=4),input_sha256=sha256(raw),tolerance=dict(atol=1e-10,rtol=1e-8),
            common_problem=common['path'],common_problem_sha256=common['sha256'],source_sha256=source_map,
            native_provenance=dict(binary_checks=[dict(name=k,sha256=v) for k,v in runtime.items()])))
        e['frozen'].append(dict(cycle=cycle,native=n,comparison=r))
    roles=['prepare','disabled']+[f'{kind}_c{cycle}' for kind in ('native','comparison') for cycle in (1,20,60,83)]
    for role in roles:
        s=save('supervisor_'+role+'.json',dict(label=role,stop_reason='completed',watchdog_exit_code=0,
            watchdog_stopped=True,global_policy_unchanged=True,failure='',authority_sha256='d'*64))
        s.update(role=role,label=role)
        for channel in ('supervisor_attempt','watchdog_attempt','watchdog_finished'):
            s[channel]=save(channel+'_'+role+'.json',dict(label=role,authority_sha256='d'*64))
        e['supervisors'].append(s)
    es=save('stage_a_evidence.json',e)
    built=save('build.json',dict(source_records=[dict(relative_path=k,sha256=v) for k,v in fortran.items()],
                               binaries=[dict(name=k,sha256=v) for k,v in mex.items()]))
    auditor=builder.ROOT/'tools/s04_e036_fem/e036_stage_b_driver.m'
    audit=save('audit.json',dict(schema='e036-stage-a-reuse-audit-v1',accepted=True,tasks_verified=10,
        stage_a_reexecuted=False,stage_a_evidence_file=es['path'],stage_a_evidence_sha256=es['sha256'],stage_a_evidence=e,
        runtime_bindings=[dict(name=k,sha256=v) for k,v in runtime.items()],adapter_bindings=adapters,
        build_receipt_path=built['path'],build_receipt_sha256=built['sha256'],audit_source_path=str(auditor),audit_source_sha256=sha256(auditor)))
    pathmap=tmp_path/'paths.json';pathmap.write_text('[]')
    return dict(audit=audit['path'],audit_sha256=audit['sha256'],semantic_binding=expected['path'],semantic_binding_sha256=expected['sha256'],
        original_source_lock=original_lock['path'],original_source_lock_sha256=original_lock['sha256'],path_map=str(pathmap),output=str(tmp_path/'result.json'))


def test_builder_preserves_raw_receipts_and_only_emits_explicit_reuse(tmp_path,monkeypatch):
    kwargs=_inputs(tmp_path,monkeypatch)
    before=sha256(kwargs['audit'])
    builder.build(**kwargs)
    result=json.loads(Path(kwargs['output']).read_text())
    assert result['stage_a_reexecuted'] is False and result['validated_scopes']['frozen_operator_equivalence'] is True
    assert sha256(kwargs['audit'])==before
    with pytest.raises(FileExistsError):builder.build(**kwargs)


@pytest.mark.parametrize('failure',['incomplete','wrong_auditor','mutated_product','wrong_python'])
def test_builder_rejects_incomplete_evidence_without_output(tmp_path,monkeypatch,failure):
    kwargs=_inputs(tmp_path,monkeypatch)
    path=Path(kwargs['audit']);audit=json.loads(path.read_text())
    if failure=='incomplete':audit['tasks_verified']=9
    elif failure=='wrong_auditor':audit['audit_source_sha256']='0'*64
    elif failure=='mutated_product':(tmp_path/'comparison_83.json').write_text('{}')
    else:
        original=Path(kwargs['original_source_lock']);lock=json.loads(original.read_text())
        lock['files']['source/compute_energy.py']='0'*64;original.write_text(json.dumps(lock))
        kwargs['original_source_lock_sha256']=sha256(original)
    path.write_text(json.dumps(audit));kwargs['audit_sha256']=sha256(path)
    with pytest.raises(ValueError):builder.build(**kwargs)
    assert not Path(kwargs['output']).exists()
