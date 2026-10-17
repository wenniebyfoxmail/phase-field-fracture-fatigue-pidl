"""Build fourteen-stage uncertain observations and eleven transitions; no fitting."""
import argparse,csv,json,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
import cv2,numpy as np,pandas as pd
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from d01_fixed_mask_measurement_pilot import polygon,graph,paths,length
from prepare_d01_state_space_inputs import supported_length,export_model_arrays,write_csv
from audit_d01_measurement_readiness import mapped_points,intervals


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def eligibility(mask,score,roi,corr):
    """Exact prior pilot screen; only the previously unseen eight cases use it."""
    sk=skeletonize(mask);adj=graph(sk);radius=ndi.distance_transform_edt(mask);special=np.zeros_like(mask)
    for p,qs in adj.items():
        if len(qs)!=2:special[p]=True
    near_special=ndi.distance_transform_edt(~special)<12;reasons=np.zeros(mask.shape,np.uint8)
    reasons[sk&~(roi&corr)]|=1;reasons[sk&(2*radius<4)]|=2;reasons[sk&(score<.8)]|=4;reasons[sk&near_special]|=8
    clear=sk&(reasons==0);ca={p:[q for q in qs if clear[q]] for p,qs in adj.items() if clear[p]};eligible=np.zeros_like(sk);kept=[]
    for chain in paths(ca):
        if length(chain)>=20:
            yy,xx=np.asarray(chain).T;eligible[yy,xx]=True;kept.append(chain)
    reasons[sk&~eligible&(reasons==0)]|=16;nearest=ndi.distance_transform_edt(~sk,return_distances=False,return_indices=True)
    use=mask&eligible[nearest[0],nearest[1]]&roi&corr;labels=np.zeros(mask.shape,np.uint8);labels[roi]=1;labels[mask&~use]=3;labels[use]=2
    polylines=[{'id':i,'length_px':length(ch),'xy':[[int(x),int(y)] for y,x in ch]} for i,ch in enumerate(kept,1)]
    assert np.array_equal((labels==2)|(labels==3),mask)
    return labels,reasons,polylines


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();root=a.root;base=a.project/'local_archive/experiments';old=base/'S03-E016-D01/full_mask_preview_cracksam_20261017';pilot=base/'S03-E016-D01/fixed_mask_measurement_pilot_20261017';prepared=base/'S03-E016-D01/common_support_state_space_inputs_20261017_r002';stage=base/'S03-E012-D01/runs/S03-E012-D01-R001';metadata=base/'S03-E004/analysis';out=root/'analysis';out.mkdir(exist_ok=False);(out/'eligibility').mkdir()
    manifest=json.loads((root/'source_manifest.json').read_text());contract=json.loads((pilot/'pilot_contract.json').read_text());prior=json.loads((prepared/'state_space_inputs.json').read_text());lock=json.loads((base/'S03-E015-D01/runs/S03-E015-D01-R000/first_frame_transects_lock.json').read_text());selections=json.loads((stage/'selected_sequences_before_pixel_access.json').read_text())['groups'];mapping=list(csv.DictReader((metadata/'load_stop_mapping.csv').open()));reg=list(csv.DictReader((stage/'stage_observables.csv').open()));oldhash=json.loads((old/'final_cleanup_hashes.json').read_text());assert all(sha(old/k)==v for k,v in oldhash.items())
    priorobs={o['image']:o for s in prior['sequences'] for o in s['observations']};observations=[];transitions=[];sequences=[];widthrows=[];metrics=[];fig,axs=plt.subplots(3,6,figsize=(24,11));[ax.axis('off') for ax in axs.flat]
    for bi,b in enumerate((4,5,6)):
        geo=lock['beams'][str(b)];shape=tuple(geo['native_shape']);wh=geo['working_shape'];sy=wh[0]/shape[0];sx=wh[1]/shape[1];t=np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])
        with np.load(stage/f'Beam{b}_stage_fields.npz') as z:hs=[np.linalg.inv(t)@h@t for h in z['homographies']]
        cases=sorted([e for e in manifest if e['beam']==b],key=lambda e:e['filename_time_s']);assert len(cases)==len(hs)==len(selections[str(b)])
        roi=polygon(shape,contract['specimen_interior_polygons_normalized'][str(b)]);corr=np.zeros(shape,bool)
        for points in contract['review_clear_corridors_normalized'][str(b)]:corr|=polygon(shape,points)
        common=np.ones(shape,bool)
        for h in hs:common&=cv2.warpPerspective(roi.astype('uint8'),h,(shape[1],shape[0]),flags=cv2.INTER_NEAREST)>0
        Image.fromarray(common.astype('uint8')*255).save(out/f'beam{b}_all_stage_common_support.png');np.savez_compressed(out/f'beam{b}_transforms.npz',current_native_to_reference_native=np.stack(hs))
        oldseq=next(s for s in prior['sequences'] if s['beam_id']==b);cuts=oldseq['paired_visible_reference_transects'];seq={'beam_id':b,'reference_image':cases[0]['id'],'common_support_file':str(out/f'beam{b}_all_stage_common_support.png'),'paired_visible_reference_transects':cuts,'fixed_transect_geometry':oldseq['fixed_transect_geometry'],'observations':[],'n_observations':len(cases),'n_adjacent_transitions':len(cases)-1,'physical_scale_calibrated':False,'grouping':'physical beam, never section or image patch'}
        table=pd.read_csv(metadata/f'extracted_small_files/Beam {b}/Filtered Data/Beam{b}Crack.txt',sep=r'\s+');yy,xx=np.where(common);box=[max(0,int(xx.min())-60),max(0,int(yy.min())-60),min(shape[1],int(xx.max())+61),min(shape[0],int(yy.max())+61)]
        for j,(e,h) in enumerate(zip(cases,hs)):
            name=e['id'];assert sha(root/'inputs'/e['file'])==e['sha256'];mask=np.asarray(Image.open(root/'refined_v3'/f'{name}_mask.png'))>0
            if e['reuse_existing_mask']:
                assert sha(root/'refined_v3'/f'{name}_mask.png')==sha(old/'refined_v3'/f'{name}_mask.png')
                labels=np.asarray(Image.open(pilot/f'{name}_eligibility_labels.png'));lines=json.loads((pilot/f'{name}_segments.json').read_text());shutil.copy2(pilot/f'{name}_eligibility_labels.png',out/'eligibility'/f'{name}.png');shutil.copy2(pilot/f'{name}_skeleton_reason_bits.png',out/'eligibility'/f'{name}_reason_bits.png')
            else:
                score=np.asarray(Image.open(root/'outputs'/f'{name}_probability16.png'),dtype=np.float32)/65535;labels,reasons,lines=eligibility(mask,score,roi,corr);Image.fromarray(labels).save(out/'eligibility'/f'{name}.png');Image.fromarray(reasons).save(out/'eligibility'/f'{name}_reason_bits.png');del score,reasons
            (out/'eligibility'/f'{name}_segments.json').write_text(json.dumps(lines));native=cv2.warpPerspective(common.astype('uint8'),np.linalg.inv(h),(shape[1],shape[0]),flags=cv2.INTER_NEAREST)>0;y,x=np.where(mask&native);jac=abs(np.linalg.det(h))/(h[2,0]*x+h[2,1]*y+h[2,2])**3;clear=labels[y,x]==2;seglen,pieces=supported_length(lines,h,common)
            metric={'image':name,'beam':b,'nominal_load_kN':e['nominal_load_kN'],'filename_time_s_nominal':e['filename_time_s'],'reuse_existing_mask':e['reuse_existing_mask'],'common_support_reference_px2':int(common.sum()),'candidate_area_reference_px2':float(jac.sum()),'eligible_area_reference_px2':float(jac[clear].sum()),'uncertain_area_reference_px2':float(jac[~clear].sum()),'eligible_segment_length_reference_px':seglen,'supported_segment_pieces':pieces};metrics.append(metric)
            m=next(v for v in mapping if v['beam_id']==f'Beam {b}' and int(v['photo_time_s'])==e['filename_time_s']);ix=int(np.argmin(abs(table['Time(s)']-e['filename_time_s'])));sample=table.iloc[ix];assert abs(float(sample['Load(kN)'])-float(m['load_kN']))<1e-6
            md={'image':name,'beam':b,'nominal_stage_load_kN':e['nominal_load_kN'],'filename_time_s_nominal':e['filename_time_s'],'nearest_logger_time_s':float(sample['Time(s)']),'logger_lookup_difference_s':float(sample['Time(s)']-e['filename_time_s']),'nominal_join_force_kN':float(sample['Load(kN)']),'nominal_join_piston_mm':float(sample['Pos(mm)']),'source_table':str(metadata/f'extracted_small_files/Beam {b}/Filtered Data/Beam{b}Crack.txt'),'synchronization_error_bound_s':None,'registration_median_residual_native_px':float(next(v['median_reprojection_native_px'] for v in reg if v['beam']==str(b) and int(v['filename_time_s'])==e['filename_time_s']))}
            widths=[];human=[];statuses=[]
            for k,cut in enumerate(cuts):
                if name in priorobs:
                    value=priorobs[name]['model_widths_strip_px'][k];truth=priorobs[name]['human_reference_widths_strip_px'][k];status='existing_human_reference_boundary_bias_uncorrected'
                else:
                    tr=next(q for q in geo['transects'] if q['id']==cut);dense=np.arange(0,120.001,.25);xy=mapped_points(tr['center'],tr['normal'],h,dense-60,np.array([0]));occupancy=cv2.remap(mask.astype('float32'),*xy,cv2.INTER_LINEAR)[0];runs=intervals(dense,occupancy);selected=[q for q in runs if q[1]>=45 and q[0]<=75];truth=None
                    if len(selected)!=1:value=None;status='unresolved_no_interval' if not selected else 'uncertain_multiple_intervals'
                    elif selected[0][2]:value=None;status='uncertain_censored_interval'
                    else:value=float(selected[0][1]-selected[0][0]);status='model_only_boundary_bias_uncorrected'+('_narrow_under_4px' if value<4 else '')
                widths.append(value);human.append(truth);statuses.append(status);widthrows.append({'image':name,'beam':b,'transect':cut,'model_width_strip_px':value,'human_reference_width_strip_px':truth,'status':status,'human_reference_available':truth is not None})
            ob={'image':name,'metadata':md,'geometry':metric,'model_widths_strip_px':widths,'human_reference_widths_strip_px':human,'width_observation_status':statuses,'measurement_variance':None,'process_variance':None,'uncertainty_flags':['microcrack_coverage_unknown','boundary_bias_uncorrected','clock_synchronization_unknown','partial_eligible_length','pixel_scale_not_metric','frame_specific_eligibility'], 'eligibility_file':str(out/'eligibility'/f'{name}.png'),'mask_source':str(old/'refined_v3'/f'{name}_mask.png') if e['reuse_existing_mask'] else str(root/'refined_v3'/f'{name}_mask.png')};seq['observations'].append(ob);observations.append(ob)
            rgb=np.asarray(Image.open(root/'inputs'/e['file']).convert('RGB'));rgb=cv2.warpPerspective(rgb,h,(shape[1],shape[0]));display=rgb.copy();wc=cv2.warpPerspective((labels==2).astype('uint8'),h,(shape[1],shape[0]),flags=cv2.INTER_NEAREST)>0;wu=cv2.warpPerspective((labels==3).astype('uint8'),h,(shape[1],shape[0]),flags=cv2.INTER_NEAREST)>0
            wc=cv2.dilate(wc.astype('uint8'),np.ones((3,3),np.uint8))>0;wu=(cv2.dilate(wu.astype('uint8'),np.ones((3,3),np.uint8))>0)&~wc;display[wc]=(.25*rgb[wc]+.75*np.array([0,220,255])).astype('uint8');display[wu]=(.25*rgb[wu]+.75*np.array([255,165,0])).astype('uint8');contours,_=cv2.findContours(common.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(display,contours,-1,(80,130,255),5);x0,y0,x1,y1=box;thumb=Image.fromarray(display[y0:y1,x0:x1]);thumb.thumbnail((1404,936));thumb.save(out/f'{name}_review.jpg',quality=94);axs[bi,j].imshow(thumb);axs[bi,j].set_title(f'{name} | {e["nominal_load_kN"]}kN\nA={metric["candidate_area_reference_px2"]:,.0f}px²'+(' | reused' if e['reuse_existing_mask'] else ' | new'),fontsize=9)
            print('MEASURED',name,flush=True)
        for j,(prev,nxt) in enumerate(zip(seq['observations'],seq['observations'][1:])):
            valid=[u is not None and v is not None for u,v in zip(prev['model_widths_strip_px'],nxt['model_widths_strip_px'])]
            transitions.append({'transition_id':f'beam{b}_{j:02d}_{j+1:02d}','beam':b,'from_image':prev['image'],'to_image':nxt['image'],'from_nominal_load_kN':prev['metadata']['nominal_stage_load_kN'],'to_nominal_load_kN':nxt['metadata']['nominal_stage_load_kN'],'delta_nominal_load_kN':nxt['metadata']['nominal_stage_load_kN']-prev['metadata']['nominal_stage_load_kN'],'delta_filename_time_s_nominal':nxt['metadata']['filename_time_s_nominal']-prev['metadata']['filename_time_s_nominal'],'width_section_ids':cuts,'valid_width_pairs':valid,'n_valid_width_pairs':sum(valid),'input_widths_strip_px':prev['model_widths_strip_px'],'next_candidate_widths_strip_px':nxt['model_widths_strip_px'],'target_kind':'future observed candidate, not independent geometry truth','uncertainty_flags':nxt['uncertainty_flags'],'future_control_policy':'conditional on supplied next nominal load; not an autonomous unknown-load forecast'})
        sequences.append(seq)
    export_model_arrays(sequences,out)
    fig.suptitle('D01 frozen pretrained method: all 14 selected loading stages\nCyan: eligible; amber: uncertain/withheld; blue: per-beam all-stage common support. Six endpoints reused unchanged.',fontsize=14);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(out/'F01_all_14_stage_masks.png',dpi=140);plt.close(fig)
    (out/'state_space_inputs.json').write_text(json.dumps({'sequences':sequences,'n_beams':3,'n_observations':14,'n_adjacent_transitions':11,'fit_performed':False,'calibrated_variances_available':False},indent=2));(out/'adjacent_transitions.json').write_text(json.dumps(transitions,indent=2));(out/'stage_observations.json').write_text(json.dumps(observations,indent=2));write_csv(out/'stage_measurements.csv',metrics);write_csv(out/'loading_time_metadata.csv',[o['metadata'] for o in observations]);write_csv(out/'fixed_section_widths.csv',widthrows)
    simple=[{k:v for k,v in t.items() if k not in ['width_section_ids','valid_width_pairs','input_widths_strip_px','next_candidate_widths_strip_px','uncertainty_flags']} for t in transitions];write_csv(out/'adjacent_transitions.csv',simple)
    ids=[o['image'] for o in observations];pairs=np.array([[ids.index(t['from_image']),ids.index(t['to_image'])] for t in transitions]);np.savez_compressed(out/'transition_index_arrays.npz',observation_pair_indices=pairs,beam=np.array([t['beam'] for t in transitions]),delta_nominal_load_kN=np.array([t['delta_nominal_load_kN'] for t in transitions]),delta_filename_time_s_nominal=np.array([t['delta_filename_time_s_nominal'] for t in transitions]))
    assert len(observations)==14 and len(transitions)==11 and all(t['delta_nominal_load_kN']>0 for t in transitions)
    assert all(sha(old/k)==v for k,v in oldhash.items())
    (out/'receipt.json').write_text(json.dumps({'completed_utc':datetime.now(timezone.utc).isoformat(),'new_masks':8,'reused_masks':6,'observations':14,'adjacent_transitions':11,'source_cleanup_artifacts_unchanged':len(oldhash),'training_fitting_filtering_forecasting':False,'MD01_touched':False,'width_human_reference_count':sum(x['human_reference_available'] for x in widthrows),'no_intermediate_human_truth_invented':True,'script_sha256':sha(Path(__file__))},indent=2))


if __name__=='__main__':main()
