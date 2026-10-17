"""E040 one-frame source-only exclusion repair; no skeleton/width/forecast calls."""
import argparse
import copy
import json
import time
from pathlib import Path

import cv2
import numpy as np

import md01_frame_geometry as v1
from md01_geometry_stability import ARCHIVE, receipt
from md01_early_relative import save, now

PROTOCOL = "step19-source-only-exclusion-repair-v1"
BASE = ARCHIVE / "S03-E038-MD01/runs/S03-E038-MD01-R001/step19/v1"


def raster(polygons, roi):
    out = np.zeros((roi[3]-roi[1],roi[2]-roi[0]),np.uint8)
    for p in polygons:
        cv2.fillPoly(out,[np.rint(np.array(p)-roi[:2]).astype(np.int32)],1)
    return out.astype(bool)


def guard(m):
    assert all(v1.sha(p)==h for p,h in m["protected_files"].items()), "Protected input changed"


def prepare(a):
    spec=json.loads(a.spec.read_text())
    assert spec["protocol"]==PROTOCOL and spec["stage"]==19
    source_manifest=ARCHIVE/"S03-E038-MD01/runs/S03-E038-MD01-R000/input_manifest.json"
    source_review=ARCHIVE/"S03-E038-MD01/runs/S03-E038-MD01-R004/independent_results.json"
    source=json.loads(source_manifest.read_text())
    f=next(f for f in source["frames"] if f["stage"]==19)
    assert f["filename"]=="IMG_0379.JPG" and spec["roi"]==source["roi"]
    assert v1.sha(f["source"])==f["sha256"] and Path(f["source"]).stat().st_size==f["bytes"]
    review=json.loads(source_review.read_text())
    assert v1.sha(BASE/"geometry_arrays.npz")==review["input_hashes_unchanged"][str(BASE/"geometry_arrays.npz")]
    supportpath=Path("docs/research/S03/S03-E037-MD01/frame_support_lock.json").resolve()
    old_support=json.loads(supportpath.read_text())["frames"]["19"]
    with np.load(BASE/"geometry_arrays.npz") as z:
        old_excluded=z["excluded"]
    assert np.array_equal(raster(old_support["exclude_polygons"],spec["roi"]),old_excluded)
    keep=raster(spec["keep_polygons_native"][:1],spec["roi"]).astype(np.uint8)
    radius=spec["left_keep_safety_buffer_px"]
    keep=cv2.dilate(keep,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1))).astype(bool)
    keep |= raster(spec["keep_polygons_native"][1:],spec["roi"])
    new_excluded=old_excluded & keep
    contours,hierarchy=cv2.findContours(new_excluded.astype(np.uint8),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    assert hierarchy is not None and np.all(hierarchy[0,:,3]==-1), "Hole requires explicit support review"
    new_support=copy.deepcopy(old_support)
    new_support["exclude_polygons"]=[(c[:,0,:]+spec["roi"][:2]).tolist() for c in contours]
    assert np.array_equal(raster(new_support["exclude_polygons"],spec["roi"]),new_excluded)
    assert not np.any(new_excluded & ~old_excluded)
    protected={str(p.resolve()):v1.sha(p) for p in [a.spec, a.protocol, Path(__file__),Path(v1.__file__),
        Path("scripts/d01_crack_profile_diagnostic.py"),supportpath,source_manifest,source_review,
        BASE/"geometry_arrays.npz",BASE/"paths.json",BASE/"metrics.json",Path(f["source"])]}
    m=dict(protocol=PROTOCOL,frame=f,spec=spec,old_support=old_support,new_support=new_support,
           baseline=str(BASE),protected_files=protected,no_score_contents_parsed=True)
    a.output.mkdir(parents=True,exist_ok=False)
    save(a.output/"input_manifest.json",m)
    np.savez_compressed(a.output/"support_arrays.npz",old_excluded=old_excluded,new_excluded=new_excluded,
                        released_support=old_excluded & ~new_excluded)
    r=receipt("E040_prepare_support_only")
    r.update(protocol=PROTOCOL,execution="succeeded",ended_at_utc=now(),no_crack_extraction=True)
    save(a.output/"run_receipt.json",r)
    print("Frozen one source-only support candidate; no crack extraction in prepare.")


def run(a):
    start,cpu=time.monotonic(),time.process_time()
    m=json.loads(a.manifest.read_text());assert m["protocol"]==PROTOCOL
    guard(m);a.output.mkdir(parents=True,exist_ok=False)
    rec=receipt("E040_single_frame_exclusion_comparison")
    rec.update(protocol=PROTOCOL,manifest_sha256=v1.sha(a.manifest),manifest_path=str(a.manifest.resolve()),execution="running")
    save(a.output/"run_start_receipt.json",rec)
    try:
        roi=m["spec"]["roi"];rgb=v1.read_frame(m["frame"],roi)
        with np.load(Path(m["baseline"])/"geometry_arrays.npz") as z:
            old={k:z[k].copy() for k in ("mask","excluded","safe")}
        mask,ex,safe=v1.extract(rgb,m["old_support"],roi)
        assert all(np.array_equal(x,old[k]) for x,k in ((mask,"mask"),(ex,"excluded"),(safe,"safe"))), "Old reconstruction mismatch"
        newmask,newex,_=v1.extract(rgb,m["new_support"],roi)
        assert np.array_equal(newex,raster(m["new_support"]["exclude_polygons"],roi))
        assert not np.any(newex & ~ex) and not np.any(mask & ~newmask)
        released=ex & ~newex;added=newmask & ~mask
        assert not np.any(newmask & newex)
        np.savez_compressed(a.output/"support_comparison_arrays.npz",old_mask=mask,new_mask=newmask,
             old_excluded=ex,new_excluded=newex,released_support=released,added_candidates=added,
             old_measurement_safe_unchanged=old["safe"])
        result=dict(stage=19,baseline_exact=True,old_candidate_area_px2=int(mask.sum()),new_candidate_area_px2=int(newmask.sum()),
             added_candidate_area_px2=int(added.sum()),old_candidate_pixels_lost=0,
             old_excluded_area_px2=int(ex.sum()),new_excluded_area_px2=int(newex.sum()),released_support_area_px2=int(released.sum()),
             added_in_released_support_px2=int((added & released).sum()),
             added_elsewhere_due_to_connectivity_px2=int((added & ~released).sum()),
             skeleton_path_thickness_forecast_recomputed=False,measurement_safe_not_replaced=True,
             no_accuracy_ground_truth=True,no_parameter_search=True)
        save(a.output/"summary.json",result)
        guard(m)
        if max(time.monotonic()-start,time.process_time()-cpu)>60:raise TimeoutError("60s cap")
        rec.update(execution="succeeded",retrieval="verified_local",protected_files_unchanged=len(m["protected_files"]))
    except Exception as e:
        rec.update(execution="failed",error=repr(e));raise
    finally:
        rec.update(ended_at_utc=now(),elapsed_wall_s=time.monotonic()-start,elapsed_cpu_s=time.process_time()-cpu)
        save(a.output/"run_receipt.json",rec)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("phase",choices=("prepare","run"))
    p.add_argument("--spec",type=Path);p.add_argument("--protocol",type=Path)
    p.add_argument("--manifest",type=Path);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();(prepare if a.phase=="prepare" else run)(a)
