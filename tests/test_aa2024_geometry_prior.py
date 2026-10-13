import json
import sys
import tempfile
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
