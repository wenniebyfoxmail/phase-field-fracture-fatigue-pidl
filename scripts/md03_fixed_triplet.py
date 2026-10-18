"""E049: source/coordinate adapter, frozen E045/E037 observer; no retuning."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageOps, ExifTags

from md01_cached_stage_forecast import ROOT, WORK, sha, save, forecast
from md01_geometric_guide_transfer import transfer
from md01_frame_geometry import extract, metrics
from md01_support_mass_forecast import observe, predict

BASE = ROOT/'local_archive/experiments/S03-E049-MD03'
META = ROOT/'local_archive/open_data/s03_independent_sequence_metadata_20261018'
PROTOCOL = WORK/'docs/research/S03/S03-E049-MD03/experiment.md'


def now(): return datetime.now(timezone.utc).isoformat()


def guard(lock):
    for p, digest in lock['protected'].items():
        if sha(p) != digest: raise ValueError('Protected input changed: '+p)


def prepare():
    out=BASE/'R000_selection';out.mkdir(parents=True,exist_ok=True)
    assert not (out/'selection_lock.json').exists(), 'Do not overwrite selection'
    items=json.loads((META/'md03_192_files.json').read_text())
    items.sort(key=lambda r:int(re.search(r'\d+',r['filename']).group()))
    n=len(items);ranks=[(n+1)//2,(3*n+3)//4,n]
    assert n==173 and ranks==[87,130,173]
    frames=[]
    for rank in ranks:
        f=items[rank-1]
        frames.append(dict(rank=rank,index=int(re.search(r'\d+',f['filename']).group()),
                           filename=f['filename'],id=f['id'],bytes=f['size'],
                           sha256=f['content_details']['sha256_hash'],
                           url=f['content_details']['download_url'],
                           source=str(BASE/'source'/f['filename'])))
    old=ROOT/'local_archive/experiments/S03-E048-MD01/runs'
    oldlock=json.loads((old/'S03-E048-MD01-R000/input_lock.json').read_text())
    protected=dict(oldlock['protected_inputs'])
    for p in old.rglob('*'):
        if p.is_file():protected[str(p)]=sha(p)
    for p in [PROTOCOL,META/'md03_192_files.json']+[
        WORK/'scripts'/name for name in ('md01_geometric_guide_transfer.py',
        'md01_frame_geometry.py','md01_cached_stage_forecast.py','md01_support_mass_forecast.py')]:
        protected[str(p)]=sha(p)
    lock=dict(frames=frames,protected=protected,prepared_utc=now(),adapter_prepare_sha256=sha(__file__),
              role='fixed file-order diagnostic; capture ordering checked separately',
              beam='19.2%',target_decoded=False,source_limit_bytes=150000000)
    guard(lock);save(out/'selection_lock.json',lock)
    print(json.dumps(dict(frames=frames,protected_files=len(protected)),indent=2))


def fetch(f):
    p=Path(f['source']);p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        req=urllib.request.Request(f['url'],headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=60) as response,p.open('xb') as out:
            while block:=response.read(1024*1024):out.write(block)
    if p.stat().st_size!=f['bytes'] or sha(p)!=f['sha256']:
        raise ValueError('Official source identity mismatch: '+str(p))
    return p


def read(f):
    p=Path(f['source'])
    if sha(p)!=f['sha256']:raise ValueError('Image hash mismatch')
    with Image.open(p) as im:
        tags={str(ExifTags.TAGS.get(k,k)):str(v) for k,v in im.getexif().items()
              if k in (256,257,258,259,262,271,272,274,306,36867,36868)}
        for ifdid in (34665,):
            try:
                tags.update({str(ExifTags.TAGS.get(k,k)):str(v) for k,v in im.getexif().get_ifd(ifdid).items()
                             if k in (36867,36868,37521,37522)})
            except (KeyError,TypeError):pass
        info=dict(filename=f['filename'],native_size=list(im.size),mode=im.mode,tags=tags,
                  frames=getattr(im,'n_frames',1),sha256=f['sha256'])
        native=np.asarray(ImageOps.exif_transpose(im))
        if im.mode!='I;16' or native.dtype!=np.uint16 or int(im.getexif()[258])!=16:
            raise ValueError('Unexpected new-source bit depth; no adaptive conversion allowed')
        gray=(native//257).astype(np.uint8)
        rgb=np.repeat(gray[:,:,None],3,axis=2)
        info['conversion']='uint16 // 257 -> uint8, fixed full code range, no image-adaptive stretch'
    info.update(oriented_size=[rgb.shape[1],rgb.shape[0]],rgb_min=int(rgb.min()),rgb_max=int(rgb.max()))
    return rgb,info


def histories():
    lock=json.loads((BASE/'R000_selection/selection_lock.json').read_text());guard(lock)
    out=BASE/'R001b_history_inspection';out.mkdir(exist_ok=False)
    rows=[]
    for f in lock['frames'][:2]:
        fetch(f);rgb,info=read(f);rows.append(info)
        preview=Image.fromarray(rgb);preview.thumbnail((1500,1000))
        preview.save(out/(Path(f['filename']).stem+'_preview.png'))
        (out/(Path(f['filename']).stem+'_preview.md')).write_text(
            '# Historical source preview\n\nQuestion: what is visible before ROI/prediction?\n'
            f'Source: {f["source"]}; SHA256{f["sha256"]}. E049 fixed history, never target.\n'
            'Single whole-source grayscale panel. Display-only thumbnail, not measurement resolution.\n'
            'Native5496x3670, uint16//257 fixed range; no contrast normalisation.\n'
            'No segmentation/accuracy/physical-width claim. Method: scripts/md03_fixed_triplet.py histories.\n')
    save(out/'source_metadata.json',rows);guard(lock)
    save(out/'receipt.json',dict(execution='succeeded',utc=now(),history_frames=2,
         target_downloaded=Path(lock['frames'][2]['source']).exists(),host=socket.gethostname()))
    print(json.dumps(rows,indent=2))


def measurement(rgb,cfg,out):
    x0,y0,x1,y1=cfg['roi'];band=cfg['band']
    assert 0<=x0<x1<=rgb.shape[1] and 0<=y0<y1<=rgb.shape[0]
    assert list(rgb.shape[:2][::-1])==cfg['oriented_size']
    crop=rgb[y0:y1,x0:x1]
    support,diag,eligible,path=transfer(crop,cfg['support'],cfg['roi'],band)
    mask,ex,safe=extract(crop,support,cfg['roi'])
    a,b,c,d=np.array(band)-np.array([x0,y0,x0,y0]);sl=np.s_[b:d,a:c]
    v,row=observe(mask[sl]);geo,traces,skel=metrics(mask,safe,cfg['roi'],band)
    assert not ex[sl].any() and not (mask&~eligible).any()
    if v['mass'] is not None:assert abs(v['area']-v['support']*v['mass'])<1e-8
    np.savez_compressed(out/'arrays.npz',roi_rgb=crop,mask=mask,excluded=ex,
          skeleton=skel,band_mask=mask[sl],band_rgb=crop[sl],row_mass=row,guide_path=path)
    result=dict(observation=v,geometry=geo,transfer=diag,
                area_is_observer_candidate_not_truth=True)
    save(out/'observation.json',result);save(out/'paths.json',traces)
    save(out/'transferred_support.json',support)
    return result


def consistency(first,later,cfg):
    x0,y0,x1,y1=cfg['roi'];ys=slice(y0,y1);xs=slice(x0,x1)
    def gray(rgb):return cv2.cvtColor(rgb[ys,xs],cv2.COLOR_RGB2GRAY)
    a,b=gray(first),gray(later)
    orb=cv2.ORB_create(nfeatures=2000)
    ka,da=orb.detectAndCompute(a,None);kb,db=orb.detectAndCompute(b,None)
    if da is None or db is None:return dict(available=False,reason='missing_features')
    matches=[m[0] for m in cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da,db,k=2)
             if len(m)==2 and m[0].distance<.75*m[1].distance]
    if len(matches)<6:return dict(available=False,reason='too_few_matches',matches=len(matches))
    cv2.setRNGSeed(20261018)
    mat,inside=cv2.estimateAffinePartial2D(np.float32([ka[m.queryIdx].pt for m in matches]),
          np.float32([kb[m.trainIdx].pt for m in matches]),method=cv2.RANSAC,ransacReprojThreshold=2)
    if mat is None:return dict(available=False,reason='affine_missing')
    residual=np.linalg.norm(np.float32([ka[m.queryIdx].pt for m in matches])@mat[:,:2].T+mat[:,2]-
                            np.float32([kb[m.trainIdx].pt for m in matches]),axis=1)
    return dict(available=True,matches=len(matches),inliers=int(inside.sum()),
        affine_roi_pixels=mat.tolist(),scale=float(np.hypot(mat[0,0],mat[1,0])),
        rotation_deg=float(np.degrees(np.arctan2(mat[1,0],mat[0,0]))),
        median_inlier_residual_px=float(np.median(residual[inside.ravel().astype(bool)])),
        diagnostic_only=True,no_warp_applied=True,material_correspondence=False)


def compute_history():
    lockpath=BASE/'R000_selection/selection_lock.json'
    lock=json.loads(lockpath.read_text());guard(lock)
    cp=BASE/'history_support.json';cfg=json.loads(cp.read_text())
    assert not Path(lock['frames'][2]['source']).exists(), 'Target already acquired'
    out=BASE/'R002_history';out.mkdir(exist_ok=False)
    start=time.monotonic();rows=[];rgbs=[];infos=[]
    for f in lock['frames'][:2]:
        rgb,info=read(f);rgbs.append(rgb);infos.append(info)
        p=out/str(f['index']);p.mkdir();rows.append(measurement(rgb,cfg,p))
    a,b,t=[f['index'] for f in lock['frames']]
    pred=predict(rows[0]['observation'],rows[1]['observation'],a,b,t,cfg['band'][2]-cfg['band'][0])
    assets={str(p):sha(p) for p in out.rglob('*') if p.is_file()}
    saved=dict(saved_utc=now(),selection_sha256=sha(lockpath),configuration_sha256=sha(cp),
          adapter_sha256=sha(__file__),history_assets=assets,history_indices=[a,b],target_index=t,
          history_observations=rows,predictions=pred,source_metadata=infos,
          equal_file_index_gaps=[b-a,t-b],target_downloaded=False,
          history_view_diagnostic=consistency(rgbs[0],rgbs[1],cfg))
    guard(lock)
    save(out/'predictions_before_target.json',saved)
    save(out/'receipt.json',dict(execution='succeeded',retrieval='verified_local',host=socket.gethostname(),
        command=sys.argv,utc=now(),wall_seconds=time.monotonic()-start,
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
        dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
        adapter_sha256=sha(__file__),prediction_sha256=sha(out/'predictions_before_target.json'),
        protected_files=len(lock['protected'])))
    assert time.monotonic()-start<120
    print(json.dumps(dict(observations=[r['observation'] for r in rows],prediction=pred,
                         source_metadata=infos),indent=2))


def compute_target():
    lockpath=BASE/'R000_selection/selection_lock.json';lock=json.loads(lockpath.read_text());guard(lock)
    cp=BASE/'history_support.json';cfg=json.loads(cp.read_text())
    pp=BASE/'R002_history/predictions_before_target.json';ph=sha(pp);saved=json.loads(pp.read_text())
    assert saved['selection_sha256']==sha(lockpath) and saved['configuration_sha256']==sha(cp)
    assert saved['adapter_sha256']==sha(__file__)
    assert all(sha(p)==h for p,h in saved['history_assets'].items())
    out=BASE/'R003_target';out.mkdir(exist_ok=False)
    save(out/'start_receipt.json',dict(started_utc=now(),prediction_sha256=ph,host=socket.gethostname(),
         target_previously_downloaded=Path(lock['frames'][2]['source']).exists(),adapter_sha256=sha(__file__),
         command=sys.argv,commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
         dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines()))
    netstart=time.monotonic();fetch(lock['frames'][2]);network_wall=time.monotonic()-netstart
    start=time.monotonic();target_decode_utc=now();rgb,info=read(lock['frames'][2])
    result=measurement(rgb,cfg,out);pred=saved['predictions'];target=result['observation']['area']
    errors={k:(abs(pred[k]-target) if pred[k] is not None else None)
            for k in ('persistence','secant','support_hold')}
    gains={k:(errors['persistence']-errors[k] if errors[k] is not None else None)
           for k in ('secant','support_hold')}
    historical,unused=read(lock['frames'][1]);view=consistency(historical,rgb,cfg)
    metadata=saved['source_metadata']+[info]
    ts=[i['tags'].get('DateTimeOriginal') for i in metadata]
    if all(ts):
        times=[datetime.strptime(s,'%Y:%m:%d %H:%M:%S') for s in ts]
        timing=dict(original_timestamps=ts,strictly_increasing=all(a<b for a,b in zip(times,times[1:])),
                    gaps_seconds=[(b-a).total_seconds() for a,b in zip(times,times[1:])],
                    origin='embedded DateTimeOriginal; camera clock, not load synchronisation')
    else:timing=dict(original_timestamps=ts,strictly_increasing=None,reason='capture timestamps unavailable')
    summary=dict(execution='succeeded',scope='one beam, one fixed file-index continuation query',
        target_index=lock['frames'][2]['index'],target_observation=result,predictions=pred,
        absolute_area_errors=errors,gains_vs_hold=gains,primary='area_secant_vs_persistence',
        paired_calculable_coverage='1/1',conditional_arm_available=pred['support_hold'] is not None,
        prediction_saved_utc=saved['saved_utc'],target_decode_started_utc=target_decode_utc,
        predictions_sha256=ph,source_metadata=metadata,timing=timing,target_view_diagnostic=view,
        network_wall_seconds=network_wall,analysis_wall_seconds=time.monotonic()-start,
        old_halfdepth_masks_scores_unchanged=True,protected_files=len(lock['protected']))
    assert sha(pp)==ph and all(sha(p)==h for p,h in saved['history_assets'].items())
    assert saved['saved_utc']<target_decode_utc;guard(lock)
    save(out/'summary.json',summary);save(out/'receipt.json',dict(ended_utc=now(),**summary))
    assert time.monotonic()-start<120
    print(json.dumps(summary,indent=2))


def tests():
    # Adapters leave the native frozen extractor and predictor arithmetic intact.
    from md01_geometric_guide_transfer import tests as gt
    from md01_support_mass_forecast import tests as ot
    gt();ot()
    assert forecast(89,132,175,100,150)['secant']==200
    assert [(n+1)//2 for n in [173]]==[87]
    print('Frozen extraction/DP, factorisation and equal-file-index arithmetic tested.')


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('prepare','histories','history','target','self-test'))
    a=p.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='histories':histories()
    elif a.phase=='history':compute_history()
    elif a.phase=='target':compute_target()
    else:tests()


if __name__=='__main__':main()
