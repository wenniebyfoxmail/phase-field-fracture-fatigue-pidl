"""Synthetic, already-validated fixtures only. Never load actual stage15."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import aa2024_geometry_prior as m
import aa2024_geometry_result_view as view


def receipt(root,mode,names,input_bindings=None):
    r=dict(mode=mode,execution_status='succeeded',run_id='SYNTHETIC_ONLY_'+mode,
        runner_sha256=m.sha(m.__file__),dependencies_sha256=m.sources(),
        artifacts_sha256={n:m.sha(root/n) for n in names})
    if input_bindings is not None:r['input_bindings']=input_bindings
    m.write_json(root/'execution_receipt.json',r)


def fixture(tmp_path):
    prep=tmp_path/'prepare';fit=tmp_path/'fit';val=tmp_path/'validation'
    for p in (prep,fit,val):p.mkdir()
    xx,yy=np.meshgrid(np.linspace(-15,15,9),np.linspace(-6,6,5));xy=np.c_[xx.ravel(),yy.ravel()]
    n=len(xy);ids=np.arange(1,n+1);w=np.linspace(.2,1,n)
    target=np.c_[.0001*xy[:,0],.0002*xy[:,1]]
    frozen=dict(ids=ids,xy=xy,weights=w,u13=np.zeros((n,2)),alpha=np.array(2.))
    for i,k in enumerate(m.ARMS):
        frozen[k]=target+(.0001*(i+1))*np.c_[xy[:,0]**2/20,xy[:,1]**2/10]
    np.savez_compressed(prep/'prepared.npz',**frozen)
    np.savez_compressed(prep/'training_geometry.npz',xy=xy)
    m.write_json(prep/'geometry_audit.json',dict(synthetic=True))
    m.write_json(prep/'preparation.json',dict(cycle='292018.5'))
    receipt(prep,'prepare',m.PREP)
    np.savez_compressed(fit/'frozen_predictions.npz',**frozen)
    np.savez_compressed(fit/'solved_fields.npz',synthetic=np.array([1]))
    m.write_json(fit/'fit.json',dict(status='four_predictions_frozen_before_held_response',
        source_prepare=m.bindings(prep,m.PREP),cycle='292018.5',held_member_sha256='SYNTHETIC_TARGET_ID'))
    receipt(fit,'fit',m.FIT,m.bindings(prep,m.PREP))
    keep=np.arange(n)!=3;fields=dict(ids=ids[keep],xy=xy[keep],weights=w[keep],target=target[keep]);scores={}
    for k in m.ARMS:
        fields[k]=frozen[k][keep]
        fields[k+'_residual']=view.closed_form_residual(xy[keep],fields[k]-fields['target'],w[keep])
        scores[k]=float(np.sum(w[keep]*np.linalg.norm(fields[k+'_residual'],axis=1))/w[keep].sum())
    np.savez_compressed(val/'validation_fields.npz',**fields)
    delta=scores['old']-scores['proxy']
    m.write_json(val/'metrics.json',dict(MAE_mm=scores,primary_old_minus_proxy_mm=delta,
        descriptive_outcome='improves' if delta>0 else 'equal' if delta==0 else 'worsens',
        source_fit=m.bindings(fit,m.FIT),target_member_sha256='SYNTHETIC_TARGET_ID',
        eligible=int(keep.sum()),frozen_support=n,missing_ids=ids[~keep].tolist(),
        area_coverage=float(w[keep].sum()/w.sum())))
    receipt(val,'validate',view.VALIDATION,m.bindings(fit,m.FIT))
    return prep,fit,val


def restamp(val,fit):receipt(val,'validate',view.VALIDATION,m.bindings(fit,m.FIT))


def test_render_synthetic_and_source_unchanged(tmp_path):
    prep,fit,val=fixture(tmp_path);out=tmp_path/'figures'
    before={str(p):m.sha(p) for r in (prep,fit,val) for p in r.iterdir()}
    with patch.object(m,'parse_nodemap',side_effect=AssertionError('no raw parser')),patch.object(m,'solve_patch',side_effect=AssertionError('no solve')):
        view.render(prep,fit,val,out)
    assert len(list(out.glob('*.png')))==len(list(out.glob('*.pdf')))==3
    for p,h in before.items():assert m.sha(Path(p))==h
    report=json.loads((out/'render_receipt.json').read_text())
    assert report['source_validation']==m.bindings(val,view.VALIDATION)
    assert report['source_fit']==m.bindings(fit,m.FIT)
    assert len(report['artifacts_sha256'])==12
    assert set(json.loads((out/'arithmetic_crosscheck.json').read_text()))==set(m.ARMS)
    assert 'SYNTHETIC_ONLY' in (out/'README_analysis.md').read_text()
    for image in out.glob('*.png'):
        note=image.with_suffix('.md').read_text().lower()
        assert len(note)>400
        for phrase in ('how to read','data provenance','limitation'):assert phrase in note
    with pytest.raises(ValueError,match='fresh'):view.render(prep,fit,val,out)
    print('SYNTHETIC_RESULT_FIGURES='+str(out))


@pytest.mark.parametrize('mutation',[
    'receipt','fit_link','prepare_link','prediction','weights','coordinates','residual',
    'metric','delta','outcome','target_hash','missing_ids','coverage','fractional_ids','nonfinite_target'])
def test_reject_mixed_or_inconsistent_packages_before_figures(tmp_path,mutation):
    prep,fit,val=fixture(tmp_path);out=tmp_path/'figures'
    metrics=json.loads((val/'metrics.json').read_text());fields=m.load(val/'validation_fields.npz')
    if mutation=='receipt':
        (val/'metrics.json').write_text('{}')
    elif mutation=='prepare_link':
        fm=json.loads((fit/'fit.json').read_text());fm['source_prepare']={};m.write_json(fit/'fit.json',fm)
        receipt(fit,'fit',m.FIT,m.bindings(prep,m.PREP))
    elif mutation in ('prediction','weights','coordinates','residual','fractional_ids','nonfinite_target'):
        if mutation=='prediction':fields['proxy'][0,0]+=.001
        if mutation=='weights':fields['weights'][0]*=2
        if mutation=='coordinates':fields['xy'][0,0]+=.001
        if mutation=='residual':fields['proxy_residual'][0,0]+=.001
        if mutation=='fractional_ids':fields['ids']=fields['ids'].astype(float)+.5
        if mutation=='nonfinite_target':fields['target'][0,0]=np.nan
        np.savez_compressed(val/'validation_fields.npz',**fields);restamp(val,fit)
    else:
        if mutation=='fit_link':metrics['source_fit']={}
        if mutation=='metric':metrics['MAE_mm']['proxy']*=2
        if mutation=='delta':metrics['primary_old_minus_proxy_mm']+=.001
        if mutation=='outcome':metrics['descriptive_outcome']='invented'
        if mutation=='target_hash':metrics['target_member_sha256']='OTHER_TARGET'
        if mutation=='missing_ids':metrics['missing_ids']=[]
        if mutation=='coverage':metrics['area_coverage']=1
        m.write_json(val/'metrics.json',metrics);restamp(val,fit)
    with pytest.raises(ValueError):view.render(prep,fit,val,out)
    assert not out.exists()


def test_zero_errors_and_delta_tie_are_valid(tmp_path):
    prep,fit,val=fixture(tmp_path)
    frozen=m.load(fit/'frozen_predictions.npz');fields=m.load(val/'validation_fields.npz')
    # Synthetic zero-error tie, never modify actual frozen predictions.
    raw=np.tile([.001,-.002],(len(frozen['ids']),1))
    for k in m.ARMS:frozen[k]=raw.copy()
    np.savez_compressed(fit/'frozen_predictions.npz',**frozen)
    receipt(fit,'fit',m.FIT,m.bindings(prep,m.PREP))
    fields['target']=np.tile([.001,-.002],(len(fields['ids']),1))
    for k in m.ARMS:fields[k]=fields['target'].copy();fields[k+'_residual']=np.zeros_like(fields['target'])
    np.savez_compressed(val/'validation_fields.npz',**fields)
    metrics=json.loads((val/'metrics.json').read_text());metrics.update(MAE_mm={k:0. for k in m.ARMS},
        primary_old_minus_proxy_mm=0.,descriptive_outcome='equal',source_fit=m.bindings(fit,m.FIT))
    m.write_json(val/'metrics.json',metrics);restamp(val,fit)
    _,mout,_,_=view.checked_data(prep,fit,val);assert mout['descriptive_outcome']=='equal'
    view.render(prep,fit,val,tmp_path/'zero_figures')


def test_scalar_projection_matches_reviewed_global_quotient():
    xy=np.array([[-2.,-1],[3,-2],[-1,4],[2,2],[1,-3]])
    w=np.array([.1,.8,2.,3.,.7])
    raw=np.c_[xy[:,0]**2*.001+2-.03*xy[:,1],xy[:,1]**2*.002-3+.03*xy[:,0]]
    np.testing.assert_allclose(view.closed_form_residual(xy,raw,w),
        m.quotient_residual(xy,raw,w),rtol=1e-10,atol=1e-14)
