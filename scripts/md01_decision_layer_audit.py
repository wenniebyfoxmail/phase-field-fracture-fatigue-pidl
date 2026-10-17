"""E040 readonly fixed decision layers; never invokes crack extraction or CC."""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

import md01_frame_geometry as v1
from md01_geometry_stability import receipt
from md01_early_relative import save,now

BOX=[4100,2600,4450,3160]


def compute(a):
    started,cpu=time.monotonic(),time.process_time()
    m=json.loads(a.manifest.read_text());assert m["frame"]["stage"]==19
    protected=dict(m["protected_files"])
    for p in [a.manifest,a.saved/"support_comparison_arrays.npz",a.saved/"summary.json",
              a.saved/"run_receipt.json",Path(__file__).resolve(),a.plan.resolve()]:
        protected[str(p.resolve())]=v1.sha(p)
    assert all(v1.sha(p)==h for p,h in protected.items())
    a.output.mkdir(parents=True,exist_ok=False)
    rec=receipt("E040_readonly_decision_layers")
    rec.update(protocol="step19-fixed-decision-layer-audit-v1",execution="running",
               input_manifest=str(a.manifest.resolve()),saved_result=str(a.saved.resolve()),
               protected_files=protected,no_crack_extraction=True,no_component_reselection=True)
    save(a.output/"run_start_receipt.json",rec)
    try:
        roi=m["spec"]["roi"];rgb=v1.read_frame(m["frame"],roi)
        gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float32)
        contrast=cv2.boxFilter(gray,-1,(101,101),borderType=cv2.BORDER_REFLECT)-gray
        seed=np.zeros(gray.shape,np.uint8)
        points=np.rint(np.array(m["old_support"]["coarse_guide_xy"])-roi[:2]).astype(np.int32)
        cv2.polylines(seed,[points],False,1,thickness=1)
        distance=distance_transform_edt(~seed.astype(bool))
        with np.load(a.saved/"support_comparison_arrays.npz") as z:
            excluded=z["new_excluded"];mask=z["new_mask"];released=z["released_support"]
        dark=gray<=100;local=contrast>=20;corridor=distance<=60;visible=~excluded
        eligible=dark & local & corridor & visible
        assert not np.any(mask & ~eligible), "Savedmask outside fixed pixel gates"
        unretained=eligible & ~mask
        arrays=dict(gray=gray,local_contrast=contrast,guide_distance=distance,
                    gray_pass=dark,contrast_pass=local,corridor_pass=corridor,
                    excluded=excluded,released_support=released,
                    pixel_gate_eligible=eligible,saved_mask=mask,post_gate_unretained=unretained)
        np.savez_compressed(a.output/"decision_layers.npz",**arrays)
        x0,y0,x1,y1=np.array(BOX)-np.array([roi[0],roi[1],roi[0],roi[1]])
        region=np.zeros(gray.shape,bool);region[y0:y1,x0:x1]=True
        def tally(scope):
            left=scope.copy();out={"pixels":int(scope.sum())}
            for name,condition in (("excluded",visible),("gray_fail",dark),
                                   ("contrast_fail_after_gray",local),("corridor_fail_after_gray_contrast",corridor)):
                out[name]=int((left & ~condition).sum());left &= condition
            out["passes_all_pixel_gates"]=int(left.sum())
            out["not_retained_in_saved_mask"]=int((left & ~mask).sum())
            out["retained_in_saved_mask"]=int((left & mask).sum())
            out["independent_gray_fail"]=int((scope & ~dark).sum())
            out["independent_contrast_fail"]=int((scope & ~local).sum())
            out["independent_corridor_fail"]=int((scope & ~corridor).sum())
            assert sum(out[k] for k in ("excluded","gray_fail","contrast_fail_after_gray","corridor_fail_after_gray_contrast","passes_all_pixel_gates"))==out["pixels"]
            return out
        summary=dict(stage=19,fixed_crop_native_xyxy=BOX,full_crop=tally(region),
                     released_in_crop=tally(region & released),
                     no_pixel_truth_or_recall=True,no_mask_or_definition_change=True,
                     inputs_unchanged=len(protected))
        save(a.output/"summary.json",summary)
        assert all(v1.sha(p)==h for p,h in protected.items())
        if max(time.monotonic()-started,time.process_time()-cpu)>30:raise TimeoutError("30s auditcap")
        rec.update(execution="succeeded",retrieval="verified_local")
    except Exception as exc:
        rec.update(execution="failed",error=repr(exc));raise
    finally:
        rec.update(ended_at_utc=now(),elapsed_wall_s=time.monotonic()-started,elapsed_cpu_s=time.process_time()-cpu)
        save(a.output/"run_receipt.json",rec)
    print(json.dumps(summary,indent=2))


def plot(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image,ImageOps
    m=json.loads(a.manifest.read_text());summary=json.loads((a.audit/"summary.json").read_text())
    with np.load(a.audit/"decision_layers.npz") as z:d={k:z[k] for k in z.files}
    rgb=v1.read_frame(m["frame"],m["spec"]["roi"])
    roi=m["spec"]["roi"];x0,y0,x1,y1=np.array(BOX)-np.array([roi[0],roi[1],roi[0],roi[1]])
    sl=np.s_[y0:y1,x0:x1];extent=(BOX[0]-.5,BOX[2]-.5,BOX[3]-.5,BOX[1]-.5)
    a.output.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"pdf.fonttype":42})
    fig,axes=plt.subplots(1,5,figsize=(14,6.4),layout="constrained")
    def tint(ax,data,color,alpha):
        rgba=np.zeros((*data.shape,4),np.float32);rgba[data]=[*color,alpha]
        ax.imshow(rgba,extent=extent,interpolation="nearest")
    titles=["a  Original RGB","b  Gray <=100 passes","c  Local contrast >=20 passes","d  Fixed guide / 60px corridor","e  Actual saved mask / unretained"]
    for i,ax in enumerate(axes):
        ax.imshow(rgb[sl],extent=extent,interpolation="nearest")
        if i in (1,2):tint(ax,d["gray_pass" if i==1 else "contrast_pass"][sl],(0,.6,.7),.75)
        if i==3:
            tint(ax,~d["corridor_pass"][sl],(.1,.1,.1),.5)
            xs=np.arange(BOX[0],BOX[2]);ys=np.arange(BOX[1],BOX[3])
            ax.contour(xs,ys,d["guide_distance"][sl],levels=[60],colors=["#E69F00"],linewidths=1)
            xy=np.array(m["old_support"]["coarse_guide_xy"])
            ax.plot(xy[:,0],xy[:,1],color="black",lw=2);ax.plot(xy[:,0],xy[:,1],color="white",lw=1)
        if i==4:
            tint(ax,d["post_gate_unretained"][sl],(.9,.32,.05),.85)
            tint(ax,d["saved_mask"][sl],(0,.35,.7),.85)
        if i:tint(ax,d["excluded"][sl],(.65,.12,.55),.25)
        ax.set(xlim=extent[:2],ylim=(extent[2],extent[3]),xlabel="Native x (px)")
        ax.set_title(titles[i],fontsize=9)
        ax.set_xticks([4150,4250,4350]);ax.set_yticks([2700,2900,3100])
        if i:ax.tick_params(labelleft=False)
    axes[0].set_ylabel("Native y (px)")
    fig.suptitle("E040 read-only Step19 left-gap diagnosis | same source, fixed gates, saved mask unchanged\n"
                  "Cyan=one condition passes, NOT crack; dark shade=outside corridor; purple=excluded\n"
                  "Blue=saved mask; orange=all pixel gates pass but not retained, NOT ground-truth missed crack",fontsize=11)
    fig.canvas.draw();renderer=fig.canvas.get_renderer();w,h=fig.canvas.get_width_height();outside=[]
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_visible() and t.get_text():
            b=t.get_window_extent(renderer)
            if b.x0<-.5 or b.y0<-.5 or b.x1>w+.5 or b.y1>h+.5:outside.append(t.get_text())
    name="F01_step19_left_decision_layers"+("_preview" if a.preview else "")
    fig.savefig(a.output/(name+".png"),dpi=150 if a.preview else 300)
    guide=(f"# How to read {name}\n\n## Data provenance\n\nE040 readonlyR008 {a.audit}, unchangedStep19 IMG_0379.JPG viaR004manifest {a.manifest}. "
           "Fixednativecrop [4100,2600,4450,3160], fullROI original101pxbackground andguide-distance semantics beforecrop. "
           "No crack extraction, component reselection, new mask, metrology or prediction.\n\n"
           "## Figure question and panels\n\nWhy did leftsupport release add0candidatepixels? a originalRGB, b cyangray<=100 eligibility, "
           "c cyanlocalcontrast>=20 eligibility, d originalguide white/black and60pxorange boundary; grayoutside corridor, "
           "e actualE040savedmaskblue, orange passes allpixelgates but absentfrom savedmask. Purpleexistingexclusion, not detection. "
           "Nativepx axes, identicalcrop/scale, source unenhanced, no displaydilation. Single-gatepass is not crack prediction.\n\n"
           f"## Numerical takeaway\n\nReleasedsupport withincrop has {summary['released_in_crop']['pixels']}px, "
           f"grayfailure {summary['released_in_crop']['gray_fail']}, nextcontrastfailure {summary['released_in_crop']['contrast_fail_after_gray']}, "
           f"then corridorfailure {summary['released_in_crop']['corridor_fail_after_gray_contrast']}, "
           f"allpixelgateeligible {summary['released_in_crop']['passes_all_pixel_gates']}, "
           f"retained {summary['released_in_crop']['retained_in_saved_mask']}. Orderedaccounting, not causalcrackpercentages.\n\n"
           "## Limitations\n\nOne already-exposed frame, regionincludes pores/texture; counts not recall or truecracklabels. "
           "No new C/N/U labels, no physicalwidth. Sharedsource/code arithmetic audit, not independent reference. "
           "Guideoutside can explain some visible omissions, but contrast and componentretention may also matter. "
           "SavedE040+1021bottom/0left result andv1/halfdepth/oldscores stay unchanged.\n\n"
           "## Related assets\n\nR008summary.json/decision_layers.npz/receipt, decision_layer_diagnostic.md andREADME_analysis.md. "
           "PDF/color/gray shareguide; grayscale is display-only.\n")
    (a.output/(name+".md")).write_text(guide)
    if not a.preview:
        fig.savefig(a.output/(name+".pdf"))
        with Image.open(a.output/(name+".png")) as im:ImageOps.grayscale(im).save(a.output/(name+"_gray.png"),dpi=(300,300))
        (a.output/(name+"_gray.md")).write_text(guide)
    plt.close(fig);save(a.output/"visual_qa.json",dict(outside_canvas_text=outside))
    rec=receipt("E040_decision_layers_render");rec.update(execution="succeeded",ended_at_utc=now(),audit=str(a.audit))
    save(a.output/"render_receipt.json",rec)


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("phase",choices=("compute","plot"))
    p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--saved",type=Path);p.add_argument("--plan",type=Path)
    p.add_argument("--audit",type=Path);p.add_argument("--preview",action="store_true")
    a=p.parse_args();(compute if a.phase=="compute" else plot)(a)
