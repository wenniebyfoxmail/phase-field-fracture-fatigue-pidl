"""Prepare, but never fit, D01 state-space inputs from six frozen masks."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from d01_fixed_mask_measurement_pilot import polygon


def read_csv(p):
    return list(csv.DictReader(p.open()))


def write_csv(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def export_model_arrays(sequences,out):
    """Serialize missingness explicitly; logger samples are not crack observations."""
    n=sum(len(s['observations']) for s in sequences)
    y=np.full((n,12),np.nan);reference=y.copy();loads=[];times=[];forces=[];pistons=[];beams=[];images=[];k=0
    for seq in sequences:
        first,last=seq['observations'][0],seq['observations'][-1];table=pd.read_csv(first['metadata']['source_table'],sep=r'\s+')
        lo=first['metadata']['filename_time_s_nominal'];hi=last['metadata']['filename_time_s_nominal']
        clip=table[(table['Time(s)']>=lo)&(table['Time(s)']<=hi)]
        path=out/f'beam{seq["beam_id"]}_nominal_logger_history.npz'
        np.savez_compressed(path,nominal_logger_time_s=clip['Time(s)'].to_numpy(),force_kN=clip['Load(kN)'].to_numpy(),piston_displacement_mm=clip['Pos(mm)'].to_numpy())
        seq['nominal_logger_history']={'file':str(path.resolve()),'samples':len(clip),'time_axis':'manually aligned nominal logger seconds; synchronization uncertainty not quantified','use':'retrospective controls/sensitivity only; future forcing not assumed known','no_regridding_or_interpolation':True}
        for ob in seq['observations']:
            for j,t in enumerate(seq['paired_visible_reference_transects']):
                value=ob['model_widths_strip_px'][j];truth=ob['human_reference_widths_strip_px'][j]
                y[k,t-1]=np.nan if value is None else value;reference[k,t-1]=np.nan if truth is None else truth
            m=ob['metadata'];loads.append(m['nominal_stage_load_kN']);times.append(m['filename_time_s_nominal']);forces.append(m['nominal_join_force_kN']);pistons.append(m['nominal_join_piston_mm']);beams.append(seq['beam_id']);images.append(ob['image']);k+=1
    np.savez_compressed(out/'state_space_input_arrays.npz',model_width_strip_px=y,human_reference_width_strip_px=reference,width_present=np.isfinite(y),nominal_stage_load_kN=np.array(loads),nominal_filename_time_s=np.array(times),nominal_join_force_kN=np.array(forces),nominal_join_piston_mm=np.array(pistons),beam_id=np.array(beams),image=np.array(images))


def project(points,h):
    # Explicit small homography arithmetic avoids platform BLAS matmul warnings.
    x,y=points.T;den=h[2,0]*x+h[2,1]*y+h[2,2]
    assert np.isfinite(den).all() and (abs(den)>1e-10).all()
    return np.c_[(h[0,0]*x+h[0,1]*y+h[0,2])/den,(h[1,0]*x+h[1,1]*y+h[1,2])/den]


def supported_length(paths,h,support):
    total=0.;pieces=0
    for path in paths:
        xy=project(np.asarray(path['xy'],float),h)
        if len(xy)<2:continue
        a,b=xy[:-1],xy[1:];mid=(a+b)/2
        points=np.rint(np.stack([a,mid,b],axis=1)).astype(int)
        valid=((points[:,:,0]>=0)&(points[:,:,0]<support.shape[1])&(points[:,:,1]>=0)&(points[:,:,1]<support.shape[0])).all(axis=1)
        ix=np.flatnonzero(valid);valid[ix]&=support[points[ix,:,1],points[ix,:,0]].all(axis=1)
        total+=float(np.linalg.norm(b-a,axis=1)[valid].sum());pieces+=int(np.count_nonzero(valid &~np.r_[False,valid[:-1]]))
    return total,pieces


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    base=a.project/'local_archive/experiments';src=base/'S03-E016-D01/full_mask_preview_cracksam_20261017';pilot=base/'S03-E016-D01/fixed_mask_measurement_pilot_20261017';old=base/'S03-E012-D01/runs/S03-E012-D01-R001';meta=base/'S03-E004/analysis';out=a.output;out.mkdir(parents=True,exist_ok=False)
    hashes=json.loads((src/'final_cleanup_hashes.json').read_text());assert all(sha(src/p)==v for p,v in hashes.items())
    contract=json.loads((pilot/'pilot_contract.json').read_text());manifest=json.loads((src/'source_manifest.json').read_text());selected=json.loads((old/'selected_sequences_before_pixel_access.json').read_text())['groups'];lock=json.loads((base/'S03-E015-D01/runs/S03-E015-D01-R000/first_frame_transects_lock.json').read_text());mapping=read_csv(meta/'load_stop_mapping.csv');registration=read_csv(old/'stage_observables.csv');prior=json.loads((pilot/'observations_for_uq.json').read_text())
    rules={'kind':'exploratory input preparation; no parameter fit','scope':'same six masks and existing metadata only; no new image acquisition or inference','spatial_unit':'three separate two-frame beam sequences; no cross-beam pixel alignment','common_support':'intersection of archived specimen-interior polygons after existing current-to-origin homographies; NEVER intersect crack masks; conservative crack corridors remain eligibility labels only','coordinate_system':'native pixel coordinates of each beam first selected image','mask_geometry':'integrate unchanged native mask pixels inside mapped common support; report native count and homography Jacobian-weighted reference-pixel area','length':'clip previously saved eligible polylines to common support, project edge lengths; no new skeleton or bridges','eligibility':'carry prior clear/uncertain labels; same footprint does not make time-varying eligibility identical','registered_mask_display':'nearest-neighbor resampling is display-only; unchanged native masks remain numeric source','time':'filename seconds and manually adjusted logger joins are nominal; physical timing uncertainty remains unknown','sensitivity':'logger +/-1 and +/-5 s windows are analyst scenarios, not synchronization confidence bounds','prediction_scope':'retrospective preparation using both viewed frames; future study must freeze supports and permitted controls at prediction origin','model_execution':'disabled; no training, fitting, filtering or forecasting'}
    (out/'preparation_contract.json').write_text(json.dumps(rules,indent=2))
    refs={};seen=set()
    for row in read_csv(pilot/'existing_width_reference_checks.csv'):
        if row['unique_index'] in seen:continue
        seen.add(row['unique_index']);refs.setdefault(row['image'],{})[int(row['transect'])]=row
    measurements=[];time_rows=[];pairs=[];sequences=[];all_metadata=[];qa=[]
    fig,axs=plt.subplots(3,2,figsize=(12,14));qfig,qaxs=plt.subplots(3,2,figsize=(10,12))
    for bi,beam in enumerate((4,5,6)):
        entries=sorted([e for e in manifest if e['id'].startswith(f'beam{beam}_')],key=lambda e:int(e['id'].split('_t')[1]));shape=tuple(lock['beams'][str(beam)]['native_shape']);wh=lock['beams'][str(beam)]['working_shape'];sy=wh[0]/shape[0];sx=wh[1]/shape[1];t=np.array([[sx,0,(sx-1)/2],[0,sy,(sy-1)/2],[0,0,1.]])
        with np.load(old/f'Beam{beam}_stage_fields.npz') as z:hs=z['homographies'].copy()
        roi=polygon(shape,contract['specimen_interior_polygons_normalized'][str(beam)]);corr=np.zeros(shape,bool)
        for points in contract['review_clear_corridors_normalized'][str(beam)]:corr|=polygon(shape,points)
        footprint=roi;common=np.ones(shape,bool);transforms=[];metadata=[]
        table_path=meta/f'extracted_small_files/Beam {beam}/Filtered Data/Beam{beam}Crack.txt';table=pd.read_csv(table_path,sep=r'\s+')
        for e in entries:
            stage=next(i for i,s in enumerate(selected[str(beam)]) if Path(s['saved_as']).name==Path(e['source']).name)
            h=np.linalg.inv(t)@hs[stage]@t;transforms.append(h)
            common&=cv2.warpPerspective(footprint.astype('uint8'),h,(shape[1],shape[0]),flags=cv2.INTER_NEAREST,borderValue=0)>0
            ftime=int(e['id'].split('_t')[1]);m=next(x for x in mapping if x['beam_id']==f'Beam {beam}' and int(x['photo_time_s'])==ftime)
            idx=int(np.argmin(abs(table['Time(s)'].to_numpy()-ftime)));row=table.iloc[idx];assert abs(row['Load(kN)']-float(m['load_kN']))<1e-6;assert abs(row['Pos(mm)']-float(m['piston_displacement_mm']))<1e-6
            d={'image':e['id'],'beam':beam,'filename_time_s_nominal':ftime,'nominal_stage_load_kN':int(m['load_step_label']),'nearest_logger_time_s':float(row['Time(s)']),'logger_lookup_difference_s':float(row['Time(s)']-ftime),'nominal_join_force_kN':float(row['Load(kN)']),'nominal_join_piston_mm':float(row['Pos(mm)']),'synchronization_error_bound_s':None,'source_table':str(table_path),'registration_inliers':int(next(x['inliers'] for x in registration if x['beam']==str(beam) and int(x['filename_time_s'])==ftime)),'archived_registration_median_residual_native_px':float(next(x['median_reprojection_native_px'] for x in registration if x['beam']==str(beam) and int(x['filename_time_s'])==ftime))}
            for window in (1,5):
                w=table[abs(table['Time(s)']-ftime)<=window];d[f'force_min_plusminus_{window}s_scenario_kN']=float(w['Load(kN)'].min());d[f'force_max_plusminus_{window}s_scenario_kN']=float(w['Load(kN)'].max())
            metadata.append(d);time_rows.append(d)
        assert common.any();Image.fromarray(common.astype('uint8')*255).save(out/f'beam{beam}_common_spatial_support.png')
        np.savez_compressed(out/f'beam{beam}_coordinate_transforms.npz',current_native_to_reference_native=np.stack(transforms))
        supported_ids=sorted(set(k for k,v in refs[entries[0]['id']].items() if v['human_status']=='visible' and v['scored']=='True')&set(k for k,v in refs[entries[1]['id']].items() if v['human_status']=='visible' and v['scored']=='True'))
        fixed_cuts=[x for x in lock['beams'][str(beam)]['transects'] if x['id'] in supported_ids]
        # Ensure the whole measured aperture at paired cuts lies inside common support.
        for cut in fixed_cuts:
            c=np.asarray(cut['center']);n=np.asarray(cut['normal']);points=np.rint(c+np.arange(-20,21)[:,None]*n).astype(int);assert common[points[:,1],points[:,0]].all(),(beam,cut['id'])
        seq={'beam_id':beam,'reference_image':entries[0]['id'],'reference_shape_hw':shape,'common_support_file':str(out/f'beam{beam}_common_spatial_support.png'),'paired_visible_reference_transects':supported_ids,'fixed_transect_geometry':fixed_cuts,'observations':[],'n_observations':2,'n_endpoint_transitions':1,'units':'geometry in beam-reference px/px^2; fixed widths in saved strip-coordinate px; no metric calibration'}
        yy,xx=np.where(common);bbox=(max(int(xx.min())-90,0),max(int(yy.min())-90,0),min(int(xx.max())+91,shape[1]),min(int(yy.max())+91,shape[0]));first_gray=None
        for j,(e,h,m) in enumerate(zip(entries,transforms,metadata)):
            image=e['id'];mask=np.asarray(Image.open(src/'refined_v3'/f'{image}_mask.png'))>0;labels=np.asarray(Image.open(pilot/f'{image}_eligibility_labels.png'))
            native_support=cv2.warpPerspective(common.astype('uint8'),np.linalg.inv(h),(shape[1],shape[0]),flags=cv2.INTER_NEAREST,borderValue=0)>0
            Image.fromarray(native_support.astype('uint8')*255).save(out/f'{image}_common_support_native.png')
            ey,ex=np.where(mask&native_support);jac=abs(np.linalg.det(h))/(h[2,0]*ex+h[2,1]*ey+h[2,2])**3;assert np.all(jac>0)
            clear=labels[ey,ex]==2;area=float(jac.sum());cleararea=float(jac[clear].sum());uncertain=float(jac[~clear].sum());assert abs(area-cleararea-uncertain)<1e-7
            length,pieces=supported_length(json.loads((pilot/f'{image}_segments.json').read_text()),h,common)
            meas={'image':image,'beam':beam,'common_spatial_support_reference_px2':int(common.sum()),'candidate_area_reference_px2':area,'candidate_area_native_px2':len(ey),'eligible_area_reference_px2':cleararea,'uncertain_area_reference_px2':uncertain,'eligible_segment_length_reference_px':length,'supported_segment_pieces':pieces,'all_geometry_is_partial_and_bias_uncorrected':True};measurements.append(meas)
            width=[refs[image][k] for k in supported_ids]
            ob={'image':image,'metadata':m,'geometry':meas,'model_widths_strip_px':[float(x['mask_width']) for x in width],'human_reference_widths_strip_px':[float(x['human_width']) for x in width],'width_observation_status':['biased_model_measurement']*len(width),'measurement_variance':None,'process_variance':None,'missing_microcracks':'unobserved, not zero','physical_units_calibration':None,'prior_observation_record':next(x for x in prior if x['image']==image)};seq['observations'].append(ob)
            for cut,row in zip(supported_ids,width):pairs.append({'beam':beam,'image':image,'transect':cut,'model_width_strip_px':float(row['mask_width']),'human_width_strip_px':float(row['human_width']),'model_minus_human_strip_px':float(row['width_difference'])})
            rgb=np.asarray(Image.open(src/'inputs'/e['file']).convert('RGB'));reg=cv2.warpPerspective(rgb,h,(shape[1],shape[0]));display=reg.copy();display[common]=(.91*display[common]+.09*np.array([50,100,255])).astype('uint8')
            wc=cv2.warpPerspective(((labels==2)&mask).astype('uint8'),h,(shape[1],shape[0]),flags=cv2.INTER_NEAREST)>0
            wu=cv2.warpPerspective(((labels==3)&mask).astype('uint8'),h,(shape[1],shape[0]),flags=cv2.INTER_NEAREST)>0
            wc=cv2.dilate(wc.astype('uint8'),np.ones((3,3),np.uint8))>0;wu=(cv2.dilate(wu.astype('uint8'),np.ones((3,3),np.uint8))>0)&~wc
            display[wc]=(.25*display[wc]+.75*np.array([0,220,255])).astype('uint8');display[wu]=(.25*display[wu]+.75*np.array([255,165,0])).astype('uint8');contours,_=cv2.findContours(common.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(display,contours,-1,(80,130,255),5)
            x0,y0,x1,y1=bbox;axes=axs[bi,j];axes.imshow(display[y0:y1,x0:x1]);axes.set_title(f'{image} | nominal {m["nominal_stage_load_kN"]} kN\nSame reference support; candidate A={area:,.0f} px²',fontsize=10);axes.axis('off')
            gray=cv2.cvtColor(reg,cv2.COLOR_RGB2GRAY);cx,cy={4:(2500,1600),5:(2300,1700),6:(2000,1500)}[beam];patch=gray[cy-200:cy+200,cx-200:cx+200].copy()
            if j==0:first_gray=patch
            else:
                window=cv2.createHanningWindow((400,400),cv2.CV_32F);shift,response=cv2.phaseCorrelate(first_gray.astype('float32'),patch.astype('float32'),window)
                qa.append({'beam':beam,'control_patch_reference_xyxy':[cx-200,cy-200,cx+200,cy+200],'phase_residual_shift_x_reference_px':shift[0],'phase_residual_shift_y_reference_px':shift[1],'phase_response':response,'interpretation':'diagnostic only; no correction or registration uncertainty calibration'})
            qaxs[bi,j].imshow(patch,cmap='gray',vmin=0,vmax=255);qaxs[bi,j].set_title(f'Beam{beam} registered texture control: '+('first' if j==0 else f'last; residual {math.hypot(*shift):.2f}px'),fontsize=10);qaxs[bi,j].axis('off')
        seq['endpoint_transition']={'delta_nominal_filename_s':metadata[1]['filename_time_s_nominal']-metadata[0]['filename_time_s_nominal'],'delta_nominal_stage_kN':metadata[1]['nominal_stage_load_kN']-metadata[0]['nominal_stage_load_kN'],'delta_nominal_join_force_kN':metadata[1]['nominal_join_force_kN']-metadata[0]['nominal_join_force_kN'],'physical_elapsed_time_validated':False,'driving_axis_recommendation':'nominal loading stage for exploratory conditional model; not fatigue cycle or elapsed-life prediction'}
        sequences.append(seq)
        all_metadata.append({'beam':beam,'existing_selected_stage_count':len(selected[str(beam)]),'existing_selected_stage_labels_kN':[x['nominal_load_kN'] for x in selected[str(beam)]],'existing_selected_image_paths':[str(old/'raw_images'/x['saved_as']) for x in selected[str(beam)]],'additional_pixels_opened_this_preparation':False,'filtered_logger_rows':len(table),'median_logger_sample_spacing_s':float(np.median(np.diff(table['Time(s)']))),'filtered_logger_time_range_s':[float(table['Time(s)'].iloc[0]),float(table['Time(s)'].iloc[-1])],'force_range_kN':[float(table['Load(kN)'].min()),float(table['Load(kN)'].max())]})
        print(f'Beam{beam}: common support {common.sum():,} reference pixels; paired clear cuts {supported_ids}',flush=True)
    fig.suptitle('D01 common spatial support in each beam first-image coordinates\nBlue boundary = same observation region, not intersected crack pixels. Cyan/amber = prior eligibility.',fontsize=12);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'F01_common_spatial_support.png',dpi=140);plt.close(fig)
    qfig.suptitle('Archived registration: fixed texture controls outside main crack corridor\nNo new registration fit; residual phase shift is a diagnostic, not a confidence bound.',fontsize=12);qfig.tight_layout(rect=(0,0,1,.95));qfig.savefig(out/'F02_registration_texture_controls.png',dpi=140);plt.close(qfig)
    write_csv(out/'common_support_measurements.csv',measurements);write_csv(out/'loading_time_metadata.csv',time_rows);write_csv(out/'paired_width_inputs.csv',pairs)
    export_model_arrays(sequences,out)
    (out/'state_space_inputs.json').write_text(json.dumps({'sequences':sequences,'n_independent_beams':3,'n_observations':6,'n_endpoint_transitions':3,'ready_to_define_model':True,'ready_to_fit_calibrated_dynamics':False,'training_performed':False},indent=2))
    (out/'available_sequence_metadata.json').write_text(json.dumps(all_metadata,indent=2));(out/'registration_diagnostics.json').write_text(json.dumps(qa,indent=2))
    spec={'status':'model scaffold only; execution disabled','simplest_candidate':'one scalar fixed-section aperture per chosen section; section measurements within a beam are correlated, not independent trajectories','state_equation':'w_next = w + v * delta_nominal_load + eta','observation_equation':'observed_width = w + section/frame-dependent boundary_bias + epsilon','alternatives':'load-normalized local linear model first; nonlinear filtering or latent switching only if data later support them','primary_inputs':'paired fixed-section widths, status and source mapping','auxiliary_inputs':'common-support candidate area plus uncertain share, and partial eligible length; do not treat varying eligibility as a growth signal','units':'saved strip-coordinate px; no mm calibration','parameters':{'growth_rate':None,'process_variance':None,'observation_variance':None,'boundary_bias_model':None},'controls_policy':'nominal stage is an exploratory conditioning axis; retrospectively joined machine force is uncertain; future forcing not assumed known','clock_uncertainty':'unknown; no invented time-to-life axis','microcrack_policy':'unknown/missing; no established detection-limit distribution','fit':False,'filter':False,'forecast':False,'calibration':False,'data_limit':'3 beams x 2 endpoints; bias, process variation and observation variance cannot be separately identified from these pairs','next_data_option':'reuse existing 14-stage metadata, 4/6/4 by beam, with the same frozen inference and observation definitions if separately authorized; no new pixels processed here','holdout_policy':'all six already development; future evaluation grouped by beam and time, never random crops/cuts'}
    (out/'state_space_model_spec.json').write_text(json.dumps(spec,indent=2))
    assert all(sha(src/p)==v for p,v in hashes.items())
    (out/'receipt.json').write_text(json.dumps({'completed_utc':datetime.now(timezone.utc).isoformat(),'source_cleanup_artifacts_unchanged':len(hashes),'six_original_masks_unchanged':True,'frozen_width_references_reused':True,'new_training_inference_or_forecast':False,'MD01_touched':False,'script_sha256':sha(Path(__file__)),'source_pilot':str(pilot),'metadata_sources':[str(meta/'load_stop_mapping.csv'),str(meta/'source_receipt.md'),str(old/'stage_observables.csv')]},indent=2))


if __name__=='__main__':main()
