"""Fixed inference using the authors' released CrackSAM adapter and SAM ViT-H."""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
import torch


def starts(n, size=448, stride=336):
    end = max(n-size, 0)
    values = list(range(0, end+1, stride))
    return values + ([end] if values[-1] != end else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, type=Path)
    args = ap.parse_args()
    root = args.root
    sys.path.insert(0, str(root/'model'))
    from segment_anything import sam_model_registry
    from delta.sam_adapter_image_encoder import Adapter_Sam
    torch.set_num_threads(4)
    torch.cuda.set_per_process_memory_fraction(0.25, 0)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.manual_seed(3407)
    # Keep author loading semantics, but restrict deserialization to tensor states
    # and map all saved device tags to CPU before the final .cuda().
    original_load = torch.load

    def safe_load(*a, **kw):
        kw.update(weights_only=True, map_location='cpu')
        return original_load(*a, **kw)

    torch.load = safe_load
    try:
        sam, _ = sam_model_registry['vit_h'](
            image_size=448, num_classes=1, pixel_mean=[0,0,0],
            pixel_std=[1,1,1], checkpoint=str(root/'model/sam_vit_h_4b8939.pth'))
        net = Adapter_Sam(sam, 32, 0.2)
        delta = root/'model/CrackSAM_adapter_d32.pth'
        net.load_delta_parameters(str(delta))
        # Author loader requires every adapter and every prompt/decoder key.
        state = safe_load(delta)
        assert len(net.w_down_attn) == 32
        for key, value in net.sam.state_dict().items():
            if key.startswith(('prompt_encoder.', 'mask_decoder.')):
                assert torch.equal(value, state[key]), key
        for i in range(32):
            for prefix, layers in [('a',net.w_down_attn),('b',net.w_up_attn),
                                   ('c',net.w_down_mlp),('d',net.w_up_mlp)]:
                assert torch.equal(layers[i].weight,state[f'w_{prefix}_{i:03d}'])
                assert torch.equal(layers[i].bias,state[f'w_{prefix}_{i:03d}_bia'])
    finally:
        torch.load = original_load
    net.eval().requires_grad_(False).cuda()
    print('Loaded official backbone and all trained adapters/prompt/decoder parameters.', flush=True)
    out = root/'outputs'
    out.mkdir(exist_ok=True)
    manifest = json.loads((root/'source_manifest.json').read_text())
    records = []
    with torch.inference_mode():
        for entry in manifest:
            src = root/'inputs'/entry['file']
            assert hashlib.sha256(src.read_bytes()).hexdigest() == entry['sha256']
            rgb = np.array(Image.open(src).convert('RGB'))
            h,w = rgb.shape[:2]
            name = entry['id']
            positions = [(y,x) for y in starts(h) for x in starts(w)]
            total = np.zeros((h,w), np.float32)
            counts = np.zeros((h,w), np.uint8)
            began = time.time()
            for off in range(0,len(positions),2):
                batch = positions[off:off+2]
                tiles = []
                for y,x in batch:
                    tile = rgb[y:y+448,x:x+448]
                    ph,pw = tile.shape[:2]
                    tiles.append(np.pad(tile,((0,448-ph),(0,448-pw),(0,0)),mode='edge'))
                inputs = torch.from_numpy(np.stack(tiles)).permute(0,3,1,2).float().cuda()/255
                logits = net(inputs, False, 448)['masks']
                assert logits.shape == (len(batch),2,448,448), logits.shape
                probs = logits.softmax(dim=1)[:,1].cpu().numpy()
                assert np.isfinite(probs).all()
                for (y,x),prob in zip(batch,probs):
                    ph,pw = min(448,h-y),min(448,w-x)
                    total[y:y+ph,x:x+pw] += prob[:ph,:pw]
                    counts[y:y+ph,x:x+pw] += 1
                if off % 40 == 0:
                    print(name,off,'/',len(positions),flush=True)
            assert counts.min() >= 1
            total /= counts
            mask = total >= 0.5
            Image.fromarray(mask.astype(np.uint8)*255).save(out/f'{name}_mask.png')
            Image.fromarray(mask.astype(np.uint8)).save(out/f'{name}_labels.png')
            Image.fromarray(np.rint(total*65535).astype(np.uint16)).save(out/f'{name}_probability16.png')
            rgba = np.zeros((h,w,4),np.uint8)
            rgba[mask] = [0,225,160,115]
            Image.fromarray(rgba).save(out/f'{name}_overlay.png')
            records.append({'id':name,'size':[w,h],'tiles':len(positions),
                            'crack_pixels':int(mask.sum()),'seconds':time.time()-began,
                            'coverage_min':int(counts.min())})
            (out/'summary.json').write_text(json.dumps(records,indent=2))
            print('DONE',records[-1],flush=True)
    receipt = {'hostname':platform.node(),'torch':torch.__version__,
               'gpu':torch.cuda.get_device_name(0),'training':False,
               'requires_grad_count':sum(p.requires_grad for p in net.parameters()),
               'peak_gpu_bytes':torch.cuda.max_memory_allocated(),
               'checkpoint_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in [root/'model/sam_vit_h_4b8939.pth',delta]}}
    (out/'execution_receipt.json').write_text(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    main()
