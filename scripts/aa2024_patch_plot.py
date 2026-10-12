#!/usr/bin/env python3
"""Visualize exact frozen E014 validation/profile outputs; no fit or scoring."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from aa2024_rigid_observable import quotient_residual


def main():
    p=argparse.ArgumentParser()
    p.add_argument("fit",type=Path)
    p.add_argument("validation",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    metric=json.loads((args.validation/"metrics.json").read_text())
    profile=json.loads((args.fit/"q_profile.json").read_text())
    with np.load(args.validation/"validation_fields.npz",allow_pickle=False) as src:
        fields={k:src[k] for k in src.files}
    xy,w=fields["xy"],fields["weights"]
    target=quotient_residual(xy,fields["target"],w)
    candidate=quotient_residual(xy,fields["candidate"],w)
    limit=max(float(np.abs(target[:,1]).max()),float(np.abs(candidate[:,1]).max()),1e-15)
    error_limit=max(float(np.linalg.norm(fields[k+"_residual"],axis=1).max()) for k in ("candidate","secant","intact","d0_only"))
    fig,axes=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
    for ax,title,v in zip(axes[0,:2],("held target delta_v modulo rigid","candidate delta_v modulo rigid"),(target[:,1],candidate[:,1])):
        artist=ax.scatter(*xy.T,c=v,s=9,cmap="RdBu_r",vmin=-limit,vmax=limit)
        ax.set_title(title);fig.colorbar(artist,ax=ax,label="mm")
    for ax,key in zip((axes[0,2],axes[1,0],axes[1,1],axes[1,2]),("candidate","secant","intact","d0_only")):
        value=np.linalg.norm(fields[key+"_residual"],axis=1)
        artist=ax.scatter(*xy.T,c=value,s=9,cmap="magma",vmin=0,vmax=max(error_limit,1e-15))
        ax.set_title(f"{key} residual norm | MAE={metric['vector_MAE_mm'][key]:.6g}mm")
        fig.colorbar(artist,ax=ax,label="mm; shared error scale")
    for ax in axes.ravel():
        ax.set_aspect("equal");ax.set_xlim(-18,18);ax.set_ylim(-9,9)
        ax.set_xlabel("reference x [mm]");ax.set_ylabel("reference y [mm]")
    fig.suptitle(f"S03-E014 | one controlled-experiment cycle126873.5 | held high load\nq={metric['q']:.4g}; paired candidate-secant MAE delta={metric['primary_candidate_minus_secant_mm']:.6g}mm | conditional static diagnostic")
    fig.savefig(args.output/"held_fields.png",dpi=180);fig.savefig(args.output/"held_fields.pdf");plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,4),constrained_layout=True)
    rows=profile["profile"]
    ax.plot([r["q"] for r in rows],[r["train_vector_MAE_mm"] for r in rows],"o-",lw=1.3,color="#0072B2")
    ax.axvline(metric["q"],ls="--",color="#D55E00",lw=1.3,label="frozen selected q")
    ax.set_xlabel("conditional localized amplitude q")
    ax.set_ylabel("training quotient vector MAE [mm]")
    ax.set_title("E014 | fit loads only | objective profile, NOT posterior")
    ax.legend();fig.savefig(args.output/"q_profile.png",dpi=180);fig.savefig(args.output/"q_profile.pdf");plt.close(fig)
    doc=f"""# E014 exact-output figure guide

Sources: {args.fit.resolve()} and {args.validation.resolve()}.
Read held_fields.png then q_profile.png; exact metrics.json/profile JSON remain
authoritative. One controlled-experiment cycle126873.5, stages7/8 fit and9
held interior; no future-cycle or independent-specimen claim. Frozen local
rectangle is the displayed ROI. Every eligible observation is displayed;
no smoothing, clipping, favorable selection or per-method error autoscaling.

Top-left/two panels show the v component after the SAME global weighted planar-
rigid quotient operator, in mm, with one signed color scale. Four remaining
panels show vector residual norms with a common zero-to-maximum scale; per-method
area-weighted vector MAEs are labels from the exact scoring JSON. Spatial nodes
are not independent experimental units. Their areas are training-derived.

q_profile.png shows all21 training loss values and frozen selectedq, no retuning
after held access. This is not a likelihood/confidence interval, and numerical
sensitivity is not practical/physical identifiability. Initial crack geometry,
diffuse width and basis are modeling priors. No fracture-energy/fatigue evolution
equation was solved, and material E is unidentifiable under normalized Dirichlet
conditions. No original exporter inverse was recovered.

Exact outcome: {json.dumps(metric)}

Interpretation: matched high-load descriptive comparison of a conditional
mechanics reconstruction and direct field secant. Primary delta alone does not
establish true damage, material recovery, future prediction, road transfer or
operational utility. Inspect rendered axes/scales/nonblank panels before any
Evidence Ready conclusion. Profile and fields select later BC/basis/model repairs
without changing the frozen primary verdict.
"""
    for name in ("README_analysis.md","held_fields.md","q_profile.md"):
        (args.output/name).write_text(doc)


if __name__=="__main__":main()
