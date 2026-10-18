"""Exact old bank plus private scoped polygon attachment; no source pixels/model."""
import importlib.util,shutil,math
from pathlib import Path
s=importlib.util.spec_from_file_location('e023_old_inputs',Path(__file__).resolve().parent.parent/'pavetrack_semantic_selector/inputs.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
images_from_manifest=old.images_from_manifest

def validate_annotations(payload,images,expected_rows):
    rows=payload['rows'];by={im:[] for im in images};seen=set()
    if len(rows)!=expected_rows:raise ValueError('annotation count')
    for row in rows:
        im=row['image_id'];ordinal=row['workbook_row']
        if im not in images or ordinal in seen:raise ValueError('annotation image/row identity')
        seen.add(ordinal);rec=images[im]
        if any(row[k]!=rec[k] for k in ['location','width','height']) or row['category'] not in ['Alligator Crack','Transverse Crack','Pothole','Patch']:raise ValueError('annotation scope/dimensions/class')
        pts=row['polygon'];b=row['box_xyxy']
        if len(pts)<3 or len(b)!=4 or not all(math.isfinite(v) for v in b) or not 0<=b[0]<b[2]<=rec['width'] or not 0<=b[1]<b[3]<=rec['height']:raise ValueError('annotation geometry')
        if not all(len(p)==2 and all(math.isfinite(v) for v in p) and 0<=p[0]<=rec['width'] and 0<=p[1]<=rec['height'] for p in pts):raise ValueError('polygon finite/bounds')
        area=abs(sum(pts[j][0]*pts[(j+1)%len(pts)][1]-pts[(j+1)%len(pts)][0]*pts[j][1] for j in range(len(pts))))/2
        if area<=0:raise ValueError('polygon zero area')
        by[im].append(row)
    if any(not v for v in by.values()):raise ValueError('annotation image coverage')
    return by

def load(path,run,cfg,lock,guard,core,legacy,prior):
    data=old.load(path,run,cfg,lock,guard,core,legacy,prior)
    source=Path(lock['annotation_snapshot']);core.e12.checked(source,lock['annotation_snapshot_sha256'],guard.check)
    dest=run/'input_snapshot/train_polygons.json';shutil.copyfile(source,dest);core.e12.checked(dest,lock['annotation_snapshot_sha256'],guard.check)
    data['annotations']=validate_annotations(core.read(dest),data['images'],lock['annotation_snapshot_rows'])
    return data
