"""Offline audit of existing masks and saved D01 visible-edge annotations."""
import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image,ImageOps,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def mapped_points(center, normal, h, x, y):
    normal=np.asarray(normal)
    tangent=np.array([-normal[1],normal[0]])
    points=np.asarray(center)+x[None,:,None]*normal+y[:,None,None]*tangent
    hp=np.concatenate([points,np.ones((*points.shape[:2],1))],axis=2)@np.linalg.inv(h).T
    xy=hp[...,:2]/hp[...,2:]
    return xy[...,0].astype(np.float32),xy[...,1].astype(np.float32)


def intervals(x,p):
    active=p>=0.5
    starts=np.flatnonzero(active & ~np.r_[False,active[:-1]])
    ends=np.flatnonzero(active & ~np.r_[active[1:],False])
    result=[]
    for a,b in zip(starts,ends):
        left=x[a] if a==0 else x[a-1]+(0.5-p[a-1])/(p[a]-p[a-1])*(x[a]-x[a-1])
        right=x[b] if b==len(x)-1 else x[b]+(0.5-p[b])/(p[b+1]-p[b])*(x[b+1]-x[b])
        result.append((float(left),float(right),bool(a==0 or b==len(x)-1)))
    return result


def stats(values):
    a=np.array([v for v in values if v is not None],float)
    return {'n':len(a),'mean':float(a.mean()) if len(a) else None,
            'median':float(np.median(a)) if len(a) else None,
            'max':float(a.max()) if len(a) else None}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.project;out=a.output;out.mkdir(exist_ok=True)
    exp=root/'local_archive/experiments'
    preview=exp/'S03-E016-D01/full_mask_preview_cracksam_20261017'
    packet=exp/'S03-E016-D01/runs/S03-E016-D01-R002'
    lock=json.loads((exp/'S03-E015-D01/runs/S03-E015-D01-R000/first_frame_transects_lock.json').read_text())
    human=json.loads((exp/'S03-E016-D01/annotation_review_20261017_v2/annotations_original.json').read_text())['annotations']
    key=json.loads((packet/'private_blind_key.json').read_text())
    manifest=json.loads((preview/'source_manifest.json').read_text())
    sources={e['source']:e for e in manifest}
    loaded={}
    for e in manifest:
        rgb=Image.open(preview/'inputs'/e['file'])
        assert rgb.getexif().get(274,1)==1
        gray=np.asarray(ImageOps.exif_transpose(rgb).convert('L'),dtype=np.float32)
        mask=np.asarray(Image.open(preview/'refined_v3'/f"{e['id']}_mask.png"),dtype=np.float32)/255
        loaded[e['source']]=(gray,mask)
    data={b:np.load(exp/f'S03-E012-D01/runs/S03-E012-D01-R001/Beam{b}_stage_fields.npz') for b in [4,5,6]}
    rows=[];views={};seen=set();unique=[];detail=[]
    for k in sorted(key,key=lambda r:r['task_id']):
        beam=k['beam'];geo=lock['beams'][str(beam)]
        native=geo['native_shape'];working=geo['working_shape']
        sy=working[0]/native[0];sx=working[1]/native[1]
        t=np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])
        h=np.linalg.inv(t)@data[beam]['homographies'][k['stage_index']]@t
        transect=next(v for v in geo['transects'] if v['id']==k['transect_id'])
        xy=mapped_points(transect['center'],transect['normal'],h,np.arange(-60,61),np.arange(-24,25))
        gray,mask=loaded[k['source']]
        strip=cv2.remap(gray,*xy,cv2.INTER_LINEAR).astype(np.uint8)
        original=np.array(Image.open(packet/'blind_packet'/f"{k['task_id']}.png"))
        assert np.array_equal(strip,original),k['task_id']+' strip mapping mismatch'
        occupancy=cv2.remap(mask,*xy,cv2.INTER_LINEAR)
        dense_x=np.arange(0,120.001,0.25)
        dense_xy=mapped_points(transect['center'],transect['normal'],h,dense_x-60,np.array([0]))
        p=cv2.remap(mask,*dense_xy,cv2.INTER_LINEAR)[0]
        runs=intervals(dense_x,p)
        candidates=[r for r in runs if r[0]<=75 and r[1]>=45]
        status='ok' if len(candidates)==1 and not candidates[0][2] else (
            'miss' if not candidates else 'censored' if len(candidates)==1 else 'multiple_intervals')
        left,right=(candidates[0][:2] if status=='ok' else (None,None))
        ref=human[k['task_id']]
        scored=ref['quality']=='visible' and status=='ok'
        width=right-left if status=='ok' else None
        hw=ref['right']-ref['left'] if ref['quality']=='visible' else None
        row={'task':k['task_id'],'unique_index':k['unique_index'],'image':sources[k['source']]['id'],
             'beam':beam,'stage':k['stage_index'],'transect':k['transect_id'],'human_status':ref['quality'],
             'human_left':ref.get('left'),'human_right':ref.get('right'),'human_width':hw,
             'mask_status':status,'mask_left':left,'mask_right':right,'mask_width':width,
             'scored':scored,'width_difference':width-hw if scored else None,
             'left_difference':left-ref['left'] if scored else None,
             'right_difference':right-ref['right'] if scored else None,
             'all_runs':json.dumps(runs)}
        rows.append(row);views[k['task_id']]=(strip,occupancy)
        if k['unique_index'] not in seen:
            unique.append(row);seen.add(k['unique_index'])
        # Fixed endpoint diagnostic: beyond last locked transect in the original
        # first-frame path direction. No choice based on model errors.
        if k['transect_id']==12 and k['unique_index'] in seen and row not in detail:
            if any(v['image']==row['image'] for v in detail):continue
            tr=geo['transects'];direction=np.asarray(tr[-1]['center'])-np.asarray(tr[0]['center'])
            direction/=np.linalg.norm(direction)
            pos=np.asarray(tr[-1]['center'])+300*direction
            hp=np.linalg.inv(h)@np.r_[pos,1];pos=hp[:2]/hp[2]
            detail.append({'image':row['image'],'center':pos.tolist()})
    assert len(unique)==24 and sum(r['human_status']=='visible' for r in unique)==17
    with (out/'all_30_width_reference_checks.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    scored=[r for r in unique if r['scored']]
    summary={'source_images':6,'unique_transects':24,'human_visible_unique':17,
             'scored_unique':len(scored),'mask_status_counts':{s:sum(r['mask_status']==s for r in unique) for s in sorted({r['mask_status'] for r in unique})},
             'width_signed':stats(r['width_difference'] for r in scored),
             'width_absolute':stats(abs(r['width_difference']) for r in scored),
             'boundary_absolute':stats(abs(r[k]) for r in scored for k in ['left_difference','right_difference']),
             'per_beam':{},'mapping':'all30 reproduced grayscale strips byte-identical',
             'limits':'single-observer endpoint agreement, not full-mask accuracy, physical widths or forecasts'}
    for b in [4,5,6]:
        rs=[r for r in scored if r['beam']==b]
        summary['per_beam'][b]={'scored':len(rs),'width_absolute':stats(abs(r['width_difference']) for r in rs),'width_signed':stats(r['width_difference'] for r in rs)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    # Every unique strip, fixed order and actual mask sampling, not a new mask.
    ordered=sorted(unique,key=lambda r:(r['beam'],r['stage'],r['transect']))
    fig,axs=plt.subplots(12,2,figsize=(13,18),layout='constrained')
    for r,ax in zip(ordered,axs.flat):
        strip,occ=views[r['task']];ax.imshow(strip,cmap='gray',vmin=0,vmax=255)
        layer=np.zeros((*occ.shape,4));layer[occ>=0.5]=[0,0.75,0.5,0.4];ax.imshow(layer)
        ax.axhline(24,color='white',lw=.5,ls=':')
        if r['human_status']=='visible':ax.plot([r['human_left'],r['human_right']],[24,24],'o',color='#CC79A7',mec='white',mew=.4,ms=4)
        if r['mask_status']=='ok':ax.plot([r['mask_left'],r['mask_right']],[24,24],'x',color='#E69F00',ms=5)
        diff=f" | delta={r['width_difference']:+.1f}px" if r['scored'] else ''
        ax.set_title(f"{r['image']} T{r['transect']} | {r['human_status']} / {r['mask_status']}"+diff,fontsize=9)
        ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('All 24 unique D01 strips | green: saved mask | pink: saved human edges | orange: model crossings\nCentral-row visible-edge comparison only; uncertain cases unscored; no threshold fitting',fontsize=11)
    fig.savefig(out/'F01_all_24_reference_strips.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for b,color in [(4,'#0072B2'),(5,'#D55E00'),(6,'#009E73')]:
        rs=[r for r in scored if r['beam']==b]
        axs[0].scatter([r['human_width'] for r in rs],[r['mask_width'] for r in rs],label=f'Beam {b} (n={len(rs)})',color=color)
    vals=[v for r in scored for v in [r['human_width'],r['mask_width']]]
    mx=max(vals)+2;axs[0].plot([0,mx],[0,mx],color='.5',lw=.8);axs[0].set(xlim=(0,mx),ylim=(0,mx),xlabel='Human visible-edge width (strip px)',ylabel='Mask crossing width (strip px)');axs[0].legend()
    axs[1].axhline(0,color='.5',lw=.8);axs[1].bar(range(len(scored)),[r['width_difference'] for r in scored],color='#0072B2')
    axs[1].set(xticks=range(len(scored)),xticklabels=[r['task'][5:] for r in scored],xlabel='Unique scored task',ylabel='Mask minus human width (strip px)')
    fig.suptitle('D01 CrackSAM reference agreement | 3 beams, one observer/session | development only')
    fig.savefig(out/'F02_width_reference_agreement.png',dpi=160);plt.close(fig)
    # Native-pixel source crops; output zoomed only for display.
    canvas=Image.new('RGB',(1800,620*6),'white');draw=ImageDraw.Draw(canvas)
    for i,d in enumerate(sorted(detail,key=lambda r:r['image'])):
        e=next(e for e in manifest if e['id']==d['image']);cx,cy=d['center'];box=(round(cx-400),round(cy-400),round(cx+400),round(cy+400))
        im=Image.open(preview/'inputs'/e['file']).convert('RGBA');ov=Image.open(preview/'refined_v3'/f"{e['id']}_overlay.png").convert('RGBA');rm=Image.open(preview/'refined_v3'/f"{e['id']}_removed_overlay.png").convert('RGBA')
        for col,(v,title) in enumerate([(im,'Original'),(Image.alpha_composite(im,ov),'Refined'),(Image.alpha_composite(im,rm),'Removed pixels')]):
            tile=v.crop(box).convert('RGB').resize((600,600))
            canvas.paste(tile,(col*600,i*620+20));draw.text((col*600+5,i*620+4),d['image']+' | '+title,fill='black')
    canvas.save(out/'F03_all_six_lower_end_checks.png')
    (out/'detail_crop_rule.json').write_text(json.dumps({'rule':'last locked transect +300px along first-frame path direction;800px square; transformed by archived homography','cases':detail},indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
