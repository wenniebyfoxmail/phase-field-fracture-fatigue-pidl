"""Publish original/previous/raw/refined/removed views for all six fixed cases."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def composite(image, overlay):
    return Image.alpha_composite(image.convert('RGBA'),overlay.convert('RGBA')).convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--public',type=Path,required=True)
    ap.add_argument('--refined',default='refined')
    args = ap.parse_args()
    p = args.root
    assets = args.public/'strong_mask_assets'
    assets.mkdir(exist_ok=True)
    cases = json.loads((p/'source_manifest.json').read_text())
    records = json.loads((p/args.refined/'summary.json').read_text())
    rows = []
    checks = []
    for entry in cases:
        name = entry['id']
        src = p/'inputs'/entry['file']
        assert digest(src) == entry['sha256']
        assert digest(src) == digest(args.public/'full_mask_assets'/entry['file'])
        image = Image.open(src).convert('RGB')
        raw = np.array(Image.open(p/'outputs'/f'{name}_mask.png'))>0
        refined = np.array(Image.open(p/args.refined/f'{name}_mask.png'))>0
        removed_im = Image.open(p/args.refined/f'{name}_removed_overlay.png')
        removed = np.array(removed_im)[:,:,3]>0
        assert raw.shape == refined.shape == (image.height,image.width)
        assert not np.any(refined & ~raw)
        assert np.array_equal(removed, raw & ~refined)
        for kind,folder in [('raw','outputs'),('refined',args.refined)]:
            overlay = Image.open(p/folder/f'{name}_overlay.png')
            assert overlay.size == image.size
            expected = raw if kind=='raw' else refined
            assert np.array_equal(np.array(overlay)[:,:,3]>0,expected)
            for suffix in ['mask','overlay']:
                shutil.copy2(p/folder/f'{name}_{suffix}.png', assets/f'{name}_{kind}_{suffix}.png')
        shutil.copy2(p/args.refined/f'{name}_removed_overlay.png',assets/f'{name}_removed_overlay.png')
        Image.fromarray(removed.astype(np.uint8)*255).save(assets/f'{name}_removed_mask.png')
        old = composite(image,Image.open(args.baseline/'outputs'/f'{name}_overlay.png'))
        new = composite(image,Image.open(p/args.refined/f'{name}_overlay.png'))
        if name=='beam4_t588':
            new.save(p/'F02_beam4_final_improved.jpg',quality=94)
        row = Image.new('RGB',(1800,430),'white')
        draw = ImageDraw.Draw(row)
        for col,(im,title) in enumerate([(image,'Original'),(old,'Previous DeepCrack'),
                                         (new,'CrackSAM + OCR/component cleanup')]):
            draw.text((col*600+8,8),name+' | '+title,fill='black')
            row.paste(im.resize((600,400)),(col*600,27))
        rows.append(row)
        checks.append({'id':name,'source_hash_match':True,'native_size':list(image.size),
                       'raw_overlay_matches':True,'refined_is_subset_of_raw':True,
                       'removed_is_exact_difference':True})
    montage = Image.new('RGB',(1800,430*len(rows)),'white')
    for i,row in enumerate(rows):montage.paste(row,(0,i*430))
    montage.save(p/'F01_all_six_previous_vs_improved.png')
    template = Path(__file__).with_name('d01_cracksam_review.html').read_text()
    html = template.replace('__REVIEW_SUMMARY__',json.dumps(records))
    (p/'cracksam_review.html').write_text(html)
    previous = args.public/'full_crack_review.html'
    backup = args.public/'deepcrack_review.html'
    if not backup.exists():shutil.copy2(previous,backup)
    for name in ['cracksam_review.html','full_crack_review.html','overlay_review.html']:
        (args.public/name).write_text(html)
    (p/'asset_checks.json').write_text(json.dumps(checks,indent=2))
    print('Published all six paired comparisons, raw/refined/removed layers; no accuracy claim.')


if __name__=='__main__':
    main()
