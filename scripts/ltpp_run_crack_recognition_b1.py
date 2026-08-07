#!/usr/bin/env python3
"""Run the dated B1 lightweight U-Net amendment on six LOSO folds."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import pathlib
import random
import sys

import cv2
import numpy as np
import torch
from skimage.morphology import skeletonize


def load_b0(path):
    spec = importlib.util.spec_from_file_location("ltpp_b0", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Block(torch.nn.Module):
    def __init__(self, a, b):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Conv2d(a, b, 3, padding=1), torch.nn.ReLU(), torch.nn.Conv2d(b, b, 3, padding=1), torch.nn.ReLU())

    def forward(self, x):
        return self.net(x)


class TinyUNet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.e1, self.e2, self.e3 = Block(1, 8), Block(8, 16), Block(16, 32)
        self.pool = torch.nn.MaxPool2d(2)
        self.u2 = torch.nn.Conv2d(32, 16, 1)
        self.u1 = torch.nn.Conv2d(16, 8, 1)
        self.d2, self.d1 = Block(32, 16), Block(16, 8)
        self.out = torch.nn.Conv2d(8, 1, 1)

    def forward(self, x):
        a = self.e1(x)
        b = self.e2(self.pool(a))
        c = self.e3(self.pool(b))
        y = torch.nn.functional.interpolate(self.u2(c), size=b.shape[-2:], mode="bilinear", align_corners=False)
        y = self.d2(torch.cat([y, b], 1))
        y = torch.nn.functional.interpolate(self.u1(y), size=a.shape[-2:], mode="bilinear", align_corners=False)
        return self.out(self.d1(torch.cat([y, a], 1)))


def sha256(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)


def make_target(b0, label, shape=(250, 762)):
    line, poly, _, _ = b0.gold_masks(label, (500, 1524))
    target = cv2.bitwise_or(line, poly)
    target = cv2.dilate(target, np.ones((3, 3), np.uint8), iterations=1)
    return cv2.resize(target, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST) / 255.0


def load_sample(b0, image, label):
    gray = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
    x = cv2.resize(gray, (762, 250), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    y = make_target(b0, label)
    return torch.from_numpy(x[None]), torch.from_numpy(y[None])


def dice_loss(logit, target):
    p = torch.sigmoid(logit)
    inter = (p * target).sum(dim=(1, 2, 3))
    return (1 - (2 * inter + 1) / (p.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3)) + 1)).mean()


def evaluate(b0, candidate, model, samples, output, fold, threshold, remove_static):
    model.eval(); rows = []
    fold_dir = output / "folds" / fold
    (fold_dir / "visual_audit").mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        for blind, section, image, label in samples:
            gray = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
            x, _ = load_sample(b0, image, label)
            prob = torch.sigmoid(model(x[None])).numpy()[0, 0]
            prob = cv2.resize(prob, (1524, 500), interpolation=cv2.INTER_LINEAR)
            pred_mask = (prob >= threshold).astype(np.uint8) * 255
            if remove_static:
                _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                static = candidate.static_line_mask(ink)
                pred_mask[static > 0] = 0
            pred_center = skeletonize(pred_mask > 0).astype(np.uint8) * 255
            gold_line, gold_poly, _, gold_lines = b0.gold_masks(label, gray.shape)
            gold = cv2.bitwise_or(gold_line, gold_poly)
            center = b0.distance_metrics(pred_center, gold_line, 10)
            buffered = b0.distance_metrics(pred_mask, gold, 10)
            endpoint = b0.endpoint_distance(gold_lines, pred_center)
            stem = f"{blind}__{section}"
            cv2.imwrite(str(fold_dir / f"{stem}__prediction_mask.png"), pred_mask)
            cv2.imwrite(str(fold_dir / f"{stem}__prediction_centerline.png"), pred_center)
            panel = fold_dir / "visual_audit" / f"{stem}__four_panel.png"
            b0.make_panel(gray, gold, pred_center, panel, stem)
            panel.with_suffix(".md").write_text(f"# B1 four-panel audit\n\n## Figure question\nDoes B1 recover current-map crack geometry for `{blind}`?\n\n## Data provenance\nFrozen image `{image}` and adjudicated label `{label}`; fold `{fold}`.\n\n## How to read\nOriginal, gold, B1 centerline prediction, TP/FP/FN overlay.\n\n## Limitation\nCurrent-map recognition only; no future-map or road-photo claim.\n")
            rows.append({"blind_id": blind, "section": section, "centerline": center, "buffered_mask": buffered, "endpoint_distance_m": endpoint})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo-root", type=pathlib.Path, required=True); ap.add_argument("--output", type=pathlib.Path, required=True); ap.add_argument("--threshold", type=float, default=0.35); ap.add_argument("--reuse-models", type=pathlib.Path); ap.add_argument("--remove-static", action="store_true"); args = ap.parse_args()
    repo = args.repo_root.resolve(); packet = repo / "local_archive/real_road_acquisition/ltpp_geoforecast_blind_vectorization_v1_20260805"; b0 = load_b0(repo / "upload code/scripts/ltpp_run_crack_recognition_b0.py"); candidate = load_b0(repo / "upload code/scripts/ltpp_extract_crack_candidates.py")
    seed_all(20260807); torch.set_num_threads(2); args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((packet / "adjudicated/adjudicated_manifest.json").read_text()); by_blind = {}
    for e in manifest["files"]:
        p = packet / "adjudicated" / e["file"]; d = json.loads(p.read_text()); by_blind[d["properties"]["primary_blind_id"]] = (d["properties"]["section"], p)
    samples = []
    for image in sorted((packet / "primary/images").glob("P*.png")):
        section, label = by_blind[image.stem]; samples.append((image.stem, section, image, label))
    sections = sorted({x[1] for x in samples}); all_rows = []
    for held in sections:
        seed_all(20260807); model = TinyUNet(); opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=0.0); loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(8.0))
        train = [x for x in samples if x[1] != held]
        model_path = (args.reuse_models / "folds" / f"LOSO-{held}" / "model.pt") if args.reuse_models else None
        if model_path and model_path.is_file():
            model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
        else:
            for _ in range(80):
                model.train(); random.shuffle(train)
                for i in range(0, len(train), 2):
                    batch = train[i:i+2]; xs, ys = zip(*(load_sample(b0, x[2], x[3]) for x in batch)); x = torch.stack(xs); y = torch.stack(ys); opt.zero_grad(); logit = model(x); loss = loss_fn(logit, y) + dice_loss(logit, y); loss.backward(); opt.step()
        rows = evaluate(b0, candidate, model, [x for x in samples if x[1] == held], args.output, f"LOSO-{held}", args.threshold, args.remove_static); all_rows.extend(rows)
        torch.save(model.state_dict(), args.output / "folds" / f"LOSO-{held}" / "model.pt")
    pooled = {"precision_weighted": float(np.average([r["centerline"]["precision"] for r in all_rows], weights=[max(1,r["centerline"]["pred_pixels"]) for r in all_rows])), "recall_weighted": float(np.average([r["centerline"]["recall"] for r in all_rows], weights=[max(1,r["centerline"]["gold_pixels"]) for r in all_rows])), "f1_map_mean": float(np.mean([r["centerline"]["f1"] for r in all_rows]))}
    section_summary = {}
    for sec in sections:
        rows = [r for r in all_rows if r["section"] == sec]; section_summary[sec] = {"map_count": len(rows), "centerline_f1_mean": float(np.mean([r["centerline"]["f1"] for r in rows])), "centerline_recall_mean": float(np.mean([r["centerline"]["recall"] for r in rows])), "endpoint_distance_m_mean": float(np.mean([r["endpoint_distance_m"] for r in rows if r["endpoint_distance_m"] is not None])) if any(r["endpoint_distance_m"] is not None for r in rows) else None}
    result = {"status":"B1_EVALUATED","method":"TinyUNet","seed":20260807,"epochs":80,"threshold":args.threshold,"target_dilation_px":3,"pooled_centerline":pooled,"section_summary":section_summary,"rows":all_rows,"code_sha256":sha256(repo/"upload code/scripts/ltpp_run_crack_recognition_b1.py"),"input_manifest_sha256":sha256(packet/"adjudicated/adjudicated_manifest.json")}
    (args.output/"b1_metrics.json").write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps({"pooled":pooled,"sections":section_summary}))


if __name__ == "__main__": main()
