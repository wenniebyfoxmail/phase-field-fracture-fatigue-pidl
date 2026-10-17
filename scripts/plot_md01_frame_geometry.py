"""E037 saved pixel geometry: raw overlays, visible support and scalar replay."""
import argparse,csv,json,os,socket,subprocess,sys,time
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image,ImageOps
from md01_early_relative import save,now
sys.path.insert(0,"/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout,render_preview


def run(a):
    started=now();start=time.monotonic();a.output.mkdir(parents=True,exist_ok=False)
    lock=json.loads(a.lock.read_text());support=json.loads(a.support.read_text());rows=[];arrays={};paths={}
    for d in (a.history,a.target):
        rows.extend(json.loads((d/"frame_metrics.json").read_text()))
        for f in (d).glob("step*/geometry_arrays.npz"):
            s=int(f.parent.name[4:])
            with np.load(f) as data:arrays[s]={k:data[k].copy() for k in data.files}
            paths[s]=json.loads((f.parent/"paths.json").read_text())
    rows.sort(key=lambda r:r["stage"]);by={r["stage"]:r for r in rows};sources={f["stage"]:f for f in lock["frames"]};scores=json.loads((a.target/"comparison.json").read_text());pred=json.loads((a.history/"geometry_predictions_before_target.json").read_text())
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})
    qa={};scope="Observer-guided candidates, not truth or old half-depth; native image pixels, not physical aperture. All frames viewed; one source trajectory."
    guide={
      "F01_visible_candidate_overlays":("Do per-frame paths remain measurable without old four-anchor correspondence?","Five observed-trace frames in stage order. Unenhanced RGB source crop; cyan tint=candidate mask; orange solid=dominant image-derived paths; grey dashed=coarse observer guidance,not measured path; magenta shading=excluded fixture/glue/boundary areas;blue rectangle=fixed forecast image-region. Unseen areas are not bridged; small omissions/false segments remain visible."),
      "F02_all_frame_geometry":("Which per-frame geometric outputs and exclusions are available?","All9frames in original stage order. Panels length inpx,area inpx2,local maskthickness inpx,excluded ROI fraction. Fullvisible support differs acrossframes: these are descriptive points,not growthcurves. Thickness bars10th–90thpoint percentiles,notconfidence intervals; black median marker. Unidentified frames explicitly missing,not zero. No interpolating missingstates or average-onlybar."),
      "F03_along_path_thickness":("What local mask-thickness distribution occurs along extracted fragments?","One panel per visible frame. Each fragment's measured path has ordered image coordinates and local s; fragments are concatenated on cumulative visible-only s,with a small displaygap and no connecting line across gaps. Withheld thickness nearROI/exclusion boundary remainsNaN. This is2xEDT-to-background pixel centres,not half-depth/normal aperture. Point grid/threshold/corridor dependence remains."),
      "F04_common_band_forecasts":("How do persistence and two-point trend compare on new image-region metrics?","Six panels separate units: area is sole primary,remaining length/mean/P10/P50/P90thickness descriptive. Black measured extractor outputs at21/22/23;grey squares=persistence,blue triangles=trend saved from21/22. Eachpanel prints both absolute errors andgain. No pooling acrossunits or six-independent-test claim; commonbandnot materialpoint correspondence."),
      "F05_common_band_overlays":("What exact image content supplies the scalar replay references?","Three original native[3900,1700,4600,1950] crops21/22/23,cyan mask andorange extractedpath. Sameimage-coordinate bounds,notmaterialregistration. Exclusionmaskmustnotintersectband;widthsamples refer tofullper-frame maskwith boundarywithholding. Showrawtexture withmask overlay,noenhancement or newmeasurement."),
      "F06_unidentified_source_regions":("What was left unidentified rather than measured as zero?","Four existing early-frame native source crops12/13/15/16 in fixedstageorder. No credible guide was defined fromeachimage,so no candidate measurement isreported. Plain sourcewith excludedboundary tint,not a successful mask or negativegroundtruth. This visual triage isobserver-assisted anddoesnot prove absent or zero-width cracks.")}
    def finish(fig,name):
        qa[name]=audit_layout(fig);stem=name+("_preview" if a.preview else "")
        caption=f"# How to read {name}\n\n## Figure question\n\n{guide[name][0]}\n\n## Data provenance\n\nE037 R001history {a.history}, R002target {a.target}; frame_metrics.json, geometry_arrays.npz, paths.json, comparison.json. Frozen source/frame support locks {a.lock}, {a.support}; sources are E0369existing images. Plot script scripts/plot_md01_frame_geometry.py, commit{subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}; render only,no new masks/geometry/predictions.\n\n## Visual grammar and panel guide\n\n{guide[name][1]}\n\n## Numerical takeaway\n\nVisible candidate frames {sum(r['full']['valid'] for r in rows)}/9; original background anchors not used. Commonband area result: {next(r for r in scores if r['metric']=='area_px2')}. Other exactmetrics remain separate in comparison.json. Old definition/scores untouched.\n\n## Limitations and claim boundary\n\n{scope} No independent segmentation groundtruth; coarse masks/guide may miss finecracks or include texture. Mask-dependent length/area/thickness change with segmentation andsupport. Fullvisible changes underocclusion are notphysicalshrinkage. Fixedimagebandallows image-space replay,not calibrated materialtracking. Retrospective1query,no population generalisation or blindvalidation.\n\n## Related assets\n\nREADME_analysis.md, scalar_replay.csv, per_frame_geometry.csv; originaltarget inE036alreadyviewed. PNG/PDFshare sidecar,grayscale markerredundancy. Previewonlydisplayversion.\n"
        (a.output/(stem+".md")).write_text(caption)
        if a.preview:render_preview(fig,a.output/(stem+".png"),dpi=150)
        else:
            fig.savefig(a.output/(stem+".png"),dpi=300);fig.savefig(a.output/(stem+".pdf"))
            with Image.open(a.output/(stem+".png")) as im:ImageOps.grayscale(im).save(a.output/(stem+"_gray.png"),dpi=(300,300))
            (a.output/(stem+"_gray.md")).write_text(caption)
        plt.close(fig)
    def image_crop(s,roi):
        with Image.open(sources[s]["source"]) as raw:return np.asarray(ImageOps.exif_transpose(raw).convert("RGB").crop(roi))
    def overlay(ax,s,roi,full=False):
        x0,y0,x1,y1=roi;ax.imshow(image_crop(s,roi),extent=[x0-.5,x1-.5,y1-.5,y0-.5]);ar=arrays[s]
        b=(np.array(roi)-np.array([3800,900,3800,900])).astype(int);mask=ar["mask"][b[1]:b[3],b[0]:b[2]];ex=ar["excluded"][b[1]:b[3],b[0]:b[2]]
        rgba=np.zeros((*mask.shape,4));rgba[mask]=[.1,.85,.95,.38];rgba[ex]=[.75,.1,.65,.35]
        ax.imshow(rgba,extent=[x0-.5,x1-.5,y1-.5,y0-.5],interpolation="nearest")
        for p in paths[s]["full" if full else "common"]:
            xy=np.array(p["xy_native"]);ax.plot(*xy.T,color="#D55E00",lw=.8)
        ax.set_xlim(x0-.5,x1-.5);ax.set_ylim(y1-.5,y0-.5)
        if full:
            pts=np.array(support["frames"][str(s)]["coarse_guide_xy"]);ax.plot(*pts.T,color=".8",ls=":",lw=.7)
            ax.add_patch(Rectangle((3900,1700),700,250,fill=False,color="#56B4E9",lw=1))
        ax.set_xticks([]);ax.set_yticks([])
    shown=[r["stage"] for r in rows if r["full"]["valid"]]
    fig,axes=plt.subplots(1,len(shown),figsize=(12,9),constrained_layout=True,squeeze=False)
    for ax,s in zip(axes[0],shown):
        overlay(ax,s,lock["roi_xyxy"],True);r=by[s]["full"]
        ax.set_title(f"Step{s}\nL={r['length_px']:.0f}px; A={r['area_px2']}px2",fontsize=9)
    fig.suptitle("E037 R001/R002 | per-frame visible candidates, no temporal-anchor requirement\nCyan=mask; orange=extracted path; dotted grey=observer guide; magenta=excluded; blue=common image band",fontsize=11)
    finish(fig,"F01_visible_candidate_overlays")
    fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True);ss=[r["stage"] for r in rows]
    for ax,key,title,unit in zip(axes.flat,("length_px","area_px2","thickness_p50_px",None),("Visible dominant-fragment length","Visible candidate area","Local mask thickness: P10 / median / P90","Excluded ROI fraction"),("px","px2","px","fraction")):
        for r in rows:
            x=r["stage"];v=r["full"].get(key) if key else r["excluded_fraction"]
            if v is None:ax.text(x,.03,"?",transform=ax.get_xaxis_transform(),ha="center",fontsize=11);continue
            ax.scatter(x,v,color="black",marker="o",s=28)
            if key=="thickness_p50_px":ax.plot([x,x],[r["full"]["thickness_p10_px"],r["full"]["thickness_p90_px"]],color="#0072B2",lw=1.5)
        ax.set(title=title,xticks=ss,xlabel="Ordinal stage",ylabel=unit);ax.set_ylim(bottom=0);ax.grid(alpha=.15)
    fig.suptitle("E037 R001/R002 | all9 existing frames; '?' = unidentified, not zero\nFull visible supports differ: do not interpret these points as physical growth/shrinkage",fontsize=11)
    finish(fig,"F02_all_frame_geometry")
    fig,axes=plt.subplots(1,len(shown),figsize=(13,4.2),sharey=True,constrained_layout=True,squeeze=False)
    for ax,s in zip(axes[0],shown):
        offset=0.
        for p in paths[s]["full"]:
            widths=np.array([np.nan if w is None else w for w in p["local_mask_thickness_px"]]);ax.plot(np.array(p["arc_length_px"])+offset,widths,color="#0072B2",lw=.9);offset+=p["length_px"]+10
        ax.set(title=f"Step{s}",xlabel="Visible-path s (px)");ax.set_ylim(bottom=0);ax.grid(alpha=.15)
    axes[0,0].set_ylabel("2 x mask EDT (px)")
    fig.suptitle("E037 R001/R002 | along-path local candidate-mask thickness\nFragments not bridged; boundary-near samples withheld; not old half-depth or physical aperture",fontsize=11)
    finish(fig,"F03_along_path_thickness")
    fig,axes=plt.subplots(2,3,figsize=(12,7.2),constrained_layout=True)
    for ax,c in zip(axes.flat,scores):
        key=c["metric"];ys=[by[s]["common"][key] for s in (21,22,23)];ax.axvspan(22.5,23.2,color=".95")
        ax.plot([21,22,23],ys,"o-",color="black",lw=1.2)
        for arm,color,m in (("persistence",".5","s"),("trend","#0072B2","^")):
            if c[arm] is not None:ax.plot([22,23],[ys[1],c[arm]],ls="--",color=color,marker=m,lw=1.1)
        ax.set(title=key.replace("_"," ")+(" [PRIMARY]" if key=="area_px2" else ""),xticks=[21,22,23],xlabel="Ordinal stage",ylabel=c["unit"]);ax.set_ylim(bottom=0);ax.margins(y=.28);ax.grid(alpha=.15)
        if c["scored"]:ax.text(.02,.97,f"AE keep {c['persistence_ae']:.2f} | trend {c['trend_ae']:.2f}\nGain {c['gain']:+.2f} {c['unit']}",transform=ax.transAxes,va="top",fontsize=8)
        else:ax.text(.5,.5,"Not scored",transform=ax.transAxes,ha="center")
    fig.legend(handles=[Line2D([],[],color="black",marker="o",label="Extractor reference"),Line2D([],[],color=".5",ls="--",marker="s",label="Persistence"),Line2D([],[],color="#0072B2",ls="--",marker="^",label="Two-point trend")],loc="outside lower center",ncols=3,frameon=False)
    fig.suptitle("E037 R001/R002 | retrospective scalar replay on the SAME fixed unoccluded image band\nOne query / already-viewed frames; separate units, not6 independent validations",fontsize=11)
    finish(fig,"F04_common_band_forecasts")
    fig,axes=plt.subplots(1,3,figsize=(12,3.4),constrained_layout=True)
    for ax,s in zip(axes,(21,22,23)):
        overlay(ax,s,lock["forecast_roi_xyxy"]);ax.set_title(f"Step{s} | common area {by[s]['common']['area_px2']}px2",fontsize=10)
    fig.suptitle("E037 R001/R002 | exact common image-space reference support\nNative x3900..4600,y1700..1950; not same-material-point registration",fontsize=11)
    finish(fig,"F05_common_band_overlays")
    early=[r["stage"] for r in rows if not support["frames"][str(r["stage"])]["visible_trace"]]
    fig,axes=plt.subplots(1,len(early),figsize=(10,8),constrained_layout=True,squeeze=False)
    for ax,s in zip(axes[0],early):
        overlay(ax,s,lock["roi_xyxy"]);ax.set_title(f"Step{s}\nUnidentified, not zero",fontsize=9)
    fig.suptitle("E037 R001 | all4 early source regions retained\nNo observer-defined credible trace; not an automatic no-crack classification or physical zero",fontsize=11)
    finish(fig,"F06_unidentified_source_regions")
    flat=[dict(stage=r["stage"],visibility=r["visibility"],excluded_fraction=r["excluded_fraction"],**{scope0+"_"+k:v for scope0 in ("full","common") for k,v in r[scope0].items()}) for r in rows]
    for name,data in (("per_frame_geometry.csv",flat),("scalar_replay.csv",scores)):
        with (a.output/name).open("x",newline="") as f:w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator="\n");w.writeheader();w.writerows(data)
    save(a.output/"layout_audit.json",qa);save(a.output/"run_receipt.json",dict(execution="succeeded",retrieval="verified_local",render_only=True,no_new_geometry=True,started_at_utc=started,ended_at_utc=now(),wall_seconds=time.monotonic()-start,commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),host=socket.gethostname(),pid=os.getpid(),command=sys.argv));print(json.dumps(qa,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("lock","support","history","target","output"):p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--preview",action="store_true");run(p.parse_args())
