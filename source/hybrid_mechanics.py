"""Hybrid-only AMOR workspace: warm iterates and exact-key numeric LU reuse.

Geometry/material element tensors and CSR scatter structure are reusable.
SuperLU has no supported separate symbolic-refactor API here: no such reuse
is claimed. A numeric factor is reused ONLY for identical CSC bytes and free
DOFs; a changed d, sign, BC set or material cannot silently reuse a stale LU.
Independent legacy assembly still audits every returned field.
"""
import hashlib
from time import perf_counter
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu, gmres, LinearOperator
from damage_conditioned_equilibrium import plane_strain_tensors,_trace_signs,assemble_amor_stiffness


class MechanicsWorkspace:
    def __init__(self,kin,material):
        self.kin=kin;self.material=dict(material);self.factor_key=None;self.factor=None;self.factor_domain=None
        t=perf_counter();_,vol,dev,bulk,shear=plane_strain_tensors(material['youngs_modulus'],material['poisson_ratio'])
        self.dev=[];self.vol=[]
        for gp in range(4):
            b=kin.b_matrices[:,gp];w=(material['thickness']*kin.det_jacobians[:,gp])[:,None,None]
            self.dev.append(np.einsum('eai,eaj->eij',b,np.einsum('ab,ebj->eaj',2*shear*dev,b))*w)
            self.vol.append(np.einsum('eai,eaj->eij',b,np.einsum('ab,ebj->eaj',bulk*vol,b))*w)
        size=2*len(kin.points);keys=kin.assembly_rows.astype(np.int64)*size+kin.assembly_cols
        unique,self.scatter=np.unique(keys,return_inverse=True)
        counts=np.bincount(unique//size,minlength=size);self.indptr=np.r_[0,np.cumsum(counts)]
        self.indices=(unique%size).astype(np.int32);self.size=size
        self.setup_seconds=perf_counter()-t

    def assemble(self,d,u):
        d=np.clip(np.asarray(d,dtype=float),0,1);signs=_trace_signs(u,self.kin)
        local=np.zeros((len(self.kin.cells),8,8))
        for gp in range(4):
            dg=np.einsum('ei,i->e',d[self.kin.cells],self.kin.shape_values[gp],optimize=False)
            g=(1-dg)**2+self.material['residual_stiffness']
            local+=g[:,None,None]*self.dev[gp]+np.where(signs[:,gp],g,1.)[:,None,None]*self.vol[gp]
        data=np.bincount(self.scatter,weights=local.ravel(),minlength=len(self.indices))
        return sparse.csr_matrix((data,self.indices,self.indptr),shape=(self.size,self.size))

    @staticmethod
    def matrix_identity(matrix,free):
        h=hashlib.sha256()
        for a in (free,matrix.indptr,matrix.indices,matrix.data):
            h.update(np.ascontiguousarray(a).tobytes())
        return h.digest(),(tuple(matrix.shape),np.asarray(free,dtype=np.int64).tobytes())

    @staticmethod
    def pivot_ratio(factor):
        piv=np.abs(factor.U.diagonal())
        ratio=float(piv.min()/max(float(piv.max()),np.finfo(float).eps))
        if not np.isfinite(ratio) or ratio<1e-14:
            raise RuntimeError('mechanics numerically near-singular')
        return ratio

    def certify_factor(self,d,u,dofs,observe=None):
        def call(kind,fn):return observe('mechanical.'+kind,fn) if observe else fn()
        matrix=call('acceptance_assembly',lambda:self.assemble(d,u))
        if not np.isfinite(matrix.data).all():raise RuntimeError('nonfinite acceptance mechanics matrix')
        mask=np.ones(self.size,bool);mask[np.asarray(dofs,dtype=int)]=False
        free=np.flatnonzero(mask)
        if not len(free):return dict(current_matrix_pivot_qualified=True,no_free_dofs=True)
        ff=matrix[free][:,free].tocsc();key,domain=self.matrix_identity(ff,free)
        reused=key==self.factor_key and domain==self.factor_domain
        factor=self.factor if reused else call('acceptance_factorization',lambda:splu(ff))
        ratio=self.pivot_ratio(factor)
        self.factor=factor;self.factor_key=key;self.factor_domain=domain
        return dict(current_matrix_pivot_qualified=True,minimum_pivot_ratio=ratio,
                    current_exact_factor_reused=bool(reused),matrix_key=key.hex())

    def solve(self,d,dofs,values,settings,initial_u=None,observe=None,strategy='direct'):
        if strategy not in ('direct','recycled_gmres'):raise ValueError('unknown mechanics strategy')
        def call(kind,fn):
            return observe('mechanical.'+kind,fn) if observe else fn()
        dofs=np.asarray(dofs,dtype=np.int32);values=np.asarray(values,dtype=float)
        mask=np.ones(self.size,bool);mask[dofs]=False;free=np.flatnonzero(mask)
        if initial_u is not None and not np.any(initial_u):initial_u=None
        if initial_u is None:
            u=np.zeros(self.size);y=self.kin.points[:,1];u[1::2]=max(abs(values))*(y-y.min())/max(np.ptp(y),np.finfo(float).eps)
            origin='boundary_linear'
        else:
            u=np.asarray(initial_u,dtype=float).copy();origin='previous_iterate'
            if u.shape!=(self.size,) or not np.isfinite(u).all():raise ValueError('invalid mechanics warm start')
            old_boundary=u[dofs].copy();norm=float(old_boundary@old_boundary)
            if norm>0:u*=float(old_boundary@values)/norm
        u[dofs]=values
        info=dict(iterations=0,factorizations=0,factor_reuses=0,stiffness_assemblies=0,
                  fresh_assemblies=0,initialization=origin,active_set_source='trace of BC-projected warm displacement',
                  symbolic_factor_reuse=False,workspace_setup_seconds=self.setup_seconds,
                  linear_strategy=strategy,krylov_attempts=0,krylov_iterations=0,
                  krylov_successes=0,krylov_fallbacks=0,krylov_matvecs=0,
                  preconditioner_applications=0,current_matrix_pivot_qualified=False)
        stable=False;smallest=1.;relative=np.inf
        for iteration in range(1,settings.max_mechanics+1):
            prev=u.copy();matrix=call('assembly',lambda:self.assemble(d,u));info['stiffness_assemblies']+=1
            if not np.isfinite(matrix.data).all():raise RuntimeError('nonfinite mechanics matrix')
            if len(free):
                ff=matrix[free][:,free].tocsc();rhs=-matrix[free][:,dofs]@values
                key,domain=self.matrix_identity(ff,free)
                recycled=False
                if (strategy=='recycled_gmres' and self.factor is not None
                        and self.factor_domain==domain and key!=self.factor_key):
                    info['krylov_attempts']+=1
                    # An old LU is ONLY a preconditioner for CURRENT ff/rhs.
                    # Relative and absolute residual targets are both tighter
                    # than original final acceptance. No stale exact-key update.
                    target=.1*settings.force_tolerance*min(settings.force_scale,
                        max(float(np.linalg.norm(rhs)),np.finfo(float).tiny))
                    def matvec(x):
                        info['krylov_matvecs']+=1
                        return ff@x
                    def precondition(x):
                        info['preconditioner_applications']+=1
                        return self.factor.solve(x)
                    def count_iteration(residual):
                        info['krylov_iterations']+=1
                        if not np.isfinite(residual):raise RuntimeError('nonfinite Krylov residual')
                    operator=LinearOperator(ff.shape,matvec=matvec,dtype=float)
                    preconditioner=LinearOperator(ff.shape,matvec=precondition,dtype=float)
                    candidate,code=call('recycled_gmres',lambda:gmres(operator,np.asarray(rhs).ravel(),
                        x0=u[free],M=preconditioner,rtol=0.,atol=target,restart=20,maxiter=4,
                        callback=count_iteration,callback_type='pr_norm'))
                    if not np.isfinite(candidate).all():raise RuntimeError('nonfinite Krylov displacement')
                    true_residual=float(np.linalg.norm(ff@candidate-rhs))
                    if not np.isfinite(true_residual):raise RuntimeError('nonfinite current mechanics residual')
                    info['krylov_last_true_residual']=true_residual
                    info['krylov_last_target']=target
                    if code==0 and true_residual<=target:
                        u[free]=candidate;recycled=True;info['krylov_successes']+=1
                    else:
                        info['krylov_fallbacks']+=1
                if not recycled:
                    if key!=self.factor_key or self.factor_domain!=domain:
                        factor=call('factorization',lambda:splu(ff))
                        self.pivot_ratio(factor)
                        self.factor=factor;self.factor_key=key;self.factor_domain=domain
                        info['factorizations']+=1
                    else:info['factor_reuses']+=1
                    ratio=self.pivot_ratio(self.factor)
                    smallest=min(smallest,ratio)
                    u[free]=call('linear_solve',lambda:self.factor.solve(np.asarray(rhs).ravel()))
                    info['current_matrix_pivot_qualified']=True
                else:
                    # Intermediate singular-consistent systems can have zero
                    # residual: final joint acceptance MUST call certify_factor.
                    info['current_matrix_pivot_qualified']=False
            u[dofs]=values
            if not np.isfinite(u).all():raise RuntimeError('nonfinite displacement')
            relative=float(np.linalg.norm(u-prev)/max(np.linalg.norm(u),np.finfo(float).eps))
            if relative<=1e-9 and np.array_equal(_trace_signs(prev,self.kin),_trace_signs(u,self.kin)):
                stable=True;break
        # Uncached independent assembly, including signs from returned u.
        final=call('fresh_assembly',lambda:assemble_amor_stiffness(self.kin,d,u,**self.material));info['fresh_assemblies']+=1
        if not np.isfinite(final.data).all():raise RuntimeError('nonfinite fresh mechanics matrix')
        if not stable and len(free):
            factor=call('fresh_factorization',lambda:splu(final[free][:,free].tocsc()));info['factorizations']+=1
            piv=abs(factor.U.diagonal());ratio=float(piv.min()/max(float(piv.max()),np.finfo(float).eps))
            if not np.isfinite(ratio) or ratio<1e-14:raise RuntimeError('fresh mechanics near-singular')
            smallest=min(smallest,ratio)
        residual=np.asarray(final@u);norm=float(np.linalg.norm(residual[free]))
        scale=max(float(np.linalg.norm(final[free][:,free]@u[free])+np.linalg.norm(final[free][:,dofs]@values)),np.finfo(float).eps) if len(free) else 1.
        if not np.isfinite(norm) or norm/scale>settings.force_tolerance:raise RuntimeError('fresh mechanics residual failed')
        info.update(iterations=iteration,minimum_pivot_ratio=smallest,relative_update=relative,
                    active_set_stable=stable,fresh_normalized_residual=norm/scale)
        return u,info
