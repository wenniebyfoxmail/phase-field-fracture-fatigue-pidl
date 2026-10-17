"""Exact existing-source inspection only; no geometry measurements."""
import argparse,json,subprocess,sys,os,socket,time,hashlib
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image,ImageOps
from md01_early_relative import save,now

p=argparse.ArgumentParser();p.add_argument("--lock",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
start=time.monotonic();started=now();lock=json.loads(a.lock.read_text());a.output.mkdir(parents=True,exist_ok=False)
fig,axes=plt.subplots(1,5,figsize=(12,9),constrained_layout=True)
for ax,f in zip(axes,[f for f in lock["frames"] if f["stage"]>=18],strict=True):
    path=Path(f["source"])
    if path.stat().st_size!=f["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest()!=f["sha256"]:raise ValueError("Source identity mismatch")
    with Image.open(path) as raw:im=ImageOps.exif_transpose(raw).convert("RGB").crop(lock["roi_xyxy"])
    ax.imshow(im,extent=[3800-.5,4800-.5,3500-.5,900-.5]);ax.set_title(f"Step{f['stage']}",fontsize=10);ax.set_xticks([4000,4400,4800]);ax.tick_params(labelsize=8)
    ax.axhspan(1700,1950,facecolor="none",edgecolor="#56B4E9",lw=1)
fig.suptitle("E037 R000 | existing per-frame visible support inspection | no mask / metric / prediction\nNative image crop; blue band=proposed fixed image-space comparison, not material tracking",fontsize=11)
fig.savefig(a.output/"source_support_inspection.png",dpi=150);plt.close(fig)
(a.output/"source_support_inspection.md").write_text("# How to read source_support_inspection\n\n## Data provenance\n\nE037 source_lock.json; existing E036 Steps18/19/21/22/23 raw photos; scripts/inspect_md01_geometry.py. No numerical geometry or forecasts computed.\n\n## Visual grammar\n\nFive fixed native [3800,900,4800,3500] crops, pixel XY axes. Blue band is native y1700..1950 and not a material-point mapping. Source colour only, no enhancement. Used solely to freeze per-frame coarse trace guidance and fixture/glue/uncertainty exclusions before new metrics.\n\n## Limitations\n\nObserver-assisted source inspection is not independent crack groundtruth, not a mask or old half-depth band. Do not infer hidden cracks behind board/glue, pixel geometry is not physical aperture. Different visible support cannot be interpreted as growth or shrinkage without an additional task definition. Existing target is already exposed; not new blind testing.\n")
save(a.output/"run_receipt.json",dict(execution="succeeded",retrieval="verified_local",inspection_only=True,started_at_utc=started,ended_at_utc=now(),wall_seconds=time.monotonic()-start,commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),dirty=subprocess.check_output(["git","status","--porcelain"],text=True).splitlines(),host=socket.gethostname(),pid=os.getpid(),command=sys.argv))
