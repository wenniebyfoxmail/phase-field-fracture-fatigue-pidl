"""Derive a fixed visual failure panel from the completed D1 checkpoint; no fitting."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import torch

def truth(v): return str(v).lower()=="true"

def overlay(rgb,mask,color):
    a=rgb.copy();m=mask.astype(bool);a[m]=(.42*a[m]+.58*np.array(color)).astype(np.uint8);return a

def main():
    p=argparse.ArgumentParser();p.add_argument("--runner-dir",required=True);p.add_argument("--checkpoint",required=True);p.add_argument("--metrics",required=True);p.add_argument("--cfd",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    sys.path.insert(0,a.runner_dir);import runner
    with open(a.metrics,newline="") as f:rows=list(csv.DictReader(f))
    low=sorted(rows,key=lambda r:(float(r["U_Z"]),r["id"]))[:4]
    high=sorted(rows,key=lambda r:(-float(r["U_Z"]),r["id"]))[:4]
    used={r["id"] for r in low+high};deg=sorted([r for r in rows if truth(r["pred_empty"]) and r["id"] not in used],key=lambda r:(float(r["U_Z"]),r["id"]))[:4]
    chosen=[("low_UZ",r) for r in low]+[("high_UZ",r) for r in high]+[("degenerate",r) for r in deg]
    cfd=Path(a.cfd);images={p.stem:p for p in (cfd/"image").glob("*.jpg")};mats={p.stem:p for p in (cfd/"groundTruth").glob("*.mat")}
    model=runner.UNet();state=torch.load(a.checkpoint,map_location="cpu",weights_only=True);model.load_state_dict(state["model"]);model.eval()
    W,H=240,160;canvas=Image.new("RGB",(W*3,(H+28)*len(chosen)),"white");draw=ImageDraw.Draw(canvas);audit=[]
    for i,(group,r) in enumerate(chosen):
        row={"id":r["id"],"image":images[r["id"]],"mask":mats[r["id"]]};rgb,y=runner.load_cfd(row);prob,_=runner.predict(model,rgb,torch.device("cpu"));pred=prob>=.5
        panels=[rgb,overlay(rgb,y,[40,255,80]),overlay(rgb,pred,[255,40,40])]
        for j,panel in enumerate(panels):canvas.paste(Image.fromarray(panel).resize((W,H),Image.Resampling.BILINEAR),(j*W,i*(H+28)))
        draw.text((4,i*(H+28)+H+3),f"{group} {r['id']} dice={float(r['dice']):.3f} UZ={float(r['U_Z']):.2f}",fill="black")
        audit.append({"selection_group":group,"id":r["id"],"recorded_dice":float(r["dice"]),"U_Z":float(r["U_Z"]),"recorded_pred_empty":truth(r["pred_empty"]),"recomputed_pred_fraction":float(pred.mean()),"reference_fraction":float(y.mean())})
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False);canvas.save(out/"d1_failure_panel.png");(out/"d1_failure_panel_selection.json").write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))

if __name__=="__main__":main()
