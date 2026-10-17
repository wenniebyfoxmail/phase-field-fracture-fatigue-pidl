"""Exploratory support-qualified measurements; never edits input masks."""
import argparse, csv, hashlib, json, math, shutil
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def polygon(shape, points):
    h,w=shape; im=Image.new('1',(w,h)); ImageDraw.Draw(im).polygon([(round(x*w),round(y*h)) for x,y in points],fill=1)
    return np.asarray(im,dtype=bool)


def graph(skeleton):
    # Suppress diagonal shortcut triangles when a cardinal intermediate exists.
    points=set(map(tuple,np.argwhere(skeleton))); adj={p:[] for p in points}
    for y,x in points:
        for dy,dx in ((0,1),(1,0),(1,1),(1,-1)):
            q=(y+dy,x+dx)
            if q not in points: continue
            if dy and dx and ((y,x+dx) in points or (y+dy,x) in points): continue
            adj[y,x].append(q); adj[q].append((y,x))
    return adj


def paths(adj):
    visited=set(); output=[]
    starts=[p for p in adj if len(adj[p])!=2]+sorted(adj)
    for p in starts:
        for q in adj[p]:
            key=tuple(sorted((p,q)))
            if key in visited: continue
            chain=[p,q]; visited.add(key); prev,cur=p,q
            while len(adj[cur])==2:
                nxt=next(t for t in adj[cur] if t!=prev)
                key=tuple(sorted((cur,nxt)))
                if key in visited: break
                visited.add(key); chain.append(nxt); prev,cur=cur,nxt
            output.append(chain)
    return output


def length(chain):
    return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(chain,chain[1:]))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    base=a.project/'local_archive/experiments/S03-E016-D01'; src=base/'full_mask_preview_cracksam_20261017';out=a.output
    out.mkdir(exist_ok=False,parents=True)
    hashes=json.loads((src/'final_cleanup_hashes.json').read_text())
    assert all(digest(src/p)==h for p,h in hashes.items())
    diag5=[(.52,.76),(.57,.61),(.68,.40),(.85,.25),(.90,.29),(.76,.45),(.68,.63),(.62,.76)]
    diag6=[(.52,.74),(.57,.62),(.70,.49),(.73,.34),(.87,.23),(.91,.26),(.79,.38),(.75,.53),(.64,.64),(.59,.75)]
    corridors={4:[[ (.82,.73),(.82,.48),(.87,.29),(.94,.25),(.94,.38),(.89,.52),(.88,.73)]],
               5:[diag5,[(.85,.35),(.91,.33),(.91,.74),(.85,.74)]],
               6:[diag6,[(.665,.52),(.72,.51),(.73,.77),(.665,.77)]]}
    rois={4:[(.065,.17),(.945,.21),(.945,.77),(.065,.75)],5:[(.085,.17),(.95,.21),(.95,.77),(.085,.75)],6:[(0,.065),(1,.10),(1,.80),(0,.80)]}
    contract={'kind':'exploration','question':'What area and visible segment lengths can the six fixed masks support, with explicit uncertainty exclusions?',
      'baseline':'all frozen mask pixels; existing 17 unique human visible-width references reused',
      'resource_cap':'six saved photographs and masks, local CPU analysis only, no new images, inference, training or forecasts',
      'target':'image-plane visible opening support; operationally clear does not imply boundary-accurate or complete',
      'source_mask':'refined_v3 unchanged; no filling, threshold changes or pruning applied to source',
      'coarse_region_selection':'conservative polygons marked from current full-frame visual inspection; shared within each beam, no outcome-based tuning',
      'specimen_interior_polygons_normalized':rois,'review_clear_corridors_normalized':corridors,
      'clear_requirements':{'inside_specimen_and_review_corridor':True,'centerline_diameter_at_least_native_px':4,'centerline_model_score_at_least':.8,'distance_from_skeleton_endpoint_or_junction_at_least_native_px':12,'minimum_supported_segment_length_native_px':20},
      'threshold_meaning':'conservative operational screening choices, not calibrated probabilities or physical detection limits; not optimized on results',
      'area':'full frozen mask pixels assigned to eligible centerline supports by nearest-skeleton partition, image px^2; no claim of true aperture area',
      'length':'skeleton of original frozen mask, 8-connected graph with diagonal shortcuts suppressed; only edges within eligible segments; no bridging gaps; image px',
      'width':'reuse frozen reference comparison, strip-coordinate px; no pooled bias subtraction',
      'unobserved':'missed micro-cracks remain unknown, not zero; no finite upper bound on missing network supplied',
      'uncertainty_labels':'screening flags, not confidence intervals; probabilities are uncalibrated model scores',
      'sanity':['source hashes unchanged','eligible and uncertain exactly partition frozen mask','graph edge length conservation','saved image coordinates native'],
      'next_test':'review eligibility overlays; then define common spatial support and observation error before any longitudinal forecast'}
    (out/'pilot_contract.json').write_text(json.dumps(contract,indent=2))
    rows=[];segments=[];fig,axes=plt.subplots(3,2,figsize=(15,13)); public=a.project/'local_archive/experiments/S03-E016-D01/runs/S03-E016-D01-R002/blind_packet';assets=public/'pilot_assets';assets.mkdir(exist_ok=True)
    for ax,p in zip(axes.flat,sorted((src/'inputs').glob('*.jpg'))):
        case=p.stem;b=int(case[4]);mask=np.asarray(Image.open(src/'refined_v3'/f'{case}_mask.png'))>0
        score=np.asarray(Image.open(src/'outputs'/f'{case}_probability16.png'),dtype=np.float32)/65535
        roi=polygon(mask.shape,rois[b]);corr=np.zeros_like(mask)
        for poly in corridors[b]:corr|=polygon(mask.shape,poly)
        sk=skeletonize(mask);adj=graph(sk); radius=ndi.distance_transform_edt(mask)
        special=np.zeros_like(mask)
        for point,neighbors in adj.items():
            if len(neighbors)!=2:special[point]=True
        near_special=ndi.distance_transform_edt(~special)<12
        reasons=np.zeros(mask.shape,np.uint8)
        reasons[sk &~(roi&corr)]|=1
        reasons[sk &(2*radius<4)]|=2
        reasons[sk &(score<.8)]|=4
        reasons[sk &near_special]|=8
        clear_sk=sk &(reasons==0)
        ca={p:[q for q in qs if clear_sk[q]] for p,qs in adj.items() if clear_sk[p]}
        eligible=np.zeros_like(sk);kept=[]
        for chain in paths(ca):
            ll=length(chain)
            if ll>=20:
                yy,xx=np.asarray(chain).T;eligible[yy,xx]=True;kept.append(chain)
        reasons[sk &~eligible &(reasons==0)]|=16
        # Nearest full-mask skeleton, not skeletonizing a cropped/eroded mask.
        nearest=ndi.distance_transform_edt(~sk,return_distances=False,return_indices=True)
        eligible_area=mask & eligible[nearest[0],nearest[1]] &roi&corr
        uncertain=mask &~eligible_area
        assert np.array_equal(eligible_area|uncertain,mask) and not np.any(eligible_area&uncertain)
        labels=np.zeros(mask.shape,np.uint8);labels[roi]=1;labels[uncertain]=3;labels[eligible_area]=2
        Image.fromarray(labels).save(out/f'{case}_eligibility_labels.png')
        Image.fromarray(reasons).save(out/f'{case}_skeleton_reason_bits.png')
        polyline=[]
        for n,ch in enumerate(kept,1):
            ll=length(ch);polyline.append({'id':n,'length_px':ll,'xy':[[int(x),int(y)] for y,x in ch]})
            segments.append({'image':case,'segment':n,'length_px':ll,'start_x':ch[0][1],'start_y':ch[0][0],'end_x':ch[-1][1],'end_y':ch[-1][0],'end_status':'support-censored; not a verified physical tip'})
        all_graph_len=sum(math.hypot(q[0]-pt[0],q[1]-pt[1]) for pt,qs in adj.items() for q in qs)/2
        eligible_len=sum(v['length_px'] for v in polyline)
        assert eligible_len<=all_graph_len+1e-6
        (out/f'{case}_segments.json').write_text(json.dumps(polyline))
        row={'image':case,'frozen_mask_area_px2':int(mask.sum()),'eligible_area_px2':int(eligible_area.sum()),'uncertain_mask_area_px2':int(uncertain.sum()),'eligible_mask_fraction':float(eligible_area.sum()/mask.sum()),'eligible_segments':len(kept),'eligible_length_px':eligible_len,'full_mask_skeleton_length_px_descriptive_only':all_graph_len,'missing_microcracks':'unresolved; not included or bounded'};rows.append(row)
        rgb=np.asarray(Image.open(p).convert('RGB'));vis=rgb.copy()
        vis[eligible_area]=(.4*rgb[eligible_area]+.6*np.array([0,220,255])).astype('uint8')
        vis[uncertain]=(.4*rgb[uncertain]+.6*np.array([255,165,0])).astype('uint8')
        # Display dilation only, to keep eligibility visible at full-frame fit scale.
        display=rgb.copy();c=ndi.binary_dilation(eligible_area,iterations=2);u=ndi.binary_dilation(uncertain,iterations=2)&~c
        display[c]=(.25*rgb[c]+.75*np.array([0,220,255])).astype('uint8');display[u]=(.25*rgb[u]+.75*np.array([255,165,0])).astype('uint8')
        thumb=Image.fromarray(display);thumb.thumbnail((1404,936));thumb.save(out/f'{case}_review.jpg',quality=94)
        Image.fromarray(vis).save(out/f'{case}_native_overlay.jpg',quality=94)
        shutil.copy2(out/f'{case}_review.jpg',assets/f'{case}.jpg');shutil.copy2(out/f'{case}_native_overlay.jpg',assets/f'{case}_native.jpg')
        ax.imshow(thumb);ax.set_title(f'{case}: eligible A={row["eligible_area_px2"]:,} px²; L={eligible_len:,.1f} px\n{len(kept)} supported segments; {100*row["eligible_mask_fraction"]:.1f}% mask area eligible',fontsize=10);ax.axis('off')
        print(json.dumps(row),flush=True)
        del nearest,score,radius,near_special
    fig.suptitle('D01 fixed-mask measurement pilot — cyan: eligible support; amber: uncertain / withheld\nDisplay marks thickened 2 px only; calculations use original pixels. Missing micro-cracks remain unobserved.',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'F01_six_image_eligibility.png',dpi=150);plt.close(fig)
    for name,data in [('eligible_measurements.csv',rows),('eligible_segments.csv',segments)]:
        with (out/name).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    audit=base/'measurement_readiness_audit_20261017'
    shutil.copy2(audit/'all_30_width_reference_checks.csv',out/'existing_width_reference_checks.csv')
    (out/'summary.json').write_text(json.dumps({'images':rows,'width_reference_source':str(audit),'width_recomputed':False,'physical_scale_available':False,'total_true_crack_geometry_available':False},indent=2))
    assert all(digest(src/p)==h for p,h in hashes.items())
    (out/'receipt.json').write_text(json.dumps({'completed_utc':datetime.now(timezone.utc).isoformat(),'source_immutable_files_checked_before_and_after':len(hashes),'masks_changed':False,'training':False,'new_inference':False,'MD01_touched':False,'script_sha256':digest(Path(__file__))},indent=2))
    cards=''.join(f'<section><h2>{r["image"]}</h2><p>Eligible area: {r["eligible_area_px2"]:,} px² · supported length: {r["eligible_length_px"]:,.1f} px · {r["eligible_segments"]} segments</p><a href="pilot_assets/{r["image"]}_native.jpg" target="_blank"><img src="pilot_assets/{r["image"]}.jpg"></a></section>' for r in rows)
    (public/'pilot_review.html').write_text('<!doctype html><meta charset="utf-8"><title>D01 fixed-mask measurement pilot</title><style>body{font:16px system-ui;margin:24px;background:#15191e;color:#eee}section{max-width:1404px;margin:32px auto}img{width:100%}p{max-width:1100px;line-height:1.5}a{color:#00dcff}</style><h1>D01: eligible geometry review</h1><p><b style="color:#00dcff">Cyan = eligible support.</b> <b style="color:orange">Amber = uncertain / withheld.</b> Eligibility is a conservative screening label, not a probability of correctness. Input masks are unchanged. Click an image for the native-resolution overlay. Preview marks are thickened 2 px for visibility; measurements use original pixels.</p><p>Fine missed cracks remain unobserved; these are partial pixel measurements, not complete area / length or physical units. Widths retain the existing positive bias diagnostic; no correction was applied.</p>'+cards)


if __name__=='__main__':main()
