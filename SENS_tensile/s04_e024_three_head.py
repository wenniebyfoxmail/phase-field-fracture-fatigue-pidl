"""D010: one-axis enrichment and strict finite-field admission, no fitting."""
import numpy as np

GUARDS = ('uv_full','uv_damage','uv_background','uv_inside_background',
          'weak_squared','driver_background','driver_inside_background')


def enrich_basis(old, direction):
    old, direction = np.asarray(old, dtype=np.float64), np.asarray(direction, dtype=np.float64)
    if old.ndim != 3 or old.shape[0] != 2 or old.shape[1:] != direction.shape:
        raise ValueError('two-basis/head-direction schema')
    if not np.isfinite(old).all() or not np.isfinite(direction).all():
        raise ValueError('nonfinite direction')
    flat = old.reshape(2,-1); v = direction.ravel()
    np.testing.assert_allclose(np.einsum('ij,kj->ik',flat,flat),np.eye(2),rtol=0,atol=1e-12)
    if abs(np.linalg.norm(v)-1)>1e-12: raise ValueError('unit verified direction required')
    projection = np.einsum('ij,j->i',flat,v)
    orth = v-np.einsum('i,ij->j',projection,flat); norm = np.linalg.norm(orth)
    if norm<=1e-8: raise ValueError('new direction not resolved outside old plane')
    basis = np.concatenate([old,(orth/norm).reshape((1,)+direction.shape)],axis=0)
    coordinates = np.r_[projection,norm]
    realized = np.einsum('i,ijk->jk',coordinates,basis)
    np.testing.assert_allclose(np.einsum('ijk,ljk->il',basis,basis),np.eye(3),rtol=0,atol=1e-12)
    gap = float(np.max(abs(realized-direction)))
    if gap>1e-12: raise ValueError('three-dimensional reconstruction')
    return basis,coordinates,realized,dict(orthogonal_remainder_norm=float(norm),reconstruction_max_abs=gap)


def admit_finite(values, baseline, delta_relative):
    if set(values)!=set(GUARDS) or set(baseline)!=set(GUARDS): raise ValueError('finite guard schema')
    if not np.isfinite([*values.values(),*baseline.values(),delta_relative]).all():
        raise ValueError('nonfinite actual guard')
    if min(baseline.values())<=0 or min(values.values())<0 or delta_relative<0:
        raise ValueError('invalid squared-error guard')
    failures=[key for key in GUARDS if values[key]>baseline[key]]
    if delta_relative>.02*(1+1e-12): failures.append('parameter_budget')
    return not failures,failures


def uv_safe_fraction(error, velocity, weights):
    """Half the smallest positive UV zero crossing; velocity is one full R step."""
    error,velocity=np.asarray(error),np.asarray(velocity)
    if error.ndim!=2 or error.shape!=velocity.shape or error.shape[1]!=2:
        raise ValueError('UV quadratic schema')
    if not np.isfinite(error).all() or not np.isfinite(velocity).all():raise ValueError('nonfinite UV quadratic')
    terms={}
    for name,weight in weights.items():
        weight=np.asarray(weight)
        if weight.shape!=(len(error),) or not np.isfinite(weight).all() or np.any(weight<0) or weight.sum()<=0:
            raise ValueError('UV quadratic weights')
        c=float(np.sum(weight[:,None]*error**2))
        b=float(np.sum(weight[:,None]*error*velocity))
        aa=float(np.sum(weight[:,None]*velocity**2))
        if not np.isfinite([c,b,aa]).all() or c<=0 or aa<=0 or b>=0:
            raise ValueError('no resolved descending UV quadratic')
        crossing=-2*b/aa
        if not np.isfinite(crossing) or crossing<=0:raise ValueError('UV crossing unresolved')
        terms[name]=dict(constant=c,linear_half=b,quadratic=aa,positive_zero_crossing=crossing)
    if not terms:raise ValueError('UV regions missing')
    fraction=min(1.,.5*min(t['positive_zero_crossing'] for t in terms.values()))
    if fraction<=0 or not np.isfinite(fraction):raise ValueError('UV safe fraction unresolved')
    return fraction,terms
