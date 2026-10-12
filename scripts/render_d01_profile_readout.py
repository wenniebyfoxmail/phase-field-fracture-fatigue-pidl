#!/usr/bin/env python3
"""Render stored E015-D01 half-depth crossings on original first/last images."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from d01_crack_profile_diagnostic import native_gray, native_homography


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--lock",type=Path,required=True)
    args=parser.parse_args()
    lock=json.loads(args.lock.read_text()); source=Path(lock["source_run"])
    groups=json.loads((source/"selected_sequences_before_pixel_access.json").read_text())["groups"]
    rows=list(csv.DictReader((args.run/"profile_measurements.csv").open()))
    output=args.run/"first_last_width_readout.png"
    if output.exists(): raise FileExistsError("do not replace previous readout")
    fig,axes=plt.subplots(3,2,figsize=(11,13),constrained_layout=True)
    for row,beam in enumerate((4,5,6)):
        geo=lock["beams"][str(beam)]; states=groups[str(beam)]
        old=np.load(source/f"Beam{beam}_stage_fields.npz")
        for col,j in enumerate((0,len(states)-1)):
            image=native_gray(source/"raw_images"/states[j]["saved_as"])
            h=native_homography(old["homographies"][j],image.shape,geo["working_shape"])
            inverse=np.linalg.inv(h); positions=[]; measured=[]
            ax=axes[row,col]; ax.imshow(image,cmap="gray",vmin=0,vmax=255)
            for t in geo["transects"]:
                record=next(r for r in rows if int(r["beam"])==beam and int(r["stage_index"])==j
                            and int(r["transect_id"])==t["id"] and r["role"]=="crack")
                center=np.array(t["center"]); normal=np.array(t["normal"])
                if record["valid"]!="True": continue
                left=float(record["left_crossing_px"]); right=float(record["right_crossing_px"])
                pts=np.stack([center+left*normal,center+right*normal])
                hp=np.column_stack([pts,np.ones(2)])@inverse.T
                xy=hp[:,:2]/hp[:,2:]; positions.extend(xy.tolist())
                ax.plot(*xy.T,color="#56B4E9",lw=1.5,marker="|",markersize=5)
                label=np.column_stack([(center+75*normal)[None,:],np.ones(1)])@inverse.T
                label=label[0,:2]/label[0,2]
                ax.text(*label,str(t["id"]),color="#56B4E9",fontsize=8)
                measured.append(float(record["fwhm_native_px"]))
            xy=np.array(positions)
            ax.set_xlim(xy[:,0].min()-130,xy[:,0].max()+130)
            ax.set_ylim(xy[:,1].max()+100,xy[:,1].min()-100)
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f"Beam {beam} | {states[j]['nominal_load_kN']} kN | t={states[j]['filename_time_s']} filename\n"
                         f"median stored half-depth width = {np.median(measured):.2f} native px",fontsize=10)
    fig.suptitle("S03-E015-D01-R001 | stored measured crossings, NOT manually labelled edges\n"
                 "First and last included stage of every beam; source-native crops; no measurement refit",fontsize=12)
    fig.savefig(output,dpi=170); plt.close(fig)
    print(output)


if __name__=="__main__": main()
