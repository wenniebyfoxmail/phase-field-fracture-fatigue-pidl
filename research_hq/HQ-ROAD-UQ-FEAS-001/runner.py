"""Frozen D1 runner for public road-crack positive-reference feasibility."""
import argparse, csv, hashlib, json, math, os, platform, random, socket, sys, time, zipfile
from pathlib import Path

import numpy as np
import PIL
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F

HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / "frozen_protocol.json").read_text())
SEED = int(PROTOCOL["seed"])


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cfd_lock(root):
    images={p.stem:p for p in (root/"image").glob("*.jpg")};mats={p.stem:p for p in (root/"groundTruth").glob("*.mat")}
    stems=sorted(images.keys() & mats.keys());rows=[]
    for stem in stems:
        for path in (images[stem],mats[stem]): rows.append([path.relative_to(root).as_posix(),path.stat().st_size,sha256(path)])
    digest=hashlib.sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest()
    return {"labeled_pairs":len(stems),"files":len(rows),"bytes":sum(r[1] for r in rows),"aggregate_sha256":digest}


def snapshot():
    files = sorted(HERE.glob("*.py")) + [HERE / "frozen_protocol.json"]
    payload = {p.name: sha256(p) for p in files}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def environment():
    import matplotlib, scipy
    return {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
            "pillow": PIL.__version__, "matplotlib": matplotlib.__version__, "scipy": scipy.__version__,
            "cuda": torch.version.cuda}


def parent_id(stem):
    bits = stem.split("_")
    if len(bits) < 3:
        raise ValueError(f"Unparseable crop stem {stem}")
    return "_".join(bits[:-2])


def extract_once(archive, destination):
    marker = destination / ".complete"
    if marker.exists():
        return
    if destination.exists():
        raise RuntimeError(f"Partial extraction exists: {destination}")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        z.extractall(destination)
    marker.write_text(sha256(archive))


def crack_pairs(root, split, excluded=()):
    d = root / split
    jpg = {p.stem: p for p in d.glob("*.jpg")}
    png = {p.stem: p for p in d.glob("*.png")}
    stems = sorted(jpg) if split == "testdata" else sorted(jpg.keys() & png.keys())
    rows = []
    for stem in stems:
        pid = stem if split == "testdata" else parent_id(stem)
        mask_stem = stem + "_mask" if split == "testdata" else stem
        if pid not in excluded and mask_stem in png:
            rows.append({"id": stem, "group": pid, "image": jpg[stem], "mask": png[mask_stem]})
    return rows


def cfd_pairs(root):
    images = {p.stem: p for p in (root / "image").glob("*.jpg")}
    mats = {p.stem: p for p in (root / "groundTruth").glob("*.mat")}
    stems = sorted(images.keys() & mats.keys())
    return [{"id": s, "group": s, "image": images[s], "mask": mats[s]} for s in stems]


def load_crack(row):
    with Image.open(row["image"]) as im:
        x = np.asarray(im.convert("RGB"))
    with Image.open(row["mask"]) as im:
        if im.mode != "1":
            vals = set(np.unique(np.asarray(im.convert("L"))).tolist())
            if not vals.issubset({0, 255}):
                raise ValueError(f"Nonbinary CRACK500 mask {row['id']}: {vals}")
        y = np.asarray(im.convert("L")) > 0
    if x.shape[:2] != y.shape:
        raise ValueError(f"Shape mismatch {row['id']}")
    return x, y


def load_cfd(row):
    from scipy.io import loadmat
    with Image.open(row["image"]) as im:
        x = np.asarray(im.convert("RGB"))
    obj = loadmat(row["mask"], squeeze_me=True, struct_as_record=False)["groundTruth"]
    y = np.asarray(obj.Boundaries) > 0
    if x.shape[:2] != y.shape or not y.any():
        raise ValueError(f"Invalid CFD pair {row['id']}")
    return x, y


class Block(nn.Sequential):
    def __init__(self, a, b):
        super().__init__(nn.Conv2d(a, b, 3, padding=1, bias=False), nn.GroupNorm(8, b), nn.ReLU(),
                         nn.Conv2d(b, b, 3, padding=1, bias=False), nn.GroupNorm(8, b), nn.ReLU())


class UNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = nn.ModuleList([Block(a, b) for a, b in [(3, 16), (16, 32), (32, 64), (64, 128)]])
        self.middle = Block(128, 256)
        self.dec = nn.ModuleList([Block(a, b) for a, b in [(384, 128), (192, 64), (96, 32), (48, 16)]])
        self.out = nn.Conv2d(16, 1, 1)
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_in", nonlinearity="relu")
            elif isinstance(m, nn.GroupNorm):
                nn.init.ones_(m.weight); nn.init.zeros_(m.bias)

    def forward(self, x, return_feature=False):
        skips = []
        for layer in self.enc:
            x = layer(x); skips.append(x); x = F.max_pool2d(x, 2)
        x = self.middle(x)
        feature = x.mean((2, 3))
        for layer, skip in zip(self.dec, reversed(skips)):
            x = layer(torch.cat([F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False), skip], 1))
        logits = self.out(x)
        return (logits, feature) if return_feature else logits


def reflect_to(a, h, w):
    ph, pw = h - a.shape[0], w - a.shape[1]
    mode = "reflect" if min(a.shape[:2]) > 1 else "edge"
    pads = ((0, ph), (0, pw)) + (() if a.ndim == 2 else ((0, 0),))
    return np.pad(a, pads, mode=mode)


class TrainSet(torch.utils.data.Dataset):
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, index):
        x, y = load_crack(self.rows[index]); size = 320
        x = reflect_to(x, max(size, x.shape[0]), max(size, x.shape[1]))
        y = reflect_to(y, x.shape[0], x.shape[1])
        top = random.randint(0, x.shape[0] - size); left = random.randint(0, x.shape[1] - size)
        x = x[top:top+size, left:left+size]; y = y[top:top+size, left:left+size]
        if random.random() < .5: x, y = x[:, ::-1], y[:, ::-1]
        if random.random() < .5: x, y = x[::-1], y[::-1]
        return torch.from_numpy(x.copy().transpose(2, 0, 1)).float()/255, torch.from_numpy(y.copy()[None]).float()


def loss_fn(logits, target):
    bce = F.binary_cross_entropy_with_logits(logits, target)
    p = torch.sigmoid(logits); dims = (1, 2, 3)
    dice = (2*(p*target).sum(dims)+1)/((p+target).sum(dims)+1)
    return .5*bce + .5*(1-dice).mean()


def starts(n, tile, overlap):
    if n <= tile: return [0]
    values = list(range(0, n-tile+1, tile-overlap))
    if values[-1] != n-tile: values.append(n-tile)
    return values


@torch.no_grad()
def predict(model, rgb, device, deadline=None):
    model.eval(); h, w = rgb.shape[:2]; tile = 640; overlap = 96
    hp = math.ceil(h/16)*16; wp = math.ceil(w/16)*16
    padded = reflect_to(rgb, hp, wp); total = np.zeros((hp, wp), np.float32); weight = np.zeros((hp, wp), np.float32)
    features, areas = [], []
    for y in starts(hp, tile, overlap):
        for x in starts(wp, tile, overlap):
            if deadline is not None and time.monotonic() >= deadline: raise TimeoutError("Six GPU-hour hard budget reached")
            patch = padded[y:min(y+tile,hp), x:min(x+tile,wp)]
            t = torch.from_numpy(patch.copy().transpose(2,0,1)).unsqueeze(0).to(device).float()/255
            logits, feat = model(t, return_feature=True); p = torch.sigmoid(logits)[0,0].cpu().numpy()
            total[y:y+p.shape[0], x:x+p.shape[1]] += p; weight[y:y+p.shape[0], x:x+p.shape[1]] += 1
            features.append(feat[0].cpu().numpy()); areas.append(p.size)
    return (total/weight)[:h,:w], np.average(np.stack(features), axis=0, weights=areas)


def metric(prob, target):
    pred = prob >= .5; den = int(pred.sum()+target.sum())
    dice = 1.0 if den == 0 else 2*int((pred & target).sum())/den
    q = prob.astype(np.float64); lc = float(np.minimum(q,1-q).mean())
    ent = np.zeros_like(q); m=(q>0)&(q<1); ent[m] = -q[m]*np.log(q[m])-(1-q[m])*np.log1p(-q[m])
    return {"dice":float(dice), "error":float(1-dice), "U_LC":lc, "U_H":float(ent.mean()),
            "pred_empty":bool(not pred.any()), "pred_full":bool(pred.all())}


def evaluate(model, rows, loader, device, source, deadline=None):
    out=[]
    for row in rows:
        if deadline is not None and time.monotonic() >= deadline: raise TimeoutError("Six GPU-hour hard budget reached")
        rgb, y = loader(row); p, z = predict(model, rgb, device, deadline); m = metric(p,y)
        out.append({"id":row["id"],"group":row["group"],"source":source,**m,"feature":z.tolist()})
    return out


def write_csv(path, rows):
    clean=[{k:v for k,v in r.items() if k!="feature"} for r in rows]
    with open(path,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(clean[0]));w.writeheader();w.writerows(clean)


def risk(rows, key):
    ordered=sorted(rows,key=lambda r:(r[key],r["id"])); vals=np.array([r["error"] for r in ordered])
    cum=np.cumsum(vals)/np.arange(1,len(vals)+1)
    return [{"k":i+1,"coverage":(i+1)/len(vals),"risk":float(v),"id":ordered[i]["id"]} for i,v in enumerate(cum)]


def approval_gate(a, lock_path, args):
    if platform.system() != "Windows" or not torch.cuda.is_available(): raise RuntimeError("Windows CUDA producer required")
    if a.get("execute") is not True or a.get("hostname") != socket.gethostname(): raise RuntimeError("Authorization/host mismatch")
    if a.get("experiment_id") != PROTOCOL["experiment_id"] or a.get("run_id") != "HQ-ROAD-UQ-FEAS-001-R001": raise RuntimeError("Run identity mismatch")
    if a.get("code_snapshot") != snapshot() or a.get("data_lock_sha256") != sha256(lock_path): raise RuntimeError("Unreviewed snapshot or data lock")
    if a.get("environment") != environment(): raise RuntimeError("Environment drift")
    if any("road420" in key.lower() for key in vars(args)): raise RuntimeError("Road420 path/config prohibited in D1")


def main():
    p=argparse.ArgumentParser();p.add_argument("--approval",required=True);p.add_argument("--lock",required=True)
    p.add_argument("--trainzip",required=True);p.add_argument("--valzip",required=True);p.add_argument("--testzip",required=True)
    p.add_argument("--cfd",required=True);p.add_argument("--cache",required=True);p.add_argument("--output",required=True);args=p.parse_args()
    approval=json.loads(Path(args.approval).read_text()); lock=json.loads(Path(args.lock).read_text()); approval_gate(approval,args.lock,args)
    for key,path in [("trainzip",args.trainzip),("valzip",args.valzip),("testzip",args.testzip)]:
        if sha256(path)!=lock[key]["sha256"]: raise RuntimeError(f"Hash mismatch {key}")
    cfd_root=Path(args.cfd)
    if cfd_lock(cfd_root)!=lock["cfd_lock"]: raise RuntimeError("CFD labeled-pair content drift")
    if approval["road420_identity_sha256"] != lock["road420_identity_sha256"]: raise RuntimeError("Road420 identity mismatch")
    out=Path(args.output); out.mkdir(parents=True,exist_ok=False); cache=Path(args.cache)
    receipt={"status":"running","experiment_id":PROTOCOL["experiment_id"],"run_id":approval["run_id"],"hostname":socket.gethostname(),
             "pid":os.getpid(),"gpu":os.environ.get("CUDA_VISIBLE_DEVICES"),"code_snapshot":snapshot(),"data_lock_sha256":sha256(args.lock),
             "command":sys.argv,"started_unix":time.time(),"scope":"public published-reference positive-rich feasibility only"}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2))
    try:
        extract_once(args.trainzip,cache/"train");extract_once(args.valzip,cache/"val");extract_once(args.testzip,cache/"test")
        train=crack_pairs(cache/"train","traincrop",set(PROTOCOL["crack500_excluded_train_parents"]))
        val=crack_pairs(cache/"val","valcrop",set(PROTOCOL["crack500_excluded_val_parents"])); test=crack_pairs(cache/"test","testdata")
        cfd=cfd_pairs(Path(args.cfd)); exp=PROTOCOL["expected"]
        counts=(len(train),len(set(r['group'] for r in train)),len(val),len(set(r['group'] for r in val)),len(test),len(cfd))
        if counts!=(exp['train_pairs'],exp['train_groups'],exp['val_pairs'],exp['val_groups'],exp['test_pairs'],exp['cfd_labeled']): raise RuntimeError(f"Inventory mismatch {counts}")
        random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED);torch.cuda.manual_seed_all(SEED);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
        device=torch.device("cuda:0");model=UNet().to(device);opt=torch.optim.Adam(model.parameters(),lr=1e-3)
        gen=torch.Generator().manual_seed(SEED);dl=torch.utils.data.DataLoader(TrainSet(train),batch_size=8,shuffle=True,num_workers=0,generator=gen)
        run_start=time.monotonic(); train_deadline=run_start+int(5.5*3600); hard_deadline=run_start+6*3600;history=[];best=-1.;best_epoch=None
        for epoch in range(1,41):
            if time.monotonic()>train_deadline:break
            model.train();losses=[]
            for x,y in dl:
                if time.monotonic()>train_deadline:break
                x=x.to(device);y=y.to(device);opt.zero_grad(set_to_none=True);loss=loss_fn(model(x),y)
                if not torch.isfinite(loss):raise RuntimeError("Nonfinite loss")
                loss.backward();opt.step();losses.append(float(loss.detach().cpu()))
            if time.monotonic()>train_deadline:break
            vm=evaluate(model,val,load_crack,device,"CRACK500_val",train_deadline);score=float(np.mean([r['dice'] for r in vm]));selected=score>best
            if selected:best=score;best_epoch=epoch;torch.save({"model":model.state_dict(),"epoch":epoch,"val_mean_dice":score},out/"best.pt")
            history.append({"epoch":epoch,"train_loss":float(np.mean(losses)),"val_mean_dice":score,"selected":selected,"elapsed_s":time.monotonic()-run_start})
            (out/"selection.json").write_text(json.dumps(history,indent=2));(out/"fit_status.json").write_text(json.dumps({"status":"running","completed_epoch":epoch,"best_epoch":best_epoch,"budget_s":21600},indent=2))
        if not (out/"best.pt").exists():raise RuntimeError("No validated checkpoint within budget")
        state=torch.load(out/"best.pt",map_location=device,weights_only=True);model.load_state_dict(state["model"])
        av=evaluate(model,val,load_crack,device,"CRACK500_val",hard_deadline); z=np.array([r["feature"] for r in av]);mu=z.mean(0);var=np.maximum(z.var(0),1e-6)
        at=evaluate(model,test,load_crack,device,"CRACK500_test",hard_deadline); b=evaluate(model,cfd,load_cfd,device,"CFD",hard_deadline)
        for rows in (av,at,b):
            for r in rows:r["U_Z"]=float(np.mean((np.array(r["feature"])-mu)**2/var))
        write_csv(out/"a_validation_metrics.csv",av);write_csv(out/"a_test_metrics.csv",at);write_csv(out/"cfd_metrics.csv",b)
        curves={k:risk(b,k) for k in ["U_LC","U_H","U_Z"]};(out/"cfd_risk_curves.json").write_text(json.dumps(curves,indent=2))
        full=float(np.mean([r['error'] for r in b])); summary={"n":len(b),"full_risk":full,"best_epoch":state['epoch'],"a_val_mean_dice":state['val_mean_dice'],"scores":{}}
        for k,c in curves.items():summary["scores"][k]={"risk_at_25":c[28]["risk"],"aurc":float(np.mean([x['risk'] for x in c])),"f2":c[28]["risk"]<=full-.05}
        f1=sum(r['dice']>0 for r in b)>=89 and sum(r['pred_empty'] or r['pred_full'] for r in b)<59
        f2=any(v['f2'] for v in summary['scores'].values());summary.update({"F1":f1,"F2":f2,"verdict":"FEASIBILITY_GO" if f1 and f2 else "FEASIBILITY_NO_GO",
          "dice_positive_count":sum(r['dice']>0 for r in b),"degenerate_prediction_count":sum(r['pred_empty'] or r['pred_full'] for r in b),"catastrophic_error_ge_0_9":sum(r['error']>=.9 for r in b),
          "scope":"public published-reference positive-rich feasibility only; not physical truth, prevalence, independent-site, safety, or human-review utility"})
        (out/"result.json").write_text(json.dumps(summary,indent=2));(out/"all_failures.json").write_text(json.dumps(sorted([r for r in b if r['error']>=.9],key=lambda r:-r['error']),indent=2))
        import matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(7,5));
        for k,c in curves.items():ax.plot([x['coverage'] for x in c],[x['risk'] for x in c],label=k)
        ax.axhline(full,color='black',ls='--',lw=1,label='full cohort');ax.set(xlabel='Accepted fraction',ylabel='Mean 1-Dice vs CFD published labels',title='HQ-ROAD-UQ-FEAS-001-R001');ax.legend();fig.tight_layout();fig.savefig(out/"cfd_risk_curves.png",dpi=180);plt.close(fig)
        (out/"README_analysis.md").write_text("Read result.json, cfd_metrics.csv and cfd_risk_curves.png. This is a finite public published-label positive-rich feasibility diagnostic. It does not establish physical crack truth, natural prevalence, independent-site generalization, field safety, or human-review utility.\n")
        (out/"fit_status.json").write_text(json.dumps({"status":"completed","completed_epoch":history[-1]['epoch'],"best_epoch":best_epoch,"budget_s":21600,"budget_stop":history[-1]['epoch']<40},indent=2))
        receipt["status"]="succeeded";receipt["checkpoint_sha256"]=sha256(out/"best.pt");receipt["result_sha256"]=sha256(out/"result.json")
    except BaseException as e:
        receipt["status"]="failed";receipt["error"]=repr(e);raise
    finally:
        receipt["ended_unix"]=time.time();(out/"receipt.json").write_text(json.dumps(receipt,indent=2))

if __name__ == "__main__": main()
