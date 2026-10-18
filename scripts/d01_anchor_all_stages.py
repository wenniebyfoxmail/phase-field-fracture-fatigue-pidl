"""All saved D01 section widths: fixed-anchor operator audit, not model fitting."""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,hashlib,subprocess,time,socket,math
import numpy as np,cv2
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_d01_measurement_readiness import mapped_points,intervals
from d01_section3_prediction import write_csv

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');BASE=ROOT/'local_archive/experiments/S03-E016-D01';EXT=BASE/'fourteen_stage_extension_20261017';OUT=BASE/'anchor_rule_all_stages_20261018'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2))
def main():
    start=time.time();OUT.mkdir(exist_ok=False);data=json.loads((EXT/'analysis/state_space_inputs.json').read_text());protected=json.loads((BASE/'beam6_section3_local_20261018_r002/frozen_contract.json').read_text())['protected_files'];manifest=json.loads((EXT/'source_manifest.json').read_text())
    for e in manifest:
        p=EXT/'inputs'/e['file'];assert sha(p)==e['sha256'];protected[str(p)]=sha(p)
    for b in (4,5,6):
        p=EXT/'analysis'/f'beam{b}_transforms.npz';protected[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in protected.items())
    contract={'stage':'bounded measurement-operator audit on exposed archive','D1':'Does fixed x60 retain the same crack interval across every exported stage/section? Check all; preserve missingness and display every flagged case.','next_D2':'Close width audit after this check; choose geometry observables from prediction objective, no automatic width tuning or model escalation.','scope':'14 saved stages, eight paired fixed beam-sections, 36 original centerline widths; nine offsets per width for324 context-line diagnostics; no new unexported sections','rule':'unique uncensored binary-mask interval containing immutable strip x60; if none/multiple/censored return uncertain; no search for largest/darkest/nearest interval, no recentering','extra_components':'preserve all intervals; flag separate intervals intersecting legacy [45,75] window, do not merge/delete; counts do not identify truth or false positives','comparison':'same frozen mapped centerline and quarter-pixel interpolation as saved; exact equality check, original broad-window rule replay, statuses and full runs exported','parallel_context':'offsets -2..2 reference tangent px step0.5; diagnostic only, no median replacement or confidence interval','ambiguity_visualization':'show all frame/section cases with any failed anchor or extra-window fragment across the nine lines, plus centerline comparison of all36','cost':'one deterministic CPU audit <2min, no training/inference/prediction or registration refit','stop':'save counts, overlays, flags; do not overwrite masks, transforms, previous results or state-space inputs','protected_files':protected};dump(OUT/'frozen_contract.json',contract)
    rows=[];central=[];cases=[];dense=np.arange(0,120.001,.25);offsets=np.arange(-2,2.001,.5);zero_diff=[]
    for seq in data['sequences']:
        b=seq['beam_id'];hs=np.load(EXT/'analysis'/f'beam{b}_transforms.npz')['current_native_to_reference_native']
        for o,h in zip(seq['observations'],hs):
            mask=(np.asarray(Image.open(o['mask_source']))>0).astype('float32')
            for j,sec in enumerate(seq['paired_visible_reference_transects']):
                cut=next(t for t in seq['fixed_transect_geometry'] if t['id']==sec);case_rows=[]
                for off in offsets:
                    xy=mapped_points(cut['center'],cut['normal'],h,dense-60,np.array([off]));p=cv2.remap(mask,*xy,cv2.INTER_LINEAR)[0];runs=intervals(dense,p);legacy=[r for r in runs if r[0]<=75 and r[1]>=45];anchored=[r for r in runs if r[0]<=60<=r[1]];status='ok' if len(anchored)==1 and not anchored[0][2] else 'missing_anchor' if not anchored else 'nonunique_anchor' if len(anchored)>1 else 'censored_anchor';chosen=anchored[0] if status=='ok' else None;extras=[r for r in legacy if chosen is None or r!=chosen];old_ok=len(legacy)==1 and not legacy[0][2]
                    r={'beam':b,'image':o['image'],'load_kN':o['metadata']['nominal_stage_load_kN'],'section':sec,'tangent_offset_ref_px':float(off),'centerline':off==0,'saved_width':o['model_widths_strip_px'][j] if off==0 else None,'anchor_status':status,'anchor_left':chosen[0] if chosen else None,'anchor_right':chosen[1] if chosen else None,'anchor_width':chosen[1]-chosen[0] if chosen else None,'legacy_status':'ok' if old_ok else 'ambiguous','legacy_width':legacy[0][1]-legacy[0][0] if old_ok else None,'extra_window_components':len(extras),'all_strip_intervals':json.dumps(runs),'old_window_intervals':json.dumps(legacy),'extra_intervals':json.dumps(extras),'source_status':o['width_observation_status'][j],'uncertainty_flags':'|'.join(o['uncertainty_flags'])};rows.append(r);case_rows.append(r)
                    if off==0:
                        assert old_ok and abs(r['legacy_width']-r['saved_width'])<1e-9;r['anchor_minus_saved']=r['anchor_width']-r['saved_width'] if chosen else None;central.append(dict(r));zero_diff.append(abs(r['legacy_width']-r['saved_width']))
                if any(r['anchor_status']!='ok' or r['extra_window_components'] for r in case_rows):
                    cases.append({'beam':b,'image':o['image'],'section':sec,'load_kN':o['metadata']['nominal_stage_load_kN'],'flagged_offsets':[r['tangent_offset_ref_px'] for r in case_rows if r['anchor_status']!='ok' or r['extra_window_components']],'n_failed_anchor':sum(r['anchor_status']!='ok' for r in case_rows),'n_extra_fragment_lines':sum(r['extra_window_components']>0 for r in case_rows)})
    # Rows need stable field lists; only central table has comparison delta.
    write_csv(OUT/'all_324_line_checks.csv',rows);write_csv(OUT/'saved_centerline_comparison.csv',central)
    dump(OUT/'flagged_cases.json',cases)
    if cases:write_csv(OUT/'flagged_cases.csv',cases)
    counts={'n_stages':14,'n_physical_beams':3,'n_fixed_beam_sections':8,'saved_centerlines':len(central),'original_centerline_replay_max_abs_difference':max(zero_diff),'centerline_anchor_valid':sum(r['anchor_status']=='ok' for r in central),'centerline_anchor_unchanged':sum(r.get('anchor_minus_saved')==0 for r in central),'centerline_anchor_changed':sum(r.get('anchor_minus_saved') is not None and abs(r['anchor_minus_saved'])>1e-9 for r in central),'centerline_extra_fragment_flags':sum(r['extra_window_components']>0 for r in central),'context_lines':len(rows),'context_anchor_valid':sum(r['anchor_status']=='ok' for r in rows),'context_legacy_ambiguous':sum(r['legacy_status']!='ok' for r in rows),'context_anchor_failed':sum(r['anchor_status']!='ok' for r in rows),'context_extra_fragment_lines':sum(r['extra_window_components']>0 for r in rows),'legacy_ambiguous_anchor_located':sum(r['legacy_status']!='ok' and r['anchor_status']=='ok' for r in rows),'flagged_frame_section_cases':len(cases),'anchor_rule_applied_to_original_observation_files':False};dump(OUT/'summary.json',counts)
    fig,axs=plt.subplots(1,2,figsize=(13,4.8));xx=np.arange(len(central));saved=np.array([r['saved_width'] for r in central]);new=np.array([r['anchor_width'] if r['anchor_width'] is not None else np.nan for r in central]);axs[0].plot(xx,saved,'o',color='black',markersize=5,label='Saved width');axs[0].plot(xx,new,'+',color='#0072b2',markersize=7,label='Fixed-x60 candidate');axs[0].set(ylabel='Width (strip px)',title='Every saved centerline, original and candidate');axs[0].legend();axs[1].plot(xx,new-saved,'o',color='#0072b2');axs[1].axhline(0,color='gray',lw=.7);axs[1].set(ylabel='Candidate minus saved width (px)',title='No replacement of saved inputs or scores')
    labs=[f'B{r["beam"]}S{r["section"]}@{r["load_kN"]}' for r in central]
    for ax in axs:ax.set_xticks(xx);ax.set_xticklabels(labs,rotation=90,fontsize=6);ax.grid(alpha=.2)
    fig.suptitle('D01 all14-stage anchor audit: 36 centerlines, 3 physical beams; exposed development archive',fontsize=11);fig.tight_layout();fig.savefig(OUT/'F01_all_saved_width_comparisons.png',dpi=160);plt.close(fig)
    # All flagged frame-section cases, split only by deterministic page size6.
    for page in range(math.ceil(len(cases)/6)):
        batch=cases[page*6:(page+1)*6];fig,axs=plt.subplots(len(batch),2,figsize=(12,2.7*len(batch)),squeeze=False)
        for axrow,case in zip(axs,batch):
            seq=next(s for s in data['sequences'] if s['beam_id']==case['beam']);idx=next(i for i,o in enumerate(seq['observations']) if o['image']==case['image']);o=seq['observations'][idx];h=np.load(EXT/'analysis'/f'beam{case["beam"]}_transforms.npz')['current_native_to_reference_native'][idx];cut=next(t for t in seq['fixed_transect_geometry'] if t['id']==case['section']);rgb=np.asarray(Image.open(EXT/'inputs'/f'{case["image"]}.jpg').convert('RGB'));mask=(np.asarray(Image.open(o['mask_source']))>0).astype('float32');ys=np.arange(-6,6.001,.25);xy=mapped_points(cut['center'],cut['normal'],h,dense-60,ys);raw=cv2.remap(rgb,*xy,cv2.INTER_LINEAR);mp=cv2.remap(mask,*xy,cv2.INTER_LINEAR)
            axrow[0].imshow(raw,extent=(0,120,6,-6),aspect='auto');axrow[1].imshow(raw,extent=(0,120,6,-6),aspect='auto');overlay=np.zeros((*mp.shape,4));overlay[mp>=.5]=[0,.8,1,.35];axrow[1].imshow(overlay,extent=(0,120,6,-6),aspect='auto')
            for ax in axrow:
                ax.axvline(60,color='#ff9f1c',ls=':',lw=1);ax.axhline(0,color='#ff9f1c',lw=.8)
                for off in case['flagged_offsets']:ax.axhline(off,color='#bb33cc',ls='--',lw=.8)
                ax.set(xlim=(30,95),xlabel='Strip x (px)',ylabel='Tangent offset (ref px)')
            axrow[0].set_title(f'{case["image"]} S{case["section"]}: raw');axrow[1].set_title(f'Frozen mask; flagged offsets {case["flagged_offsets"]}')
        fig.suptitle('All flagged cases: orange fixed anchor/centerline; magenta context ambiguity\nCyan is existing mask, not truth. No intervals merged, no pixels changed.',fontsize=11);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/f'F02_flagged_cases_page{page+1}.png',dpi=160);plt.close(fig)
    assert all(sha(p)==h for p,h in protected.items());dump(OUT/'receipt.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'runtime_s':time.time()-start,'host':socket.gethostname(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent.parent,text=True).strip(),'script_sha256':sha(__file__),'protected_count':len(protected),'all_protected_files_unchanged':True,'no_training_inference_prediction_or_registration_fit':True});print(json.dumps(counts,indent=2));print(json.dumps(cases,indent=2))
if __name__=='__main__':main()
