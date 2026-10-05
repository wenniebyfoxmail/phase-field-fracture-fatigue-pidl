"""Independent NumPy translation of archived GRIPHFiTH AMOR weak form."""
import numpy as np


def assert_native_gp_shape(shape):
    """Lock archived gauss_quad + quad_composition order, including node order."""
    pts=(0.577350269189626,-0.577350269189626)
    signs=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])
    expected=np.array([(1+signs[:,0]*x)*(1+signs[:,1]*y)/4 for y in pts for x in pts])
    np.testing.assert_allclose(shape,expected,rtol=0,atol=5e-16)
    return expected

def assemble(xy, conn, uv, damage, young=1., nu=.3, thickness=1., eta=0.):
    xy,uv,damage=np.asarray(xy),np.asarray(uv),np.asarray(damage)
    force=np.zeros_like(uv); mass=np.zeros(len(xy)); energies=[]; psis=[]; shapes=[]; dets=[]
    shear=young/(2*(1+nu)); bulk=young/(3*(1-2*nu))
    c=young/((1+nu)*(1-2*nu))*np.array([[1-nu,nu,0],[nu,1-nu,0],[0,0,(1-2*nu)/2]])
    ivol=np.array([[1.,1.,0.],[1.,1.,0.],[0.,0.,0.]])
    idev=np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]])
    signs=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])
    a=1/np.sqrt(3)
    for xi,et in ((a,a),(-a,a),(a,-a),(-a,-a)):
        n=(1+signs[:,0]*xi)*(1+signs[:,1]*et)/4
        dn=np.stack([signs[:,0]*(1+signs[:,1]*et),signs[:,1]*(1+signs[:,0]*xi)])/4
        jac=np.einsum('an,enb->eab',dn,xy[conn]);det=np.linalg.det(jac)
        if not np.all(np.isfinite(det)&(det>0)):raise ValueError('Invalid Jacobian')
        grad=np.linalg.solve(jac,np.broadcast_to(dn,(len(conn),2,4)))
        k=np.einsum('ean,enb->eab',grad,uv[conn])
        eps=np.stack([k[:,0,0],k[:,1,1],k[:,1,0]+k[:,0,1]],axis=1)
        tensile=eps[:,:2].sum(1)>=0
        plus=np.broadcast_to(2*shear*idev,(len(conn),3,3)).copy();plus[tensile]=c
        minus=np.broadcast_to(bulk*ivol,(len(conn),3,3)).copy();minus[tensile]=0
        dg=damage[conn]@n;dec=(1-dg)**2+eta
        sp=np.einsum('eij,ej->ei',plus,eps)
        sigma=np.einsum('eij,ej->ei',minus,eps)+dec[:,None]*sp
        local=np.stack([grad[:,0,:]*sigma[:,0,None]+grad[:,1,:]*sigma[:,2,None],grad[:,1,:]*sigma[:,1,None]+grad[:,0,:]*sigma[:,2,None]],axis=2)*det[:,None,None]*thickness
        np.add.at(force,conn.ravel(),local.reshape(-1,2))
        np.add.at(mass,conn.ravel(),(det[:,None]*n).ravel())
        energies.append(.5*np.sum(eps*sigma,axis=1)*det*thickness)
        psis.append(.5*np.sum(eps*sp,axis=1));shapes.append(n);dets.append(det)
    return dict(force=force,mass=mass/mass.sum(),energy=float(np.sum(energies)),psi=np.stack(psis,axis=1),shape=np.array(shapes),det=np.stack(dets,axis=1))
