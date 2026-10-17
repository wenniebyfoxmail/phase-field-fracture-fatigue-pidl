"""Explicit OCR/compact-component cleanup; preserve raw masks and all removals."""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import torch


def rgba(mask, color):
    result = np.zeros((*mask.shape,4),np.uint8)
    result[mask] = [*color,115]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--cached-ocr',type=Path)
    ap.add_argument('--text-proposals-only',action='store_true')
    ap.add_argument('--output',type=Path)
    ap.add_argument('--first-frame-text-prior',action='store_true')
    args = ap.parse_args()
    root = args.root
    if args.cached_ocr is None:
        sys.path.insert(0,str(root/'ocr_deps'))
        import easyocr
        torch.set_num_threads(4)
        torch.cuda.set_per_process_memory_fraction(0.15,0)
        reader = easyocr.Reader(['en'],gpu=True,model_storage_directory=str(root/'ocr_models'),
                                user_network_directory=str(root/'ocr_user'),verbose=False)
    out = args.output or root/'refined'
    out.mkdir(exist_ok=True)
    cases = json.loads((root/'source_manifest.json').read_text())
    records = []
    first_cases = {}
    for item in sorted(cases,key=lambda c:int(c['id'].split('_t')[1])):
        first_cases.setdefault(item['id'].split('_t')[0],item['id'])
    with torch.inference_mode():
        for case in cases:
            began = time.time()
            name = case['id']
            rgb = np.array(Image.open(root/'inputs'/case['file']).convert('RGB'))
            raw = np.array(Image.open(root/'outputs'/f'{name}_mask.png')) > 0
            text_mask = np.zeros(raw.shape,np.uint8)
            ocr = []
            if args.cached_ocr is not None:
                cached=json.loads((args.cached_ocr/f'{name}_cleanup.json').read_text())['ocr']
                detections=[(o['polygon'],o['text'],o['confidence'],name) for o in cached]
                first=first_cases[name.split('_t')[0]]
                if args.first_frame_text_prior and first!=name:
                    prior=json.loads((args.cached_ocr/f'{first}_cleanup.json').read_text())['ocr']
                    detections += [(o['polygon'],o['text'],o['confidence'],first) for o in prior]
            else:
                detections=[(*d,name) for d in reader.readtext(rgb,canvas_size=2560,mag_ratio=1,paragraph=False,detail=1)]
            for poly,text,confidence,source_case in detections:
                letters = re.sub('[^A-Za-z]','',text)
                symbols = re.sub('[^A-Za-z0-9]','',text)
                poly = np.rint(poly).astype(np.int32)
                sides = np.ptp(poly,axis=0)+1
                aspect = float(sides.min()/sides.max())
                exclude = bool(letters) and sides[1]<=600 and aspect>=0.12 and (
                    (len(symbols)>=2 and confidence>=0.15) or
                    (len(symbols)==1 and confidence>=0.65 and aspect>=0.15))
                if args.text_proposals_only:
                    exclude = sides[1]<=600 and aspect>=0.12
                exclude = bool(exclude)
                ocr.append({'polygon':poly.tolist(),'text':text,'confidence':float(confidence),
                            'excluded':exclude,'bbox_short_long':aspect,'source_case':source_case})
                if exclude: cv2.fillPoly(text_mask,[poly],1)
            text_mask = cv2.dilate(text_mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))>0
            candidate = raw & ~text_mask
            grouped = cv2.dilate(candidate.astype(np.uint8),
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
            n,labels,stats,_ = cv2.connectedComponentsWithStats(grouped,connectivity=8)
            refined = np.zeros(raw.shape,bool)
            components = []
            for label in range(1,n):
                x,y,w,h,_ = [int(v) for v in stats[label]]
                support = (labels[y:y+h,x:x+w]==label) & candidate[y:y+h,x:x+w]
                yy,xx = np.where(support)
                area = len(xx)
                if not area: continue
                dx,dy = xx-xx.mean(),yy-yy.mean()
                cov = np.array([[np.mean(dx*dx),np.mean(dx*dy)],
                                [np.mean(dx*dy),np.mean(dy*dy)]])
                eig = np.maximum(np.linalg.eigvalsh(cov),0)
                axis_ratio = float(np.sqrt((eig[1]+1)/(eig[0]+1)))
                span = int(max(np.ptp(xx)+1,np.ptp(yy)+1))
                fill = float(area/((np.ptp(xx)+1)*(np.ptp(yy)+1)))
                reason = 'retain'
                if area<12: reason='tiny_group'
                elif span<120 and axis_ratio<3: reason='small_compact_group'
                elif span<360 and axis_ratio<1.8 and fill>0.25: reason='compact_group'
                if reason=='retain': refined[y:y+h,x:x+w] |= support
                components.append({'group':label,'bbox':[x,y,w,h],'area':area,'span':span,
                                   'axis_ratio':axis_ratio,'fill_fraction':fill,'decision':reason})
            removed = raw & ~refined
            assert not np.any(refined & ~raw)
            Image.fromarray(refined.astype(np.uint8)*255).save(out/f'{name}_mask.png')
            Image.fromarray(rgba(refined,[0,225,160])).save(out/f'{name}_overlay.png')
            Image.fromarray(rgba(removed,[255,155,45])).save(out/f'{name}_removed_overlay.png')
            Image.fromarray(text_mask.astype(np.uint8)*255).save(out/f'{name}_text_regions.png')
            (out/f'{name}_cleanup.json').write_text(json.dumps({'ocr':ocr,'components':components},indent=2))
            record = {'id':name,'raw_pixels':int(raw.sum()),'retained_pixels':int(refined.sum()),
                      'text_removed_pixels':int((raw & text_mask).sum()),
                      'component_removed_pixels':int((removed & ~text_mask).sum()),
                      'ocr_excluded':[o['text'] for o in ocr if o['excluded']],
                      'seconds':time.time()-began}
            records.append(record)
            (out/'summary.json').write_text(json.dumps(records,indent=2))
            print('DONE',record,flush=True)


if __name__=='__main__':
    main()
