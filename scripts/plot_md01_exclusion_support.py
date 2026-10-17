"""Render saved E040 masks/support and source, with no extraction or metrology."""
import argparse
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps

import md01_frame_geometry as v1
from md01_geometry_stability import receipt
from md01_early_relative import save,now


def run(a):
    t=time.monotonic();m=json.loads(a.manifest.read_text())
    summary=json.loads((a.run/"summary.json").read_text())
    with np.load(a.run/"support_comparison_arrays.npz") as z:d={k:z[k] for k in z.files}
    rgb=v1.read_frame(m["frame"],m["spec"]["roi"])
    a.output.mkdir(parents=True,exist_ok=False)
    rec=receipt("E040_render_preview" if a.preview else "E040_render_final")
    rec["protocol"]=m["protocol"]
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42})
    cols=[("Original RGB",None), ("Old v1 mask","old"), ("Tighter-support mask","new"), ("Added candidates","added")]
    figures=[];layout={}

    def overlay(ax,mask,color,alpha,extent):
        rgba=np.zeros((*mask.shape,4),np.float32);rgba[mask]=[*color,alpha]
        ax.imshow(rgba,extent=extent,interpolation="nearest")

    def panel(ax,box,label,key):
        x0,y0,x1,y1=box;rx0,ry0=m["spec"]["roi"][:2]
        sl=np.s_[y0-ry0:y1-ry0,x0-rx0:x1-rx0]
        extent=(x0-.5,x1-.5,y1-.5,y0-.5)
        ax.imshow(rgb[sl],extent=extent,interpolation="nearest")
        if key in ("old","new"):
            overlay(ax,d[key+"_excluded"][sl],(.65,.12,.55),.3,extent)
            overlay(ax,d[key+"_mask"][sl],(0,.65,.72) if key=="old" else (0,.35,.7),.8,extent)
        if key=="added":overlay(ax,d["added_candidates"][sl],(.9,.32,.05),.85,extent)
        ax.set(xlim=extent[:2],ylim=(extent[2],extent[3]),xticks=[],yticks=[])
        ax.set_title(label,fontsize=10)

    def finish(fig,stem,panels):
        fig.canvas.draw();renderer=fig.canvas.get_renderer();w,h=fig.canvas.get_width_height()
        outside=[]
        for text in fig.findobj(matplotlib.text.Text):
            if text.get_visible() and text.get_text():
                b=text.get_window_extent(renderer)
                if b.x0<-.5 or b.y0<-.5 or b.x1>w+.5 or b.y1>h+.5:outside.append(text.get_text())
        layout[stem]=dict(outside_canvas_text=outside)
        name=stem+("_preview" if a.preview else "")
        fig.savefig(a.output/(name+".png"),dpi=150 if a.preview else 300)
        guide=(f"# How to read {stem}\n\n## Figure question\n\nDoes source-only exclusion tightening recover visible candidate segments?\n\n"
               f"## Data provenance\n\nE040 R001: {a.run}; manifest {a.manifest}; lockedStep19 IMG_0379.JPG, native6000x4000 ROI[3800,900,4800,3500]. "
               f"Render commit {rec['commit']}. Reads saved masks/support only; no extraction/metrology.\n\n"
               f"## Visual grammar and panels\n\n{panels} Purple=excluded, cyan=old candidate, blue=new candidate, orange=added candidate. "
               "Same support/scale across columns, native pixels, no display dilation/filling. Original RGB unenhanced; "
               "green released-support is only in the separate preparation preview, not a crack claim.\n\n"
               f"## Numerical takeaway\n\nOldarea {summary['old_candidate_area_px2']}px2, newarea {summary['new_candidate_area_px2']}px2, "
               f"added {summary['added_candidate_area_px2']}px2; releasedsupport {summary['released_support_area_px2']}px2. "
               f"Added in releasedsupport {summary['added_in_released_support_px2']}px2, elsewhere due to connectivity "
               f"{summary['added_elsewhere_due_to_connectivity_px2']}px2. Original candidate pixels lost=0. These are not true-positive counts.\n\n"
               "## Limitations and claim boundary\n\nOne already-exposed frame, source/AI-observer polygons not independent truth. "
               "Right support unchanged; actual glue/hardware stays excluded by conservative design but no pixel truth validation. "
               "False positives and fine misses remain. Fixedguide ends3300 and60pxcorridor limits lower coverage. "
               "No hidden crack bridging, skeleton/path/thickness/forecast recomputation or physical width. Oldv1/halfdepth/scores preserved. "
               "Support released does not automatically become crack; orange pixels may still be texture.\n\n"
               "## Related assets\n\nREADME_analysis.md, R001summary.json, support_comparison_arrays.npz, R004manifest, support_repair.json, visual_qa.json. "
               "PDF/color/gray share the guide; gray is display-only.\n")
        (a.output/(name+".md")).write_text(guide)
        if not a.preview:
            fig.savefig(a.output/(name+".pdf"))
            with Image.open(a.output/(name+".png")) as im:ImageOps.grayscale(im).save(a.output/(name+"_gray.png"),dpi=(300,300))
            (a.output/(name+"_gray.md")).write_text(guide)
        figures.append(stem);plt.close(fig)

    fig,axes=plt.subplots(1,4,figsize=(11,9),layout="constrained")
    for ax,(name,key) in zip(axes,cols):panel(ax,m["spec"]["roi"],name,key)
    fig.suptitle(f"E040 | Step19 | exclusion support only; fixed threshold and guide\n"
                  f"Old {summary['old_candidate_area_px2']}px2 -> new {summary['new_candidate_area_px2']}px2; "
                  f"added {summary['added_candidate_area_px2']}px2 (not verified crack area)\n"
                  "Purple=excluded; cyan=old; blue=new; orange=added; no skeleton/width/forecast update",fontsize=11)
    finish(fig,"F01_step19_full_support_comparison","Four fullROI columns: original / old / new / added.")

    crops=m["spec"]["fixed_display_crops_native"]
    fig,axes=plt.subplots(2,4,figsize=(11,9),layout="constrained",gridspec_kw={"height_ratios":[560,190]})
    for i,box in enumerate(crops):
        for ax,(name,key) in zip(axes[i],cols):panel(ax,box,name,key)
        axes[i,0].set_ylabel(f"native x[{box[0]},{box[2]}), y[{box[1]},{box[3]})",fontsize=8)
    fig.suptitle("E040 | fixed source-only close-ups (selected before changed-support extraction)\n"
                  "Top: left glue-adjacent visible surface; bottom: lower visible crack / specimen edge\n"
                  "Purple=excluded, not predicted crack; orange=new candidate, not independent truth",fontsize=11)
    finish(fig,"F02_step19_fixed_local_comparison","Rows are fixed nativecrops [4100,2600,4450,3160] and[4050,3230,4390,3420]. Eachrow four identical-support columns: original/old/new/added.")
    save(a.output/"visual_qa.json",layout)
    rec.update(execution="succeeded",ended_at_utc=now(),elapsed_wall_s=time.monotonic()-t,groups=figures,source_run=str(a.run))
    save(a.output/"render_receipt.json",rec)


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--run",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--preview",action="store_true");run(p.parse_args())
