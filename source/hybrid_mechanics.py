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
from scipy.sparse.linalg import splu
from damage_conditioned_equilibrium import plane_strain_tensors,_trace_signs,assemble_amor_stiffness


class MechanicsWorkspace:
    def __init__(self,kin,material):
        self.kin=kin;self.material=dict(material);self.factor_key=None;self.factor=None
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

    def solve(self,d,dofs,values,settings,initial_u=None,observe=None):
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
                  symbolic_factor_reuse=False,workspace_setup_seconds=self.setup_seconds)
        stable=False;smallest=1.;relative=np.inf
        for iteration in range(1,settings.max_mechanics+1):
            prev=u.copy();matrix=call('assembly',lambda:self.assemble(d,u));info['stiffness_assemblies']+=1
            if not np.isfinite(matrix.data).all():raise RuntimeError('nonfinite mechanics matrix')
            if len(free):
                ff=matrix[free][:,free].tocsc();rhs=-matrix[free][:,dofs]@values
                h=hashlib.sha256()
                for a in (free,ff.indptr,ff.indices,ff.data):h.update(np.ascontiguousarray(a).tobytes())
                key=h.digest()
                if key!=self.factor_key:
                    self.factor=call('factorization',lambda:splu(ff));self.factor_key=key;info['factorizations']+=1
                else:info['factor_reuses']+=1
                piv=np.abs(self.factor.U.diagonal());ratio=float(piv.min()/max(float(piv.max()),np.finfo(float).eps))
                if not np.isfinite(ratio) or ratio<1e-14:raise RuntimeError('mechanics numerically near-singular')
                smallest=min(smallest,ratio)
                u[free]=call('linear_solve',lambda:self.factor.solve(np.asarray(rhs).ravel()))
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
