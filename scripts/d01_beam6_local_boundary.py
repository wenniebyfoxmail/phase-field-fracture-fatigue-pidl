"""Local raw-image/mask diagnostic, 20/30kN only; saved masks/transforms untouched."""
from pathlib import Path
from datetime import datetime,timezone
import json,csv,hashlib,time,subprocess,socket
import numpy as np,cv2
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from audit_d01_measurement_readiness import mapped_points,intervals
from d01_section3_prediction import write_csv

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');BASE=ROOT/'local_archive/experiments/S03-E016-D01';EXT=BASE/'fourteen_stage_extension_20261017';OUT=BASE/'beam6_section3_local_20261018'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2))
def main():
    started=time.time();OUT.mkdir(exist_ok=False);source=EXT/'analysis/state_space_inputs.json';data=json.loads(source.read_text());seq=next(s for s in data['sequences'] if s['beam_id']==6);cut=next(t for t in seq['fixed_transect_geometry'] if t['id']==3);center=np.array(cut['center']);normal=np.array(cut['normal']);tangent=np.array([-normal[1],normal[0]]);obs=seq['observations'][1:3];hs=np.load(EXT/'analysis/beam6_transforms.npz')['current_native_to_reference_native'][1:3]
    protected=json.loads((BASE/'width_change_uncertainty_20261018/frozen_contract.json').read_text())['protected_files']
    manifest=json.loads((EXT/'source_manifest.json').read_text());paths=[EXT/'inputs'/f'{o["image"]}.jpg' for o in obs]
    for o,p in zip(obs,paths):assert sha(p)==next(e['sha256'] for e in manifest if e['id']==o['image']);protected[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in protected.items())
    contract={'scope':'Beam6 section3, saved 20/30kN images only, no new source or learned inference','question':'local residual displacement versus boundary/sampling fragility','fixed_before_computation':True,'texture_windows':'six predetermined windows, centers normal offsets +/-70 and tangent offsets -70/0/+70 reference px, half-size24; include all, record mask occupancy and texture quality','local_match':'normalized cross correlation raw grayscale, integer +/-4 reference-px search with quadratic subpixel peak, plus phase correlation diagnostic; no transform correction or width replacement','position_probe':'same saved mask operator on nine parallel transects at tangent offsets -2..2 reference px, step.5; original centerline remains authoritative','boundary_probe':'show raw grayscale profiles and frozen mask crossings; illustrative 20/50/80 percent local contrast crossings on centerline, do not relabel as visible-edge truth or substitute metric','boundary_contrast_definition':'shoulder=median raw gray x15..35 and85..105; dark level=median x55..65; select one interval overlapping x45..75; mark ambiguous if absent/multiple/censored','limits':'local texture motion mixes residual registration and actual deformation; separate crack sides, not independent samples or calibrated covariance. Illustrative grayscale threshold range is operator sensitivity, not uncertainty bound','stop':'one deterministic CPU diagnostic <2min, no training, registration changes, mask changes or prediction rerun; propose smallest operator fix only','protected_files':protected}
    dump(OUT/'frozen_contract.json',contract)
    rgbs=[np.asarray(Image.open(p).convert('RGB')) for p in paths];grays=[cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY) for rgb in rgbs];masks=[(np.asarray(Image.open(o['mask_source']))>0).astype('float32') for o in obs]
    def refsample(arr,h,xx,yy,flag=cv2.INTER_LINEAR):
        pts=np.stack([xx,yy,np.ones_like(xx)],-1)@np.linalg.inv(h).T
        return cv2.remap(arr,(pts[...,0]/pts[...,2]).astype('float32'),(pts[...,1]/pts[...,2]).astype('float32'),flag)
    def patch(arr,h,c,half):
        xx,yy=np.meshgrid(np.arange(-half,half)+c[0],np.arange(-half,half)+c[1]);return refsample(arr,h,xx,yy)
    texture=[]
    for side in [-1,1]:
        for along in [-70,0,70]:
            c=center+side*70*normal+along*tangent;p0=patch(grays[0],hs[0],c,24);p1=patch(grays[1],hs[1],c,24);search=patch(grays[1],hs[1],c,28);match=cv2.matchTemplate(search,p0,cv2.TM_CCOEFF_NORMED);_,peak,_,loc=cv2.minMaxLoc(match);ix,iy=loc;sub=[]
            for k,size in [(0,match.shape[1]),(1,match.shape[0])]:
                q=ix if k==0 else iy
                if q==0 or q==size-1:sub.append(0.);continue
                a,b,c0=(match[iy,q-1:q+2] if k==0 else match[q-1:q+2,ix]);den=float(a-2*b+c0);sub.append(float(.5*(a-c0)/den) if abs(den)>1e-8 else 0.)
            shift=np.array([ix-4+sub[0],iy-4+sub[1]]);win=cv2.createHanningWindow((48,48),cv2.CV_32F);phase,response=cv2.phaseCorrelate(p0.astype('float32'),p1.astype('float32'),win)
            occupancy=[float(patch(m,h,c,24).mean()) for m,h in zip(masks,hs)]
            texture.append({'side_normal':side,'along_reference_px':along,'center_x':c[0],'center_y':c[1],'dx_ref_px':shift[0],'dy_ref_px':shift[1],'normal_component_ref_px':float(shift@normal),'tangent_component_ref_px':float(shift@tangent),'ncc_zero':float(match[4,4]),'ncc_peak':peak,'peak_on_search_boundary':ix in [0,8] or iy in [0,8],'patch20_sd':float(p0.std()),'patch30_sd':float(p1.std()),'mask_fraction20':occupancy[0],'mask_fraction30':occupancy[1],'phase_dx_ref_px':phase[0],'phase_dy_ref_px':phase[1],'phase_response':response})
    write_csv(OUT/'texture_patch_displacements.csv',texture)
    dense=np.arange(0,120.001,.25);ys=np.arange(-2,2.001,.5);widths=[];profiles=[];boundary=[];crossings={};rawstrip=[];maskstrip=[]
    def selected(p):
        rr=[r for r in intervals(dense,p) if r[0]<=75 and r[1]>=45]
        if len(rr)!=1 or rr[0][2]:return None
        return rr[0]
    for frame,(o,h,gray,mask,rgb) in enumerate(zip(obs,hs,grays,masks,rgbs)):
        for y in ys:
            xy=mapped_points(center,normal,h,dense-60,np.array([y]));mp=cv2.remap(mask,*xy,cv2.INTER_LINEAR)[0];r=selected(mp);assert r is not None
            widths.append({'image':o['image'],'load_kN':o['metadata']['nominal_stage_load_kN'],'tangent_offset_ref_px':y,'left':r[0],'right':r[1],'width':r[1]-r[0],'saved_centerline':y==0})
            if y==0:
                assert abs((r[1]-r[0])-o['model_widths_strip_px'][0])<1e-9;crossings[frame]=r;g=cv2.remap(gray,*xy,cv2.INTER_LINEAR)[0].astype(float)
                for x,gg,mm in zip(dense,g,mp):profiles.append({'image':o['image'],'x_strip_px':x,'gray':gg,'mask_occupancy':mm})
                shoulder=float(np.median(g[((dense>=15)&(dense<=35))|((dense>=85)&(dense<=105))]));dark=float(np.median(g[(dense>=55)&(dense<=65)]))
                assert shoulder>dark
                for fraction in [.2,.5,.8]:
                    threshold=dark+fraction*(shoulder-dark);rr=selected((g<=threshold).astype('float32'))
                    boundary.append({'image':o['image'],'fraction_dark_to_shoulder':fraction,'threshold_gray':threshold,'shoulder_gray':shoulder,'dark_gray':dark,'left':rr[0] if rr else None,'right':rr[1] if rr else None,'width':rr[1]-rr[0] if rr else None,'status':'one_uncensored_interval' if rr else 'ambiguous','interpretation':'contrast-operator sensitivity only, not visible-edge reference'})
        xy=mapped_points(center,normal,h,np.arange(-60,60.001,.25),np.arange(-20,20.001,.25));rawstrip.append(cv2.remap(rgb,*xy,cv2.INTER_LINEAR));maskstrip.append(cv2.remap(mask,*xy,cv2.INTER_LINEAR))
    write_csv(OUT/'parallel_transect_widths.csv',widths);write_csv(OUT/'centerline_profiles.csv',profiles);write_csv(OUT/'contrast_operator_diagnostic.csv',boundary)
    paired=[]
    for y in ys:
        z=[next(r for r in widths if r['image']==o['image'] and r['tangent_offset_ref_px']==y) for o in obs];paired.append({'tangent_offset_ref_px':y,'width20':z[0]['width'],'width30':z[1]['width'],'change':z[1]['width']-z[0]['width']})
    write_csv(OUT/'paired_parallel_changes.csv',paired)
    side_summary={}
    for side in [-1,1]:
        z=[r for r in texture if r['side_normal']==side];side_summary[str(side)]={'median_dx':float(np.median([r['dx_ref_px'] for r in z])),'median_dy':float(np.median([r['dy_ref_px'] for r in z])),'normal_components':[r['normal_component_ref_px'] for r in z],'ncc_peaks':[r['ncc_peak'] for r in z]}
    summary={'saved_centerline_widths':[o['model_widths_strip_px'][0] for o in obs],'centerline_change':paired[4]['change'],'parallel_same_offset_change_range':[min(r['change'] for r in paired),max(r['change'] for r in paired)],'parallel_width20_range':[min(r['width20'] for r in paired),max(r['width20'] for r in paired)],'parallel_width30_range':[min(r['width30'] for r in paired),max(r['width30'] for r in paired)],'parallel_band_median_widths':[float(np.median([r['width20'] for r in paired])),float(np.median([r['width30'] for r in paired]))],'texture_side_diagnostics':side_summary,'no_registration_correction_applied':True,'no_width_replacement_applied':True}
    dump(OUT/'summary.json',summary)
    fig,axs=plt.subplots(2,2,figsize=(12,10));half=180;xx,yy=np.meshgrid(np.arange(-half,half+1)+center[0],np.arange(-half,half+1)+center[1])
    for i,(rgb,h,mask) in enumerate(zip(rgbs,hs,masks)):
        crop=refsample(rgb,h,xx,yy);mc=refsample(mask,h,xx,yy,cv2.INTER_NEAREST)>0;extent=(-half,half,half,-half);axs[0,i].imshow(crop,extent=extent);overlay=np.zeros((*mc.shape,4));overlay[mc]=[0,.8,1,.28];axs[0,i].imshow(overlay,extent=extent);line=np.array([-50,50])[:,None]*normal;axs[0,i].plot(line[:,0],line[:,1],color='#ff9f1c',lw=1.5)
        for r in texture:
            c=np.array([r['center_x'],r['center_y']])-center;rect=np.array([[-24,-24],[24,-24],[24,24],[-24,24]])+c;axs[0,i].add_patch(Polygon(rect,fill=False,edgecolor='#bb33cc' if r['side_normal']<0 else '#44cc55',lw=1));axs[0,i].text(c[0],c[1],f'{r["side_normal"]:+d}/{r["along_reference_px"]:+g}',color='white',fontsize=7,ha='center')
        axs[0,i].set(title=f'{20+10*i} kN: archived registration; cyan frozen mask',xlabel='Reference x offset (px)',ylabel='Reference y offset (px)')
        axs[1,i].imshow(rawstrip[i],extent=(0,120,20,-20),aspect='auto');ol=np.zeros((*maskstrip[i].shape,4));ol[maskstrip[i]>=.5]=[0,.8,1,.25];axs[1,i].imshow(ol,extent=(0,120,20,-20),aspect='auto');axs[1,i].axhline(0,color='#ff9f1c',lw=1);axs[1,i].axhspan(-2,2,color='#bb33cc',alpha=.10)
        for x in crossings[i][:2]:axs[1,i].plot(x,0,'o',color='#ff9f1c',markersize=5)
        axs[1,i].set(title=f'Raw pixels + unchanged mask; width {obs[i]["model_widths_strip_px"][0]:.3f}',xlabel='Strip coordinate x (px)',ylabel='Tangent offset (reference px)')
    fig.suptitle('Beam6 section3, 20–30 kN: local registration and boundary inspection\nOrange = saved centerline/crossings; patch boxes test texture, not crack matching',fontsize=12);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/'F01_local_mask_texture_overlays.png',dpi=160);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(12,8))
    for i in [0,1]:
        z=[r for r in profiles if r['image']==obs[i]['image']];ax=axs[0,i];ax.plot(dense,[r['gray'] for r in z],color='black',label='Raw grayscale centerline');ax.axvspan(crossings[i][0],crossings[i][1],color='#00b4d8',alpha=.2,label='Frozen mask interval')
        for r in boundary:
            if r['image']==obs[i]['image']:ax.axhline(r['threshold_gray'],ls=':',lw=1,label=f'{r["fraction_dark_to_shoulder"]:.0%} illustrative contrast')
        ax.set(xlim=(30,90),title=f'{20+10*i} kN boundary profile',xlabel='Strip coordinate x (px)',ylabel='Gray level');ax.legend(fontsize=7);ax.grid(alpha=.2)
    ax=axs[1,0]
    for i in [0,1]:
        z=[r for r in widths if r['image']==obs[i]['image']];ax.plot(ys,[r['width'] for r in z],'o-',label=f'{20+10*i} kN')
    ax.set(title='Parallel-line diagnostic; original y=0 retained',xlabel='Tangent offset (reference px)',ylabel='Mask width (strip px)');ax.legend();ax.grid(alpha=.2)
    ax=axs[1,1]
    for side,color in [(-1,'#bb33cc'),(1,'#44aa55')]:
        z=[r for r in texture if r['side_normal']==side];ax.scatter([r['dx_ref_px'] for r in z],[r['dy_ref_px'] for r in z],label=f'Crack side {side:+d}',color=color)
        for r in z:ax.annotate(f't={r["along_reference_px"]:+g}',(r['dx_ref_px'],r['dy_ref_px']),fontsize=7)
    ax.axhline(0,color='gray',lw=.7);ax.axvline(0,color='gray',lw=.7);ax.set(title='NCC texture displacement: residual + deformation',xlabel='dx (reference px)',ylabel='dy (reference px)');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Existing images: operator/position sensitivity, not calibrated uncertainty or new measurements for prediction',fontsize=10);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'F02_boundary_position_texture.png',dpi=160);plt.close(fig)
    assert all(sha(p)==h for p,h in protected.items())
    dump(OUT/'receipt.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'runtime_s':time.time()-started,'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent.parent,text=True).strip(),'script_sha256':sha(__file__),'host':socket.gethostname(),'protected_count':len(protected),'all_protected_files_unchanged':True,'masks_transforms_forecast_inputs_unchanged':True,'no_training':True,'no_new_prediction':True})
    print(json.dumps(summary,indent=2));print('CONTRAST',json.dumps(boundary,indent=2))
if __name__=='__main__':main()
