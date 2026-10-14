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
    assert p['orthogonal_RMS_mm']<1e-14
    assert p['tilt_degrees']==pytest.approx(np.degrees(np.arctan(np.sqrt(13))))
    np.testing.assert_allclose(p['unit_normal_xyz'],np.array([-2,-3,1])/np.sqrt(14))
    mesh,t,_=m.rectangular_mesh(nx=3,ny=3,width=2,height=2)
    c=m.prior_coverage(mesh,t,np.zeros(9));assert c['lumped_damage_area_mm2']==0
    assert c['degradation_area_integral_mm2']==pytest.approx(4*(1+1e-6))

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
                    body='\n'.join(f'{i+1};{x};{y};{.01*x};{f*.001*x};{f*(.002*np.sign(y)*np.exp(-((x-1)/6)**2)+.001*y)};0;0;0;0;0' for i,(x,y) in enumerate(xy))
                z.writestr(f'global_3d_dic/Nodemaps/global_3d_dic_results_1_{stage}.txt',header+body)
            z.writestr('global_3d_dic/Connections/global_3d_dic_results_1_13_connections.txt','Type;Element #;Node 1;Node 2;Node 3\n'+'\n'.join(f'3;{i};{a};{b};{c}' for i,(a,b,c) in enumerate(t)))
        with patch.object(m,'EXPECTED_SIZE',archive.stat().st_size),patch.object(m,'EXPECTED_MD5',hashlib.md5(archive.read_bytes()).hexdigest()),patch.object(m,'parse_nodemap',wraps=m.parse_nodemap) as parser:
            m.prepare(archive,out);assert parser.call_count==2
        audit=json.loads((out/'geometry_audit.json').read_text())
        assert len(audit['profiles']['3.6']['outer_indices'])==14
        assert audit['plane']['tilt_degrees']==pytest.approx(np.degrees(np.arctan(.01)))
        a=m.load(out/'prepared.npz');assert len(a['mesh'])==861 and a['boundary'].sum()==120
        meta=json.loads((out/'preparation.json').read_text())
        assert len(meta['boundary_interpolation'])==120 and set(meta['prior_coverage'])=={'old','proxy'}
        assert meta['proxy_geometry']['length_mm']>0
