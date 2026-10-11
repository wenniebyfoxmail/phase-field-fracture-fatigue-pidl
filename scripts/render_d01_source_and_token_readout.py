#!/usr/bin/env python3
"""Explain existing D01 outputs; no detection, registration fit or score rerun."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageOps

from d01_multiview_repeatability import load_gray, sha256, warp_image
from d01_observation_token_mvp import tokenize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("fresh readout directory required")
    args.output.mkdir(parents=True)
    token_root = args.archive/"S03-E010/runs/S03-E010-R001"
    raw_root = args.archive/"S03-E006/analysis/raw_images"
    datasets = []
    for beam in (4,5,6):
        with np.load(token_root/f"Beam{beam}_tokens.npz",allow_pickle=False) as f:
            datasets.append({k:f[k].copy() for k in f.files})
    vmax = max(float(d["tokens"][:,d["valid"],3].max()) for d in datasets)
    fig,axes = plt.subplots(3,4,figsize=(18,10),constrained_layout=True)
    displayed, checks = [], []
    mappable = None
    for row,(beam,data) in enumerate(zip((4,5,6),datasets)):
        metadata=json.loads(str(data["metadata_json"]))
        common=data["common_mask"]
        yy,xx=np.where(common)
        xedges=np.linspace(xx.min(),xx.max()+1,9).astype(int)
        yedges=np.linspace(yy.min(),yy.max()+1,9).astype(int)
        warped=[]
        for index in (0,1):
            record=metadata[index]
            source=raw_root/record["source_path"]
            if sha256(source) != record["source_sha256"]:
                raise ValueError(f"source identity mismatch: {source}")
            image,_,_=load_gray(source)
            aligned,_=warp_image(image,data["homographies"][index],common.shape)
            warped.append(aligned)
            token,valid,coverage,centers=tokenize(aligned,common)
            matched=(np.allclose(token,data["tokens"][index],atol=1e-8,rtol=1e-8)
                     and np.array_equal(valid,data["valid"])
                     and np.allclose(coverage,data["coverage"]) 
                     and np.allclose(centers/float(data["canonical_scale"]),data["centers_native_px"]))
            if not matched:
                raise ValueError(f"stored readout reproduction mismatch: {source}")
            checks.append({"source":str(source),"stored_transform_index":index,
                           "token_matches_archive":bool(matched)})
            displayed.append({"beam":f"Beam {beam}","view":record["view"],
                              "source_file":str(source),"nominal_stop_label_kN":10,
                              "exact_synchronization":False})
        with Image.open(raw_root/metadata[0]["source_path"]) as im:
            original=np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
        axes[row,0].imshow(original)
        axes[row,0].set_title(f"Beam {beam} | original fixed image\n{Path(metadata[0]['source_path']).name}",fontsize=10)
        axes[row,0].set(xlabel="Native x (px)",ylabel="Native y (px)")
        for col,index in ((1,0),(2,1)):
            ax=axes[row,col]
            ax.imshow(warped[index],cmap="gray",vmin=0,vmax=255)
            ax.contour(common.astype(float),levels=[.5],colors=["#56B4E9"],linewidths=.8)
            ax.set_title(("Fixed" if index==0 else "Moving")+" view in the same canonical region\n"+Path(metadata[index]['source_path']).name,fontsize=10)
        ax=axes[row,3]
        ax.imshow(warped[0],cmap="gray",vmin=0,vmax=255)
        values=np.ma.array(data["tokens"][0,:,3].reshape(8,8),mask=~data["valid"].reshape(8,8))
        ax.imshow(values,extent=(xedges[0],xedges[-1],yedges[-1],yedges[0]),
                  interpolation="nearest",cmap="magma",vmin=0,vmax=vmax,alpha=.68)
        mappable=matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(0,vmax),cmap="magma")
        for x in xedges: ax.axvline(x,color="white",alpha=.65,lw=.4)
        for y in yedges: ax.axhline(y,color="white",alpha=.65,lw=.4)
        for i,(x,y) in enumerate(data["centers_native_px"]*float(data["canonical_scale"])):
            if not data["valid"][i]:
                ax.plot(x,y,"x",color="#56B4E9",markersize=7)
        ax.set_title(f"Saved dark-ridge patch means\n{data['valid'].sum()}/64 valid cells; NOT crack labels",fontsize=10)
        for ax in axes[row,1:]:
            ax.set(xlim=(xx.min()-20,xx.max()+20),ylim=(yy.max()+20,yy.min()-20),
                   xlabel="Canonical working x (px)",ylabel="Canonical working y (px)")
    cbar=fig.colorbar(mappable,ax=list(axes[:,3]),fraction=.04,pad=.02)
    cbar.set_label("Mean normalized dark-ridge response\nShared scale across all beams/views")
    fig.suptitle("D01 / S03-E010-R001 | all 3 beams, first low-stop fixed + moving view | existing development outputs",fontsize=13)
    fig.supxlabel("Blue outline: shared image support. Grid: observation patches. Blue x: missing patch. Colours are image response, not a crack mask.",fontsize=11)
    fig.savefig(args.output/"source_to_token_readout.png",dpi=180)
    fig.savefig(args.output/"source_to_token_readout.pdf")
    plt.close(fig)
    inventory=[]
    locks=[("registration_and_tokens",args.archive/"S03-E006/analysis/selection_manifest.json",raw_root),
           ("ruler_detection",args.archive/"S03-E007/analysis/selection_manifest.json",args.archive/"S03-E007/raw_images"),
           ("moving_ruler_inventory",args.archive/"S03-E009/runs/S03-E009-R001/run_receipt.json",args.archive/"S03-E009/runs/S03-E009-R001/raw_images")]
    identities={}
    for use,lock,root in locks:
        for item in json.loads(lock.read_text())["files"]:
            path=root/item["saved_as"]
            if not path.is_file(): raise FileNotFoundError(path)
            with Image.open(path) as im: width,height=im.size
            prior=identities.get(item["sha256"],"")
            identities.setdefault(item["sha256"],str(path))
            inventory.append({"use":use,"beam":Path(item["saved_as"]).parts[0],
                              "kind":"reference" if "ref" in path.stem.lower() else "state_image",
                              "raw_file":str(path),"width_px":width,"height_px":height,
                              "bytes":path.stat().st_size,"same_source_as":prior})
    with (args.output/"data_used_inventory.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(inventory[0])); writer.writeheader(); writer.writerows(inventory)
    report={"rendered_at_utc":datetime.now(timezone.utc).isoformat(),
            "source_run":"S03-E010-R001","existing_scores_changed":False,
            "registration_refitted":False,"selection_rule":"all three beams; first low fixed/moving view in archived metadata",
            "stored_output_reproduction":checks,"displayed_originals":displayed,
            "physical_file_records":len(inventory),"unique_source_images":len(identities),
            "token_colour_limits":[0,vmax],"crack_annotations_present":False}
    (args.output/"readout_receipt.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"figure":str(args.output/"source_to_token_readout.png"),
                      "unique_source_images":len(identities),"reproduced_examples":len(checks),
                      "crack_annotations_present":False},indent=2))


if __name__=="__main__": main()
