import json
from pathlib import Path
import sys

import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from fixed_weight_roundoff import certify_negative_energy


FIXTURE = Path(__file__).parent / 'fixtures/fixed_weight_negative_energy_five_points.json'
POINTS = json.loads(FIXTURE.read_text())['points']


def args(point):
    return dict(xy=np.array(point['coordinates'],dtype=np.float64),
                u=np.array(point['u_node'],dtype=np.float64),
                d=np.array(point['d_node'],dtype=np.float64),
                native_shape=np.array(point['Nxi'],dtype=np.float64),
                native_derivative=np.array(point['dNdxi'],dtype=np.float64),
                raw_H=point['history'][0],raw_q=point['history'][2])


@pytest.mark.parametrize('point',POINTS)
def test_exact_five_points_have_rigid_translation_certificate(point):
    supplied = args(point)
    snapshots = {k:v.copy() for k,v in supplied.items() if isinstance(v,np.ndarray)}
    result = certify_negative_energy(**supplied)
    assert result['canonical_H'] == result['canonical_q'] == 0
    assert 0 < result['ratio'] <= 1
    assert result['absolute_bound'] >= abs(supplied['raw_H'])
    assert result['gamma_operation_count'] == sum(result['dot_operation_counts']) == 44
    assert len(result['branches']) == 2
    json.dumps(result,allow_nan=False)
    for key,value in snapshots.items():
        np.testing.assert_array_equal(value,supplied[key])


def test_rejects_one_ulp_nonconstant_displacement():
    supplied=args(POINTS[0]); supplied['u'][1,0]=np.nextafter(supplied['u'][1,0],np.inf)
    with pytest.raises(ValueError,match='bitwise constant'):
        certify_negative_energy(**supplied)


@pytest.mark.parametrize('mutation,message',[
    ('damage','zero nodal damage'),('q','raw_H == raw_q'),
    ('large','exceeds'),('dtype','float64'),('nonfinite','finite'),
    ('basis','partition of unity'),('shape','inconsistent'),
    ('det','determinant'),('reversed','determinant')])
def test_invalid_state_is_not_repaired(mutation,message):
    supplied=args(POINTS[0])
    if mutation=='damage': supplied['d'][0]=np.nextafter(0.,1.)
    elif mutation=='q': supplied['raw_q']=np.nextafter(supplied['raw_H'],0.)
    elif mutation=='large': supplied['raw_H']=supplied['raw_q']=-1e-6
    elif mutation=='dtype': supplied['u']=supplied['u'].astype(np.float32)
    elif mutation=='nonfinite': supplied['xy'][0,0]=np.nan
    elif mutation=='basis': supplied['native_derivative'][0,0]=np.nextafter(supplied['native_derivative'][0,0],np.inf)
    elif mutation=='shape': supplied['native_shape'][0]=0.
    elif mutation=='det': supplied['xy']*=1e-6
    elif mutation=='reversed': supplied['xy']=supplied['xy'][[0,3,2,1]]
    with pytest.raises(ValueError,match=message):
        certify_negative_energy(**supplied)


def test_bound_scales_quadratically_with_rigid_displacement():
    supplied=args(POINTS[0]); first=certify_negative_energy(**supplied)
    supplied['u']*=2.; supplied['raw_H']*=4.; supplied['raw_q']*=4.
    second=certify_negative_energy(**supplied)
    assert second['absolute_bound'] == pytest.approx(4*first['absolute_bound'],rel=1e-14,abs=0)


def test_tiny_u_does_not_hide_overflow_in_gp_stiffness():
    supplied=args(POINTS[0])
    supplied['xy']=np.array([[0.,0.],[1e-160,0.],[1e-160,1e160],[0.,1e160]])
    supplied['u']=np.tile([1e-200,2e-200],(4,1))
    supplied['raw_H']=supplied['raw_q']=-1e-100
    with pytest.raises(ValueError,match='overflow'):
        certify_negative_energy(**supplied)


def test_bitwise_condition_includes_signed_zero():
    supplied=args(POINTS[0]); supplied['u'][:]=0.; supplied['u'][0,0]=-0.
    with pytest.raises(ValueError,match='bitwise constant'):
        certify_negative_energy(**supplied)
