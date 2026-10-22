"""Small synthetic evidence fixtures; never execute Stage A or a field solve."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/s04_e036'))
from stage_a_reuse import PYTHON_OPERATORS, FEM_FUNCTIONS, effective_physics_contract, validate_stage_a_reuse
from window_inputs import sha256
from run_paired_windows import fatigue_config
from test_e036_native_diagnostics import _problem


def _fixture(tmp_path):
    root=tmp_path/'source_snapshot';root.mkdir()
    files={}
    for relative in PYTHON_OPERATORS:
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('# synthetic hash fixture; never imported\n')
        files[relative]=sha256(path)
    p=_problem();p.common=dict(schema='synthetic_only',fixed_damage_nodes_zero_based=[0])
    p.fatigue=fatigue_config(p.common)
    binding=dict(schema='s04_e036_semantic_binding_v1',python_operator_files=files,
        fem_functions={name:'a'*64 for name in FEM_FUNCTIONS},
        fortran_sources={f'synthetic_{i}.f90':'b'*64 for i in range(10)},
        mex_binaries={'synthetic.mexw64':'c'*64},physics_contract=effective_physics_contract(p))
    expected=tmp_path/'expected.json';expected.write_text(json.dumps(binding))
    evidence={}
    for name in ('prepare','disabled_transition_readback','frozen_c1','frozen_c20','frozen_c60',
                 'frozen_c83','supervisor_chain','build_receipt','original_source_lock'):
        path=tmp_path/(name+'.json');path.write_text('{"synthetic_unit_fixture":true}')
        evidence[name]=dict(path=str(path),sha256=sha256(path))
    validation=tmp_path/'validation.json'
    doc=dict(schema='s04_e036_fem_validation_v2',accepted=True,stage_a_reexecuted=False,
        stage_a_owner='01a1603e-8e80-7153-a753-d895b9edb7f5',semantic_binding=binding,evidence=evidence,
        validated_scopes=dict(frozen_operator_equivalence=True,disabled_transition_readback=True))
    validation.write_text(json.dumps(doc))
    return root,p,expected,validation,doc


def test_reuse_matches_operators_and_effective_values_without_whole_tree_equivalence(tmp_path):
    root,p,expected,validation,_=_fixture(tmp_path)
    unrelated=root/'new_controller.py';unrelated.write_text('# different separately locked controller\n')
    result=validate_stage_a_reuse(validation,expected,root,p)
    assert result['stage_a_reexecuted'] is False
    assert 'new_PIDL_controller' in result['not_validated_here']


def test_python_operator_drift_fails_even_when_controller_is_unrelated(tmp_path):
    root,p,expected,validation,_=_fixture(tmp_path)
    (root/'source/compute_energy.py').write_text('# drift\n')
    with pytest.raises(ValueError,match='operator changed'):
        validate_stage_a_reuse(validation,expected,root,p)


@pytest.mark.parametrize('change', ['material','native_geometry','acceptance','fatigue'])
def test_effective_runtime_semantics_are_bound_not_just_source_hash(tmp_path,change):
    root,p,expected,validation,_=_fixture(tmp_path)
    if change=='material':p.mat.mat_E=2.
    elif change=='native_geometry':p.native_x[0,0]+=1e-10
    elif change=='acceptance':p.common['new_unreviewed_policy']=True
    else:p.fatigue['alpha_T']=1.
    with pytest.raises(ValueError,match='effective runtime values'):
        validate_stage_a_reuse(validation,expected,root,p)


@pytest.mark.parametrize('change',['new_stage_a','wrong_owner','missing_evidence','missing_scope','changed_kernel'])
def test_incomplete_or_relabelled_stage_a_evidence_is_rejected(tmp_path,change):
    root,p,expected,validation,doc=_fixture(tmp_path)
    if change=='new_stage_a':doc['stage_a_reexecuted']=True
    elif change=='wrong_owner':doc['stage_a_owner']='this-task'
    elif change=='missing_evidence':doc['evidence'].pop('frozen_c83')
    elif change=='missing_scope':doc['validated_scopes']['disabled_transition_readback']=False
    else:doc['semantic_binding']['fem_functions']['e036_native_candidate']='d'*64
    validation.write_text(json.dumps(doc))
    with pytest.raises(ValueError):validate_stage_a_reuse(validation,expected,root,p)
