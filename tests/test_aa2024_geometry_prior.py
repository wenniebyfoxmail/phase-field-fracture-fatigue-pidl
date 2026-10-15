import json
import sys
import tempfile
import hashlib
import zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import aa2024_geometry_prior as m

def test_affine_interpolation():
    x,y=np.meshgrid(np.arange(-3.,4),np.arange(-3.,4));xy=np.c_[x.ravel(),y.ravel()]
    v=np.c_[1+xy[:,0]-2*xy[:,1],3+2*xy[:,0]+xy[:,1]]
    p=np.array([[.2,.3],[-1.2,1.7]])
    got,dist,ranks=m.affine_at(xy,v,p)
    np.testing.assert_allclose(got,np.c_[1+p[:,0]-2*p[:,1],3+2*p[:,0]+p[:,1]],atol=1e-14)
    assert ranks==[3,3] and np.all(dist<=2)

def test_halfheight_and_lobe_rule():
    x=np.arange(-10.,11);y=np.maximum(1-np.abs(x)/4,0)
    c=m.halfheight(x,y);assert c['left_mm']==-2 and c['right_mm']==2
    y[0]=.75;c=m.halfheight(x,y);assert c['lobes_above_halfheight']==2
    assert c['left_mm']==-2 and c['peak_x_mm']==0
    with pytest.raises(ValueError):m.halfheight(x,np.ones(len(x)))
    with pytest.raises(ValueError):m.halfheight(x,np.zeros(len(x)))
    y[3]=np.nan
    with pytest.raises(ValueError):m.halfheight(x,y)

def test_primary_profile_rigid_invariance():
    x,y=np.meshgrid(m.X,np.arange(-7.2,7.21,.9));xy=np.c_[x.ravel(),y.ravel()]
    v=np.c_[np.zeros(len(xy)),.004*np.exp(-(xy[:,0]/6)**2)*np.sign(xy[:,1])+.001*xy[:,1]]
    rigid=np.c_[2-.2*xy[:,1],-3+.2*xy[:,0]]
    a=m.profile(xy,v,3.6);b=m.profile(xy,v+rigid,3.6)
    np.testing.assert_allclose(a['corrected_mm'],b['corrected_mm'],atol=3e-15)
    assert a['crossings'] is not None and a['crossings']['left_mm']<0<a['crossings']['right_mm']
    assert a['crossings']['left_mm']==pytest.approx(b['crossings']['left_mm'],abs=1e-10)

def test_priors_and_connection_validation():
    xy=np.array([[0.,0.],[1,0],[0,1]])
    d=m.segment_prior(xy,-9,6);assert d[0]==1 and np.all((d>=0)&(d<=1))
    s='Type;Element #;Node 1;Node 2;Node 3\n3;1;0;1;2\n3;2;-1;-1;-1'
    np.testing.assert_allclose(m.area_weights(s,xy,np.ones(3,bool)),np.full(3,1/6))
    for bad in (s+'\n3;3;2;0;1',s.replace('0;1;2','-1;1;2'),s.replace('0;1;2','0;1;3')):
        with pytest.raises(ValueError):m.area_weights(bad,xy,np.ones(3,bool))

def test_stage15_header_does_not_parse_body():
    h=m.headers('# current_stage_index:15\n# reference_stage_index:1\n# cycles:292018.5\n# force:3\n1;FORBIDDEN')
    assert m.identity(h,15)==3
    with pytest.raises(ValueError):m.identity(h,12)

def test_finalization_overrun_failed_receipt():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'out';args=['driver','fit','--input',td,'--output',str(out),'--source-commit','synthetic','--run-id','synthetic']
        with patch.object(sys,'argv',args),patch.object(m.socket,'gethostname',return_value='GPUServer8'),patch.object(m,'completed'),patch.object(m,'bindings',return_value={}),patch.object(m,'fit'),patch.object(m.time,'monotonic',side_effect=[0,599.999,600]):
            with pytest.raises(TimeoutError):m.main()
        r=json.loads((out/'execution_receipt.json').read_text());assert r['execution_status']=='failed'

def test_missing_support_and_failed_receipt_stop_before_high():
    p=m.profile(np.array([[0.,0.],[1,0],[0,1],[1,1]]),np.zeros((4,2)),3.6)
    assert p['crossings'] is None and not all(p['supported'])
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);m.write_json(root/'execution_receipt.json',dict(mode='fit',execution_status='failed'))
        with pytest.raises(ValueError):m.validate(root,root/'ABSENT_HELD',root)

def test_distance_ties_use_facet_ids_and_are_permutation_invariant():
    xy=np.array([[-1.,0.],[1.,0.],[0.,-1.],[0.,1.],[1.,1.]])
    ids=np.array([9,3,7,1,11]);du=np.c_[xy[:,0]**2,xy[:,1]**2]
    notes=[];a=m.affine_at(xy,du,np.array([[0.,0.]]),ids=ids,diagnostics=notes)[0]
    assert notes[0]['neighbor_ids']==[1,3,7,9]
    order=np.array([3,4,1,0,2]);other=[]
    b=m.affine_at(xy[order],du[order],np.array([[0.,0.]]),ids=ids[order],diagnostics=other)[0]
    np.testing.assert_array_equal(a,b);assert other==notes
    assert sum(notes[0]['coefficients'])==pytest.approx(1)
    assert notes[0]['condition_number']>=1 and notes[0]['coefficient_L1']>=1

def test_same_side_never_uses_opposite_facet():
    xy=np.array([[0.,-.1],[0.,.1],[-.3,.2],[.3,.2],[0.,.4]])
    notes=[];m.affine_at(xy,np.c_[xy[:,0],xy[:,1]],np.array([[0.,1.8]]),same_side=True,diagnostics=notes)
    assert 1 not in notes[0]['neighbor_ids'] and notes[0]['supported']
    missing=[];v,_,_=m.affine_at(xy[:3],np.zeros((3,2)),np.array([[0.,1.8]]),same_side=True,diagnostics=missing)
    assert not missing[0]['supported'] and np.isnan(v).all()

def test_plateau_bounds_and_missing_component():
    x=np.arange(-5.,6);y=np.array([0,0,.5,.5,1,1,1,.5,.5,0,0.])
    c=m.halfheight(x,y);assert c['left_mm']==-3 and c['right_mm']==3
    assert c['peak_x_mm']==-1 and c['left_bracket_mm']==[-4,-3]
    y[0]=np.nan;assert m.halfheight(x,y,allow_missing=True)['left_mm']==-3
    y[2]=np.nan
    with pytest.raises(ValueError,match='missing'):m.halfheight(x,y,allow_missing=True)

def test_primary_outer14_and_secondary_needs_both_tails():
    x,y=np.meshgrid(m.X,np.arange(-7.2,7.21,.9));xy=np.c_[x.ravel(),y.ravel()]
    du=np.c_[np.zeros(len(xy)),.004*np.exp(-(xy[:,0]/6)**2)*np.sign(xy[:,1])]
    primary=m.profile(xy,du,3.6)
    assert len(primary['outer_indices'])==14 and len(primary['outer_residual_mm'])==14
    assert len(primary['interpolation'])==106
    keep=xy[:,0]>-10
    secondary=m.profile(xy[keep],du[keep],2.7)
    assert secondary['crossings'] is None and 'both sides' in secondary['issue']

def test_tilted_flat_plane_and_coverage_decomposition():
    xy=np.array([[-1.,-1],[1,-1],[-1,1],[1,1]])
    p=m.plane_diagnostic(np.c_[xy,2*xy[:,0]+3*xy[:,1]+4],np.zeros((4,3)))
    assert p['OLS_plane_orthogonal_RMS_mm']<1e-14
    assert p['tilt_degrees']==pytest.approx(np.degrees(np.arctan(np.sqrt(13))))
    np.testing.assert_allclose(p['unit_normal_xyz'],np.array([-2,-3,1])/np.sqrt(14))
    mesh,t,_=m.rectangular_mesh(nx=3,ny=3,width=2,height=2)
    c=m.prior_coverage(mesh,t,np.zeros(9));assert c['discrete_prior_integral_mm2']==0
    assert c['degradation_area_integral_mm2']==pytest.approx(4*(1+1e-6))
    assert c['area_mean_local_degradation_fraction']==pytest.approx(0)
    c=m.prior_coverage(mesh,t,np.ones(9)*.5)
    assert c['discrete_prior_integral_mm2']==pytest.approx(2)
    assert c['area_mean_local_stiffness_multiplier']==pytest.approx(.25+1e-6)
    assert c['area_mean_local_degradation_fraction']==pytest.approx(1-(.25+1e-6)/(1+1e-6))

def test_displacement_rms_is_not_reference_coordinate_difference():
    xyz=np.array([[-1.,-1,0],[1,-1,0],[-1,1,0],[1,1,0]])
    p=m.plane_diagnostic(xyz,np.tile([3.,4.,12.],(4,1)))
    assert p['reference_coordinates']=='stage13_serialized_reference_XYZ'
    assert p['displacement_component_order']==['delta_U','delta_V','delta_W']
    np.testing.assert_allclose(p['raw_displacement_increment_RMS_UVW_mm'],[3,4,12])
    assert p['OLS_plane_orthogonal_RMS_mm']==0

def test_three_mocked_solves_and_budget_blocks_prefix():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'prep';root.mkdir();out=Path(td)/'fit';out.mkdir()
        mesh,t,bd=m.rectangular_mesh(nx=3,ny=3,width=36,height=18)
        xy=mesh;np.savez_compressed(root/'prepared.npz',ids=np.arange(1,10),xy=xy,weights=np.ones(9),
            u13=np.zeros((9,2)),alpha=2,train_v=.001*xy,mesh=mesh,tri=t,boundary=bd,bc=.001*mesh[bd],old=np.zeros(9),proxy=np.zeros(9))
        m.write_json(root/'preparation.json',dict(cycle='292018.5',forces=[1,2,3],held_member_sha256='synthetic',proxy_geometry={}))
        # Mock regular sampling because the production mesh is deliberately not solved here.
        with patch.object(m,'completed'),patch.object(m,'bindings',return_value={}),patch.object(m,'solve_patch',return_value=(.001*xy,1e-15)) as s,patch.object(m,'sample_regular_mesh',return_value=.001*xy),patch.object(m.time,'monotonic',return_value=1):
            m.fit(root,out,0);assert s.call_count==3
        assert set(m.load(out/'frozen_predictions.npz'))>=set(m.ARMS)
        bad=Path(td)/'overrun';bad.mkdir()
        with patch.object(m,'completed'),patch.object(m,'solve_patch') as s,patch.object(m.time,'monotonic',return_value=600):
            with pytest.raises(TimeoutError):m.fit(root,bad,0)
            s.assert_not_called();assert not (bad/'fit.json').exists()

def test_synthetic_prepare_never_converts_stage15_body():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);archive=root/'toy.zip';out=root/'prep';out.mkdir()
        xy,t,_=m.rectangular_mesh(nx=57,ny=21,width=50.4,height=18)
        schema='# ID; x_undef [mm]; y_undef [mm]; z_undef [mm]; u [mm]; v [mm]; w [mm]; epsx [%]; epsy [%]; epsxy [1]; epseqv [%]\n'
        with zipfile.ZipFile(archive,'w') as z:
            for stage,f in ((13,1),(14,2),(15,3)):
                header=f'# current_stage_index:{stage}\n# reference_stage_index:1\n# cycles:292018.5\n# force:{f}\n'+schema
                body='1;FORBIDDEN;FORBIDDEN;FORBIDDEN;FORBIDDEN;FORBIDDEN;FORBIDDEN;0;0;0;0'
                if stage!=15:
                    body='\n'.join(f'{i+1};{x+(5e-7 if stage==14 else 0)};{y};{.01*x};{f*.001*x};{f*(.002*np.sign(y)*np.exp(-((x-1)/6)**2)+.001*y)};0;0;0;0;0' for i,(x,y) in enumerate(xy))
                z.writestr(f'global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt',header+body)
            z.writestr('global_3d_dic/Connections/global_3d_dic_results_1_13_connections.txt','Type;Element #;Node 1;Node 2;Node 3\n'+'\n'.join(f'3;{i};{a};{b};{c}' for i,(a,b,c) in enumerate(t)))
        with patch.object(m,'EXPECTED_SIZE',archive.stat().st_size),patch.object(m,'EXPECTED_MD5',hashlib.md5(archive.read_bytes()).hexdigest()),patch.object(m,'parse_nodemap',wraps=m.parse_nodemap) as parser:
            m.prepare(archive,out);assert parser.call_count==2
        audit=json.loads((out/'geometry_audit.json').read_text())
        assert len(audit['profiles']['3.6']['outer_indices'])==14
        assert audit['plane']['tilt_degrees']==pytest.approx(np.degrees(np.arctan(.01)))
        a=m.load(out/'prepared.npz');assert len(a['mesh'])==861 and a['boundary'].sum()==120
        obs=(np.abs(xy[:,0])<16.2)&(np.abs(xy[:,1])<7.2)
        np.testing.assert_array_equal(a['xy'],xy[obs])
        meta=json.loads((out/'preparation.json').read_text())
        assert len(meta['boundary_interpolation'])==120 and set(meta['prior_coverage'])=={'old','proxy'}
        assert meta['proxy_geometry']['length_mm']>0

def mock_prepared(root,alpha=2.):
    root.mkdir()
    mesh,t,bd=m.rectangular_mesh(nx=3,ny=3,width=36,height=18)
    np.savez_compressed(root/'prepared.npz',ids=np.arange(1,10),xy=mesh,weights=np.ones(9),
        u13=np.zeros((9,2)),alpha=alpha,train_v=.001*mesh,mesh=mesh,tri=t,boundary=bd,
        bc=.001*mesh[bd],old=np.zeros(9),proxy=np.zeros(9))
    m.write_json(root/'preparation.json',dict(cycle='292018.5',forces=[1,2,3],held_member_sha256='toy',proxy_geometry={}))
    return mesh

def test_nonfinite_alpha_has_failed_receipt_before_any_solve(tmp_path):
    root=tmp_path/'prep';mock_prepared(root,np.inf);out=tmp_path/'fit'
    args=['driver','fit','--input',str(root),'--output',str(out),'--source-commit','toy','--run-id','toy']
    with patch.object(sys,'argv',args),patch.object(m.socket,'gethostname',return_value='GPUServer8'),patch.object(m,'completed'),patch.object(m,'bindings',return_value={}),patch.object(m,'solve_patch') as solve:
        with pytest.raises(ValueError,match='alpha'):m.main()
        solve.assert_not_called()
    assert json.loads((out/'execution_receipt.json').read_text())['execution_status']=='failed'
    assert not (out/'frozen_predictions.npz').exists()

def test_prediction_overflow_stops_before_freeze_and_held_parse(tmp_path):
    root=tmp_path/'prep';mesh=mock_prepared(root,1e308);out=tmp_path/'fit';out.mkdir()
    with patch.object(m,'completed'),patch.object(m,'solve_patch',return_value=(mesh,0)),patch.object(m,'sample_regular_mesh',return_value=mesh),np.errstate(over='ignore',invalid='ignore'):
        with pytest.raises(ValueError,match='frozen prediction'):m.fit(root,out,m.time.monotonic())
    assert not (out/'frozen_predictions.npz').exists()
    m.write_json(out/'fit.json',dict(status='four_predictions_frozen_before_held_response'))
    bad={k:np.zeros((12,2)) for k in ('xy','u13')+m.ARMS}
    bad.update(ids=np.arange(1,13),weights=np.ones(12),alpha=np.array(2.))
    bad['proxy'][0,0]=np.inf;np.savez_compressed(out/'frozen_predictions.npz',**bad)
    with patch.object(m,'completed'),patch.object(m,'parse_nodemap') as parser:
        with pytest.raises(ValueError,match='frozen prediction'):m.validate(out,tmp_path/'NONEXISTENT_HELD',tmp_path)
        parser.assert_not_called()

def test_tied_separated_maxima_select_first_only():
    x=np.arange(-6.,7);y=np.zeros(13);y[3]=y[9]=1
    c=m.halfheight(x,y)
    assert c['peak_x_mm']==-3 and c['left_mm']==-3.5 and c['right_mm']==-2.5
    assert c['lobes_above_halfheight']==2

@pytest.mark.parametrize('checks_before_failure',[5,7])
def test_third_solve_or_serialization_overrun_fails_whole_fit(tmp_path,checks_before_failure):
    root=tmp_path/'prep';mesh=mock_prepared(root);out=tmp_path/'fit'
    args=['driver','fit','--input',str(root),'--output',str(out),'--source-commit','toy','--run-id','toy']
    checks=[None]*checks_before_failure+[TimeoutError('soft600s synthetic')]
    with patch.object(sys,'argv',args),patch.object(m.socket,'gethostname',return_value='GPUServer8'),patch.object(m,'completed'),patch.object(m,'bindings',return_value={}),patch.object(m,'solve_patch',return_value=(mesh*.001,0)) as solve,patch.object(m,'sample_regular_mesh',return_value=mesh*.001),patch.object(m,'check_budget',side_effect=checks):
        with pytest.raises(TimeoutError):m.main()
        assert solve.call_count==3
    assert json.loads((out/'execution_receipt.json').read_text())['execution_status']=='failed'
    assert (out/'frozen_predictions.npz').exists()==(checks_before_failure==7)

def test_successful_validation_restricts_one_common_planar_support(tmp_path):
    root=tmp_path/'fit';root.mkdir();out=tmp_path/'validate';out.mkdir()
    xy=np.c_[np.tile(np.arange(4.),3),np.repeat(np.arange(3.),4)]
    a={k:np.zeros((12,2)) for k in ('u13',)+m.ARMS}
    a.update(ids=np.arange(1,13),xy=xy,weights=np.arange(1.,13),alpha=np.array(2.))
    np.savez_compressed(root/'frozen_predictions.npz',**a)
    high=tmp_path/'toy_high';high.write_text('synthetic parser stub; not real field')
    m.write_json(root/'fit.json',dict(status='four_predictions_frozen_before_held_response',held_member_sha256=m.sha(high),held_force=3))
    h=dict(headers=dict(current_stage_index='15',reference_stage_index='1',cycles='292018.5',force='3'),
        ids=a['ids'],xyz=np.c_[xy,np.full(12,np.nan)],u=np.zeros((12,3)))
    h['u'][:,2]=np.nan;h['u'][0,0]=np.nan
    with patch.object(m,'completed'),patch.object(m,'bindings',return_value={}),patch.object(m,'parse_nodemap',return_value=h) as parser:
        m.validate(root,high,out);parser.assert_called_once()
    result=m.load(out/'validation_fields.npz');metrics=json.loads((out/'metrics.json').read_text())
    np.testing.assert_array_equal(result['ids'],a['ids'][1:])
    np.testing.assert_array_equal(result['weights'],a['weights'][1:])
    assert metrics['eligible']==11 and all(v==0 for v in metrics['MAE_mm'].values())

def test_training_renderer_source_binding_and_no_held_access(tmp_path):
    import aa2024_geometry_prior_view as view
    root=tmp_path/'prep';mesh=mock_prepared(root);out=tmp_path/'figures';out.mkdir()
    xy=np.array([[x,y] for y in np.arange(-7.2,7.21,.9) for x in m.X])
    du=np.c_[xy[:,0]*.001,.004*np.sign(xy[:,1])*np.exp(-(xy[:,0]/6)**2)]
    profiles={str(b):m.profile(xy,du,b) for b in (3.6,1.8,2.7)}
    mesh,tri,bd=m.rectangular_mesh();cross=profiles['3.6']['crossings']
    old=m.segment_prior(mesh,-9,6);proxy=m.segment_prior(mesh,cross['left_mm'],cross['right_mm'])
    obs=(np.abs(xy[:,0])<16.2)&(np.abs(xy[:,1])<7.2)
    np.savez_compressed(root/'prepared.npz',mesh=mesh,tri=tri,boundary=bd,bc=.0001*mesh[bd],
        xy=xy[obs],weights=np.ones(obs.sum())*.81,old=old,proxy=proxy)
    m.write_json(root/'geometry_audit.json',dict(profiles=profiles))
    np.savez_compressed(root/'training_geometry.npz',xy=xy)
    meta=json.loads((root/'preparation.json').read_text());meta.update(proxy_geometry=cross,
        prior_coverage={k:m.prior_coverage(mesh,tri,d) for k,d in (('old',old),('proxy',proxy))})
    m.write_json(root/'preparation.json',meta)
    m.write_json(root/'execution_receipt.json',dict(mode='prepare',run_id='SYNTHETIC_ONLY',execution_status='succeeded',runner_sha256=m.sha(m.__file__),dependencies_sha256=m.sources(),artifacts_sha256={n:m.sha(root/n) for n in m.PREP}))
    with patch.object(m,'parse_nodemap',side_effect=AssertionError('no parser')),patch.object(m,'solve_patch',side_effect=AssertionError('no solve')):
        view.assets(root,out)
    assert len(list(out.glob('*.png')))==len(list(out.glob('*.pdf')))==2
    receipt=json.loads((out/'render_receipt.json').read_text())
    assert receipt['source_prepare']==m.bindings(root,m.PREP)
    assert len(receipt['artifacts_sha256'])==7
    for name in ('README_analysis.md','training_profiles.md','training_spatial_assets.md'):
        assert 'SYNTHETIC_ONLY' in (out/name).read_text()
    (root/'geometry_audit.json').write_text('{}')
    with pytest.raises(ValueError,match='artifact'):view.assets(root,out)
    print('SYNTHETIC_FIGURES='+str(out))
