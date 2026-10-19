"""Read-only qualification of candidate public B sources; never reads Road420."""
import argparse, hashlib, io, json, zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.fft import dctn

GAPS_RAW = "pavement crack datasets/GAPS384/GAPs384_raw_img_gt.zip"
GAPS_IMG = "pavement crack datasets/GAPS384/croppedimg.zip"
GAPS_GT = "pavement crack datasets/GAPS384/croppedgt.zip"
TREE_IMG = "pavement crack datasets/cracktree200/cracktree200rgb.zip"
TREE_GT = "pavement crack datasets/cracktree200/cracktree200_gt.zip"
EXCLUDE_TRAIN = {"20160328_154452", "20160328_154454", "20160329_103609", "20160329_103800", "20160329_111111"}
EXCLUDE_VAL = {"20160329_103807"}


def sha_bytes(data): return hashlib.sha256(data).hexdigest()


def parent(stem): return "_".join(stem.split("_")[:-2])


def decode(data, mode="RGB"):
    with Image.open(io.BytesIO(data)) as im: return np.asarray(im.convert(mode))


def phash(a):
    im=Image.fromarray(a).convert("L").resize((32,32),Image.Resampling.LANCZOS)
    c=dctn(np.asarray(im,dtype=np.float32),type=2,norm="ortho")[:8,:8]
    bits=(c>np.median(c[1:])).reshape(-1);value=0
    for bit in bits:value=(value<<1)|int(bit)
    return value


def inner(outer,name):
    data=outer.read(name);q=zipfile.ZipFile(io.BytesIO(data));assert q.testzip() is None
    return data,q


def binary_mask(data):
    a=decode(data,"L");vals=np.unique(a)
    if not set(vals.tolist()).issubset({0,255}):raise ValueError(f"Nonbinary mask values: {vals[:12]}")
    return a>0


def gaps_inventory(rawzip):
    images={Path(n).stem:n for n in rawzip.namelist() if n.startswith("img/") and n.lower().endswith(".jpg")}
    masks={Path(n).stem.removesuffix("_mask"):n for n in rawzip.namelist() if n.startswith("gt/") and n.lower().endswith("_mask.png")}
    pairs=[]
    for stem in sorted(images.keys() & masks.keys()):
        rgb=decode(rawzip.read(images[stem]));mask=binary_mask(rawzip.read(masks[stem]))
        if rgb.shape[:2]!=mask.shape:raise ValueError(stem)
        pairs.append((stem,rgb,mask))
    return pairs,sorted(images.keys()-masks.keys())


def tree_inventory(imgzip,gtzip):
    images={Path(n).stem:n for n in imgzip.namelist() if n.lower().endswith(".jpg")}
    masks={Path(n).stem:n for n in gtzip.namelist() if n.lower().endswith(".png")}
    ratios=[]
    for stem in sorted(images.keys() & masks.keys()):
        rgb=decode(imgzip.read(images[stem]));mask=binary_mask(gtzip.read(masks[stem]));assert rgb.shape[:2]==mask.shape
        ratios.append(float(mask.mean()))
    return {"pairs":len(ratios),"shape":[600,800],"nonempty":sum(x>0 for x in ratios),"foreground_ratio":{"min":min(ratios),"median":float(np.median(ratios)),"max":max(ratios)}}


def known_images(crack_root,cfd_root):
    rows=[]
    for name,excluded in [("traincrop.zip",EXCLUDE_TRAIN),("valcrop.zip",EXCLUDE_VAL)]:
        with zipfile.ZipFile(crack_root/name) as z:
            for n in z.namelist():
                p=Path(n)
                if p.suffix.lower()==".jpg" and parent(p.stem) not in excluded:rows.append((f"CRACK500/{p.stem}",decode(z.read(n))))
    with zipfile.ZipFile(crack_root/"testdata.zip") as z:
        for n in z.namelist():
            p=Path(n)
            if p.suffix.lower()==".jpg":rows.append((f"CRACK500/{p.stem}",decode(z.read(n))))
    mats={p.stem for p in (cfd_root/"groundTruth").glob("*.mat")}
    for p in sorted((cfd_root/"image").glob("*.jpg")):
        if p.stem in mats:rows.append((f"CFD/{p.stem}",decode(p.read_bytes())))
    return rows


def overlap_screen(gaps,known):
    known_hash=[(name,phash(rgb),hashlib.sha256(rgb.tobytes()).hexdigest(),rgb.shape) for name,rgb in known]
    exact=[];near=[];closest=[]
    for stem,rgb,_ in gaps:
        pix=hashlib.sha256(rgb.tobytes()).hexdigest();rotations=[phash(np.rot90(rgb,k)) for k in range(4)]
        best=(65,None,None)
        for name,h,pix2,shape in known_hash:
            if rgb.shape==shape and pix==pix2:exact.append([stem,name])
            for k,rh in enumerate(rotations):
                d=(rh^h).bit_count()
                if d<best[0]:best=(d,name,k)
                if d<=8:near.append({"gaps":stem,"known":name,"rotation":k,"hamming":d})
        closest.append({"gaps":stem,"known":best[1],"rotation":best[2],"hamming":best[0]})
    return exact,near,sorted(closest,key=lambda x:(x["hamming"],x["gaps"]))[:12]


def contact_sheet(pairs,path):
    order=np.argsort([m.mean() for _,_,m in pairs]);idx=np.unique(np.linspace(0,len(order)-1,12,dtype=int));chosen=[pairs[order[i]] for i in idx]
    cell=(320,250);canvas=Image.new("RGB",(cell[0]*4,cell[1]*3),"white");draw=ImageDraw.Draw(canvas)
    for i,(stem,rgb,mask) in enumerate(chosen):
        im=Image.fromarray(rgb).resize((320,220),Image.Resampling.BILINEAR);m=Image.fromarray((mask*255).astype(np.uint8)).resize((320,220),Image.Resampling.NEAREST)
        a=np.asarray(im).copy();mm=np.asarray(m)>0;a[mm]=(.45*a[mm]+.55*np.array([255,40,40])).astype(np.uint8)
        x=(i%4)*cell[0];y=(i//4)*cell[1];canvas.paste(Image.fromarray(a),(x,y));draw.text((x+4,y+224),f"{stem} fg={mask.mean():.4f}",fill="black")
    canvas.save(path)


def main():
    p=argparse.ArgumentParser();p.add_argument("--outer",required=True);p.add_argument("--crack-inner",required=True);p.add_argument("--cfd",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(a.outer) as z:
        rawdata,raw=inner(z,GAPS_RAW);cropdata,crop=inner(z,GAPS_IMG);gtdata,gt=inner(z,GAPS_GT);tidata,ti=inner(z,TREE_IMG);tgdata,tg=inner(z,TREE_GT)
        gaps,unpaired=gaps_inventory(raw);tree=tree_inventory(ti,tg)
        for name,data in [("GAPs384_raw_img_gt.zip",rawdata),("croppedimg.zip",cropdata),("croppedgt.zip",gtdata)]: (out/name).write_bytes(data)
    crop_img={Path(n).stem for n in crop.namelist() if n.lower().endswith(".jpg")};crop_gt={Path(n).stem for n in gt.namelist() if n.lower().endswith(".png")};crop_stems=sorted(crop_img&crop_gt);crop_groups={"_".join(s.split("_")[:2]) for s in crop_stems}
    known=known_images(Path(a.crack_inner),Path(a.cfd));exact,near,closest=overlap_screen(gaps,known)
    contact_sheet(gaps,out/"gaps384_overlay_audit.png")
    ratios=[float(m.mean()) for _,_,m in gaps]
    report={
      "date":"2026-10-19","source_outer":str(Path(a.outer).resolve()),"outer_sha256":hashlib.sha256(Path(a.outer).read_bytes()).hexdigest(),
      "inner_sha256":{"raw":sha_bytes(rawdata),"cropped_images":sha_bytes(cropdata),"cropped_masks":sha_bytes(gtdata)},
      "gaps384":{"raw_images":404,"labeled_pairs":len(gaps),"unpaired_image_count":len(unpaired),"unpaired_images":unpaired,"shape":[1080,1920],"mask_values":[0,255],"nonempty_masks":sum(x>0 for x in ratios),"foreground_ratio":{"min":min(ratios),"median":float(np.median(ratios)),"max":max(ratios)},"cropped_pairs":len(crop_stems),"cropped_parent_ids":len(crop_groups)},
      "cracktree200":tree,
      "overlap_screen":{"known_images":len(known),"comparisons_with_four_rotations":len(gaps)*len(known)*4,"exact_decoded_pixel_matches":len(exact),"phash_hamming_le_8":len(near),"exact":exact,"near":near,"closest":closest,"road420_accessed":False},
      "qualification":"GAPS384_PROVISIONAL_B_FOR_FINITE_PUBLISHED_LABEL_TRANSFER_ONLY",
      "limits":["FPHBN derivative package has no recognized repository license; local academic research only, no redistribution","derivative package has no road/site mapping","new-B versus sealed Road420 duplication remains unchecked","published masks are author reannotations, not physical crack width truth"]}
    (out/"qualification_receipt.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=="__main__":main()
