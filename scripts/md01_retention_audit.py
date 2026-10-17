"""Explain saved-mask retention from cached eligible pixels, never emit a mask."""
import argparse
import json
import time
from pathlib import Path
import cv2
import numpy as np
import md01_frame_geometry as v1
from md01_geometry_stability import receipt
from md01_early_relative import save,now


def run(a):
    start,cpu=time.monotonic(),time.process_time()
    prior=json.loads((a.audit/"run_receipt.json").read_text())
    protected=dict(prior["protected_files"])
    for p in [a.audit/"decision_layers.npz",a.audit/"summary.json",a.audit/"run_receipt.json",a.plan,Path(__file__).resolve()]:
        protected[str(p.resolve())]=v1.sha(p)
    assert all(v1.sha(p)==h for p,h in protected.items())
    a.output.mkdir(parents=True,exist_ok=False)
    rec=receipt("E040_cached_component_retention_audit")
    rec.update(protocol="cached-retention-explanation-v1",execution="running",protected_files=protected)
    save(a.output/"run_start_receipt.json",rec)
    try:
        with np.load(a.audit/"decision_layers.npz") as z:
            eligible=z["pixel_gate_eligible"];distance=z["guide_distance"]
            saved=z["saved_mask"];released=z["released_support"]
        count,labels,stats,_=cv2.connectedComponentsWithStats(eligible.astype(np.uint8),connectivity=8)
        contact=set(np.unique(labels[eligible & (distance<=12)]).tolist())
        savedcounts=np.bincount(labels[saved],minlength=count)
        region=np.zeros(eligible.shape,bool);region[1700:2260,300:650]=True
        local=np.bincount(labels[region & released & eligible],minlength=count)
        ledger=[];groups=dict(no12pxcontact_only=0,height_below30_only=0,both=0,retained=0)
        for k in range(1,count):
            x,y,w,h,area=[int(v) for v in stats[k]]
            touches=k in contact;longenough=h>=30;keep=touches and longenough
            assert int(savedcounts[k])==(area if keep else 0), "Cached component does not explain saved result"
            if not local[k]:continue
            reason="retained" if keep else "both" if not touches and not longenough else "no12pxcontact_only" if not touches else "height_below30_only"
            groups[reason]+=int(local[k])
            ledger.append(dict(label=k,area_px=area,bbox_native_xywh=[x+3800,y+900,w,h],
                height_px=h,touches_original_guide_12px=touches,height_at_least30=longenough,
                saved_retained_pixels=int(savedcounts[k]),released_pixels_in_fixed_crop=int(local[k]),reason=reason))
        assert sum(groups.values())==1974 and groups["retained"]==0
        summary=dict(total_cached_components=count-1,all_component_saved_retention_matches=True,
                     fixed_crop_released_eligible_pixels=int(local[1:].sum()),
                     fixed_crop_pixel_counts_by_retention_reason=groups,
                     involved_components=ledger,no_new_mask=True,no_source_decode=True,
                     no_extractor_or_prediction=True,no_truth_or_accuracy_claim=True)
        save(a.output/"summary.json",summary)
        assert all(v1.sha(p)==h for p,h in protected.items())
        if max(time.monotonic()-start,time.process_time()-cpu)>30:raise TimeoutError("30s cap")
        rec.update(execution="succeeded",retrieval="verified_local",protected_files_unchanged=len(protected))
    except Exception as exc:
        rec.update(execution="failed",error=repr(exc));raise
    finally:
        rec.update(ended_at_utc=now(),elapsed_wall_s=time.monotonic()-start,elapsed_cpu_s=time.process_time()-cpu)
        save(a.output/"run_receipt.json",rec)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--audit",type=Path,required=True)
    p.add_argument("--plan",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    run(p.parse_args())
