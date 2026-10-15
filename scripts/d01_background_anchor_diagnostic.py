#!/usr/bin/env python3
"""Frozen Beam4 background translation; no crack width enters its fit."""
import argparse
import csv
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import zlib

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from PIL import Image, ImageOps

from independent_d01_halfdepth import (native_to_source, median_source_profile,
                                     sampling_grid, bilinear, measure, VARIANTS)

ANCHORS = [(role, n, t) for role, ts in (("fit", (-24, 24)), ("check", (-72, 72)))
           for n in (-100, 100) for t in ts]
HALF = 15
SEARCH = 8
UNSAFE_FIRST_FRAME = {(1,5)}  # Origin-only visual screen: CHECK patch touches curved crack.


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def load_inputs(inputs):
    g = json.loads((inputs / "geometry.json").read_text())["beams"]["4"]
    with np.load(inputs / "Beam4_inputs.npz", allow_pickle=False) as z:
        h, s, loads = (z[k].copy() for k in ("homographies", "normal_offsets_native_px", "loads_kN"))
    if ([t["id"] for t in g["transects"]] != list(range(1, 13)) or loads.tolist() != [10, 30, 40, 50]
            or len(g["stages"]) != 4 or h.shape != (4,3,3) or not np.isfinite(h).all()
            or not np.array_equal(s,np.arange(-60,60.25,.25)) or g["native_shape"] != [3744,5616]
            or g["working_shape"] != [1333,2000]):
        raise ValueError("frozen Beam4 identity mismatch")
    for j,stage in enumerate(g["stages"]):
        if stage["beam"] != 4 or stage["nominal_load_kN"] != loads[j]:
            raise ValueError("stage/load/beam mismatch")
    for tr in g["transects"]:
        c,n=np.asarray(tr["center"],float),np.asarray(tr["normal"],float)
        if c.shape!=(2,) or n.shape!=(2,) or not np.isfinite([c,n]).all() or abs(np.linalg.norm(n)-1)>1e-8:
            raise ValueError("invalid frozen transect")
    return g, h, s, loads


def load_gray(stage):
    p = Path(stage["source_image"])
    raw = p.read_bytes()
    if len(raw) != stage["bytes"] or f"{zlib.crc32(raw) & 0xffffffff:08x}" != stage["crc32"]:
        raise ValueError("source size/CRC identity changed")
    with Image.open(p) as im:
        gray=np.asarray(ImageOps.exif_transpose(im).convert("L"), dtype=np.float32)
    if gray.shape != (3744,5616): raise ValueError("native decode shape changed")
    return gray


def prepared_binding(inputs,prepared):
    """One digest for this externally sourced input/template snapshot; Git owns code."""
    digest=hashlib.sha256()
    for p in (inputs/"geometry.json", inputs/"Beam4_inputs.npz", prepared/"templates.npz", prepared/"anchor_manifest.csv"):
        b=p.read_bytes()
        digest.update(p.name.encode()+b"\0"+str(len(b)).encode()+b"\0"+b)
    return digest.hexdigest()


def local_grid(transect, ncenter, tcenter, radius):
    n = np.asarray(transect["normal"], float)
    t = np.array([-n[1], n[0]])
    v = np.arange(-radius, radius+1)
    nn, tt = np.meshgrid(v+ncenter, v+tcenter)
    return np.asarray(transect["center"], float) + nn[..., None]*n + tt[..., None]*t


def source_sample(image, points, H, geometry):
    q = native_to_source(points, np.linalg.inv(H), geometry["native_shape"], geometry["working_shape"])
    return bilinear(image, q)


def match_patch(template, search):
    if template.shape != (31,31) or search.shape != (47,47):
        raise ValueError("frozen template/search shape mismatch")
    std = float(np.std(template, dtype=np.float64))
    result = dict(available=False, reason="weak_template", template_std=std,
                  shift_n=np.nan, shift_t=np.nan, ncc_peak=np.nan, peak_separation=np.nan)
    if not np.isfinite(template).all() or not np.isfinite(search).all():
        raise ValueError("nonfinite patch")
    if std <= 1.0:
        return result
    scores = cv2.matchTemplate(np.ascontiguousarray(search, np.float32),
                               np.ascontiguousarray(template, np.float32), cv2.TM_CCOEFF_NORMED)
    if not np.isfinite(scores).all():
        result["reason"] = "nonfinite_ncc"
        return result
    row, col = np.unravel_index(np.argmax(scores), scores.shape)
    peak = float(scores[row,col])
    other = scores.copy()
    other[max(0,row-1):row+2, max(0,col-1):col+2] = -np.inf
    result.update(ncc_peak=peak, peak_separation=peak-float(np.max(other)))
    if row in (0, scores.shape[0]-1) or col in (0, scores.shape[1]-1):
        result["reason"] = "search_boundary"
        return result
    def refine(a, b, c):
        denominator = a-2*b+c
        return float(np.clip(.5*(a-c)/denominator, -.5, .5)) if denominator < -1e-12 else 0.
    dn = col-SEARCH+refine(float(scores[row,col-1]),peak,float(scores[row,col+1]))
    dt = row-SEARCH+refine(float(scores[row-1,col]),peak,float(scores[row+1,col]))
    result.update(available=True, reason="available_proxy", shift_n=float(dn), shift_t=float(dt))
    return result


def fit_translation(anchor_results):
    fit = [r for r in anchor_results if r["role"] == "fit"]
    if len(fit) != 4:
        raise ValueError("must fit only four FIT observations")
    if not all(r["available"] for r in fit):
        return None
    return np.median([[r["shift_n"],r["shift_t"]] for r in fit], axis=0)


def origin_prepare(inputs, output):
    output.mkdir(parents=True, exist_ok=False)
    g, h, s, loads = load_inputs(inputs)
    im = load_gray(g["stages"][0])
    templates, anchors = {}, []
    fig, ax = plt.subplots(figsize=(7, 11))
    ax.imshow(im, cmap="gray", vmin=0, vmax=255)
    fig2, axes = plt.subplots(12,8,figsize=(12,17))
    corners = []
    for row, tr in enumerate(g["transects"]):
        for j, (role,n,t) in enumerate(ANCHORS):
            grid = local_grid(tr,n,t,HALF)
            patch = source_sample(im,grid,h[0],g)
            name = f"t{tr['id']}_a{j}"
            templates[name] = patch
            mapped=native_to_source(grid,np.linalg.inv(h[0]),g["native_shape"],g["working_shape"])
            poly = mapped[[0,0,-1,-1],[0,-1,-1,0]]
            envelope=local_grid(tr,n,t,HALF+SEARCH)
            source_sample(im,envelope,h[0],g)  # Verify actual47x47 search support at preparation.
            mapped_envelope=native_to_source(envelope,np.linalg.inv(h[0]),g["native_shape"],g["working_shape"])
            outer=mapped_envelope[[0,0,-1,-1],[0,-1,-1,0]]
            corners.extend(outer.tolist())
            eligible=(tr["id"],j) not in UNSAFE_FIRST_FRAME
            color=("#0072B2" if role=="fit" else "#D55E00") if eligible else "#CC0000"
            ax.add_patch(Polygon(poly,fill=False,edgecolor=color,lw=.7))
            ax.add_patch(Polygon(outer,fill=False,edgecolor=color,lw=.5,linestyle="--",alpha=.7))
            anchors.append(dict(transect_id=tr["id"],anchor_id=j,role=role,offset_n=n,offset_t=t,
                                template_std=float(np.std(patch,dtype=np.float64)),eligible_first_frame=eligible,
                                exclusion_reason="" if eligible else "origin_patch_intersects_crack"))
            axes[row,j].imshow(patch,cmap="gray",vmin=0,vmax=255)
            axes[row,j].set(xticks=[],yticks=[],title=f"{role[0].upper()} {n},{t}" if row==0 else "")
            if j==0: axes[row,j].set_ylabel(f"T{tr['id']}",rotation=0,labelpad=13)
        point=native_to_source(np.array(tr["center"]),np.linalg.inv(h[0]),g["native_shape"],g["working_shape"])
        ax.text(*point,str(tr["id"]),color="#009E73",fontsize=8)
    corners=np.array(corners)
    ax.set(xlim=(corners[:,0].min()-30,corners[:,0].max()+30),
           ylim=(corners[:,1].max()+30,corners[:,1].min()-30),xlabel="Origin native x (px)",ylabel="Origin native y (px)",
           title="Beam4 first-frame anchors | 10 kN\nBlue FIT / orange CHECK / red unavailable; all12 transects")
    fig.tight_layout()
    fig2.suptitle("First frame only | all96 fixed background templates\n31x31 px, shared gray scale0..255; columns FIT4 then CHECK4")
    fig2.tight_layout(rect=[0,0,1,.96])
    for stem,f in (("first_frame_anchor_layout",fig),("first_frame_anchor_templates",fig2)):
        f.savefig(output/f"{stem}.png",dpi=160)
        plt.close(f)
        (output/f"{stem}.md").write_text(f"""# How to read {stem}
## Figure question
Are the predeclared local anchors on background rather than the crack, ruler or specimen border?
## Data provenance
Only Beam4 first fixed image, 10 kN: `{g['stages'][0]['source_image']}`. Frozen E018 safe geometry, all12 transects. Script `scripts/d01_background_anchor_diagnostic.py --mode prepare`. No later-stage matching or width values.
## Visual grammar and panel guide
Layout: native source pixels; solid31x31 templates and dashed47x47 search envelopes; blue FIT, orange CHECK, green transect IDs. All polygons mapped through actual H0. Templates: 12 rows of transects, eight fixed anchor columns (FIT4 then CHECK4), each31x31, shared gray0..255. No smoothing, intensity normalisation or outcome-based selection.
## Key numerical takeaway
96 predetermined patches; fixed origin-screen exclusions are red, retained in `anchor_manifest.csv` rather than moved. Fixed offsets normal+/-100, tangent+/-24(FIT)/+/-72(CHECK). Source scale is native pixels, not mm.
## Limitations and claim boundary
This first-frame capability view is not true material correspondence or registration accuracy; later-stage fits still require separate review. Cracks/voids visible elsewhere do not become labels or physical landmarks. Different transects are spatially dependent. Do not silently move a conflicting patch after target access.
""")
    np.savez_compressed(output/"templates.npz",**templates)
    write_csv(output/"anchor_manifest.csv",anchors)
    (output/"preparation.json").write_text(json.dumps(dict(stage=0,load_kN=10,templates=96,inputs=str(inputs),source=g["stages"][0],
                                                           binding_sha256=prepared_binding(inputs,output),
                                                           code_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                                                           git_status=subprocess.check_output(["git","status","--short"],text=True)),indent=2)+"\n")


def diagnostic(inputs, prepared, output, budget=120):
    if not 0 < budget <= 120:
        raise ValueError("budget must be in (0,120]")
    output.mkdir(parents=True, exist_ok=False)
    start, cpu = time.monotonic(), time.process_time()
    receipt = dict(started_utc=datetime.now(timezone.utc).isoformat(),hostname=socket.gethostname(),pid=os.getpid(),
                   code_commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                   git_status=subprocess.check_output(["git","status","--short"],text=True),
                   budget_seconds=budget,execution="running",inputs=str(inputs),prepared=str(prepared),
                   thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")})
    anchor_rows, shifts, widths, examples = [], [], [], {}
    def check():
        if time.monotonic()-start >= budget or time.process_time()-cpu >= budget:
            raise TimeoutError("CPU/wall budget")
    try:
        g,h,s,loads=load_inputs(inputs)
        prep=json.loads((prepared/"preparation.json").read_text())
        receipt["prepared_binding_sha256"]=prepared_binding(inputs,prepared)
        if receipt["prepared_binding_sha256"] != prep["binding_sha256"]:
            raise ValueError("input/template snapshot mismatch")
        with np.load(prepared/"templates.npz",allow_pickle=False) as z:
            templates={k:z[k] for k in z.files}
        if set(templates)!={f"t{i}_a{j}" for i in range(1,13) for j in range(8)} or any(v.shape!=(31,31) or not np.isfinite(v).all() for v in templates.values()):
            raise ValueError("prepared template schema mismatch")
        for stage_index,stage in enumerate(g["stages"]):
            check()
            image=load_gray(stage)
            for tr in g["transects"]:
                check()
                identity=dict(stage_index=stage_index,load_kN=float(loads[stage_index]),transect_id=tr["id"])
                matched=[]
                if stage_index:
                    for j,(role,n,t) in enumerate(ANCHORS):
                        check()
                        if (tr["id"],j) in UNSAFE_FIRST_FRAME:
                            result=dict(available=False,reason="unsafe_first_frame",template_std=float(np.std(templates[f"t{tr['id']}_a{j}"],dtype=np.float64)),
                                        shift_n=np.nan,shift_t=np.nan,ncc_peak=np.nan,peak_separation=np.nan)
                        else:
                            search=source_sample(image,local_grid(tr,n,t,HALF+SEARCH),h[stage_index],g)
                            result=match_patch(templates[f"t{tr['id']}_a{j}"],search)
                        matched.append(dict(identity,anchor_id=j,role=role,offset_n=n,offset_t=t,**result))
                    correction=fit_translation(matched)
                    for r in matched:
                        paired=r["available"] and correction is not None
                        original=float(np.linalg.norm([r["shift_n"],r["shift_t"]])) if r["available"] else np.nan
                        adjusted=float(np.linalg.norm(np.array([r["shift_n"],r["shift_t"]])-correction)) if paired else np.nan
                        anchor_rows.append(dict(r,correction_available=correction is not None,
                                                before_residual_px=original,after_residual_px=adjusted))
                else:
                    correction=np.zeros(2)
                shifts.append(dict(identity,available=correction is not None,
                                   shift_n=float(correction[0]) if correction is not None else np.nan,
                                   shift_t=float(correction[1]) if correction is not None else np.nan))
                nvec=np.asarray(tr["normal"],float)
                tvec=np.array([-nvec[1],nvec[0]])
                for arm in ("original_H","background_aligned"):
                    available=arm=="original_H" or correction is not None
                    delta=np.zeros(2) if arm=="original_H" else (correction[0]*nvec+correction[1]*tvec if available else None)
                    for variant in VARIANTS:
                        check()
                        if available:
                            points=sampling_grid(tr["center"],tr["normal"],s,variant)+delta
                            source=native_to_source(points,np.linalg.inv(h[stage_index]),g["native_shape"],g["working_shape"])
                            profile=median_source_profile(image,source)
                            result=measure(s,profile)
                        else:
                            result=dict(width_px=np.nan,valid=False,reason="unavailable_correction")
                        widths.append(dict(identity,arm=arm,variant=variant,width_px=result["width_px"],valid=result["valid"],reason=result["reason"]))
                        if tr["id"]==6 and variant=="baseline" and available:
                            key=f"st{stage_index}_{arm}"
                            strip=local_grid(tr,0,0,60) + delta
                            # Local display extent +/-60 along both normal and tangent.
                            examples[key+"_strip"]=source_sample(image,strip,h[stage_index],g)
                            examples[key+"_profile"]=profile
                            examples[key+"_deficit"]=result["deficit"]
                            examples[key+"_crossings"]=np.array([result["left_px"],result["right_px"],result["width_px"]])
        check()
        receipt["execution"]="succeeded"
    except Exception as exc:
        receipt.update(execution="stopped",error=repr(exc))
        raise
    finally:
        write_csv(output/"anchor_matches.csv",anchor_rows)
        write_csv(output/"translations.csv",shifts)
        write_csv(output/"width_variants.csv",widths)
        if examples: np.savez_compressed(output/"examples.npz",**examples)
        receipt.update(ended_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       anchor_rows=len(anchor_rows),translation_rows=len(shifts),width_rows=len(widths))
        if receipt["wall_seconds"]>=budget or receipt["cpu_seconds"]>=budget:
            receipt["execution"]="budget_stopped"
        (output/"runtime_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        if receipt["execution"]=="budget_stopped": raise TimeoutError("budget during finalization")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("prepare","run"),required=True)
    p.add_argument("--inputs",type=Path,required=True)
    p.add_argument("--prepared",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.mode=="prepare": origin_prepare(a.inputs,a.output)
    else:
        if a.prepared is None: p.error("--prepared required for run")
        diagnostic(a.inputs,a.prepared,a.output)


if __name__=="__main__": main()
