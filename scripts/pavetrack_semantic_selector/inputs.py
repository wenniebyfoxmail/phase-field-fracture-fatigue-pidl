"""Allowlisted E017 snapshot and exact835 train-image identities, no pixel read."""
from pathlib import Path,PureWindowsPath

def images_from_manifest(manifest,locations,cfg,lock):
    images={}
    for row in manifest:
        im=row['image_id'];fields=['image_id','location','prepared_image','prepared_image_sha256','width','height'];value={k:row[k] for k in fields}
        path=PureWindowsPath(value['prepared_image']);root=PureWindowsPath(lock['source_image_root'])
        if path.parent!=root or path.name!=im or not (path.is_absolute() or Path(value['prepared_image']).is_absolute()) or '..' in path.parts:raise ValueError('train image path scope')
        if im not in locations or locations[im]!=value['location'] or value['location'] not in cfg['locations']:raise ValueError('train image location scope')
        h=value['prepared_image_sha256']
        if not isinstance(h,str) or len(h)!=64 or any(ch not in '0123456789abcdef' for ch in h):raise ValueError('image hash identity')
        if any(type(value[k]) is not int or value[k]<=0 for k in ['width','height']):raise ValueError('image dimensions')
        if im in images and images[im]!=value:raise ValueError('image conflicting identity')
        images[im]=value
    if set(images)!=set(locations) or len(images)!=lock['source_images'] or len(images)!=cfg['input_counts']['images']:raise ValueError('image coverage')
    return images

def load(path,run,cfg,lock,guard,core,legacy,prior):
    data=prior.load(path,run,cfg,lock,guard,core,legacy)
    manifest=core.read(data['snapshot']/lock['image_identity_member'])['rows']
    if len(manifest)!=len(data['candidates']):raise ValueError('image candidate alignment')
    for i,(m,row) in enumerate(zip(manifest,data['candidates'],strict=True)):
        if (row['index'],row['parent_id'],row['image_id'],row['location'])!=(i,m['source_parent_key'],m['image_id'],m['location']):raise ValueError('pixel candidate identity')
    data['manifest']=manifest;data['images']=images_from_manifest(manifest,data['image_locations'],cfg,lock)
    return data
