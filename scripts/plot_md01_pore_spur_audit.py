"""Render saved E039 source/before/after/deletion panels; no mask filtering."""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image, ImageOps

import md01_frame_geometry as v1
from md01_geometry_stability import receipt
from md01_early_relative import save, now
sys.path.insert(0, "/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout, render_preview


def run(a):
    start = time.monotonic()
    m = json.loads(a.manifest.read_text())
    summary = json.loads((a.run / "summary.json").read_text())
    a.output.mkdir(parents=True, exist_ok=False)
    with (a.output / "summary.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    # Profile before plotting; descriptive schema, not generic statistical advice.
    profile = subprocess.run([sys.executable, "/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts/profile_data.py",
                              str(a.output / "summary.csv"), "--json"], check=True, capture_output=True, text=True)
    (a.output / "data_profile.json").write_text(profile.stdout)
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "pdf.fonttype":42, "axes.spines.top":False, "axes.spines.right":False})
    qa = {}
    rec = receipt("E039_render_preview" if a.preview else "E039_render_final")
    rec["protocol"] = m["protocol"]
    roi = m["roi"]

    def finish(fig, name, text):
        qa[name] = audit_layout(fig)
        stem = name + ("_preview" if a.preview else "")
        guide = (f"# How to read {name}\n\n## Data provenance\n\nE039 R001 saved masks and metrics: {a.run}; "
                 f"manifest {a.manifest}; source identities validated against E037/E038 locks. "
                 f"Render code commit {rec['commit']}; no new segmentation or forecasts in renderer.\n\n"
                 f"## Visual grammar and numerical takeaway\n\n{text}\n\n"
                 "## Limitations\n\nCandidate geometric filter, not pore ground truth. Deleted pixels may include short broad true crack branches. "
                 "Protected-path inscribed disks deliberately retain adjacent pores; loops and isolated components are not cleaned. "
                 "Original full/common path coordinates and their local 2xEDT thickness are preserved by construction, not validated physical width. "
                 "Recomputed skeleton paths can differ; old v1, half-depth and prediction scores unchanged. Five frames of one trajectory, "
                 "45 correlated settings, not independent samples. Threshold sensitivity is not accuracy or a confidence interval. "
                 "Raw RGB is unenhanced. No material correspondence, hidden-area interpolation or mm conversion.\n\n"
                 "## Related assets\n\nREADME_analysis.md, summary.csv, data_profile.json, visual_qa.json and independent review. "
                 "PNG/PDF share this guide; gray is a display copy.\n")
        (a.output / (stem+".md")).write_text(guide)
        if a.preview:
            render_preview(fig, a.output / (stem+".png"), dpi=150)
        else:
            fig.savefig(a.output / (stem+".png"), dpi=300)
            fig.savefig(a.output / (stem+".pdf"))
            with Image.open(a.output / (stem+".png")) as im:
                ImageOps.grayscale(im).save(a.output / (stem+"_gray.png"), dpi=(300,300))
            (a.output / (stem+"_gray.md")).write_text(guide)
        plt.close(fig)

    def tint(ax, mask, color, alpha):
        rgba = np.zeros((*mask.shape, 4), np.float32)
        rgba[mask] = [*color, alpha]
        ax.imshow(rgba, interpolation="nearest")

    for frame, row in zip(m["frames"], summary):
        stage = frame["stage"]
        assert stage == row["stage"]
        rgb = v1.read_frame(frame, roi)
        src = Path(m["input_root"]) / f"step{stage}" / "v1"
        with np.load(src / "geometry_arrays.npz") as f:
            old = {k:f[k] for k in f.files}
        with np.load(a.run / f"step{stage}/v1/geometry_arrays.npz") as f:
            new = {k:f[k] for k in f.files}
        count, labels, stats, _ = cv2.connectedComponentsWithStats(new["removed"].astype(np.uint8), 8)
        crop = None
        if count > 1:
            k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            x, y, w, h, n = [int(v) for v in stats[k]]
            crop = [max(0,x-80), max(0,y-80), min(rgb.shape[1],x+w+80), min(rgb.shape[0],y+h+80)]
        save(a.output / f"step{stage}_display_selection.json", dict(stage=stage, crop_xyxy_roi=crop,
             rule="largest removed 8-connected component, label-order tie; 80px margin", selected_component_px=int(stats[k,-1]) if crop else 0))
        fig = plt.figure(figsize=(11,11), constrained_layout=True)
        gs = fig.add_gridspec(2,4,height_ratios=[3.4,1.25])
        colors = [(0,.65,.75), (0,.35,.7), (.9,.32,.05)]
        layers = [None, old["mask"], new["mask"], new["removed"]]
        titles = ["a  Original RGB", "b  Original v1 mask", "c  Retained mask", "d  Removed candidates"]
        for j in range(4):
            ax = fig.add_subplot(gs[0,j])
            ax.imshow(rgb)
            if layers[j] is not None:
                tint(ax, layers[j], colors[j-1], .75)
            if j:
                tint(ax, old["excluded"], (.65,.1,.6), .2)
            if crop:
                xx, yy, xxx, yyy = crop
                ax.add_patch(Rectangle((xx,yy),xxx-xx,yyy-yy,fill=False,edgecolor="black",lw=.9))
            ax.set_title(titles[j],fontsize=10)
            ax.set(xticks=[],yticks=[],xlim=(-.5,rgb.shape[1]-.5),ylim=(rgb.shape[0]-.5,-.5))
            ax = fig.add_subplot(gs[1,j])
            if crop:
                xx, yy, xxx, yyy = crop
                ax.imshow(rgb[yy:yyy,xx:xxx])
                if layers[j] is not None:
                    tint(ax, layers[j][yy:yyy,xx:xxx], colors[j-1], .75)
                ax.set_title(f"{chr(101+j)}  Same source zoom",fontsize=10)
            else:
                ax.text(.5,.5,"No removed component",ha="center",va="center",transform=ax.transAxes)
            ax.set(xticks=[],yticks=[])
        fig.suptitle(f"E039 | Step{stage} / {Path(frame['source']).name} | fixed ROI; no display dilation\n"
                     f"Removed {row['removed_px']} / {old['mask'].sum()}px2 ({100*row['removed_fraction']:.2f}%); "
                     f"{row['eligible_branches']} eligible terminal branches\n"
                     "Cyan=before; blue=retained; orange=deleted candidate, not confirmed pore; purple=excluded",fontsize=11)
        finish(fig,f"F01_step{stage}_pore_candidate_cleanup",
               f"Top: identical full ROI original / original v1 mask / retained / removed overlays. Bottom: identical source crop "
               f"chosen by largest removed connected component plus80px margin; not visually or prediction-error selected. "
               f"Step{stage}: {row['removed_px']}px2 removed ({100*row['removed_fraction']:.3f}%). "
               f"All {row['protected_points']} protected full/common path pixels and original2xEDT values unchanged exactly. "
               "This only demonstrates a conservative local candidate repair; inspect original source for pore-like versus linear shapes.")

    fig = plt.figure(figsize=(11,7),constrained_layout=True)
    gs = fig.add_gridspec(2,2,height_ratios=[2,1])
    for j, band in enumerate(("full", "common")):
        ax = fig.add_subplot(gs[0,j])
        for i, row in enumerate(summary):
            before = 100*row[f"{band}_before_max_abs_relative_area_change"]
            after = 100*row[f"{band}_after_max_abs_relative_area_change"]
            ax.plot([i-.13,i+.13],[before,after],color=".5",lw=1)
            ax.scatter(i-.13,before,color=".3",marker="o",label="Before" if i==0 else None)
            ax.scatter(i+.13,after,color="#0072B2",marker="s",label="After" if i==0 else None)
            ax.annotate(f"{before:.2f}",(i-.13,before),xytext=(-5,9),textcoords="offset points",ha="right",fontsize=9)
            ax.annotate(f"{after:.2f}",(i+.13,after),xytext=(5,9 if after < 8 else -15),textcoords="offset points",ha="left",fontsize=9)
        ax.set(xticks=range(5),xticklabels=[str(r["stage"]) for r in summary],xlabel="Stage",ylabel="Max absolute area setting-change (%)",ylim=(0,None))
        ax.margins(x=.15,y=.18)
        ax.set_title("Full visible ROI" if band=="full" else "Fixed common image band")
        ax.grid(alpha=.15)
        ax.legend(loc="upper right")
    ax = fig.add_subplot(gs[1,:]); ax.axis("off")
    cell = [[r["stage"],r["removed_px"],f"{100*r['removed_fraction']:.3f}%",r["eligible_branches"],r["protected_points"],"0.000"] for r in summary]
    table = ax.table(cellText=cell,colLabels=["Stage","Removed px2","Removed / v1","Eligible branches","Protected points","Fixed-path EDT delta (px)"],loc="center",cellLoc="center")
    table.auto_set_font_size(False);table.set_fontsize(9);table.scale(1,1.6)
    fig.suptitle("E039 | Conservative deletion and residual 8-setting area sensitivity\nSame rule across45 saved cases; lower sensitivity is not accuracy",fontsize=12)
    finish(fig,"F02_removal_and_residual_sensitivity",
           "Exact paired gray before/blue after maximum absolute relative area changes vs own default over eight existing OAT settings. "
           "Separate full/common scales; table reports default5frames removal, eligibility and original protected path coverage. "
           "Zero EDT delta is a construction invariant, not measurement validation. All settings retained; no gain-based parameter choice.")
    save(a.output / "visual_qa.json", qa)
    rec.update(execution="succeeded", ended_at_utc=now(), elapsed_wall_s=time.monotonic()-start,
               source_run=str(a.run), groups=len(qa))
    save(a.output / "render_receipt.json", rec)


if __name__ == "__main__":
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("--run",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--preview",action="store_true")
    run(p.parse_args())
