"""Read-only prepared-asset QA; no static solve or held response access."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from aa2024_patch_mechanics import rectangular_mesh,candidate_basis


def main():
    p=argparse.ArgumentParser();p.add_argument("prepared",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    with np.load(args.prepared/"prepared.npz",allow_pickle=False) as src:a={k:src[k] for k in src.files}
    xy,tri,bd=rectangular_mesh();d0,b=candidate_basis(xy)
    for key,value in (("mesh",xy),("tri",tri),("boundary",bd),("d0",d0),("basis",b)):
        if not np.array_equal(a[key],value):raise ValueError("asset mismatch "+key)
    v=xy[tri];area=((v[:,1,0]-v[:,0,0])*(v[:,2,1]-v[:,0,1])-(v[:,1,1]-v[:,0,1])*(v[:,2,0]-v[:,0,0]))/2
    w=a["weights"]
    if not (np.isfinite(a["bc"]).all() and np.isfinite(a["train_v"]).all() and np.isfinite(w).all() and np.all(w>0)):
        raise ValueError("nonfinite spatial asset")
    summary={"status":"local_asset_QA_no_FEM_or_q_fit","nodes":len(xy),"triangles":len(tri),
             "element_area_min_max_mm2":[float(area.min()),float(area.max())],"mesh_area_mm2":float(area.sum()),
             "boundary_nodes":int(bd.sum()),"interior_points":len(a["ids"]),
             "unique_observation_ids":len(set(a["ids"].tolist())),
             "observation_area_sum_mm2":float(w.sum()),"observation_area_min_max_mm2":[float(w.min()),float(w.max())],
             "d0_min_max":[float(d0.min()),float(d0.max())],"b_min_max":[float(b.min()),float(b.max())],
             "BC_component_ranges_mm":np.stack((a["bc"].min(0),a["bc"].max(0))).tolist(),
             "training_component_ranges_mm":np.stack((a["train_v"].min(0),a["train_v"].max(0))).tolist(),
             "exact_grid_basis_checks":True,"no_held_response":True}
    fig,axes=plt.subplots(2,2,figsize=(10,6),constrained_layout=True)
    for ax,title,value in zip(axes[0],("d0: fixed geometric PRIOR","b: fixed localized amplitude PRIOR"),(d0,b)):
        sc=ax.scatter(*xy.T,c=value,s=9,cmap="viridis",vmin=0,vmax=1);fig.colorbar(sc,ax=ax,label="dimensionless")
        ax.set_title(title)
    ax=axes[1,0];sc=ax.scatter(*a["obs_xy"].T,c=a["train_v"][:,1],s=12,cmap="RdBu_r",vmin=-float(np.abs(a["train_v"][:,1]).max()),vmax=float(np.abs(a["train_v"][:,1]).max()))
    ax.scatter(*xy[bd].T,s=10,c="black",label="fixed outer BC")
    ax.set_title("fit-only delta_v at646 observed positions");fig.colorbar(sc,ax=ax,label="mm");ax.legend(fontsize=8)
    ax=axes[1,1];ax.quiver(*xy[bd].T,a["bc"][:,0],a["bc"][:,1],angles="xy",scale_units="xy",scale=.003)
    ax.set_title("training affine-interpolated BC\narrows exaggerated333x; no high BC")
    for ax in axes.ravel():ax.set_aspect("equal");ax.set_xlim(-20,20);ax.set_ylim(-11,11);ax.set_xlabel("x [mm]");ax.set_ylabel("y [mm]")
    fig.suptitle("E014-R002 prepared assets | one controlled cycle126873.5 | no inverse result")
    fig.savefig(args.output/"prepared_assets.png",dpi=170);fig.savefig(args.output/"prepared_assets.pdf");plt.close(fig)
    (args.output/"asset_QA.json").write_text(json.dumps(summary,indent=2))
    doc=f"""# Prepared spatial-asset review guide

Source: {args.prepared.resolve()}/prepared.npz with preparation.json and receipt.
Cycle126873.5, stages7/8 training only. No high displacement/strain converted.
Read prepared_assets.png then asset_QA.json, finally the complete NPZ arrays.
Top: d0 and b fixed modeling priors, NOT measured true phase field or material
length scale. Bottom-left: every646 original interior fit observation and all
120 outer BC nodes. Bottom-right: training-only interpolated increments,
arrows exaggerated333x for display, never rescaled in numerical assets.
Physical coordinates and displacements in mm. Artificial36x18mm rectangle,
861 nodes/1600 CCW CSTs; this is not grip geometry. Missing facets are not cracks.
Actual geometry/topology/basis/BC/mask/weights and source lineage must be
independently reviewed before solving; hash agreement alone is insufficient.
QA values: {json.dumps(summary)}. Exact outputs are authoritative.
This figure makes no q sensitivity, inverse, held score or future claim.
"""
    for name in ("README_analysis.md","prepared_assets.md"):(args.output/name).write_text(doc)
    print(json.dumps(summary))


if __name__=="__main__":main()
