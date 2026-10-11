#!/usr/bin/env python3
"""Common-operator FEM/PIDL cross replay at early, middle and late cycles."""
from __future__ import annotations

import csv
import argparse
import json
import math
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
RUN = HERE.parent
OUT = HERE / "multicycle_cross_replay"
INPUT = OUT
HANDOFF = Path(".")
CYCLES = np.array([1, 20, 60, 76, 82, 83, 85, 89], dtype=int)


def q4_geometry(points, cells):
    g = 1.0 / np.sqrt(3.0)
    loc = ((g, g), (-g, g), (g, -g), (-g, -g))
    shape, dref = [], []
    for xi, eta in loc:
        shape.append([.25*(1-xi)*(1-eta), .25*(1+xi)*(1-eta),
                      .25*(1+xi)*(1+eta), .25*(1-xi)*(1+eta)])
        dref.append([[-.25*(1-eta), .25*(1-eta), .25*(1+eta), -.25*(1+eta)],
                     [-.25*(1-xi), -.25*(1+xi), .25*(1+xi), .25*(1-xi)]])
    shape, dref = np.asarray(shape), np.asarray(dref)
    xy = points[cells]
    jac = np.einsum("gij,ejk->egik", dref, xy)
    det = np.linalg.det(jac)
    dshape = np.einsum("egij,gjk->egik", np.linalg.inv(jac), dref)
    gp_xy = np.einsum("gn,enx->egx", shape, xy)
    if np.any(det <= 0): raise RuntimeError("non-positive Q4 Jacobian")
    return shape, dshape, det, gp_xy


def t3_geometry(points, cells):
    xy = points[cells]
    x0,y0=xy[:,0,0],xy[:,0,1]; x1,y1=xy[:,1,0],xy[:,1,1]; x2,y2=xy[:,2,0],xy[:,2,1]
    twice=(x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
    if np.any(twice <= 0): raise RuntimeError("non-positive T3 area")
    shape=np.array([[2/3,1/6,1/6],[1/6,2/3,1/6],[1/6,1/6,2/3]],float)
    grad=np.stack((np.stack((y1-y2,y2-y0,y0-y1),axis=1),
                   np.stack((x2-x1,x0-x2,x1-x0),axis=1)),axis=1)/twice[:,None,None]
    dshape=np.repeat(grad[:,None,:,:],3,axis=1)
    weights=np.repeat((twice/6)[:,None],3,axis=1)
    gp_xy=np.einsum("gn,enx->egx",shape,xy)
    return shape,dshape,weights,gp_xy


def interp(field,cells,shape): return np.einsum("en,gn->eg",field[cells],shape)
def grad(field,cells,dshape): return np.einsum("egin,en->egi",dshape,field[cells])


def amor_raw(u,v,cells,dshape):
    gu,gv=grad(u,cells,dshape),grad(v,cells,dshape)
    exx,eyy,gamma=gu[...,0],gv[...,1],gu[...,1]+gv[...,0]
    E,nu=1.0,.3; mu=E/(2*(1+nu)); bulk=E/(3*(1-2*nu))
    ivol=np.array([[1,1,0],[1,1,0],[0,0,0]],float)
    idev=np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]],float)
    C=bulk*ivol+2*mu*idev; Cdev=2*mu*idev
    eps=np.stack((exx,eyy,gamma),axis=-1)
    sig=np.einsum("ij,...j->...i",Cdev,eps)
    pos=exx+eyy>=0
    sig[pos]=np.einsum("ij,...j->...i",C,eps[pos])
    return .5*np.einsum("...i,...i->...",eps,sig)


def corr(a,b,w):
    w=w/w.sum(); am=np.sum(w*a); bm=np.sum(w*b)
    den=math.sqrt(np.sum(w*(a-am)**2)*np.sum(w*(b-bm)**2))
    return float(np.sum(w*(a-am)*(b-bm))/den) if den else None


def comp(ref,cand,w):
    ir=float(np.sum(w*ref)); ic=float(np.sum(w*cand))
    return {"fem_integral":ir,"pidl_integral":ic,"pidl_over_fem":ic/ir,
            "delta_pct":(ic/ir-1)*100,
            "relative_l2":float(np.sqrt(np.sum(w*(cand-ref)**2)/np.sum(w*ref**2))),
            "correlation":corr(ref,cand,w)}


def load_fem(top):
    with h5py.File(INPUT/f"fem_nodal/fem_{top}_nodal_trajectory.mat","r") as h:
        cycles=np.asarray(h["cycles"]).reshape(-1).astype(int)
        return cycles,*(np.asarray(h[k],float) for k in ("u_node","v_node","d_node"))


def load_mesh(top):
    if top=="q4":
        with h5py.File(HANDOFF/"mesh/canonical_mesh_geometry.mat","r") as h:
            p=np.asarray(h["node_coords"],float).T
            c=np.asarray(h["connectivity_q4"],int).T-1
        return p,c,q4_geometry(p,c)
    with np.load(HANDOFF/"mesh/paired_t3_mesh.npz") as z:
        p=np.asarray(z["node_coords"],float); c=np.asarray(z["connectivity_t3"],int)-1
    return p,c,t3_geometry(p,c)


def direct_c83_check(top,raw,g,active,w):
    path=RUN/f"pidl_selected/raw_c83/{top}_c83_step414.npz"
    with np.load(path) as z:
        stored=(np.asarray(z["psi_raw_gp"],float),np.asarray(z["g_alpha_gp"],float),np.asarray(z["psi_active_gp"],float))
    return {name:comp(s,x,w) for name,s,x in zip(("raw","g","active"),stored,(raw,g,active))}


def replay(top):
    points,cells,(shape,dshape,w,xy)=load_mesh(top)
    fcy,fu,fv,fd=load_fem(top)
    with np.load(INPUT/f"pidl_nodal/pidl_{top}_nodal_trajectory.npz") as z:
        pcy=z["cycles"].astype(int); pu=z["u_node"].astype(float); pv=z["v_node"].astype(float); pd=z["d_node"].astype(float)
        coord=np.asarray(z["node_coords"],float)
    if not np.array_equal(fcy,CYCLES) or not np.array_equal(pcy,CYCLES): raise RuntimeError("cycle mismatch")
    coord_error=float(np.max(np.abs(coord-points)))
    rows=[]; fields={}
    for i,c in enumerate(CYCLES):
        fr=amor_raw(fu[i],fv[i],cells,dshape); pr=amor_raw(pu[i],pv[i],cells,dshape)
        fg=(1-interp(fd[i],cells,shape))**2; pg=(1-interp(pd[i],cells,shape))**2
        pg_clip=(1-interp(np.clip(pd[i],0,1),cells,shape))**2
        FF=fr*fg; PF=pr*fg; FP=fr*pg; PP=pr*pg; PPclip=pr*pg_clip
        ints={k:float(np.sum(w*x)) for k,x in {"FF":FF,"PF":PF,"FP":FP,"PP":PP}.items()}
        lr=math.log(ints["PP"]/ints["FF"])
        raw_eff=.5*(math.log(ints["PF"]/ints["FF"])+math.log(ints["PP"]/ints["FP"]))
        dmg_eff=.5*(math.log(ints["FP"]/ints["FF"])+math.log(ints["PP"]/ints["PF"]))
        delta=np.abs(PP-FF); mass=w*delta; denom=float(mass.sum())
        row={"topology":top,"cycle":int(c),"coord_max_abs_error":coord_error,
             **{f"{k}_integral":v for k,v in ints.items()},
             "total_log_ratio":lr,"raw_log_effect":raw_eff,"damage_log_effect":dmg_eff,
             "negative_damage_node_fraction":float(np.mean(pd[i]<0)),
             "above_one_damage_node_fraction":float(np.mean(pd[i]>1)),
             "damage_min":float(pd[i].min()),"damage_max":float(pd[i].max()),
             "bounded_PP_integral":float(np.sum(w*PPclip)),
             "bounded_PP_delta_pct":float((np.sum(w*PPclip)/ints["PP"]-1)*100),
             "abs_active_gap_x_centroid":float(np.sum(mass*xy[...,0])/denom),
             "abs_active_gap_abs_y_centroid":float(np.sum(mass*np.abs(xy[...,1]))/denom)}
        for name,a,b in (("raw",fr,pr),("g",fg,pg),("active",FF,PP)):
            row.update({f"{name}_{k}":v for k,v in comp(a,b,w).items()})
        rows.append(row); fields[int(c)]={"FF":FF,"PP":PP,"xy":xy,"w":w}
        if c==83: check=direct_c83_check(top,pr,pg,PP,w)
    return rows,fields,{"coordinate_max_abs_error":coord_error,"c83_nodal_replay_vs_direct_diagnostic":check}


def plot_timeline(rows):
    fig,ax=plt.subplots(2,2,figsize=(11,8),sharex=True)
    for top,color in (("q4","#0072B2"),("t3","#D55E00")):
        r=[x for x in rows if x["topology"]==top]; c=[x["cycle"] for x in r]
        for name,ls in (("raw","-"),("g","--"),("active",":")):
            ax[0,0].plot(c,[x[f"{name}_relative_l2"] for x in r],ls,marker="o",color=color,label=f"{top.upper()} {name}")
            ax[0,1].plot(c,[x[f"{name}_correlation"] for x in r],ls,marker="o",color=color,label=f"{top.upper()} {name}")
        ax[1,0].plot(c,[x["raw_log_effect"] for x in r],"-o",color=color,label=f"{top.upper()} displacement")
        ax[1,0].plot(c,[x["damage_log_effect"] for x in r],"--o",color=color,label=f"{top.upper()} damage")
        ax[1,1].plot(c,[x["bounded_PP_delta_pct"] for x in r],"-o",color=color,label=top.upper())
    ax[0,0].set_ylabel("weighted relative L2"); ax[0,1].set_ylabel("weighted correlation")
    ax[1,0].set_ylabel("Shapley log effect on active integral"); ax[1,1].set_ylabel("bounded-damage change in PIDL active integral (%)")
    for a in ax.ravel(): a.axvspan(83,85,color="0.9",zorder=-5); a.grid(alpha=.25); a.legend(fontsize=8,ncol=2)
    ax[1,0].set_xlabel("cycle"); ax[1,1].set_xlabel("cycle")
    fig.suptitle("FEM–PIDL multi-cycle common-operator cross replay")
    fig.tight_layout(); fig.savefig(OUT/"multicycle_cross_replay_timeline.png",dpi=220); plt.close(fig)


def plot_location(all_fields):
    chosen=(1,60,83,85); fig,axs=plt.subplots(2,4,figsize=(14,6),sharex=True,sharey=True)
    for row,top in enumerate(("q4","t3")):
        for col,c in enumerate(chosen):
            f=all_fields[top][c]; xy=f["xy"].reshape(-1,2); diff=(f["PP"]-f["FF"]).reshape(-1)
            lim=np.quantile(np.abs(diff),.995); lim=max(lim,1e-12)
            hb=axs[row,col].hexbin(xy[:,0],xy[:,1],C=np.clip(diff,-lim,lim),reduce_C_function=np.mean,
                                   gridsize=90,cmap="coolwarm",vmin=-lim,vmax=lim,mincnt=1)
            axs[row,col].set_title(f"{top.upper()} c{c}"); axs[row,col].set_aspect("equal")
            fig.colorbar(hb,ax=axs[row,col],shrink=.72)
    fig.suptitle("PIDL − FEM active-driver difference under the same native operator\n(color clipped at each panel's 99.5th |difference| percentile)")
    fig.tight_layout(); fig.savefig(OUT/"multicycle_active_gap_location.png",dpi=220); plt.close(fig)


def main():
    global RUN, OUT, INPUT, HANDOFF
    ap=argparse.ArgumentParser()
    ap.add_argument("--analysis-root",type=Path,required=True,
                    help="Run analysis directory containing pidl_selected and nodal exports")
    ap.add_argument("--handoff",type=Path,required=True,help="Sealed FEM mesh handoff root")
    ap.add_argument("--output",type=Path,help="Defaults to ANALYSIS_ROOT/multicycle_cross_replay")
    args=ap.parse_args()
    analysis=args.analysis_root.resolve(); RUN=analysis.parent; HANDOFF=args.handoff.resolve()
    INPUT=analysis/"multicycle_cross_replay"
    OUT=(args.output or INPUT).resolve()
    OUT.mkdir(exist_ok=True)
    rows=[]; fields={}; validation={}
    for top in ("q4","t3"):
        r,f,v=replay(top); rows+=r; fields[top]=f; validation[top]=v
    cols=list(rows[0])
    with (OUT/"cross_replay_metrics.csv").open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=cols); w.writeheader(); w.writerows(rows)
    summary={"schema":"s04e011-multicycle-common-operator-cross-replay-v1",
             "cycles":CYCLES.tolist(),
             "state_contract":{"FEM":"cycle peak converged nodal u/v/d after final staggered iterate",
                               "PIDL":"cycle peak trained model at step 5*c-1 evaluated at U=0.12",
                               "replay":"deterministic re-evaluation of both nodal fields with the same native Q4 GP4 or paired T3 GP3 operator; no equilibrium re-solve"},
             "validation":validation,"rows":rows}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    plot_timeline(rows); plot_location(fields)
    print(json.dumps({"validation":validation,"rows":rows},allow_nan=False))


if __name__=="__main__": main()
