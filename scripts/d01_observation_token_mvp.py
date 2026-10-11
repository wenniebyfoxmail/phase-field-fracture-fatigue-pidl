#!/usr/bin/env python3
"""Development C0 token serialization on the already-viewed S03-E006 IB set."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from d01_local_registration_holdout import SELECTION, evaluate_registration, transformed_corners
from d01_multiview_repeatability import load_gray, register, ridge_response, sha256, warp_image


def tokenize(image, common):
    yy, xx = np.where(common)
    if len(xx) == 0:
        raise ValueError("empty common support")
    xedges = np.linspace(xx.min(), xx.max()+1, 9).astype(int)
    yedges = np.linspace(yy.min(), yy.max()+1, 9).astype(int)
    gray = image.astype(np.float32) / 255
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.hypot(gx, gy)
    ridge = ridge_response(image)
    tokens, valid, coverage, centers = [], [], [], []
    for y1, y2 in zip(yedges[:-1], yedges[1:]):
        for x1, x2 in zip(xedges[:-1], xedges[1:]):
            mask = common[y1:y2, x1:x2]
            fraction = float(mask.mean()) if mask.size else 0
            good = fraction >= .5 and bool(mask.any())
            vals = gray[y1:y2,x1:x2][mask]
            tokens.append([float(vals.mean()), float(vals.std()),
                           float(gradient[y1:y2,x1:x2][mask].mean()),
                           float(ridge[y1:y2,x1:x2][mask].mean())] if good else [0.,0.,0.,0.])
            valid.append(good)
            coverage.append(fraction)
            centers.append([(x1+x2)/2,(y1+y2)/2])
    return np.array(tokens), np.array(valid), np.array(coverage), np.array(centers)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    git = lambda *a: subprocess.check_output(["git", *a], cwd=repo, text=True).strip()
    if git("status", "--porcelain"):
        raise RuntimeError("commit source before development execution")
    if args.output.exists():
        raise FileExistsError("fresh output required")
    args.output.mkdir(parents=True)
    receipt = {"experiment_id":"S03-E010", "run_id":"S03-E010-R001",
               "protocol":"development-v1", "role":"C0_development_only",
               "producer":"Mac-PIDL", "hostname":socket.gethostname(), "pid":os.getpid(),
               "commit":git("rev-parse","HEAD"), "git_dirty":False,
               "python":sys.executable, "command":sys.argv, "gpu":None,
               "started_at_utc":datetime.now(timezone.utc).isoformat(),
               "execution":"running", "retrieval":"pending"}
    def save_receipt():
        (args.output/"run_receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    save_receipt()
    manifest = json.loads((args.source/"selection_manifest.json").read_text())
    sources = {r["saved_as"]:r for r in manifest["files"]}
    def load(relative):
        path = args.source/"raw_images"/relative
        if sha256(path) != sources[relative]["sha256"]:
            raise ValueError(f"identity mismatch: {relative}")
        return load_gray(path)
    rows, overview, summaries = [], [], []
    loads = {"Beam 4":(10,50),"Beam 5":(10,60),"Beam 6":(10,40)}
    for beam,spec in SELECTION.items():
        ref,scale,_ = load(spec["reference"])
        images,masks,metadata,transforms = [],[],[],[]
        for stop in ("low","high"):
            paths = [spec[f"{stop}_fixed"],*spec[f"{stop}_moving"]]
            for index,relative in enumerate(paths):
                image,_,_ = load(relative)
                reg = register(image,ref,scale)
                corners = transformed_corners(image.shape,reg.homography) if reg.homography is not None else None
                valid,reason = evaluate_registration(reg,"fixed" if index==0 else "moving",corners)
                if not valid:
                    raise ValueError(f"registration admission failed: {relative}: {reason}")
                warped,mask = warp_image(image,reg.homography,ref.shape)
                images.append(warped); masks.append(mask); transforms.append(reg.homography)
                metadata.append({"beam":beam,"stop":stop,"view":"fixed" if index==0 else f"moving{index}",
                                 "source_path":relative,"source_sha256":sources[relative]["sha256"],
                                 "nominal_stop_label_kN":loads[beam][stop=="high"],
                                 "exact_frame_load_known":False})
        common = cv2.erode(np.logical_and.reduce(masks).astype(np.uint8),np.ones((41,41),np.uint8)).astype(bool)
        tokens=[]
        for image in images:
            token,valid,coverage,centers = tokenize(image,common)
            tokens.append(token)
        tokens=np.stack(tokens)
        if not valid.any() or not np.isfinite(tokens).all():
            raise ValueError(f"nonempty finite token condition failed: {beam}")
        path=args.output/(beam.replace(" ","")+"_tokens.npz")
        np.savez_compressed(path,tokens=tokens,valid=valid,coverage=coverage,
                            centers_native_px=centers/scale,homographies=np.stack(transforms),
                            common_mask=common,canonical_scale=scale,
                            metadata_json=np.array(json.dumps(metadata)),
                            feature_names=np.array(["gray_mean","gray_sd","gradient_mean","dark_ridge_mean"]))
        with np.load(path,allow_pickle=False) as check:
            if not np.array_equal(tokens,check["tokens"]) or json.loads(str(check["metadata_json"])) != metadata:
                raise ValueError("serialization roundtrip failed")
        for start,stop in ((0,"low"),(4,"high")):
            for j in range(start+1,start+4):
                values=np.abs(tokens[j,valid]-tokens[start,valid]).mean(axis=0)
                rows.append({"beam":beam,"comparison":"moving_vs_fixed_same_stop","stop":stop,
                             "source_path":metadata[j]["source_path"],"valid_patches":int(valid.sum()),
                             **dict(zip(["gray_mean_MAD","gray_sd_MAD","gradient_mean_MAD","ridge_mean_MAD"],values))})
        values=np.abs(tokens[4,valid]-tokens[0,valid]).mean(axis=0)
        rows.append({"beam":beam,"comparison":"fixed_high_vs_low","stop":"cross_stop",
                     "source_path":metadata[4]["source_path"],"valid_patches":int(valid.sum()),
                     **dict(zip(["gray_mean_MAD","gray_sd_MAD","gradient_mean_MAD","ridge_mean_MAD"],values))})
        summaries.append({"beam":beam,"observations":8,"valid_patches_per_image":int(valid.sum()),
                          "all_patches":64,"token_shape":list(tokens.shape),"roundtrip_ok":True})
        overview.append((beam,ref,common,centers,tokens,valid,scale))
    with (args.output/"descriptor_differences.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    fig,axes=plt.subplots(3,2,figsize=(12,10))
    for i,(beam,ref,common,centers,tokens,valid,scale) in enumerate(overview):
        yy,xx=np.where(common); x1,x2=xx.min(),xx.max(); y1,y2=yy.min(),yy.max()
        axes[i,0].imshow(ref,cmap="gray",vmin=0,vmax=255)
        axes[i,0].scatter(centers[valid,0],centers[valid,1],s=10,color="#E69F00")
        axes[i,0].set(xlim=(x1-20,x2+20),ylim=(y2+20,y1-20),xlabel="Canonical working x (px)",ylabel="Canonical working y (px)",title=f"{beam}: {valid.sum()}/64 valid patch tokens")
        matched=[r for r in rows if r["beam"]==beam]
        axes[i,1].plot(range(6),[r["ridge_mean_MAD"] for r in matched[:6]],"o",color="#0072B2",label="moving vs fixed, same stop")
        axes[i,1].axhline(matched[6]["ridge_mean_MAD"],color="#D55E00",ls="--",label="fixed high vs low")
        axes[i,1].set(xticks=range(6),xticklabels=["L1","L2","L3","H1","H2","H3"],ylabel="Mean absolute ridge-token difference",title=f"{beam}: descriptive comparison; no accuracy gate")
        axes[i,1].legend(fontsize=8)
    limit=max(r["ridge_mean_MAD"] for r in rows)*1.2
    for ax in axes[:,1]: ax.set_ylim(0,limit)
    fig.suptitle("S03-E010-R001 | three beams, all 24 viewed observations | C0 development only")
    fig.tight_layout(); fig.savefig(args.output/"token_overview.png",dpi=160); plt.close(fig)
    summary={"serialized_observations":24,"beams":summaries,"feature_count":4,
             "all_roundtrip_ok":True,"scientific_verdict":"DEVELOPMENT_ONLY",
             "physical_scale":"canonical_pixels_only","crack_accuracy_validated":False,
             "prediction_tested":False}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    receipt.update(execution="succeeded",retrieval="verified_local",ended_at_utc=datetime.now(timezone.utc).isoformat())
    save_receipt(); print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
