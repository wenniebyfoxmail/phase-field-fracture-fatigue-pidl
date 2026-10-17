"""Fixed pretrained SegFormer visual preview. No training or metric qualification."""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor


def starts(n, size=256, stride=192):
    return list(range(0, max(n - size, 0) + 1, stride)) + (
        [max(n - size, 0)] if max(n - size, 0) % stride else []
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--model', type=Path, required=True)
    args = ap.parse_args()
    torch.set_num_threads(2)
    torch.cuda.set_per_process_memory_fraction(0.18, 0)
    processor = SegformerImageProcessor.from_pretrained(args.model, local_files_only=True)
    model = SegformerForSemanticSegmentation.from_pretrained(
        args.model, local_files_only=True, use_safetensors=True
    ).eval().cuda()
    assert model.config.id2label[1] == 'crack'
    assert model.config.num_labels == 3
    out = args.root / 'outputs'
    out.mkdir(exist_ok=True)
    records = []
    with torch.inference_mode():
        for src in sorted((args.root / 'inputs').glob('*.jpg')):
            began = time.time()
            rgb = np.array(Image.open(src).convert('RGB'))
            h, w = rgb.shape[:2]
            probs = np.zeros((3, h, w), dtype=np.float32)
            counts = np.zeros((h, w), dtype=np.float32)
            positions = [(y, x) for y in starts(h) for x in starts(w)]
            for off in range(0, len(positions), 4):
                batch = positions[off:off + 4]
                tiles = []
                for y, x in batch:
                    tile = rgb[y:y + 256, x:x + 256]
                    ph, pw = tile.shape[:2]
                    tile = np.pad(tile, ((0, 256-ph), (0, 256-pw), (0, 0)), mode='edge')
                    tiles.append(Image.fromarray(tile))
                inputs = processor(images=tiles, return_tensors='pt').to('cuda')
                logits = model(**inputs).logits
                pred = F.interpolate(logits, (256, 256), mode='bilinear', align_corners=False)
                pred = pred.softmax(dim=1).cpu().numpy()
                for (y, x), p in zip(batch, pred):
                    ph, pw = min(256, h-y), min(256, w-x)
                    probs[:, y:y+ph, x:x+pw] += p[:, :ph, :pw]
                    counts[y:y+ph, x:x+pw] += 1
                if off % 200 == 0:
                    print(src.stem, off, '/', len(positions), flush=True)
            assert counts.min() >= 1
            probs /= counts[None]
            labels = probs.argmax(axis=0).astype(np.uint8)
            mask = labels == 1
            Image.fromarray(mask.astype(np.uint8)*255).save(out / f'{src.stem}_mask.png')
            Image.fromarray(labels).save(out / f'{src.stem}_labels.png')
            Image.fromarray(np.rint(probs[1]*65535).astype(np.uint16)).save(out / f'{src.stem}_probability16.png')
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[mask] = [0, 225, 160, 115]
            Image.fromarray(rgba).save(out / f'{src.stem}_overlay.png')
            record = {'id': src.stem, 'size': [w,h], 'tiles': len(positions),
                      'crack_pixels': int(mask.sum()), 'crack_fraction': float(mask.mean()),
                      'seconds': time.time()-began, 'min_coverage': float(counts.min())}
            records.append(record)
            (out/'summary.json').write_text(json.dumps(records, indent=2))
            print('DONE', record, flush=True)
    receipt = {'hostname': platform.node(), 'torch': torch.__version__,
               'cuda_device': torch.cuda.get_device_name(0),
               'checkpoint_sha256': hashlib.sha256((args.model/'model.safetensors').read_bytes()).hexdigest(),
               'training': False, 'images': len(records), 'gpu_peak_allocated': torch.cuda.max_memory_allocated()}
    (out/'execution_receipt.json').write_text(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
