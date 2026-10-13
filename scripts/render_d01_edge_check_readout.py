#!/usr/bin/env python3
"""No refit: overlay recorded edge definitions on the blinded native strips."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--run",type=Path,required=True)
    args=p.parse_args(); key=json.loads((args.run/"private_blind_key.json").read_text())
    fig,axes=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
    fig.set_constrained_layout_pads(hspace=.12,wspace=.04)
    for col,beam in enumerate((4,5,6)):
        d=np.load(args.run/f"Beam{beam}_checks.npz")
        for row,j in enumerate((0,len(d["loads_kN"])-1)):
            task=next(k for k in key if k["beam"]==beam and k["stage_index"]==j and k["transect_id"]==6 and k["repeat_of_unique_index"] is None)
            with Image.open(args.run/"blind_packet"/(task["task_id"]+".png")) as im: image=np.array(im)
            ax=axes[row,col]; ax.imshow(image,cmap="gray",vmin=0,vmax=255,extent=(-60.5,60.5,24.5,-24.5),interpolation="nearest")
            for x in d["half_depth_edges"][j,5]: ax.plot([x,x],[-4,4],color="#56B4E9",lw=2.3)
            for x in d["gradient_edges"][j,5]:
                if np.isfinite(x): ax.plot([x,x],[-4,4],color="#D55E00",lw=1.5,ls="--")
            ax.set(title=f"Beam {beam} | {d['loads_kN'][j]:.0f} kN | fixed transect 6",xlabel="Normal offset (native reference px)",ylabel="Tangent offset (px)",xlim=(-40,40))
    fig.suptitle(f"{args.run.name} | source pixels rotated into transect coordinates; NO edge refit\nBlue=half-depth crossings, orange=gradient edges; algorithm agreement, NOT independent ground truth")
    target=args.run/"edge_on_image_comparison_v2.png"
    if target.exists(): raise FileExistsError("do not replace a previous readout")
    fig.savefig(target,dpi=170); plt.close(fig); print(target)


if __name__=="__main__": main()
