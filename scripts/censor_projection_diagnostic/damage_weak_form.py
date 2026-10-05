"""Independent NumPy AT1 damage weak vector for strictly feasible nodal states.

Frozen fatigue coefficient; no derivative through its construction. The penalty
term vanishes only when d >= previous nodally (positive Q4 shape functions).
"""
import numpy as np


def assemble_damage(xy, conn, damage, previous, psi, fatigue):
    xy=np.asarray(xy);conn=np.asarray(conn);d=np.asarray(damage);prev=np.asarray(previous)
    psi=np.asarray(psi);fatigue=np.asarray(fatigue)
    if not all(np.isfinite(x).all() for x in (xy,d,prev,psi,fatigue)):
        raise ValueError('Nonfinite field')
    if not ((0<=prev).all() and (prev<=d).all() and (d<=1).all()):
        raise ValueError('Strict feasible state required; penalty cannot be omitted')
    if psi.shape!=(len(conn),4) or fatigue.shape!=psi.shape:
        raise ValueError('Expected native four-GP fields')
    signs=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])
    a=1/np.sqrt(3);res=np.zeros(len(xy));energy=0.
    for q,(xi,et) in enumerate(((a,a),(-a,a),(a,-a),(-a,-a))):
        n=(1+signs[:,0]*xi)*(1+signs[:,1]*et)/4
        dn=np.stack([signs[:,0]*(1+signs[:,1]*et),signs[:,1]*(1+signs[:,0]*xi)])/4
        jac=np.einsum('an,enb->eab',dn,xy[conn]);det=np.linalg.det(jac)
        if not (det>0).all():raise ValueError('Invalid Jacobian')
        grad=np.linalg.solve(jac,np.broadcast_to(dn,(len(conn),2,4)))
        dg=d[conn]@n;gd=np.einsum('ean,en->ea',grad,d[conn])
        # Gc=.01, ell=.01, cw=8/3, t=1; Gc/ell=1.
        frac=fatigue[:,q]/(8/3)
        local=(-2*(1-dg)*psi[:,q])[:,None]*n
        local+=frac[:,None]*(n+2*.01**2*np.einsum('ean,ea->en',grad,gd))
        np.add.at(res,conn.ravel(),(local*det[:,None]).ravel())
        energy+=np.sum(det*((1-dg)**2*psi[:,q]+frac*(dg+.01**2*(gd**2).sum(1))))
    return res,float(energy)
