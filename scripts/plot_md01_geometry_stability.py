"""Display saved E038 geometry; does not extract masks or fit parameters."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import numpy as np
from PIL import Image, ImageOps

import md01_frame_geometry as v1
from md01_early_relative import save, now
sys.path.insert(0, "/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout, render_preview


def run(a):
    started, clock_start = now(), time.monotonic()
    a.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(a.manifest.read_text())
    rows = json.loads((a.run / "all_metrics.json").read_text())
    by = {(r["stage"],r["arm"]):r for r in rows}
    stages, arms, roi = manifest["stages"], [x["id"] for x in manifest["arms"]], manifest["roi"]
    labels = ["G-5", "G+5", "C-5", "C+5", "x-5", "x+5", "y-5", "y+5"]
    source = {f["stage"]:f for f in manifest["frames"]}
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "pdf.fonttype":42,
                         "axes.spines.top":False, "axes.spines.right":False})
    qa = {}
    title_scope = "E038 R001 | 5 existing frames / 9 fixed settings; sensitivity, not accuracy"
    commit = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()

    def finish(fig, name, question, how):
        qa[name] = audit_layout(fig)
        stem = name + ("_preview" if a.preview else "")
        caption = (f"# How to read {name}\n\n## Figure question\n\n{question}\n\n"
                   f"## Data provenance\n\nE038 R001saved arrays/paths/metrics: {a.run}; inputmanifest: {a.manifest}. "
                   f"Five original E036images18/19/21/22/23, E037v1 preserved. Plotcode scripts/plot_md01_geometry_stability.py commit{commit}; renderonly,no remeasurement.\n\n"
                   f"## Visual grammar and panels\n\n{how}\n\n"
                   "## Numerical takeaway\n\nExact45setting-frame metrics are in R001metrics.csv/all_metrics.json; perframe extrema in summary.json. "
                   "All8predeclared perturbations retained, none selected as replacement. See README_analysis.md for stage-specific results.\n\n"
                   "## Limitations and claim boundary\n\nOne source trajectory, not5specimens or45independent validations. "
                   "Observer-guided mask, not independent labels or automatic full-image detection. Full visible support differs across frames; "
                   "no physical growth/closure or material tracking. 2xEDT is local candidate-mask thickness, not half-depth/perpendicular aperture/mm. "
                   "No forecast computation/error-based tuning; olddefinitions/scores unchanged. Finite OAT range notCI orfullfactorial robustness.\n\n"
                   "## Related assets\n\nREADME_analysis.md, R001metrics.csv, summary.json, protocol and independent_review.md. "
                   "PNG/PDFshare this guide; grayscale is display-only, not new geometry.\n")
        (a.output/(stem+".md")).write_text(caption)
        if a.preview:
            render_preview(fig, a.output/(stem+".png"), dpi=150)
        else:
            fig.savefig(a.output/(stem+".png"), dpi=300)
            fig.savefig(a.output/(stem+".pdf"))
            with Image.open(a.output/(stem+".png")) as im:
                ImageOps.grayscale(im).save(a.output/(stem+"_gray.png"), dpi=(300,300))
            (a.output/(stem+"_gray.md")).write_text(caption)
        plt.close(fig)

    def show_source(ax, rgb):
        ax.imshow(rgb, extent=[roi[0]-.5,roi[2]-.5,roi[3]-.5,roi[1]-.5])
        ax.set_xlim(roi[0]-.5,roi[2]-.5)
        ax.set_ylim(roi[3]-.5,roi[1]-.5)
        ax.set_xticks([])
        ax.set_yticks([])

    def tint(ax, data, color, alpha):
        rgba = np.zeros((*data.shape,4))
        rgba[data] = [*color,alpha]
        ax.imshow(rgba, extent=[roi[0]-.5,roi[2]-.5,roi[3]-.5,roi[1]-.5],interpolation="nearest")

    for stage in stages:
        rgb = v1.read_frame(source[stage],roi)
        root = a.run/f"step{stage}"
        with np.load(root/"v1/geometry_arrays.npz") as f:
            data = {k:f[k].copy() for k in f.files}
        paths = json.loads((root/"v1/paths.json").read_text())["full"]
        with np.load(root/"fixed_path_stability.npz") as f:
            widths, baseline = f["thickness_grid"].copy(), f["baseline_thickness"].copy()
        fig = plt.figure(figsize=(10,11), constrained_layout=True)
        gs = fig.add_gridspec(3,4,height_ratios=[5,1.25,.6])
        axes = [fig.add_subplot(gs[0,k]) for k in range(4)]
        names = ["a  Original source", "b  v1 candidate mask", "c  Entire v1 skeleton", "d  Selected main paths"]
        for ax, name in zip(axes,names):
            show_source(ax,rgb)
            ax.set_title(name,fontsize=10)
        axes[1].images[0].set_visible(False)
        axes[1].set_facecolor("#f5f5f5")
        tint(axes[1],data["mask"],(.05,.5,.65),1)
        tint(axes[1],data["excluded"],(.75,.1,.65),.35)
        axes[2].images[0].set_alpha(.35)
        skeleton_display = cv2.dilate(data["skeleton"].astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        tint(axes[2],skeleton_display,(0,.35,.75),1)
        for p in paths:
            xy = np.array(p["xy_native"])
            axes[3].plot(xy[:,0],xy[:,1],color="#D55E00",lw=1)
        tint(axes[3],data["excluded"],(.75,.1,.65),.25)
        lineax, countax = fig.add_subplot(gs[1,:]), fig.add_subplot(gs[2,:])
        offset, begin = 0., 0
        for p in paths:
            n = len(p["arc_length_px"])
            sl = slice(begin,begin+n)
            sample = widths[:,sl]
            available = np.sum(np.isfinite(sample),axis=0)
            low = np.min(np.where(np.isfinite(sample),sample,np.inf),axis=0)
            high = np.max(np.where(np.isfinite(sample),sample,-np.inf),axis=0)
            low[available==0] = np.nan
            high[available==0] = np.nan
            s = np.array(p["arc_length_px"]) + offset
            lineax.fill_between(s,low,high,color=".75",alpha=.7)
            lineax.plot(s,baseline[sl],color="#0072B2",lw=1)
            countax.plot(s,available,color="black",lw=.8)
            offset += p["length_px"] + 10
            begin += n
        max_width = float(np.nanmax(widths))
        lineax.set_ylim(0,max_width*1.08)
        lineax.set_ylabel("Local mask thickness (px)")
        lineax.set_title("e  Fixed v1 path: blue=v1; gray=available-setting min/max (not CI)",fontsize=10)
        lineax.tick_params(labelbottom=False)
        countax.set(xlabel="Visible-path display s (px); 10px padding between fragments is not measured length",
                    ylabel="Settings",ylim=(-.4,9.5),yticks=[0,3,6,9])
        countax.set_title("f  Available settings per point (0..9); missing is not zero thickness",fontsize=9)
        for ax in (lineax,countax):
            ax.set_xlim(-5,max(1,offset-10)+5)
            ax.grid(alpha=.15)
        r = by[stage,"v1"]["full"]
        fig.suptitle(f"{title_scope}\nStep{stage}: v1 area {r['area_px2']}px2; visible dominant paths {r['length_px']:.1f}px",fontsize=11)
        finish(fig,f"F01_step{stage}_identification_layers",
               "How do raw source, candidate pixels, complete skeleton, selected paths and local thickness differ?",
               "a unenhanced original fixedROI; b binaryv1mask inblue and excludedregions inmagenta (white=not selected,not true negative); "
               "c allv1skeleton shown with3x3 display-onlydilation for legibility, not measuredthickness; d orange selectedmainpaths onRGB, excludedmagenta. "
               "e fixedv1path coordinates, bluev1 andgrayfinite9settingmin/max,notCI; gaps retained and10pxpaddingperfragmentdisplayonly. "
               "f numberofsettings withmaskpresent+safeatthatpoint; dropouts notfilled0thickness. No coordinate matching acrossframes.")

    fig,axes = plt.subplots(3,2,figsize=(12,9),constrained_layout=True)
    for row,(metric,factor,label) in enumerate((("area_px2",100,"Area change (%)"),("length_px",100,"Path length change (%)"),("thickness_p50_px",1,"Own-path median thickness change (px)"))):
        matrices = []
        for scope in ("full","common"):
            key = metric + ("_relative_delta" if factor==100 else "_delta")
            matrices.append(np.array([[by[s,arm][scope+"_change"][key] for arm in arms[1:]] for s in stages],float)*factor)
        lim = max(1e-8,float(np.nanmax(np.abs(matrices))))
        norm = Normalize(-lim,lim)
        for col,(scope,matrix) in enumerate(zip(("Full visible ROI","Common image band"),matrices)):
            ax = axes[row,col]
            ax.imshow(matrix,cmap="RdBu_r",norm=norm,aspect="auto")
            ax.set(xticks=range(8),xticklabels=labels,yticks=range(5),yticklabels=[f"Step{s}" for s in stages],title=f"{scope}: {label}")
            for y in range(5):
                for x in range(8):
                    value = matrix[y,x]
                    ax.text(x,y,f"{value:+.1f}" if np.isfinite(value) else "NA",ha="center",va="center",fontsize=8,
                            color="white" if np.isfinite(value) and abs(value)>.6*lim else "black")
        fig.colorbar(ScalarMappable(norm=norm,cmap="RdBu_r"),ax=axes[row,:],label=label,shrink=.8)
    fig.suptitle(title_scope+"\nAll8 one-at-a-time alternatives vs preserved v1; no forecast-based selection",fontsize=11)
    finish(fig,"F02_all_setting_geometry_changes","Which geometric outputs depend most on small fixed setting changes?",
           "Rows5frames,columns8alternatives in fixedorder. G=gray upperthreshold,C=minimumlocalcontrast,x/y=guide shift; signs are5levels/5nativepixels. "
           "Three panelrows area%,length%,ownpathmedianthicknesspx. Full/common share eachmetric's signedzero-centredcolourrange. "
           "Numbers are exactsaved-output differences roundedonly fordisplay; allarms retained,notselected byaccuracy orforecastgain.")

    fig,axes = plt.subplots(1,5,figsize=(12,8),constrained_layout=True)
    for ax,stage in zip(axes,stages):
        rgb = v1.read_frame(source[stage],roi)
        show_source(ax,rgb)
        with np.load(a.run/f"step{stage}/fixed_path_stability.npz") as f:
            counts=f["mask_setting_count"].copy()
        ax.imshow(np.ma.masked_where(counts==0,counts),cmap="viridis",vmin=1,vmax=9,
                  extent=[roi[0]-.5,roi[2]-.5,roi[3]-.5,roi[1]-.5],interpolation="nearest")
        ax.set_title(f"Step{stage}")
    fig.colorbar(ScalarMappable(norm=Normalize(1,9),cmap="viridis"),ax=axes,label="Candidate-mask support count / 9 settings",ticks=[1,3,5,7,9],shrink=.55)
    fig.suptitle(title_scope+"\nSpatial support across fixed settings; NOT probability or ground-truth agreement",fontsize=11)
    finish(fig,"F03_spatial_setting_support","Where do the fixed alternatives keep or drop candidate pixels?",
           "All5unalteredROI images,overlaidcandidate-membershipcountamongbaseline+8alternatives; sharedviridis1..9withzero transparent. "
           "Count9meansselectedunderall9settings,nottruecrackcertainty; lowcountsindicatethreshold/guide sensitivity. No spatialregistration or newmask inferred.")

    fig,axes = plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
    specifications = [("full_change","path_distance_p90_px",1,"Symmetric nearest-path distance P90 (px)",None),
                      (None,"fixed_v1_path_available_fraction",100,"Fixed v1 path availability (%)",100)]
    for ax,(scope,key,factor,title,upper) in zip(axes,specifications):
        matrix=np.array([[(by[s,arm][scope][key] if scope else by[s,arm][key]) for arm in arms[1:]] for s in stages],float)*factor
        top = upper if upper else max(1e-8,float(np.nanmax(matrix)))
        im=ax.imshow(matrix,cmap="viridis",vmin=0,vmax=top,aspect="auto")
        ax.set(xticks=range(8),xticklabels=labels,yticks=range(5),yticklabels=[f"Step{s}" for s in stages],title=title)
        for y in range(5):
            for x in range(8):
                value=matrix[y,x]
                ax.text(x,y,f"{value:.1f}" if np.isfinite(value) else "NA",ha="center",va="center",fontsize=8,color="black" if value>.6*top else "white")
        fig.colorbar(im,ax=ax,shrink=.8,label="px" if scope else "%")
    fig.suptitle(title_scope+"\nPath changes and missing mask support are separate from thickness shifts",fontsize=11)
    finish(fig,"F04_path_and_sample_stability","Does the extracted path or coverage change even when scalar geometry looks similar?",
           "All5frames×8alternatives. LeftP90 ofpooledbidirectional nearestpoint distancesbetweenvariantselectedpath andv1,notpositiontruth; branches/dropouts affectit. "
           "Rightfractionoforiginalsafev1pathpoints stillinsidevariantmaskandfixedsafearea,notdetectorrecall. Separatecolourbars/units andallcells shown.")
    save(a.output/"layout_audit.json",qa)
    save(a.output/"run_receipt.json",dict(execution="succeeded",retrieval="verified_local",render_only=True,
         commit=commit,dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),
         started_at_utc=started,ended_at_utc=now(),wall_seconds=time.monotonic()-clock_start,
         host=socket.gethostname(),pid=os.getpid(),command=sys.argv))
    print(json.dumps(qa,indent=2))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    for key in ("run","manifest","output"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--preview",action="store_true")
    run(p.parse_args())
