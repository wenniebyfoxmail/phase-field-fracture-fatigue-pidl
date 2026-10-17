"""Validate returned masks and publish local-only review assets."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--public', type=Path, required=True)
    args = ap.parse_args()
    entries = json.loads((args.root/'source_manifest.json').read_text())
    assets = args.public/'full_mask_assets'
    assets.mkdir(exist_ok=True)
    rendered = []
    checks = []
    for entry in entries:
        name = entry['id']
        src = args.root/'inputs'/entry['file']
        assert hashlib.sha256(src.read_bytes()).hexdigest() == entry['sha256']
        original = Image.open(src).convert('RGB')
        mask = Image.open(args.root/'outputs'/f'{name}_mask.png')
        overlay = Image.open(args.root/'outputs'/f'{name}_overlay.png')
        labels = Image.open(args.root/'outputs'/f'{name}_labels.png')
        assert all(im.size == original.size for im in [mask,overlay,labels])
        m = np.array(mask) > 0
        assert np.array_equal(m, np.array(labels)==1)
        assert np.array_equal(m, np.array(overlay)[:,:,3]>0)
        assert set(np.unique(np.array(mask))) <= {0,255}
        combined = Image.alpha_composite(original.convert('RGBA'), overlay).convert('RGB')
        combined.save(args.root/'outputs'/f'{name}_composite.jpg', quality=92)
        pair = Image.new('RGB', (1600, 564), 'white')
        draw = ImageDraw.Draw(pair)
        draw.text((12,9), name+' | original', fill='black')
        draw.text((812,9), name+' | pretrained mask, opacity 45%', fill='black')
        pair.paste(original.resize((800,533)), (0,28))
        pair.paste(combined.resize((800,533)), (800,28))
        rendered.append(pair)
        shutil.copy2(src, assets/entry['file'])
        for suffix in ['mask','overlay']:
            filename=f'{name}_{suffix}.png'
            shutil.copy2(args.root/'outputs'/filename,assets/filename)
        checks.append({'id':name, 'native_dimensions_match':True,
                       'binary_mask_matches_class1_and_overlay':True,
                       'source_hash_matches':True})
    montage = Image.new('RGB',(1600,564*len(rendered)),'white')
    for i,pair in enumerate(rendered): montage.paste(pair,(0,i*564))
    montage.save(args.root/'F01_all_six_full_frame_masks.jpg',quality=92)
    montage.save(args.root/'F01_all_six_full_frame_masks.png')
    # Fixed representative: first beam's final endpoint, chosen before inference.
    shutil.copy2(args.root/'outputs'/'beam4_t588_composite.jpg',args.root/'F02_beam4_final_full_mask.jpg')
    html = Path(__file__).with_name('d01_full_mask_review.html')
    shutil.copy2(html,args.root/'full_crack_review.html')
    previous = args.public/'overlay_review.html'
    backup = args.public/'width_band_review.html'
    if previous.exists() and not backup.exists(): shutil.copy2(previous,backup)
    for filename in ['full_crack_review.html','overlay_review.html']:
        shutil.copy2(html,args.public/filename)
    (args.root/'asset_checks.json').write_text(json.dumps(checks,indent=2))
    print('Published six native-resolution mask previews; no scientific accuracy score.')


if __name__ == '__main__':
    main()
