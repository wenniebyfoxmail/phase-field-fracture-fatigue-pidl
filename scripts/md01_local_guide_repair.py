"""One same-source local-guide comparison; unchanged v1 extractor/thresholds."""
import argparse,copy,json,time
from pathlib import Path
import numpy as np
import md01_frame_geometry as v1
from md01_geometry_stability import receipt
from md01_early_relative import save,now


def run(a):
    start,cpu=time.monotonic(),time.process_time()
    m=json.loads(a.manifest.read_text());spec=json.loads(a.spec.read_text())
    assert m["frame"]["stage"]==19 and spec["status"].startswith("authorised_for_one_")
    assert v1.sha(a.manifest)==spec["parent_support_manifest_sha256"]
    protected=dict(m["protected_files"])
    for p in [a.manifest,a.spec,a.plan,Path(__file__).resolve(),a.baseline/"support_comparison_arrays.npz",a.baseline/"summary.json",a.baseline/"run_receipt.json"]:
        protected[str(p.resolve())]=v1.sha(p)
    assert all(v1.sha(p)==h for p,h in protected.items())
    support=copy.deepcopy(m["new_support"]);new_support=copy.deepcopy(support)
    new_support["coarse_guide_xy"]=spec["proposed_coarse_guide_native_xy"]
    assert new_support["coarse_guide_xy"][:5]==support["coarse_guide_xy"][:5]
    assert new_support["coarse_guide_xy"][-1]==support["coarse_guide_xy"][-1]
    assert {k:v for k,v in new_support.items() if k!="coarse_guide_xy"}=={k:v for k,v in support.items() if k!="coarse_guide_xy"}
    a.output.mkdir(parents=True,exist_ok=False)
    rec=receipt("E041_single_local_guide_comparison")
    rec.update(protocol="step19-local-guide-source-v1",execution="running",protected_files=protected,
               parent_manifest=str(a.manifest.resolve()),frozen_spec=spec)
    save(a.output/"run_start_receipt.json",rec)
    try:
        roi=m["spec"]["roi"];rgb=v1.read_frame(m["frame"],roi)
        with np.load(a.baseline/"support_comparison_arrays.npz") as z:
            baseline=z["new_mask"];excluded=z["new_excluded"];bottom=z["added_candidates"]
        old,ex,_=v1.extract(rgb,support,roi)
        assert np.array_equal(old,baseline) and np.array_equal(ex,excluded)
        new,newex,_=v1.extract(rgb,new_support,roi)
        assert np.array_equal(newex,excluded) and not np.any(new&newex)
        added=new&~old;removed=old&~new
        np.savez_compressed(a.output/"guide_comparison_arrays.npz",old_mask=old,new_mask=new,
                            excluded=excluded,added=added,removed=removed,old_bottom_additions=bottom)
        crop=np.s_[1700:2260,300:650]
        summary=dict(stage=19,baseline_exact=True,old_area_px2=int(old.sum()),new_area_px2=int(new.sum()),
             added_px2=int(added.sum()),removed_px2=int(removed.sum()),
             left_crop_old_px2=int(old[crop].sum()),left_crop_new_px2=int(new[crop].sum()),
             left_crop_added_px2=int(added[crop].sum()),left_crop_removed_px2=int(removed[crop].sum()),
             old_bottom_added_px2=int(bottom.sum()),old_bottom_additions_retained_px2=int((bottom&new).sum()),
             thresholds_and_exclusions_unchanged=True,no_width_path_forecast_or_scoring=True,
             no_true_crack_accuracy_claim=True)
        assert summary["new_area_px2"]==summary["old_area_px2"]+summary["added_px2"]-summary["removed_px2"]
        save(a.output/"summary.json",summary)
        save(a.output/"support_and_source.json",dict(frame=m["frame"],roi=roi,old_support=support,new_support=new_support))
        assert all(v1.sha(p)==h for p,h in protected.items())
        if max(time.monotonic()-start,time.process_time()-cpu)>60:raise TimeoutError("60s cap")
        rec.update(execution="succeeded",retrieval="verified_local",protected_files_unchanged=len(protected))
    except Exception as exc:
        rec.update(execution="failed",error=repr(exc));raise
    finally:
        rec.update(ended_at_utc=now(),elapsed_wall_s=time.monotonic()-start,elapsed_cpu_s=time.process_time()-cpu)
        save(a.output/"run_receipt.json",rec)
    print(json.dumps(summary,indent=2))


def plot(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image,ImageOps
    m=json.loads((a.result/"support_and_source.json").read_text())
    summary=json.loads((a.result/"summary.json").read_text())
    with np.load(a.result/"guide_comparison_arrays.npz") as z:d={k:z[k] for k in z.files}
    rgb=v1.read_frame(m["frame"],m["roi"]);a.output.mkdir(parents=True,exist_ok=False)
    rec=receipt("E041_saved_guide_comparison_render")
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42})
    qa={}
    for stem,box,size in [("F01_fixed_left_guide_comparison",[4100,2600,4450,3160],(11,6)),
                          ("F02_full_roi_guide_comparison",m["roi"],(11,8))]:
        x0,y0,x1,y1=np.array(box)-np.array([3800,900,3800,900]);sl=np.s_[y0:y1,x0:x1]
        extent=(box[0]-.5,box[2]-.5,box[3]-.5,box[1]-.5)
        fig,axes=plt.subplots(1,4,figsize=size,layout="constrained")
        def tint(ax,data,color,alpha):
            rgba=np.zeros((*data.shape,4),np.float32);rgba[data]=[*color,alpha]
            ax.imshow(rgba,extent=extent,interpolation="nearest")
        for i,(ax,title) in enumerate(zip(axes,["Original RGB","Old guide / saved mask","Aligned guide / candidate","Orange added / green removed"])):
            ax.imshow(rgb[sl],extent=extent,interpolation="nearest")
            if i in (1,2):
                tint(ax,d["excluded"][sl],(.65,.12,.55),.25)
                tint(ax,d["old_mask" if i==1 else "new_mask"][sl],(0,.6,.7) if i==1 else (0,.35,.7),.8)
            if i==3:
                tint(ax,d["added"][sl],(.9,.32,.05),.85);tint(ax,d["removed"][sl],(0,.6,.4),.85)
            ax.set(xlim=extent[:2],ylim=(extent[2],extent[3]),xticks=[],yticks=[]);ax.set_title(title,fontsize=9)
        axes[0].set_xlabel(f"native x[{box[0]},{box[2]}), y[{box[1]},{box[3]})",fontsize=8)
        fig.suptitle(f"E041 | Step19 | only local guide changed; thresholds/exclusions fixed\n"
                      f"FullROI +{summary['added_px2']} / -{summary['removed_px2']} candidatepx2; "
                      f"leftcrop +{summary['left_crop_added_px2']} / -{summary['left_crop_removed_px2']}\n"
                      "Purple=excluded; cyan=old, blue=new; orange/green are changes, not truth labels",fontsize=11)
        fig.canvas.draw();renderer=fig.canvas.get_renderer();w,h=fig.canvas.get_width_height();outside=[]
        for t in fig.findobj(matplotlib.text.Text):
            if t.get_visible() and t.get_text():
                b=t.get_window_extent(renderer)
                if b.x0<-.5 or b.y0<-.5 or b.x1>w+.5 or b.y1>h+.5:outside.append(t.get_text())
        qa[stem]=dict(outside_canvas_text=outside)
        name=stem+("_preview" if a.preview else "")
        fig.savefig(a.output/(name+".png"),dpi=150 if a.preview else 300)
        guide=(f"# How to read {stem}\n\n## Data provenance\n\nE041R001savedarrays {a.result}; unchangedlockedStep19IMG_0379.JPG, nativeROI[3800,900,4800,3500]. "
               f"Crop{box} fixedbeforecandidate. Renderercommit {rec['commit']}, no extraction inplot.\n\n"
               "## Question and panels\n\nDoes one source-derived guide alignment recover left visible candidate structures? "
               "Fourcolumns original/oldcyanmask/newbluemask/differences orangeadded, greenremoved. Purpleunchangedexclusion. "
               "Same native support/scale, sourceunenhanced, no displaydilation/filling; guidesarecandidateinputs, not measuredpaths, andnotdrawn here.\n\n"
               f"## Numerical takeaway\n\nFullarea {summary['old_area_px2']}to{summary['new_area_px2']}px2; added{summary['added_px2']}, removed{summary['removed_px2']}. "
               f"Fixedleftcrop added{summary['left_crop_added_px2']}, removed{summary['left_crop_removed_px2']}. "
               f"Retains {summary['old_bottom_additions_retained_px2']}/{summary['old_bottom_added_px2']}oldE040bottomadditions.\n\n"
               "## Limitations\n\nOne already-exposed frame, AI/source-defined guide, no independentpixeltruth orphysicalwidth. "
               "Addedmaskmayinclude pores/texture, removedmaskmayinclude realcrack. Reportboth. No skeleton/path/thickness/forecast/scoring, "
               "no new source or threshold tuning. Oldv1/E038/E039/E040/halfdepth/scores unchanged.\n\n"
               "## Related assets\n\nREADME_analysis.md, R001summary/receipt, support_and_source.json, exactguideproposal andE041experiment.md. "
               "PDF/color/gray sharethisguide; graydisplayonly, use colour for change direction.\n")
        (a.output/(name+".md")).write_text(guide)
        if not a.preview:
            fig.savefig(a.output/(name+".pdf"))
            with Image.open(a.output/(name+".png")) as im:ImageOps.grayscale(im).save(a.output/(name+"_gray.png"),dpi=(300,300))
            (a.output/(name+"_gray.md")).write_text(guide)
        plt.close(fig)
    save(a.output/"visual_qa.json",qa)
    rec.update(execution="succeeded",ended_at_utc=now(),source_result=str(a.result));save(a.output/"render_receipt.json",rec)


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("phase",choices=("run","plot"));p.add_argument("--output",type=Path,required=True)
    for key in ("manifest","spec","plan","baseline","result"):p.add_argument("--"+key,type=Path)
    p.add_argument("--preview",action="store_true");a=p.parse_args();(run if a.phase=="run" else plot)(a)
