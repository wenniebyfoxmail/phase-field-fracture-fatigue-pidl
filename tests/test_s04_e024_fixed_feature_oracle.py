import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e024_fixed_feature_oracle import project_head

def test_weighted_linear_solution_with_bias_and_zero_support():
    x=np.array([[1.,0.,1.],[0.,1.,1.],[1.,1.,1.],[0.,0.,0.],[2.,1.,1.]])
    beta=np.array([[2.,-1.],[1.,3.],[4.,2.]])
    y=x@beta;y[3]=[7.,-2.];m=np.array([1.,4.,2.,3.,5.])
    result,info=project_head(x,y,m)
    for row in result:
        np.testing.assert_allclose(row['coef'],beta,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(row['direct_rms'],np.sqrt(3/15*53),rtol=1e-12)
        assert row['rank']==3 and row['prediction'][3].tolist()==[0.,0.]
    assert info['svd_orthogonality_inf']<1e-12

def test_rank_deficiency_and_nonuniform_weights_match_lstsq():
    rng=np.random.default_rng(3);a=rng.normal(size=(100,4));x=np.c_[a,a[:,1]+2*a[:,3],np.zeros(100)]
    y=rng.normal(size=(100,2));mass=np.linspace(.1,5,100);sw=np.sqrt(mass/mass.sum())
    rows,info=project_head(x,y,mass)
    c=np.linalg.lstsq(sw[:,None]*x,sw[:,None]*y,rcond=info['base_rcond'])[0]
    assert all(r['rank']==4 for r in rows)
    np.testing.assert_allclose(rows[1]['prediction'],x@c,rtol=1e-11,atol=1e-12)
    assert rows[1]['projection_realization_weighted_gap']<1e-12

@pytest.mark.parametrize('bad',['mass','shape','nan','zero'])
def test_invalid_inputs_refused(bad):
    x=np.eye(3);y=np.ones((3,2));m=np.ones(3)
    if bad=='mass':m[0]=0
    elif bad=='shape':y=y[:2]
    elif bad=='nan':x[0,0]=np.nan
    else:x[:]=0
    with pytest.raises(ValueError):project_head(x,y,m)
