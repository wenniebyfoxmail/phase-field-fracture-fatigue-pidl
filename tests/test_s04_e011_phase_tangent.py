"""Trial-fatigue directional derivative must agree with residual differences."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parents[1]/'tools/s04_e011_analysis'))
from audit_phase_tangent import assemble,phase_jvp,q4_geometry


def test_full_trial_f_derivative_and_inactive_fatigue_control():
    points=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
    cells=np.array([[0,1,2,3]]);N,B,w,_=q4_geometry(points,cells)
    d=np.array([.2,.3,.4,.25]);direction=np.array([.01,-.02,.03,.02]);lower=np.zeros(4)
    h=np.zeros((1,4,4));h[:,:,3]=1
    for energy,active in [(2.,True),(.1,False)]:
        raw=np.full((1,4),energy);r,state=assemble(d,raw,lower,h,cells,N,B,w,4)
        full=phase_jvp(direction,np.zeros_like(raw),state,cells,N,B,w,4,True)
        picard=phase_jvp(direction,np.zeros_like(raw),state,cells,N,B,w,4,False)
        r1,_=assemble(d+1e-6*direction,raw,lower,h,cells,N,B,w,4)
        diff=(r1-r)/1e-6
        assert np.linalg.norm(diff-full)/np.linalg.norm(full)<2e-6
        if active:assert np.linalg.norm(diff-picard)/np.linalg.norm(diff)>.05
        else:np.testing.assert_array_equal(full,picard)
