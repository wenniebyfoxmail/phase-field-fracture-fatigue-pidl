#!/usr/bin/env python3
"""Algorithm-free pixel-coordinate sheets, no private-key or result access."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

GUIDE="""# Anonymous visual-only boundary annotation
Only read this folder's guide, task list, raw anonymous PNGs and readout PNGs.
No parent directory, repository, memory, previous results, keys or websites.
Do not invoke detectors, grayscale/profile calculations, hashes, duplicate
searches or image generation. Inspect EVERY task visually, independently.
Annotate apparent left/right dark-crack boundaries on CENTRAL ROW y=24.
Raw crop 121x49, strip x pixel centers 0..120. Arrows identify row, NOT edges.
Readouts use nearest-neighbor fixed grayscale; report strip coordinates,
not enlarged display coordinates, using 0.5/1 pixel granularity.
Return exactly one row per task_001..task_030, columns:
task_id,left_px,right_px,left_min_px,left_max_px,right_min_px,right_max_px,quality,confidence,notes
quality = visible / uncertain / occluded. Confidence high/medium/low is
subjective, not a calibrated probability. Plausible ranges contain estimates.
Keep branches/spall/shadow/occlusion or unclear boundaries uncertain; don't
force valid endpoints. Uncertain/occluded numeric entries may be blank.
No inference of hidden specimen, chronology or loading. Do not use another
task's answer as a shortcut. Write output CSV and exposure note via apply_patch
to the exact supplied output paths. Exposure note: agent identity, all inputs
actually read, any prior/algorithm exposure, possible recognition/memory, AI
visual coordinate limitations. No accuracy/research claim. No other agents.
"""

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--public-packet",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(); repo=Path(__file__).resolve().parents[1]
    git=lambda *a:subprocess.check_output(["git",*a],cwd=repo,text=True).strip()
    if git("status","--porcelain"): raise RuntimeError("commit before preparation")
    if args.output.exists(): raise FileExistsError("fresh output required")
    files=sorted(args.public_packet.glob("task_*.png"))
    if [f.stem for f in files]!=[f"task_{i:03d}" for i in range(1,31)]: raise ValueError("task identity mismatch")
    args.output.mkdir(parents=True); data=args.output/"blind_input"; data.mkdir()
    for file in files:
        with Image.open(file) as im: array=np.array(im)
        if array.shape!=(49,121): raise ValueError("crop geometry mismatch")
        shutil.copy2(file,data/file.name)
        fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
        ax.imshow(array,cmap="gray",vmin=0,vmax=255,extent=(-.5,120.5,48.5,-.5),interpolation="nearest")
        for edge,outer in ((-.5,-4),(120.5,124)):
            ax.annotate("",xy=(edge,24),xytext=(outer,24),arrowprops={"arrowstyle":"->","color":"#0072B2"})
        ax.set(xlim=(-4,124),ylim=(48.5,-.5),xticks=np.arange(0,121,5),yticks=[0,12,24,36,48],
               xlabel="Strip pixel-center x (reference pixels; NOT enlarged display)",ylabel="Row y",title=f"{file.stem} | annotate row y=24 | anonymous")
        ax.tick_params(axis="x",labelsize=8); fig.savefig(data/(file.stem+"_readout.png"),dpi=120); plt.close(fig)
    (data/"annotation_guide.md").write_text(GUIDE)
    (data/"task_ids.json").write_text(json.dumps([f.stem for f in files],indent=2)+"\n")
    receipt={"experiment_id":"S03-E017-D01","run_id":"S03-E017-D01-R000","protocol":"ai-visual-development-v1",
             "role":"algorithm_free_input_preparation","producer":"Mac-PIDL CPU","hostname":socket.gethostname(),
             "pid":os.getpid(),"commit":git("rev-parse","HEAD"),"git_dirty":False,"command":sys.argv,
             "source":"E016 public anonymous PNG crops only","tasks":30,"source_geometry":[49,121],
             "private_key_read":False,"candidate_boundaries_included":False,"execution":"succeeded",
             "retrieval":"verified_local","completed_at_utc":datetime.now(timezone.utc).isoformat()}
    (args.output/"run_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n"); print(data)

if __name__=="__main__": main()
