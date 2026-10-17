"""One explicitly pinned train-only pooled cache in addition to E017 allowlist."""
import shutil
from pathlib import Path
import numpy as np


def content_snapshot(run,cfg,lock,guard,core):
    pin=lock['content_cache'];path=Path(pin['path']);core.e12.checked(path,pin['sha256'],guard.check)
    if path.stat().st_size!=pin['bytes']:raise ValueError('content cache bytes')
    if pin['sha256']!=core.read(run/'input_snapshot'/pin['scoring_receipt_member'])['files']['pooled_features.npy']:raise ValueError('content scoring identity')
    dest=run/pin['copy_to_run'];dest.parent.mkdir(exist_ok=False);shutil.copyfile(path,dest);core.e12.checked(dest,pin['sha256'],guard.check)
    with dest.open('rb') as f:
        version=np.lib.format.read_magic(f)
        if version!=(1,0):raise ValueError('content NPY version')
        shape,fortran,dtype=np.lib.format.read_array_header_1_0(f)
    if list(shape)!=pin['shape'] or shape[1]!=cfg['content']['dimensions'] or fortran or dtype!=np.dtype('float32'):raise ValueError('content header')
    X=np.load(dest,mmap_mode='r',allow_pickle=False)
    if X.flags.writeable or not X.flags.c_contiguous or X.shape!=tuple(pin['shape']) or X.dtype!=np.dtype('float32'):raise ValueError('content mmap')
    return X


def load(path,run,cfg,lock,guard,core,legacy,prior):
    core.require_producer(cfg);data=prior.load(path,run,cfg,lock,guard,core,legacy)
    identity=core.read(run/'input_snapshot'/lock['content_cache']['row_identity_member'])['rows']
    if len(identity)!=lock['content_cache']['shape'][0] or [r['source_parent_key'] for r in identity]!=[r['parent_id'] for r in data['candidates']] or any(row['index']!=i or row['image_id']!=identity[i]['image_id'] or row['location']!=identity[i]['location'] for i,row in enumerate(data['candidates'])):raise ValueError('content row-to-candidate identity')
    data['content']=content_snapshot(run,cfg,lock,guard,core);return data
