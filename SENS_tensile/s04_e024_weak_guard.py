"""Native AMOR matrix-free tangent and bounded two-coordinate offline correction."""
import numpy as np
from scipy.optimize import minimize

class Mechanics:
    def __init__(self,xy,conn,damage,origin):
        self.conn=conn;self.n=len(xy);self.geo=[];mass=np.zeros(self.n)
        signs=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])
        a=1/np.sqrt(3)
        for xi,eta in [(a,a),(-a,a),(a,-a),(-a,-a)]:
            n=(1+signs[:,0]*xi)*(1+signs[:,1]*eta)/4
            dn=np.stack([signs[:,0]*(1+signs[:,1]*eta),signs[:,1]*(1+signs[:,0]*xi)])/4
            jac=np.einsum('an,enb->eab',dn,xy[conn]);det=np.linalg.det(jac);assert (det>0).all()
            grad=np.linalg.solve(jac,np.broadcast_to(dn,(len(conn),2,4)))
            g=(1-np.einsum('en,n->e',damage[conn],n))**2
            np.add.at(mass,conn.ravel(),(det[:,None]*n).ravel())
            self.geo.append((grad,det,g))
        self.mass=mass/mass.sum();self.free=~(np.isclose(xy[:,1],-.5,rtol=0,atol=1e-12)|np.isclose(xy[:,1],.5,rtol=0,atol=1e-12))
        self.branches=self.strains(origin)[...,:2].sum(2)>=0
    def strains(self,uv):
        ans=[]
        for grad,det,g in self.geo:
            d=np.einsum('ean,enb->eab',grad,uv[self.conn]);ans.append(np.stack([d[:,0,0],d[:,1,1],d[:,1,0]+d[:,0,1]],axis=1))
        return np.stack(ans,axis=1)
    def force(self,uv,tangent=False):
        eps=self.strains(uv);f=np.zeros_like(uv);mu=1/(2*1.3);bulk=1/(3*.4)
        for j,(grad,det,g) in enumerate(self.geo):
            ex,ey,ga=eps[:,j,:].T;tr=ex+ey;positive=self.branches[:,j] if tangent else tr>=0
            vol=bulk*np.where(positive,g,1.)*tr
            sx=2*mu*g*(ex-tr/3)+vol;sy=2*mu*g*(ey-tr/3)+vol;ss=mu*g*ga
            local=np.stack([grad[:,0,:]*sx[:,None]+grad[:,1,:]*ss[:,None],grad[:,1,:]*sy[:,None]+grad[:,0,:]*ss[:,None]],axis=2)*det[:,None,None]
            np.add.at(f,self.conn.ravel(),local.reshape(-1,2))
        if not np.isfinite(f).all():raise ValueError('nonfinite force')
        return f
    def dual(self,f):return f[self.free]/np.sqrt(self.mass[self.free,None])


def two_coordinate(q,g,h,t):
    """min g.z+.5 z.Qz with ball and normalized force quadratic guard."""
    fun=lambda z:float(np.einsum('i,i',g,z)+.5*np.einsum('i,ij,j',z,q,z))
    jac=lambda z:g+np.einsum('ij,j->i',q,z)
    guard=lambda z:float(-2*np.einsum('i,i',h,z)-np.einsum('i,ij,j',z,t,z))
    guard_jac=lambda z:-2*h-2*np.einsum('ij,j->i',t,z)
    result=minimize(fun,np.zeros(2),jac=jac,method='SLSQP',constraints=[dict(type='ineq',fun=lambda z:1-np.dot(z,z),jac=lambda z:-2*z),dict(type='ineq',fun=guard,jac=guard_jac)],options=dict(maxiter=100,ftol=1e-12))
    z=result.x;feasible=bool(np.isfinite(z).all() and np.dot(z,z)<=1+1e-10 and guard(z)>=-1e-10)
    return z,dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),plane_ball=float(np.dot(z,z)),linearized_force_guard=guard(z),proxy_objective=fun(z),feasible=feasible)
