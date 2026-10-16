"""E033 historical source inspection only; no measurement or target access."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import os
import subprocess
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image, ImageOps

sys.path.insert(0, "/Users/wenxiaofang/.codex/skills/scipilot-figure-skill/scripts")
from visual_qa import audit_layout

SOURCE = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E033-MD01/raw_images")
FILES = ("IMG_0326.JPG", "IMG_0329.JPG")
CROP = (2500, 250, 4000, 3400)


def main(args):
    start = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({"font.size":10, "font.family":"DejaVu Sans", "pdf.fonttype":42,
                         "axes.spines.top":False, "axes.spines.right":False})
    fig, axes = plt.subplots(2, 2, figsize=(10, 11), constrained_layout=True,
                             gridspec_kw={"height_ratios":[1, 2.3]})
    for i, name in enumerate(FILES):
        with Image.open(SOURCE/name) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            if image.size != (6000, 4000):
                raise ValueError("Unexpected historical native dimensions")
            preview = image.copy()
            preview.thumbnail((1600, 1100))
            axes[0,i].imshow(preview, extent=(0,6000,4000,0))
            x0,y0,x1,y1 = CROP
            axes[0,i].add_patch(Rectangle((x0,y0), x1-x0, y1-y0,
                                         fill=False, color="#0072B2", lw=1.3))
            crop = image.crop(CROP)
            crop.save(args.output/f"step{i+2}_native_loading_crop.png")
            axes[1,i].imshow(crop, extent=(x0,x1,y1,y0))
        axes[0,i].set_title(f"Step {i+2} | {name}\nHistory only: same fixed camera", fontsize=10)
        axes[0,i].set_xticks([])
        axes[0,i].set_yticks([])
        axes[1,i].set_title("Same native loading-region crop", fontsize=10)
        axes[1,i].set_xlabel("Native source x (px)")
        axes[1,i].set_ylabel("Native source y (px)")
    fig.suptitle("S03-E033-MD01 | controlled-experiment development case\n"
                 "History inspection before profile choice; Step4 not acquired", fontsize=12)
    fig.supxlabel("Blue box: geometry-based inspection crop, NOT a sampling band. "
                  "Yellow wire / metal fixtures are external objects.", fontsize=9)
    qa = audit_layout(fig)
    fig.savefig(args.output/"F01_early_history_inspection.png", dpi=300)
    with Image.open(args.output/"F01_early_history_inspection.png") as im:
        ImageOps.grayscale(im).save(args.output/"F01_early_history_inspection_gray.png", dpi=(300,300))
    # Final vector export is a separate explicit call after the PNG visual check.
    if args.vector:
        fig.savefig(args.output/"F01_early_history_inspection.pdf")
    plt.close(fig)
    receipt = dict(execution="succeeded", retrieval="verified_local", render_only=True,
                   no_measurement=True, source_files=list(FILES), crop_native_xyxy=CROP,
                   target_accessed=False, command=sys.argv, host=socket.gethostname(), pid=os.getpid(),
                   commit=subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip(),
                   dirty=subprocess.check_output(["git","status","--porcelain"], text=True).splitlines(),
                   ended_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-start)
    for name, value in (("run_receipt.json",receipt),("layout_audit.json",qa)):
        with (args.output/name).open("x") as stream:
            json.dump(value,stream,indent=2)
            stream.write("\n")
    print(json.dumps(qa))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--vector",action="store_true")
    main(p.parse_args())
