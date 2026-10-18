#!/usr/bin/env python3
"""Offline zero-update head-readout attribution, without models, SVD or training.

Coefficient infinity norms from different bases are coordinate-dependent. This
analysis therefore also compares Phi(Phi^T R) in one fixed CPU mass norm. It is
called a physical basis-image, not an exactly orthogonal/Riesz projector.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_block_diagnosis import independent_operator, q4_fields, metric, dump, sha
from analyze_pidl_head_newton import (ROOT, BASE, INPUTS, read_json, record, worker_output,
                                      fields, score, panel, finite_range)
from analyze_pidl_hidden_newton import boundary_check

GTOL=1e-10
DISPLAY_FLOOR=1e-20
INITIAL=BASE/'runs/pf_s04e011_learnednewton_e2dc61d_20261018T125034Z_production'
FORCES=[f'network_{j}' for j in range(3)]+[f'nodal_{j}' for j in range(5)]
BASES=['source','fresh0','fresh1','fresh2']
SCOPE=('FEM/PIDL c20s4 peak, physical cycle 20, substep 4, step 99, U=.11999988; '
       'fixed conditional accepted FEM damage and Smooth B0 boundary. Zero optimizer/parameter/history updates. '
       'This is a bounded numerical readout diagnosis, not an optimizer, network-capacity, physical-teacher '
       'or coupled fatigue-evolution experiment. The unchanged 1e-10 head-gradient threshold is a per-basis '
       'readout label; its crossing never invalidates an otherwise valid frozen-field observation.')


def js(path,role,sources):
    record(path,role,sources);return read_json(path)


def array(path,role,sources):
    record(path,role,sources);a=np.load(path,allow_pickle=False)
    if not np.isfinite(a).all():raise ValueError('Nonfinite saved array: '+str(path))
    return a


def inf(a):return float(np.max(np.abs(a))) if np.size(a) else 0.


def norm(a):return float(np.sqrt(np.einsum('i,i->',np.ravel(a),np.ravel(a),optimize=False)))


def comparison(a,b):
    return dict(maxabs=inf(a-b),l2=norm(a-b),reference_l2=norm(b),
                relative_l2=norm(a-b)/norm(b) if norm(b)>0 else None,
                exactly_equal=bool(np.array_equal(a,b)))


def project(phi,force):
    # Explicit order, no BLAS dot/matmul, no optimizer-selected contraction path.
    g=np.einsum('nr,kn->kr',phi,force,optimize=False)
    if not np.isfinite(g).all():raise ValueError('Nonfinite deterministic projection')
    return g


def image(phi,g):
    q=np.einsum('nr,kr->kn',phi,g,optimize=False)
    if not np.isfinite(q).all():raise ValueError('Nonfinite physical basis-image')
    return q


def mass_comparison(a,b,mass):
    num=float(np.einsum('kn,n,kn->',a-b,mass,a-b,optimize=False))
    den=float(np.einsum('kn,n,kn->',b,mass,b,optimize=False))
    return dict(mass_L2_difference=float(np.sqrt(max(num,0.))),
                reference_mass_L2=float(np.sqrt(max(den,0.))),
                mass_relative_L2_difference=float(np.sqrt(num/den)) if den>0 else None,
                maxabs_difference=inf(a-b))


def label(g):
    return dict(gradient_inf=inf(g),gradient_l2=norm(g),gradient_inf_tolerance=GTOL,
                below_or_equal_threshold=bool(inf(g)<=GTOL))


def csv_write(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=keys,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def save(fig,path,caption,provenance):
    fig.savefig(path,dpi=155);plt.close(fig)
    path.with_suffix('.md').write_text('# '+path.stem+'\n\n'+caption+'\n\n## Data provenance\n\n'+provenance+
        '\n\n## How to read\n\n'+caption+
        '\n\n## Limitation\n\n'+SCOPE+' Coefficient infinity norms across different bases are not coordinate-invariant. '
        'Physical basis-image q=Phi(Phi^T R) comparisons use one independent deterministic CPU nodal mass. '
        'No independent full Gram, SVD or subspace-angle computation is added; q is not certified as an exact orthogonal projector. '
        'All physical arrays and metrics are untransformed. Display log floors apply only to figures. '
        'Figures need visual inspection before report adoption.\n',encoding='utf-8')


def plots(out,rows,physical_rows,spread,repeat,forces,numpy_forces,inp,provenance):
    fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained')
    groups=[('gpu','Saved GPU projection'),('numpy_same_force','NumPy projection: same saved force'),
            ('numpy_q4_force','NumPy projection: independent Q4 force')]
    force_labels=FORCES
    all_values=[r['gradient_inf'] for r in rows]
    lo=np.log10(DISPLAY_FLOOR);hi=max(np.log10(max(all_values+[DISPLAY_FLOOR])),np.log10(GTOL)+.5)
    for ax,(kind,title) in zip(axs,groups):
        lookup={(r['force'],r['basis']):r for r in rows if r['calculation']==kind}
        values=np.array([[lookup[(f,b)]['gradient_inf'] for b in BASES] for f in force_labels])
        im=ax.imshow(np.log10(np.maximum(values,DISPLAY_FLOOR)),aspect='auto',vmin=lo,vmax=hi,cmap='viridis')
        for i,f in enumerate(force_labels):
            for j,b in enumerate(BASES):
                ax.text(j,i,f'{values[i,j]:.2e}\n'+('PASS' if values[i,j]<=GTOL else 'MISS'),ha='center',va='center',fontsize=6,color='white')
        ax.set_xticks(range(4),BASES,rotation=35);ax.set_yticks(range(8),force_labels);ax.set_title(title,fontsize=10)
    fig.colorbar(im,ax=axs.tolist(),shrink=.7,label='log10(g infinity); display floor 1e-20')
    fig.suptitle('Frozen PIDL c20s4: unchanged head target 1e-10 | per-basis labels, not validity gates')
    save(fig,out/'readout_cross_projection.png','Three cross tables separate saved GPU reduction, deterministic NumPy reduction of the identical force, '
        'and independent native-Q4 force replay. Rows identify actual full-network or cached-leaf force observations; columns identify saved/fresh bases. '
        'Each cell prints its untransformed g infinity and the unchanged 1e-10 PASS/MISS label. Log colour floor 1e-20 is display only.',provenance)
    fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    ax=axs[0,0]
    for group in ['network','nodal']:
        rr=[r for r in spread if r['group']==group]
        ax.plot(range(4),[r['coefficient_range_inf'] for r in rr],'o-',label=group+' force repeats')
    ax.set_xticks(range(4),BASES,rotation=25);ax.set_ylabel('max coordinate range of g (same basis)');ax.legend(fontsize=8)
    ax.set_title('Fixed Phi: force-repeat effect')
    ax=axs[0,1]
    for kind in ['saved_network_0','independent_Q4_network_0']:
        rr=[r for r in physical_rows if r['fixed_force']==kind]
        ax.plot(range(4),[r['mass_L2_difference'] for r in rr],'o-',label=kind)
    ax.set_xticks(range(4),BASES,rotation=25);ax.set_ylabel('CPU mass L2 of q_basis - q_source');ax.legend(fontsize=7)
    ax.set_title('Fixed force: physical basis-image change')
    ax=axs[1,0]
    for b in BASES:
        rr=[r for r in rows if r['basis']==b and r['calculation']=='numpy_same_force']
        ax.plot(range(8),[r['GPU_projection_maxabs_difference'] for r in rr],'o-',label=b)
    ax.set_xticks(range(8),FORCES,rotation=50);ax.set_ylabel('maxabs GPU g - NumPy g');ax.legend(fontsize=7)
    ax.set_title('Same Phi and saved force: reduction-order difference')
    ax=axs[1,1]
    ax.plot(range(len(repeat)),[inf(x) for x in repeat],'o-',label='five fixed force / fixed Phi GPU reductions')
    ax.axhline(GTOL,color='r',ls='--',label='unchanged 1e-10 target');ax.set_xlabel('projection repetition');ax.set_ylabel('g infinity')
    ax.set_title('No force or basis change');ax.legend(fontsize=7)
    for ax in axs.flat:ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.grid(alpha=.2)
    fig.suptitle('PIDL c20s4 numerical attribution | coefficient spread and physical q have separate units')
    save(fig,out/'readout_attribution.png','Upper left fixes each Phi and varies only saved force repetition; range is max coordinate peak-to-peak, with network and leaf groups separate. '
        'Upper right fixes R and compares physical basis-images q=Phi(Phi^T R) against source in the same independent CPU mass norm. '
        'Lower left fixes both Phi and saved R and compares GPU versus NumPy projection. Lower right repeats exactly the same GPU force/Phi operation five times. '
        'All y axes are linear with scientific notation; coordinate norms and physical-image norms are never merged.',provenance)
    fig,axs=plt.subplots(2,3,figsize=(14,9),layout='constrained');cells=inp['cells'];poly=inp['nodes'][cells]
    differences=[forces['network_0']-numpy_forces['network_0'],forces['nodal_0']-numpy_forces['nodal_0'],forces['network_2']-forces['network_0']]
    titles=['network 0 minus NumPy Q4','cached leaf 0 minus NumPy Q4','network 2 minus network 0']
    for k,component in enumerate(['nodal gu','nodal gv']):
        means=[np.mean(x[k][cells],axis=1) for x in differences];lo,hi=finite_range(means,signed=True)
        for j,(v,title) in enumerate(zip(means,titles)):
            pc=panel(axs[k,j],poly,v,title+' | '+component,lo,hi,signed=True)
        cb=fig.colorbar(pc,ax=axs[k,:].tolist(),shrink=.72,pad=.01);cb.set_ticks(np.linspace(lo,hi,5));cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2e'))
        cb.set_label(component+' signed difference; native force units')
    fig.suptitle('Frozen PIDL c20s4: spatial location and amplitude of numerical force differences')
    save(fig,out/'readout_force_differences.png','Rows are nodal horizontal/vertical force differences; columns separate GPU-versus-independent-Q4 and full-network repeat differences. '
        'For display only, the four nodal force values are averaged within each Q4 cell; shared signed linear limits within each component row, five numeric ticks. '
        'Forces are not divided by area or mass. Full nodal arrays and maxabs/L2 diagnostics, rather than cell display means, are authoritative.',provenance)


def analyze(run,out,inputs_manifest=INPUTS,initial_run=INITIAL,render=True):
    if out.exists():raise FileExistsError('Refuse overwrite: '+str(out))
    out.mkdir(parents=True);sources=[];checks=[]
    def check(name,passed,**detail):checks.append(dict(check=name,passed=bool(passed),**detail))
    manifest=js(inputs_manifest,'input binding manifest',sources);item=next(x for x in manifest['cases'] if x['cycle']==20);ip=Path(item['path'])
    if ip.stat().st_size!=item['bytes'] or sha(ip)!=item['sha256']:raise ValueError('Bound input SHA/size mismatch')
    record(ip,'conditional accepted FEM c20s4 outer18 input',sources);record(Path(__file__),'offline analyzer',sources)
    with np.load(ip,allow_pickle=False) as z:inp={k:z[k] for k in z.files}
    op,oppath=independent_operator(ROOT);record(oppath,'independent NumPy Q4 operator',sources)
    geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo;n=len(inp['nodes']);mass=np.zeros(n)
    for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
    fem={k:inp[k+'_fem'].astype(float) for k in ['u','v','d']};ref=q4_fields(fem,inp,op,geo)
    check('independent_native_FEM_force',inf(ref['_nodal_force'].reshape(-1)-inp['ru_fem'].reshape(-1))<=1e-10 and ref['independent_free_u_l2']<1e-8,
          native_force_maxabs=inf(ref['_nodal_force'].reshape(-1)-inp['ru_fem'].reshape(-1)),free_u_l2=ref['independent_free_u_l2'])
    source_folder=worker_output(initial_run)/'c20_s4';source_info=js(source_folder/'result.json','unique learned-head source result',sources)
    check('accepted_source',source_info.get('status')=='completed' and source_info.get('actual_network') is not None and not source_info.get('rolled_back',False))
    source_fields=fields(source_folder/'fields.npz',n,sources,'unique learned-head source fields')
    case=worker_output(run)/'c20_s4';info=js(case/'result.json','zero-update audit result',sources)
    for key in ['weights_exact_unchanged','Smooth_B0_anchor_unchanged','mechanical_damage_exact_FEM','physical_state_exact_unchanged','threshold_is_readout_label_only']:
        check(key,info.get(key) is True)
    for key in ['optimizer_updates','parameter_updates','history_commits','rollout_steps','ridge']:
        check(key,info.get(key)==0)
    check('worker_completed',info.get('status')=='completed')
    check('fixed_target',info.get('gradient_inf_tolerance')==GTOL)
    check('single_cached_feature_encode',info.get('cached_features_encode_count')==1)
    check('basis_mass_is_frozen_mass0',info.get('basis_mass')=='mass0 only')
    if source_info.get('actual_network') is not None:
        check('declared_source_energy',abs(info['source_energy']-source_info['actual_network']['E_el'])<=1e-10)
    check('zero_weight_digest',bool(info.get('weights_before_sha256')) and info.get('weights_before_sha256')==info.get('weights_after_sha256'))
    check('state_identity',(info.get('cycle'),info.get('substep'),info.get('step'))==(20,4,99))
    check('fixed_repetition_counts',(info.get('network_repetitions'),info.get('nodal_repetitions'),info.get('fresh_svd_repetitions'))==(3,5,3))
    cached=fields(case/'cache/fields.npz',n,sources,'cached network0 fields')
    forces={};numpy_forces={};force_rows=[];raw_head={};physical_arrays={};metrics={}
    for name in FORCES:
        fp=case/'forces'/f'{name}.npz';f=fields(fp,n,sources,'frozen PIDL '+name);meta=js(fp.with_suffix('.json'),'force metadata '+name,sources)
        with np.load(fp,allow_pickle=False) as z:
            force=np.stack([np.asarray(z[k],dtype=float).reshape(-1) for k in ['gu','gv']])
            if name.startswith('network_'):
                if 'raw_head_gradient' not in z:raise ValueError('Missing same-graph raw UV-head gradient '+name)
                raw_head[name]=np.asarray(z['raw_head_gradient'],dtype=float)
        if force.shape!=(2,n) or not np.isfinite(force).all():raise ValueError('Invalid saved force '+name)
        for key in ['u','v','d']:
            check(name+' source '+key,inf(f[key]-source_fields[key])<=1e-12,maxabs=inf(f[key]-source_fields[key]))
            check(name+' cached '+key,inf(f[key]-cached[key])<=1e-12,maxabs=inf(f[key]-cached[key]))
        check(name+' exact mechanical FEM damage',np.array_equal(f['d'],fem['d']))
        try:boundary_check(f,fem,inp);bc=True
        except ValueError:bc=False
        check(name+' fixed boundary',bc)
        r,q=score(f,fem,inp,op,geo,ref,mass);metrics[name]=r
        for key,val in metric(ref['raw'],q['raw'],w).items():r['raw_vs_FEM_'+key]=val
        check(name+' source energy',abs(r['E_el']-info['source_energy'])<=1e-10,independent=r['E_el'])
        check(name+' GPU energy replay',abs(r['E_el']-meta['E_el'])<=1e-10,producer=meta['E_el'],independent=r['E_el'])
        nf=q['_nodal_force'].reshape(2,n);forces[name]=force;numpy_forces[name]=nf
        force_rows.append(dict(force=name,**comparison(force,nf),free_u_l2_GPU=norm(force.reshape(-1)[inp['freeu']]),free_u_l2_NumPy=r['free_u_l2']))
        physical_arrays.update({name+'__'+k:v for k,v in f.items()})
        physical_arrays.update({name+'__GPUforce':force,name+'__NumPyQ4force':nf,name+'__raw':q['raw'],name+'__active':q['active']})
    native=case/'native_fem_force.npz';record(native,'producer native FEM force',sources)
    with np.load(native,allow_pickle=False) as z:native_force=np.concatenate([z['gu'].reshape(-1),z['gv'].reshape(-1)])
    check('producer_native_FEM_force',inf(native_force-inp['ru_fem'].reshape(-1))<=1e-10,maxabs=inf(native_force-inp['ru_fem'].reshape(-1)))
    mass_rows=[]
    for name in ['mass0','gpu0','gpu1','gpu2','cpu_add_at','cpu_numpy_element_sums']:
        a=array(case/'mass'/f'{name}.npy','saved nodal mass '+name,sources)
        if a.shape!=(n,) or np.any(a<0):raise ValueError('Invalid mass '+name)
        mass_rows.append(dict(mass=name,**comparison(a,mass),mass_sum=float(a.sum()),reference_mass_sum=float(mass.sum())))
    mass_metadata=js(case/'mass/metadata.json','mass accumulation metadata',sources)
    features=array(case/'cache/features.npy','same cached hidden features',sources);bubble=array(case/'cache/bubble.npy','same cached boundary bubble',sources)
    check('cached_features_shape',features.shape==(n,400));check('cached_bubble_shape',bubble.shape==(n,))
    phi={};transforms={};basis_rows=[]
    for name in BASES:
        folder=case/'bases'/name;phi[name]=array(folder/'phi.npy','actual saved Phi '+name,sources);transforms[name]=array(folder/'transform.npy','actual saved T '+name,sources)
        meta=js(folder/'metadata.json','basis metadata '+name,sources)
        if phi[name].ndim!=2 or phi[name].shape[0]!=n or transforms[name].shape!=(401,phi[name].shape[1]):raise ValueError('Invalid basis shape '+name)
        check(name+' saved_rank_metadata',meta.get('retained_rank')==phi[name].shape[1])
        if name!='source':
            check(name+' current_full401',meta.get('original_columns')==401 and meta.get('cached_features') is True and meta.get('basis_mass')=='mass0')
        same=phi[name].shape==phi['source'].shape
        basis_rows.append(dict(basis=name,rank=phi[name].shape[1],phi_maxabs_difference_vs_source=inf(phi[name]-phi['source']) if same else None,
            same_coordinate_shape_as_source=same,phi_exactly_equal_source=bool(np.array_equal(phi[name],phi['source'])),
            whitened_gram_maxabs_error_producer=meta.get('whitened_gram_maxabs_error'),metadata=meta))
    gpu_archive=case/'projections.npz';record(gpu_archive,'saved GPU cross gradient vectors',sources)
    with np.load(gpu_archive,allow_pickle=False) as z:gpu={key:z[key] for key in z.files}
    gpu_labels=js(case/'projections.json','saved GPU cross threshold labels',sources)
    label_lookup={(r['force'],r['basis']):r for r in gpu_labels}
    rows=[];vectors={};spread=[];physical_rows=[];order_rows=[];qfields={}
    for bname in BASES:
        rank=phi[bname].shape[1];groups={'network':[],'nodal':[]}
        for fname in FORCES:
            key=fname+'__'+bname;g=np.asarray(gpu[key]).reshape(2,rank)
            if not np.isfinite(g).all():raise ValueError('Nonfinite saved GPU projected gradient')
            check('saved GPU threshold label '+key,label_lookup[(fname,bname)]['below_or_equal_threshold']==(inf(g)<=GTOL))
            gn=project(phi[bname],forces[fname]);gq=project(phi[bname],numpy_forces[fname])
            for kind,value in [('gpu',g),('numpy_same_force',gn),('numpy_q4_force',gq)]:
                row=dict(force=fname,basis=bname,rank=rank,calculation=kind,**label(value))
                if kind=='numpy_same_force':row.update(GPU_projection_maxabs_difference=inf(value-g),GPU_projection_l2_difference=norm(value-g))
                rows.append(row);vectors[kind+'__'+key]=value.reshape(-1)
            groups[fname.split('_')[0]].append(gn)
            if fname in raw_head:
                h=raw_head[fname]
                if h.shape!=(2,401) or not np.isfinite(h).all():raise ValueError('Invalid raw head gradient')
                hg=np.einsum('kc,cr->kr',h,transforms[bname],optimize=False)
                order_rows.append(dict(force=fname,basis=bname,rawhead_T_gradient_inf=inf(hg),Phi_R_gradient_inf=inf(gn),
                                       maxabs_order_difference=inf(hg-gn),l2_order_difference=norm(hg-gn)))
                vectors['rawhead_T__'+key]=hg.reshape(-1)
        for group,values in groups.items():
            gs=np.stack(values);spread.append(dict(basis=bname,group=group,repetitions=len(values),coefficient_range_inf=inf(np.ptp(gs,axis=0)),
                gradient_inf_range=float(np.ptp([inf(x) for x in values])),max_difference_from_first=inf(gs-gs[0])))
        for fname,force in [('saved_network_0',forces['network_0']),('independent_Q4_network_0',numpy_forces['network_0'])]:
            qfields[(fname,bname)]=image(phi[bname],project(phi[bname],force))
            physical_rows.append(dict(fixed_force=fname,basis=bname,**mass_comparison(qfields[(fname,bname)],qfields[(fname,'source')],mass)))
    repeat=array(case/'fixed_projection_repeat.npy','fixed force/source Phi repeated GPU projections',sources)
    if repeat.shape!=(5,2*phi['source'].shape[1]):raise ValueError('Invalid fixed projection repetition shape')
    repeat_rows=[dict(repetition=j,**label(g),maxabs_vs_first=inf(g-repeat[0])) for j,g in enumerate(repeat)]
    vectors['fixed_projection_repeat']=repeat;vectors['independent_CPU_mass']=mass
    for (force,basis),q in qfields.items():physical_arrays['basis_image__'+force+'__'+basis]=q
    np.savez_compressed(out/'gradient_vectors.npz',**vectors);np.savez_compressed(out/'physical_arrays.npz',**physical_arrays)
    csv_write(out/'cross_gradients.csv',rows);csv_write(out/'force_replay.csv',force_rows);csv_write(out/'mass_comparison.csv',mass_rows)
    csv_write(out/'fixed_basis_force_spread.csv',spread);csv_write(out/'fixed_force_basis_image.csv',physical_rows)
    csv_write(out/'projection_order.csv',order_rows);csv_write(out/'fixed_projection_repeat.csv',repeat_rows)
    csv_write(out/'field_metrics.csv',[dict(force=k,**v) for k,v in metrics.items()])
    valid=all(c['passed'] for c in checks)
    result=dict(protocol='S04-E011-HEAD-READOUT-AUDIT-OFFLINE-r1',run=str(run),status='verified_frozen_numerical_diagnosis' if valid else 'invalid_physical_or_frozen_contract',
        scope=SCOPE,validity_checks=checks,gradient_inf_tolerance=GTOL,threshold_misses_do_not_invalidate=True,
        weight_identity_proof='producer before/after state digests; offline analyzer does not load models',worker=info,
        field_metrics=metrics,force_replay=force_rows,cross_gradients=rows,basis_metadata=basis_rows,mass_comparisons=mass_rows,
        mass_metadata=mass_metadata,fixed_basis_force_spread=spread,fixed_force_physical_basis_image=physical_rows,
        fixed_projection_repeats=repeat_rows,projection_order=order_rows,
        fixed_projection_coefficient_range_inf=inf(np.ptp(repeat,axis=0)),
        independent_no_new_SVD=True,source_files=sources,
        interpretation='Within-basis repeat spread separates force observations from projection reduction. Fixed-force physical basis-images '
            'separate basis reconstruction from coordinate-infinity changes, but are not certified orthogonal projectors. Different-basis g infinity '
            'values alone cannot attribute variation to force. Fresh SVD bases all use mass0; GPU mass-repeat differences are not SVD-arm inputs. '
            'T-transformed raw parameter gradients versus Phi-transformed nodal forces are an auxiliary rounding/order comparison, not a new criterion. '
            'Original accepted endpoint and earlier verdicts remain unchanged; no optimizer step or capacity inference is made.')
    dump(out/'summary.json',result)
    provenance='Run: '+str(run)+'. Bound input and exact source identities, array paths, sizes and SHA256: summary.json/source_files. '
    if render:plots(out,rows,physical_rows,spread,repeat,forces,numpy_forces,inp,provenance)
    (out/'README_analysis.md').write_text('# Frozen PIDL c20s4 head-readout numerical diagnosis\n\n'+SCOPE+'\n\n'
        'Read summary.json validity_checks before interpreting gradients. A 1e-10 MISS is preserved as an observation, not an invalid experiment. '
        'Independent float64 NumPy native-Q4 forces, FEM field comparisons, raw/active weighted L2/correlations/integrals, saved GPU forces, full gradient vectors '
        'and physical basis-images are retained. No model is loaded or forwarded locally. The source FEM state is conditional accepted c20 outer18, not a complete trajectory.\n\n'
        '## Data provenance\n\n'+provenance+'\n\n## How to read\n\n'
        'readout_cross_projection.png separates force/operator/reduction sources. readout_attribution.png fixes one factor at a time. '
        'readout_force_differences.png locates signed nodal-force differences. All three have standalone explanatory sidecars. '
        'CSV files use LF line endings; gradient_vectors.npz contains every projection vector; physical_arrays.npz contains actual fields, raw/active GP arrays, '
        'nodal forces and physical basis-images. Coefficient arrays use blocked [u components, v components] ordering.\n\n## Limitation\n\n'+
        result['interpretation']+' Physical basis-image norms use one independently assembled CPU mass and avoid comparing incompatible coefficient coordinates. '
        'No new full Gram or subspace-angle calculation is performed; producer whitening metadata is retained. Figure display floors never clip metric arrays.\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--dest',type=Path)
    p.add_argument('--inputs-manifest',type=Path,default=INPUTS);p.add_argument('--initial-run',type=Path,default=INITIAL);p.add_argument('--no-render',action='store_true')
    a=p.parse_args();dest=a.dest or a.run/'analysis_head_readout_audit'
    result=analyze(a.run.resolve(),dest.resolve(),a.inputs_manifest.resolve(),a.initial_run.resolve(),not a.no_render)
    print(result['status'])
