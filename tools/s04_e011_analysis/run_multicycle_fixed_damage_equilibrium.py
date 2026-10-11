#!/usr/bin/env python3
"""Multi-cycle native Q4/T3 fixed-damage equilibrium intervention."""
from __future__ import annotations

import csv
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu


HERE=Path(__file__).resolve().parent
RUN=HERE.parent
OUT=HERE/"multicycle_fixed_damage_equilibrium"
REPLAY=HERE/"multicycle_cross_replay"
HANDOFF=Path(".")
CYCLES=(1,60,83,85)


@dataclass
class Kin:
    points: np.ndarray; cells: np.ndarray; shape: np.ndarray; b: np.ndarray; weights: np.ndarray
    dofs: np.ndarray; rows: np.ndarray; cols: np.ndarray


def plane_strain(E=1.0,nu=.3):
    mu=E/(2*(1+nu)); bulk=E/(3*(1-2*nu))
    iv=np.array([[1,1,0],[1,1,0],[0,0,0]],float)
    idev=np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]],float)
    return bulk*iv+2*mu*idev,iv,idev,bulk,mu


def finish_kin(points,cells,shape,dshape,weights):
    ne,ng,nnode=len(cells),len(shape),cells.shape[1]
    b=np.zeros((ne,ng,3,2*nnode),float)
    b[:,:,0,0::2]=dshape[:,:,:,0]
    b[:,:,1,1::2]=dshape[:,:,:,1]
    b[:,:,2,0::2]=dshape[:,:,:,1]
    b[:,:,2,1::2]=dshape[:,:,:,0]
    dofs=np.empty((ne,2*nnode),np.int32); dofs[:,0::2]=2*cells; dofs[:,1::2]=2*cells+1
    rows=np.repeat(dofs,2*nnode,axis=1).reshape(-1)
    cols=np.tile(dofs,(1,2*nnode)).reshape(-1)
    return Kin(points,cells,shape,b,weights,dofs,rows,cols)


def build_q4(points,cells):
    g=1/np.sqrt(3); loc=((-g,-g),(g,-g),(g,g),(-g,g)); shape=[]; dref=[]
    for xi,eta in loc:
        shape.append([.25*(1-xi)*(1-eta),.25*(1+xi)*(1-eta),.25*(1+xi)*(1+eta),.25*(1-xi)*(1+eta)])
        dref.append([[-.25*(1-eta),.25*(1-eta),.25*(1+eta),-.25*(1+eta)],[-.25*(1-xi),-.25*(1+xi),.25*(1+xi),.25*(1-xi)]])
    shape=np.asarray(shape); dref=np.asarray(dref); xy=points[cells]
    jac=np.einsum("gij,ejk->egik",dref,xy); det=np.linalg.det(jac)
    if np.any(det<=0): raise RuntimeError("non-positive Q4 Jacobian")
    dshape=np.einsum("egij,gjk->egki",np.linalg.inv(jac),dref)
    return finish_kin(points,cells,shape,dshape,det)


def build_t3(points,cells):
    xy=points[cells]; x0,y0=xy[:,0,0],xy[:,0,1]; x1,y1=xy[:,1,0],xy[:,1,1]; x2,y2=xy[:,2,0],xy[:,2,1]
    twice=(x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
    if np.any(twice<=0): raise RuntimeError("non-positive T3 area")
    shape=np.array([[2/3,1/6,1/6],[1/6,2/3,1/6],[1/6,1/6,2/3]],float)
    grad=np.stack((np.stack((y1-y2,y2-y0,y0-y1),axis=1),np.stack((x2-x1,x0-x2,x1-x0),axis=1)),axis=2)/twice[:,None,None]
    dshape=np.repeat(grad[:,None,:,:],3,axis=1)
    weights=np.repeat((twice/6)[:,None],3,axis=1)
    return finish_kin(points,cells,shape,dshape,weights)


def prescribed(points,U=.11999988):
    bot=np.flatnonzero(np.isclose(points[:,1],points[:,1].min(),atol=1e-10,rtol=0))
    top=np.flatnonzero(np.isclose(points[:,1],points[:,1].max(),atol=1e-10,rtol=0))
    dof=np.concatenate((2*bot,2*top,2*bot+1,2*top+1)); val=np.concatenate((np.zeros(len(bot)+len(top)+len(bot)),np.full(len(top),U)))
    o=np.argsort(dof); return dof[o].astype(np.int32),val[o],top,bot


def signs(kin,u):
    strain=np.einsum("egij,ej->egi",kin.b,u[kin.dofs]); return strain[:,:,0]+strain[:,:,1]>=0


def assemble(kin,d,u,eta):
    C,iv,idev,bulk,mu=plane_strain(); s=signs(kin,u); de=d[kin.cells]; ndof=kin.dofs.shape[1]
    ke=np.zeros((len(kin.cells),ndof,ndof),float)
    for gp in range(len(kin.shape)):
        b=kin.b[:,gp]; dgp=np.einsum("ei,i->e",de,kin.shape[gp]); g=(1-dgp)**2+eta; pos=s[:,gp]
        ct=np.empty((len(b),3,3),float); ct[pos]=g[pos,None,None]*C
        ct[~pos]=bulk*iv[None]+g[~pos,None,None]*(2*mu*idev)[None]
        cb=np.einsum("eab,ebj->eaj",ct,b); ke+=np.einsum("eai,eaj->eij",b,cb)*kin.weights[:,gp,None,None]
    return sparse.coo_matrix((ke.reshape(-1),(kin.rows,kin.cols)),shape=(2*len(kin.points),)*2).tocsr()


def energies(kin,u):
    C,_,idev,_,mu=plane_strain(); strain=np.einsum("egij,ej->egi",kin.b,u[kin.dofs]); pos=strain[:,:,0]+strain[:,:,1]>=0
    out=np.empty(pos.shape,float); dev=2*mu*idev
    for gp in range(len(kin.shape)):
        e=strain[:,gp]; ct=np.empty((len(e),3,3),float); ct[pos[:,gp]]=C; ct[~pos[:,gp]]=dev
        out[:,gp]=.5*np.einsum("ei,ei->e",e,np.einsum("eij,ej->ei",ct,e))
    return out


def qualify_matrix(K,free,min_pivot=1e-14):
    fac=splu(K[free][:,free].tocsc()); p=np.abs(fac.U.diagonal()); ratio=float(p.min()/max(float(p.max()),np.finfo(float).eps))
    if not np.isfinite(ratio) or ratio<min_pivot: raise RuntimeError(f"near-singular pivot ratio {ratio:.3e}")
    return fac,ratio


def solve(kin,d,eta,initial=None,maxit=12,bound_damage=True):
    d=np.asarray(d,float).reshape(-1)
    if bound_damage: d=np.clip(d,0,1)
    pd,pv,top,bot=prescribed(kin.points); size=2*len(kin.points)
    mask=np.ones(size,bool); mask[pd]=False; free=np.flatnonzero(mask)
    if initial is None:
        u=np.zeros(size); ymin,ymax=kin.points[:,1].min(),kin.points[:,1].max(); u[1::2]=pv.max()*(kin.points[:,1]-ymin)/(ymax-ymin)
    else:
        u=np.asarray(initial,float).reshape(-1).copy()
        if u.shape!=(size,) or not np.all(np.isfinite(u)): raise ValueError("invalid initial displacement")
    u[pd]=pv
    minratio=1.; stable=False
    for it in range(1,maxit+1):
        prev=u.copy(); K=assemble(kin,d,u,eta); fac,ratio=qualify_matrix(K,free); minratio=min(minratio,ratio)
        rhs=-K[free][:,pd]@pv; u[free]=fac.solve(np.asarray(rhs).reshape(-1)); u[pd]=pv
        change=np.linalg.norm(u-prev)/max(np.linalg.norm(u),np.finfo(float).eps); schange=np.count_nonzero(signs(kin,prev)!=signs(kin,u))
        if change<=1e-9 and schange==0: stable=True; break
    K=assemble(kin,d,u,eta); fac,ratio=qualify_matrix(K,free); minratio=min(minratio,ratio)
    r=np.asarray(K@u).reshape(-1); scale=max(np.linalg.norm(K[free][:,free]@u[free])+np.linalg.norm(K[free][:,pd]@pv),np.finfo(float).eps); nr=float(np.linalg.norm(r[free])/scale)
    if nr>1e-8: raise RuntimeError(f"free residual {nr:.3e}")
    psi=energies(kin,u); dgp=np.einsum("ei,gi->eg",d[kin.cells],kin.shape); g=(1-dgp)**2+eta
    return {"u":u,"psi":psi,"active":g*psi,"force":r,"iterations":it,"stable":stable,"residual":nr,"pivot":minratio,"top":top,"bot":bot}


def original_residual(kin,d,u,eta,bound_damage=True):
    damage=np.asarray(d,float).reshape(-1)
    if bound_damage: damage=np.clip(damage,0,1)
    pd,pv,top,bot=prescribed(kin.points); free=np.setdiff1d(np.arange(2*len(kin.points)),pd,assume_unique=True); K=assemble(kin,damage,u,eta); r=np.asarray(K@u).reshape(-1)
    scale=max(np.linalg.norm(K[free][:,free]@u[free])+np.linalg.norm(K[free][:,pd]@pv),np.finfo(float).eps)
    return float(np.linalg.norm(r[free])/scale),float(r[2*top+1].sum())


def rel(a,b,w): return float(np.sqrt(np.sum(w*(b-a)**2)/max(np.sum(w*a*a),1e-300)))
def corr(a,b,w):
    w=w/w.sum(); am=np.sum(w*a); bm=np.sum(w*b); den=math.sqrt(np.sum(w*(a-am)**2)*np.sum(w*(b-bm)**2)); return float(np.sum(w*(a-am)*(b-bm))/den) if den else None


def load(top):
    if top=="q4":
        with h5py.File(HANDOFF/"mesh/canonical_mesh_geometry.mat","r") as h: p=np.asarray(h["node_coords"]).T; c=np.asarray(h["connectivity_q4"]).T.astype(int)-1
        kin=build_q4(p,c)
    else:
        with np.load(HANDOFF/"mesh/paired_t3_mesh.npz") as z: p=np.asarray(z["node_coords"],float); c=np.asarray(z["connectivity_t3"],int)-1
        kin=build_t3(p,c)
    with h5py.File(REPLAY/f"fem_nodal/fem_{top}_nodal_trajectory.mat","r") as h:
        cy=np.asarray(h["cycles"]).reshape(-1).astype(int); fu=np.asarray(h["u_node"],float); fv=np.asarray(h["v_node"],float); fd=np.asarray(h["d_node"],float)
    with np.load(REPLAY/f"pidl_nodal/pidl_{top}_nodal_trajectory.npz") as z: pcy=z["cycles"].astype(int); pu=z["u_node"].astype(float); pv=z["v_node"].astype(float); pd=z["d_node"].astype(float)
    if not np.array_equal(cy,pcy): raise RuntimeError("cycle mismatch")
    return kin,cy,(fu,fv,fd),(pu,pv,pd)


def main():
    global RUN, OUT, REPLAY, HANDOFF
    ap=argparse.ArgumentParser()
    ap.add_argument("--analysis-root",type=Path,required=True)
    ap.add_argument("--handoff",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    analysis=args.analysis_root.resolve(); RUN=analysis.parent; HANDOFF=args.handoff.resolve()
    REPLAY=analysis/"multicycle_cross_replay"
    OUT=(args.output or analysis/"multicycle_fixed_damage_equilibrium").resolve()
    OUT.mkdir(exist_ok=True); rows=[]; comparisons=[]; saved={}
    for top in ("q4","t3"):
        kin,cycles,fem,pidl=load(top); area=kin.weights.sum(1); nodearea=np.zeros(len(kin.points))
        for j in range(kin.cells.shape[1]): np.add.at(nodearea,kin.cells[:,j],area/kin.cells.shape[1])
        pdofs,_,topnodes,botnodes=prescribed(kin.points); free=np.setdiff1d(np.arange(2*len(kin.points)),pdofs,assume_unique=True)
        for cycle in CYCLES:
            i=int(np.flatnonzero(cycles==cycle)[0]); fields={"FEM":fem,"PIDL":pidl}; results={}
            for arm,(uu,vv,dd) in fields.items():
                uorig=np.column_stack((uu[i],vv[i])).reshape(-1); d=np.clip(dd[i],0,1)
                for eta in (0.,1e-6):
                    base={"topology":top,"cycle":cycle,"damage_source":arm,"eta":eta,"operator":f"native {top.upper()} AMOR fixed-damage equilibrium"}
                    try:
                        res=solve(kin,d,eta,initial=uorig); ores,oreact=original_residual(kin,d,uorig,eta); key=(arm,eta); results[key]=res
                        dispw=np.repeat(nodearea,2); psi0=energies(kin,uorig); dgp=np.einsum("ei,gi->eg",d[kin.cells],kin.shape); a0=((1-dgp)**2+eta)*psi0
                        rows.append({**base,"status":"PASS","error":"","iterations":res["iterations"],"active_set_stable":res["stable"],"normalized_free_residual":res["residual"],"minimum_pivot_ratio":res["pivot"],
                                     "original_common_operator_residual":ores,"original_top_reaction":oreact,"equilibrium_top_reaction":float(res["force"][2*topnodes+1].sum()),
                                     "original_to_equilibrium_displacement_rel_l2":rel(uorig,res["u"],dispw),
                                     "original_to_equilibrium_active_rel_l2":rel(a0,res["active"],kin.weights),"original_to_equilibrium_active_corr":corr(a0,res["active"],kin.weights)})
                    except RuntimeError as e: rows.append({**base,"status":"FAIL_SINGULAR_OR_UNQUALIFIED","error":str(e)})
                    print(top,cycle,arm,eta,rows[-1]["status"],rows[-1].get("iterations",""),flush=True)
                    (OUT/"progress.json").write_text(json.dumps({"arm_replays":rows,"damage_effect_comparisons":comparisons},indent=2,allow_nan=False)+"\n")
            for eta in (0.,1e-6):
                if ("FEM",eta) not in results or ("PIDL",eta) not in results: continue
                a,b=results[("FEM",eta)],results[("PIDL",eta)]; dw=np.repeat(nodearea,2)
                comparisons.append({"topology":top,"cycle":cycle,"eta":eta,
                    "equilibrium_displacement_rel_l2":rel(a["u"],b["u"],dw),"equilibrium_displacement_corr":corr(a["u"],b["u"],dw),
                    "equilibrium_active_rel_l2":rel(a["active"],b["active"],kin.weights),"equilibrium_active_corr":corr(a["active"],b["active"],kin.weights),
                    "pidl_damage_reaction_delta_pct":(b["force"][2*topnodes+1].sum()/a["force"][2*topnodes+1].sum()-1)*100})
                if eta==1e-6: saved[(top,cycle)]=(a,b)
        print(top,"complete",flush=True)
    for name,data in (("arm_replays.csv",rows),("damage_effect_comparisons.csv",comparisons)):
        keys=[]
        for x in data:
            for k in x:
                if k not in keys: keys.append(k)
        with (OUT/name).open("w",newline="") as h: w=csv.DictWriter(h,fieldnames=keys); w.writeheader(); w.writerows(data)
    summary={"schema":"s04e011-multicycle-native-fixed-damage-equilibrium-v1","cycles":list(CYCLES),"state":"cycle peak nodal damage clipped to [0,1]",
             "operators":"topology-native Q4 GP4 or paired T3 GP3 AMOR, E=1, nu=0.3, U=0.11999988; eta=0 qualification and eta=1e-6 sensitivity",
             "causal_scope":"fixed-damage displacement equilibrium intervention only; fatigue and damage are not evolved","arm_replays":rows,"damage_effect_comparisons":comparisons}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    fig,ax=plt.subplots(2,2,figsize=(11,8),sharex=True)
    for top,color in (("q4","#0072B2"),("t3","#D55E00")):
        cr=[x for x in comparisons if x["topology"]==top and x["eta"]==1e-6]; c=[x["cycle"] for x in cr]
        ax[0,0].plot(c,[x["equilibrium_displacement_rel_l2"] for x in cr],"-o",color=color,label=top.upper())
        ax[0,1].plot(c,[x["equilibrium_active_rel_l2"] for x in cr],"-o",color=color,label=top.upper())
        ax[1,0].plot(c,[x["pidl_damage_reaction_delta_pct"] for x in cr],"-o",color=color,label=top.upper())
        for arm,ls in (("FEM","-"),("PIDL","--")):
            rr=[x for x in rows if x["topology"]==top and x["damage_source"]==arm and x["eta"]==1e-6 and x["status"]=="PASS"]
            ax[1,1].plot([x["cycle"] for x in rr],[x["original_common_operator_residual"] for x in rr],ls+"o",color=color,label=f"{top.upper()} {arm}")
    ax[0,0].set_ylabel("equilibrium displacement rel-L2"); ax[0,1].set_ylabel("equilibrium active rel-L2")
    ax[1,0].set_ylabel("PIDL-damage reaction vs FEM-damage (%)"); ax[1,1].set_ylabel("original-field common-operator residual")
    ax[1,1].set_yscale("log")
    for a in ax.ravel(): a.axvspan(83,85,color="0.9",zorder=-5); a.grid(alpha=.25); a.legend()
    ax[1,0].set_xlabel("cycle"); ax[1,1].set_xlabel("cycle"); fig.suptitle("Multi-cycle fixed-damage common-equilibrium intervention (eta=1e-6 sensitivity)")
    fig.tight_layout(); fig.savefig(OUT/"multicycle_fixed_damage_equilibrium.png",dpi=220); plt.close(fig)
    print(json.dumps({"rows":len(rows),"comparisons":len(comparisons)}))


if __name__=="__main__": main()
