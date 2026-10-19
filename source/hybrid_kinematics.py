"""Hybrid-only Q4 geometry with fixed float64 operation order across BLAS builds.

No LAPACK determinant/inverse or contracted dot products participate in the
identity. This keeps the FULL derived-operator byte identity strict, rather
than dropping B/det from its hash or rounding coefficients to pass admission.
"""
import numpy as np
from damage_conditioned_equilibrium import Q4Kinematics


def build_portable_native_q4_kinematics(points,cells):
    points=np.asarray(points,dtype=np.float64);cells=np.asarray(cells,dtype=np.int32)
    if (points.ndim!=2 or points.shape[1]<2 or cells.ndim!=2 or cells.shape[1]!=4
            or not len(cells) or cells.min()<0 or cells.max()>=len(points)
            or not np.isfinite(points).all()):raise ValueError('invalid Q4 geometry')
    g=0.5773502691896258  # exact binary64 1/sqrt(3), native GP ordering
    shapes=np.empty((4,4));B=np.zeros((len(cells),4,3,8));dets=np.empty((len(cells),4))
    xy=points[cells,:2]
    for gp,(xi,eta) in enumerate(((g,g),(-g,g),(g,-g),(-g,-g))):
        shapes[gp]=.25*np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])
        deriv=.25*np.array([[-(1-eta),1-eta,1+eta,-(1+eta)],[-(1-xi),-(1+xi),1+xi,1-xi]])
        J=np.zeros((len(cells),2,2))
        for node in range(4):
            for a in range(2):
                for b in range(2):J[:,a,b]=J[:,a,b]+deriv[a,node]*xy[:,node,b]
        det=J[:,0,0]*J[:,1,1]-J[:,0,1]*J[:,1,0]
        if not np.isfinite(det).all() or np.any(det<=0):raise ValueError('non-positive Q4 Jacobian')
        inv=np.empty_like(J)
        inv[:,0,0]=J[:,1,1]/det;inv[:,0,1]=-J[:,0,1]/det
        inv[:,1,0]=-J[:,1,0]/det;inv[:,1,1]=J[:,0,0]/det
        grad=np.empty((len(cells),2,4))
        for a in range(2):
            for node in range(4):grad[:,a,node]=inv[:,a,0]*deriv[0,node]+inv[:,a,1]*deriv[1,node]
        B[:,gp,0,0::2]=grad[:,0];B[:,gp,1,1::2]=grad[:,1]
        B[:,gp,2,0::2]=grad[:,1];B[:,gp,2,1::2]=grad[:,0];dets[:,gp]=det
    dofs=np.empty((len(cells),8),dtype=np.int32);dofs[:,0::2]=2*cells;dofs[:,1::2]=2*cells+1
    return Q4Kinematics(points[:,:2],cells,shapes,B,dets,dofs,np.repeat(dofs,8,axis=1).ravel(),np.tile(dofs,(1,8)).ravel())
