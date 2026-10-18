"""D008: fixed D007 plane, one additional exact nodal-background UV constraint."""
import numpy as np
from scipy.optimize import minimize


def background_plane(q,g,h,t,bg_g,bg_q):
    arrays=[np.asarray(v,dtype=np.float64) for v in (q,g,h,t,bg_g,bg_q)]
    q,g,h,t,bg_g,bg_q=arrays
    if any(not np.isfinite(v).all() for v in arrays):raise ValueError('nonfinite plane input')
    if any(v.shape!=(2,2) for v in (q,t,bg_q)) or any(v.shape!=(2,) for v in (g,h,bg_g)):raise ValueError('plane shape')
    dot=lambda a,b:float(np.einsum('i,i',a,b))
    mv=lambda m,z:np.einsum('ij,j->i',m,z)
    quad=lambda z,m:float(np.einsum('i,ij,j',z,m,z))
    objective=lambda z:dot(g,z)+.5*quad(z,q)
    weak=lambda z:-2*dot(h,z)-quad(z,t)
    background=lambda z:-2*dot(bg_g,z)-quad(z,bg_q)
    result=minimize(objective,np.zeros(2),jac=lambda z:g+mv(q,z),method='SLSQP',constraints=[
        dict(type='ineq',fun=lambda z:1-dot(z,z),jac=lambda z:-2*z),
        dict(type='ineq',fun=weak,jac=lambda z:-2*h-2*mv(t,z)),
        dict(type='ineq',fun=background,jac=lambda z:-2*bg_g-2*mv(bg_q,z))],options=dict(maxiter=100,ftol=1e-12))
    z=result.x
    finite=bool(np.isfinite(z).all() and np.isfinite([weak(z),background(z),objective(z)]).all())
    feasible=bool(finite and dot(z,z)<=1+1e-10 and weak(z)>=-1e-10 and background(z)>=-1e-10)
    return z,dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),plane_ball=dot(z,z),linearized_force_guard=weak(z),background_proxy_guard=background(z),proxy_objective=objective(z),feasible=feasible)
