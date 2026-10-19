"""Saved-array parser fixtures only; no network, mechanics solve or SVD."""
import json
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis'))
from analyze_pidl_persisted_phi_hidden_newton import (
    GRAD_KEYS,basis_folder,validate_basis_metadata,validate_budget,readout_identity,probe_stability)


def metadata():
    return dict(retained_rank=386,current_full_raw_columns=401,actual_saved_Phi_reused=True,
        initial_Phi_reconstructed=False,initial_SVD_calls=0,source_phi_sha256='a'*64,phi_sha256='a'*64,
        source_transform_sha256='b'*64,transform_sha256='b'*64,bound_hidden_sha256='c'*64,
        originating_weights_sha256='d'*64)


def budget(phase):
    return dict(prior_evaluations=35,new_probe_production_cap=365,total_prior_plus_new_cap=400,
        new_probe_production_deadline_seconds=600,cap=40 if phase=='probe' else 325,deadline_seconds=60 if phase=='probe' else 540,
        prior_elapsed_seconds=None,cumulative_elapsed_seconds_claim=False,evaluations=5)


def saved_readout(case,label):
    bp=case/'bases/initial';bp.mkdir(parents=True,exist_ok=True)
    (bp/'metadata.json').write_text(json.dumps(metadata()))
    folder=case/'readouts';folder.mkdir(exist_ok=True)
    g=np.zeros(772);g[0]=8e-11
    row=dict(label=label,status='verified',objective='raw_Eel',E_el=.005,
        free_u_l2=.01,uv_mass_rel_L2=.07,uv_H1_rel=.58,
        basis_ref='/remote/output/c20_s4/bases/initial',basis_phi_sha256='a'*64,
        hidden_sha256='c'*64,basis_bound_hidden_sha256='c'*64,bound_weights_sha256='d'*64,
        basis_hidden_match=True,reduced_gradient_inf=8e-11,reduced_gradient_l2=8e-11,
        gradient_inf_tolerance=1e-10,head_stationarity_closed=True,
        source_field_maxabs=dict(u=0.,v=0.,d=0.),source_energy_abs_error=0.)
    row.update({k:8e-11 if k.startswith('conditioned') else .01 for k in GRAD_KEYS})
    (folder/(label+'_actual.json')).write_text(json.dumps(row))
    np.save(folder/(label+'_actual_projected_gradient.npy'),g)
    np.savez(folder/(label+'.npz'),u=np.zeros(3),v=np.zeros(3),d=np.zeros(3),gu=np.zeros(3),gv=np.zeros(3),raw_head_gradient=np.zeros((2,401)))
    return row


def test_initial_actual_basis_does_not_require_fresh_svd_fields():
    # The reused source metadata intentionally has no original_columns or dynamic flag.
    validate_basis_metadata(metadata(),True)


def test_initial_phi_must_be_exact_copy():
    value=metadata();value['source_phi_sha256']='e'*64
    with pytest.raises(ValueError,match='saved source SHA'):validate_basis_metadata(value,True)


def test_hidden_basis_still_requires_full401_dynamic_policy():
    value=metadata();value.update(retained_rank=390,original_columns=401,dynamic_current_feature_basis=True,old_restricted_span_used=False)
    validate_basis_metadata(value,False)
    value['old_restricted_span_used']=True
    with pytest.raises(ValueError,match='full401'):validate_basis_metadata(value,False)


def test_basis_pointer_maps_remote_small_metadata_without_reconstruction(tmp_path):
    assert basis_folder(tmp_path,'/remote/output/c20_s4/bases/hidden_1')==tmp_path/'bases/hidden_1'
    with pytest.raises(ValueError):basis_folder(tmp_path,'/remote/../../unregistered_basis')


def test_small_readout_valid_without_local_large_phi(tmp_path):
    row=saved_readout(tmp_path,'initial_learned_head')
    result=readout_identity(row,tmp_path,[])
    assert result['head_closed'] is True
    assert result['local_actual_basis_files']['phi.npy']=='not_retrieved_no_reconstruction'
    assert not (tmp_path/'bases/initial/phi.npy').exists()
    row['hidden_sha256']='e'*64
    with pytest.raises(ValueError,match='hidden state'):readout_identity(row,tmp_path,[])


def test_budget_is_prior35_plus_new365_not_cumulative_walltime():
    validate_budget(budget('production'),'production')
    value=budget('production');value['cumulative_elapsed_seconds_claim']=True
    with pytest.raises(ValueError,match='cumulative wall-time'):validate_budget(value,'production')


def test_probe_requires_three_actual_vectors_same_phi_and_weights(tmp_path):
    case=tmp_path/'retrieved/archive/output/c20_s4';case.mkdir(parents=True)
    rows=[saved_readout(case,label) for label in ['initial_learned_head','probe_repeat_1','probe_repeat_2']]
    result=dict(budget('probe'),status='probe_passed',all_three_same_Phi_readouts_passed=True,
        optimizer_updates=0,parameter_updates=0,history_commits=0,rollout_steps=0,
        damage_output_row_unchanged=True,Smooth_B0_anchor_unchanged=True,
        mechanical_damage_exact_FEM=True,boundary_unchanged=True,actual_Phi_repetition_readouts=rows)
    (case/'result.json').write_text(json.dumps(result))
    observed=probe_stability(tmp_path,[])
    assert observed['status']=='verified_three_same_actual_Phi'
    assert observed['full_gradient_coordinate_range_inf']==0.
    # A falsely labelled stable source with differing weights is not admitted.
    result['actual_Phi_repetition_readouts'][2]['bound_weights_sha256']='e'*64
    (case/'readouts/probe_repeat_2_actual.json').write_text(json.dumps(result['actual_Phi_repetition_readouts'][2]))
    (case/'result.json').write_text(json.dumps(result))
    with pytest.raises(ValueError,match='hold actual Phi/weights fixed'):probe_stability(tmp_path,[])
