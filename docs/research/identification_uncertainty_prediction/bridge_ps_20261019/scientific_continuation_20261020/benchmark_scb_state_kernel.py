"""ONE predeclared artificial end-to-end development benchmark; no SCB science.
Four ARTIFICIAL cores x two origins, known constant-growth oracle. No real payload.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import time
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
from scb_state_kernel import (NotQualified, adapt_normalized, compare, donors,
                              inspect_real_case, whole_core_splits)
from scb_metadata_interface import audit_metadata


def artificial_fixture():
    # Normalized interface fields; not an assumed author file format or SCB dataset.
    t={n:[] for n in ('entities','frame_load_join','response_catalog','reference_catalog','origins','splits')}
    payload={'response_rows':[], 'origin_covariates':[], 'reference_values':[]}
    cfg={'alpha':10., 'threads':1, 'horizons_cycles':[10], 'primary_horizon_cycles':10,
         'phase_tolerance_fraction':.01, 'sigma_floor_mm':.05,
         'sigma_floor_basis':'ARTIFICIAL benchmark oracle, not SCB resolution',
         'reference_effect_delta_mm':.1, 'effect_delta_basis':'ARTIFICIAL ONLY; not a scientific decision',
         'feature_schema':{'geometry_load_plan_columns':['ARTIFICIAL_known_load'],
                           'current_response_columns':['ARTIFICIAL_global','ARTIFICIAL_local'],
                           'local_response_columns':['ARTIFICIAL_local'],
                           'units':{'ARTIFICIAL_known_load':'ARTIFICIAL_N','ARTIFICIAL_global':'ARTIFICIAL_mm','ARTIFICIAL_local':'ARTIFICIAL_mm'}},
         'donor_max_standardized_distance':100., 'donor_support_basis':'ARTIFICIAL fixture support',
         'frozen_before_outer_targets':True}
    for i in range(4):
        tid=f'ARTIFICIAL_TEST_{i}';core=f'ARTIFICIAL_CORE_{i}'
        t['entities'].append(dict(study_id='ARTIFICIAL_ONLY_NOT_SCB',road_section_id='ARTIFICIAL_ROAD',core_id=core,specimen_id=f'ARTIFICIAL_SPECIMEN_{i}',test_id=tid,entity_source_asset_id='ARTIFICIAL_identity'))
        for n in (0,10,20,30,40):
            t['frame_load_join'].append(dict(test_id=tid,pair_id=f'ARTIFICIAL_pair_{n}',left_frame_id=f'L{n}',right_frame_id=f'R{n}',left_asset_id='ARTIFICIAL_image_L',right_asset_id='ARTIFICIAL_image_R',cycle=n,phase_fraction=.25,roi_id='ARTIFICIAL_ROI',registration_id='ARTIFICIAL_common_calibration',machine_source_asset_id='ARTIFICIAL_load',sync_source_asset_id='ARTIFICIAL_trigger'))
            t['response_catalog'].append(dict(test_id=tid,cycle=n,phase_fraction=.25,roi_id='ARTIFICIAL_ROI',feature_source_max_cycle=n,response_asset_id='ARTIFICIAL_DIC',geometry_asset_id='ARTIFICIAL_geometry',geometry_unit='mm',feature_pipeline_id='ARTIFICIAL_shared_pipeline'))
            payload['response_rows'].append(dict(test_id=tid,cycle=n,roi_id='ARTIFICIAL_ROI',current_length_mm=.5+.2*i+.1*n,response={'ARTIFICIAL_global':i+.01*n,'ARTIFICIAL_local':i*.2+.001*(i+1)*n*n},response_asset_id='ARTIFICIAL_DIC',geometry_asset_id='ARTIFICIAL_geometry',feature_pipeline_id='ARTIFICIAL_shared_pipeline',source_max_cycle=n))
        for n in (20,40):
            t['origins'].append(dict(test_id=tid,origin_cycle=n,history_cycles=[n-20,n-10,n],phase_fraction=.25,roi_id='ARTIFICIAL_ROI',load_plan_known_at_cycle=n,load_plan_until_cycle=n+10,load_plan_asset_id='ARTIFICIAL_known_plan'))
            payload['origin_covariates'].append(dict(test_id=tid,origin_cycle=n,roi_id='ARTIFICIAL_ROI',values={'ARTIFICIAL_known_load':1.+i*.01},available_at_cycle=n,load_plan_asset_id='ARTIFICIAL_known_plan',geometry_asset_id='ARTIFICIAL_geometry',matching_stratum=['ARTIFICIAL_constant_plan']))
            rid=f'ARTIFICIAL_REF_{i}_{n+10}'
            t['reference_catalog'].append(dict(reference_id=rid,test_id=tid,cycle=n+10,roi_id='ARTIFICIAL_ROI',unit='mm',independent_of_dic=True,reference_source_asset_id='ARTIFICIAL_independent_reference',reference_resolution_mm=.01))
            payload['reference_values'].append(dict(reference_id=rid,length_mm=.5+.2*i+.1*(n+10),reference_source_asset_id='ARTIFICIAL_independent_reference'))
    t['splits']=whole_core_splits(t['entities'])
    return t,payload,cfg


def benchmark(case):
    started=time.monotonic();case=Path(case)
    received=case/'state_interface_preparation_20261020/received_metadata.json'
    before=hashlib.sha256(received.read_bytes()).hexdigest()
    real_cfg=json.loads(Path(__file__).with_name('scb_state_config.json').read_text())
    refused=inspect_real_case(case,real_cfg)
    assert refused['status']=='REFUSED_UNBOUND_OR_UNAUTHORIZED_REAL_EXECUTION'
    assert refused['scientific_payloads_opened']==refused['real_fits']==0
    assert refused['actual_core_count'] is None
    tables,payload,cfg=artificial_fixture()
    samples,refs,audit=adapt_normalized(tables,payload,cfg)
    assert all(abs(s.g[2]-1)<1e-12 and abs(s.g[3])<1e-12 for s in samples)
    result=compare(samples,refs,cfg)
    assert result['actual_closed_form_solves']==32
    assert len(result['predictions'])==48 and len(result['per_core'])==24
    oracle=cfg['sigma_floor_mm']*(math.sqrt(2)-1)/math.sqrt(math.pi)
    for row in result['predictions']:
        assert row['sigma_mm']==.05
        if row['arm']!='P':
            assert abs(row['mu_mm']-row['reference_mm'])<1e-12
            assert abs(row['crps_mm']-oracle)<1e-12
    assert abs(result['primary_delta_state_mm'])<1e-12
    # Shared current prefix transform; no held future may train or set its scale.
    for fold in result['folds']:
        held=fold['held_core'];h=fold['H_cycles'];prefix=held+'/H'+str(h)
        ts={x['role'].split('/')[-1]:x for x in result['method_fit_trace'] if x['role'].startswith(prefix+'/final/')}
        count=len(ts['C']['mean'])
        for arm in ('H','D'):
            assert ts[arm]['mean'][:count]==ts['C']['mean']
            assert ts[arm]['scale'][:count]==ts['C']['scale']
        assert ts['H']['mean']==ts['D']['mean'] and ts['H']['scale']==ts['D']['scale']
        assert all(held not in v['cores'] for v in result['method_fit_trace'] if v['role'].startswith(prefix))
        bykey={s.key:s for s in samples}
        for queries,donor_keys in [(fold['training_keys'],fold['train_donor_keys']),(fold['query_keys'],fold['query_donor_keys'])]:
            for key,donor_key in zip(queries,donor_keys):
                assert donor_key in fold['training_keys'] and bykey[donor_key].core!=bykey[key].core
        accesses=[v for v in result['reference_access_log'] if v['purpose'].startswith(prefix)]
        assert all(held not in v['cores'] for v in accesses if '/outer/' not in v['purpose'])
    # Necessary invalid-data checks within this same benchmark, no second real/synthetic study.
    leak=copy.deepcopy(tables);leak['entities'][1]['core_id']=leak['entities'][0]['core_id']
    try:audit_metadata(leak,[10],.01)
    except ValueError:pass
    else:raise AssertionError('mother-core leakage was accepted')
    leak=copy.deepcopy(payload);leak['response_rows'][0]['source_max_cycle']=999
    try:adapt_normalized(tables,leak,cfg)
    except NotQualified:pass
    else:raise AssertionError('future prefix was accepted')
    samecore=[s for s in samples if s.core==samples[0].core]
    import numpy as np
    ids,reasons,_=donors(samecore,[samecore[0]],np.zeros(len(samecore[0].g)),np.ones(len(samecore[0].g)),cfg)
    assert ids==[None] and reasons==['NO_OTHER_FIT_CORE_LOAD_PHASE_SUPPORT']
    # Unit effect average: identical analytic CRPS per core must equal the pooled primary.
    for h,values in result['by_horizon'].items():
        for arm in ('G','C','H','D','S'):
            assert abs(values['equal_core_crps_mm'][arm]-oracle)<1e-12
    assert hashlib.sha256(received.read_bytes()).hexdigest()==before
    elapsed=time.monotonic()-started
    assert elapsed<10
    return {'status':'PASS_ARTIFICIAL_DEVELOPMENT_BENCHMARK_ONLY',
            'scope':'one predeclared end-to-end path plus necessary truth constraints; NOT SCB data or a scientific micro-study',
            'artificial_only':True, 'real_payloads_opened':0, 'real_scientific_fits':0,
            'artificial_fixture_cores':4, 'artificial_fixture_origins':8,
            'artificial_closed_form_solves':32, 'artificial_prediction_rows':48,
            'analytic_Gaussian_CRPS_oracle_at_mu_equals_y':oracle,
            'checks':['whole mother-core splits','shared current-prefix/innovation transforms','fit-side different-core donor',
                      'C-only development-core crossfit common sigma','conditional means and CRPS analytic oracle',
                      'equal-core summaries','no held future in training or scale','future/core-leak rejection',
                      'unsupported donor explicit','real empty admission refuses before payload','received_metadata unchanged'],
            'received_metadata_sha256_before_and_after':before,'elapsed_seconds':elapsed,
            'no_additional_test_or_review_required_by_this_result':True}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',required=True);args=p.parse_args()
    result=benchmark(args.case)
    path=Path(args.case)/'benchmark_result_20261025.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
