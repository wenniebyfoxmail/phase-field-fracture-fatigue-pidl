#!/usr/bin/env python3
"""Independent offline Q4 analysis of installed UV-head Newton endpoints.

No model loading, training, solver evaluation, SSH, or history updates.  Partial
worker fields are theta0 fallbacks and are never scored as Newton candidates.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_block_diagnosis import independent_operator, q4_fields, dump, sha, metric

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011')
PBD = BASE/'runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production'
HEAD = BASE/'runs/pf_s04e011_uvhead_c3e4228_20261018T101024Z_production'
INPUTS = BASE/'pidl_block_preparation_20261017_v1/inputs_manifest.json'
METHODS = ['FEM', 'original_UV_FEMd', 'PBD_full_U_energy', 'UVHEAD_r1', 'Newton_head']
LABELS = ['conditional FEM', 'original UV + FEM d', 'PBD full-network U', 'UVHEAD-r1 fixed head', 'Newton fixed head']
FOUR = ['E_el', 'free_u_l2', 'uv_mass_rel_L2', 'uv_H1_rel']
ACTIVE_LOG_FLOOR = 1e-12  # Display only; common to both states, no metric clipping.
BOUNDARY = ('Independent conditional accepted FEM c1s4/c20s4 peaks, fixed exact FEM damage, '
            'native Q4/2x2 Gauss points, eta=0. Original UV, full-network U energy and both head '
            'candidates are frozen-damage mechanical blocks, not new jointly solved PIDL trajectories. '
            'No full-network capacity, physical truth, teacher, or fatigue-evolution certificate.')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def record(path, role, sources):
    row = dict(path=str(path.resolve()), role=role, bytes=path.stat().st_size, sha256=sha(path))
    sources.append(row)
    return row


def worker_output(run):
    return run/'retrieved/archive/output'


def fields(path, n, sources, role):
    record(path, role, sources)
    with np.load(path, allow_pickle=False) as z:
        f = {k:np.asarray(z[k], dtype=np.float64).reshape(-1) for k in ['u','v','d']}
    for k,v in f.items():
        if v.shape != (n,) or not np.isfinite(v).all():
            raise ValueError(f'Invalid {path}:{k}')
    return f


def score(f, fem, inp, op, geo, ref, mass):
    q = q4_fields(f, inp, op, geo)
    w = geo[2]
    uvden = float(np.sum(mass*(fem['u']**2+fem['v']**2)))
    hden = float(np.sum(w*np.sum(ref['gu']**2+ref['gv']**2,axis=2)))
    uvnum = float(np.sum(mass*((f['u']-fem['u'])**2+(f['v']-fem['v'])**2)))
    hnum = float(np.sum(w*np.sum((q['gu']-ref['gu'])**2+(q['gv']-ref['gv'])**2,axis=2)))
    if uvden <= 0 or hden <= 0:
        raise ValueError('Undefined displacement reference norm')
    r = dict(E_el=q['E_el'], free_u_l2=q['independent_free_u_l2'],
             uv_mass_rel_L2=float(np.sqrt(uvnum/uvden)), uv_H1_rel=float(np.sqrt(hnum/hden)),
             elastic_excess_relative_FEM=float(q['E_el']/ref['E_el']-1),
             active_integral=float(np.sum(w*q['active'])))
    for key,val in metric(ref['active'],q['active'],w).items():
        r['active_vs_FEM_'+key] = val
    return r,q


def verify_four(actual, independent):
    result = {}
    for key in FOUR:
        a,b = float(actual[key]),float(independent[key])
        if not np.isfinite([a,b]).all(): raise ValueError('Nonfinite '+key)
        error = abs(a-b)
        # Same existing offline audit definition; absolute guard handles FEM zeros.
        tolerance = 1e-12+1e-9*max(abs(a),abs(b))
        result[key] = dict(producer=a,independent=b,absolute_difference=error,
                           tolerance=tolerance,passed=bool(error<=tolerance))
    if not all(x['passed'] for x in result.values()):
        raise ValueError('Independent four-metric replay mismatch: '+str(result))
    return result


def endpoint(run, cycle, sources):
    folder = worker_output(run)/f'c{cycle}_s4'
    rp = folder/'result.json'
    if not rp.exists(): return None,dict(status='missing',folder=str(folder))
    record(rp, 'worker result', sources);info=read_json(rp)
    if info.get('status') != 'completed' or info.get('actual_network') is None:
        return None,dict(status=info.get('status','unknown'),folder=str(folder),
                         excluded_reason='No verified installed-head endpoint; fields may be theta0 fallback',worker=info)
    if not (folder/'fields.npz').exists():
        return None,dict(status='fields_missing',folder=str(folder),worker=info)
    if info.get('cycle') != cycle or info.get('substep') != 4:
        raise ValueError('Head state identity mismatch')
    for key in ['hidden_and_damage_head_exactly_unchanged','Smooth_B0_anchor_unchanged','frozen_damage_lower_f_unchanged']:
        if info.get(key) is not True: raise ValueError('Frozen contract missing/false: '+key)
    if info.get('history_commits') != 0 or info.get('rollout_steps') != 0:
        raise ValueError('Unexpected history/rollout update')
    return folder,dict(status='completed',folder=str(folder),worker=info)


def decision(state):
    """Keep reduced stationarity, actual installation, and global force distinct."""
    status=state['new_endpoint'];rows=state['metrics_by_method']
    if status['status']!='completed' or 'Newton_head' not in rows:
        return dict(retained_span_closed=False,conclusion='Newton endpoint unverified; no candidate, gain, or feature-floor claim')
    info=status['worker'];actual=info['actual_network'];solver=info.get('solver',{})
    actual_inf=actual.get('reduced_gradient_inf')
    cond_inf=info.get('conditioned_reduced_gradient_inf')
    if cond_inf is None:cond_inf=info.get('conditioned_gradient_inf')
    tolerance=float(solver.get('gtol',1e-10))
    actual_closed=actual_inf is not None and actual_inf<=tolerance
    conditioned_closed=cond_inf is not None and cond_inf<=tolerance
    if info.get('stationarity_closed') is not None and bool(info['stationarity_closed'])!=bool(actual_closed):
        raise ValueError('Worker stationarity flag differs from actual installed gradient')
    realization_limited=bool(conditioned_closed and not actual_closed)
    comparisons={}
    for label in ['PBD_full_U_energy','UVHEAD_r1']:
        if label in rows:
            b=rows[label]['E_el'];a=rows['Newton_head']['E_el']
            comparisons[label]=dict(energy_difference=a-b,relative_energy_reduction=1-a/b,
                                   interpretation='numerical comparison only; see full independent values')
    statement=('Actual installed network closes the declared reduced infinity-gradient criterion in the retained frozen-feature span. '
               'Any remaining FEM discrepancy is conditional on that retained span and fixed FEM damage; it is not a full-network capacity bound.'
               if actual_closed else
               'Conditioned coordinates close but actual installed-head gradient does not: numerical realization/implementation limit, not a represented-field floor.'
               if realization_limited else
               'Reduced stationarity remains unresolved within the declared budget; neither flat energy nor finite cap establishes a frozen-feature floor.')
    return dict(actual_reduced_gradient_inf=actual_inf,conditioned_reduced_gradient_inf=cond_inf,
                reduced_gradient_tolerance=tolerance,retained_span_closed=bool(actual_closed),
                realization_limited=realization_limited,global_nodal_force=rows['Newton_head']['free_u_l2'],
                actual_minus_conditioned_gradient_inf=info.get('actual_minus_conditioned_gradient_inf'),
                actual_minus_conditioned_energy=info.get('actual_minus_conditioned_energy'),
                linear_vs_actual_uv_maxabs=info.get('linear_vs_actual_uv_maxabs'),
                solver_stop=solver.get('stop'),comparisons=comparisons,conclusion=statement)


def finite_range(values, signed=False):
    if signed:
        lim=max((float(np.max(np.abs(v))) for v in values),default=0.)
        lim=max(lim,1e-16);return -lim,lim
    lo=min(float(np.min(v)) for v in values);hi=max(float(np.max(v)) for v in values)
    if hi<=lo:
        pad=max(abs(lo)*1e-12,1e-16);lo-=pad;hi+=pad
    return lo,hi


def panel(ax, polygons, values, title, lo, hi, signed=False):
    pc=PolyCollection(polygons,array=values,cmap='RdBu_r' if signed else 'viridis',
                      norm=Normalize(lo,hi),edgecolors='none',rasterized=True)
    ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(title,fontsize=8)
    ax.set_xlabel('native x');ax.set_ylabel('native y')
    return pc


def save_figure(fig,path,caption,provenance):
    fig.savefig(path,dpi=155);plt.close(fig)
    path.with_suffix('.md').write_text(
        '# '+path.stem+'\n\n'+caption+'\n\n'
        '## Data provenance\n\n'+provenance+'\n\n'
        '## How to read\n\n'
        'Read panel titles for the exact method and quantity; compare FEM-first method columns within each field row. '
        'The figure-specific caption above defines axes, panels, colour limits and endpoint markers. '
        'Missing/partial panels are labelled explicitly.\n\n'
        '## Limitation\n\n'+BOUNDARY+' '
        'All accepted endpoints and missing/partial statuses are named in summary.json; missing candidates are not zero or theta0. '
        'Displacement and signed UV-error colour scales are linear. Mechanical-field active panels show '
        'log10(max(GP-weighted active cell mean, 1e-12)), with the same display floor in both states and no upper clipping. '
        'Comparisons share limits within each quantity row, not across quantities or states. '
        'GP/Jacobian-weighted Q4 cell means are rendered; full GP metrics, nodal mass-L2 and full gradient-H1 are in metrics.csv. '
        'Reduced-coordinate gradient is distinct from global nodal force; a flat loss is not stationarity. '
        'Images require visual inspection before adoption into the report.\n')


def state_maps(out,state,inp,geo,op,physical,gp,provenance):
    cycle=state['cycle'];N,_,w,_=geo;c=inp['cells'];poly=inp['nodes'][c]
    mean=lambda x:np.sum(w*x,axis=1)/w.sum(1)
    fig,axs=plt.subplots(3,5,figsize=(18,10),layout='constrained',squeeze=False)
    for row,(key,label) in enumerate([('u','horizontal displacement u'),('v','vertical displacement v'),('active','log10(active cell mean)')]):
        vals={name:mean(gp[name]['active'] if key=='active' else op.interp(f[key],c,N)) for name,f in physical.items()}
        if key=='active':
            vals={name:np.log10(np.maximum(value,ACTIVE_LOG_FLOOR)) for name,value in vals.items()}
        lo,hi=finite_range(list(vals.values()));pcs=[]
        for j,(name,title) in enumerate(zip(METHODS,LABELS)):
            ax=axs[row,j]
            if name not in vals:
                ax.text(.5,.5,'NO VERIFIED ENDPOINT',ha='center',va='center',transform=ax.transAxes,fontsize=8)
                ax.set_title(label+' | '+title,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,poly,vals[name],title if row==0 else label,lo,hi))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[row,:].tolist(),shrink=.75,pad=.01)
            cb.set_ticks(np.linspace(lo,hi,5))
            cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f' if key=='active' else '%.2e'))
            cb.set_label(label+'; display floor=1e-12' if key=='active' else label)
    fig.suptitle(f'c{cycle}s4 | FEM-first mechanical fields, exact fixed FEM d | u/v linear; active log10 cell mean',fontsize=11)
    save_figure(fig,out/f'c{cycle}_mechanical_fields.png',
                f'Conditional FEM and four explicitly named PIDL U candidates at c{cycle}s4. '
                'Rows u/v/log10(active cell mean); fixed exact FEM damage in every method. FEM is the first column. '
                'The u/v rows use linear colour scales. Active is first averaged over the Q4 cell with GP/Jacobian weights, '
                'then displayed as log10(max(cell mean, 1e-12)); both states use the same fixed display floor and no upper clipping. '
                'Full-GP energy/field metrics remain untransformed. Each row shares limits across all methods; no row-to-row colour comparison. '
                'Blank Newton or old-head panels mean endpoint missing/partial, not a candidate.',provenance)
    fig,axs=plt.subplots(2,4,figsize=(15,7),layout='constrained',squeeze=False)
    for row,key in enumerate(['u','v']):
        errors={name:mean(op.interp(f[key]-physical['FEM'][key],c,N)) for name,f in physical.items() if name!='FEM'}
        lo,hi=finite_range(list(errors.values()),signed=True);pcs=[]
        for j,(name,title) in enumerate(zip(METHODS[1:],LABELS[1:])):
            ax=axs[row,j]
            if name not in errors:
                ax.text(.5,.5,'NO VERIFIED ENDPOINT',ha='center',va='center',transform=ax.transAxes,fontsize=8)
                ax.set_title(title,fontsize=8);ax.set_axis_off();continue
            pcs.append(panel(ax,poly,errors[name],key+': '+title+' minus FEM',lo,hi,signed=True))
        if pcs:
            cb=fig.colorbar(pcs[0],ax=axs[row,:].tolist(),shrink=.75,pad=.01)
            cb.set_ticks(np.linspace(lo,hi,5));cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2e'));cb.set_label('signed '+key+' error')
    fig.suptitle(f'c{cycle}s4 | signed displacement errors to FEM, Newton at right | linear shared row scales',fontsize=11)
    save_figure(fig,out/f'c{cycle}_uv_errors.png',
                f'Signed u and v errors, candidate minus conditional FEM at c{cycle}s4. '
                'The right column is the installed Newton head only if verified. '
                'Every row has one symmetric linear colour scale with five numeric ticks, explicitly formatted in scientific notation. '
                'No clipping or symmetry-log remapping.',provenance)


def scalar_figures(out,states,provenance):
    fig,axs=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    specs=[('elastic_excess_relative_FEM','Elastic excess / FEM'),('free_u_l2','Global free-u nodal force L2'),
           ('uv_mass_rel_L2','Displacement mass relative L2'),('uv_H1_rel','Q4 gradient/H1 relative error'),
           ('active_vs_FEM_relative_L2','Active weighted relative L2'),('active_integral','Active integral')]
    for state in states:
        cy=state['cycle'];rows=state['metrics_by_method']
        for ax,(key,title) in zip(axs.ravel(),specs):
            values=[rows.get(name,{}).get(key,np.nan) for name in METHODS]
            ax.plot(range(5),[np.nan if v is None else v for v in values],'o-',label=f'c{cy}s4')
            ax.set_xticks(range(5),['FEM','Original UV','PBD full U','Head r1','Newton head'],rotation=25,ha='right',fontsize=8)
            ax.set_title(title,fontsize=10);ax.grid(alpha=.2)
    for ax in axs.ravel():
        if ax.lines:ax.legend(fontsize=8)
    fig.suptitle('Same native-Q4 elastic energy, same fixed FEM damage | full independent replay',fontsize=11)
    save_figure(fig,out/'newton_head_decision.png',
                'Both prescribed peak states and all five mechanical comparators. Energy excess, global nodal force, '
                'mass/H1 field errors and full-GP active diagnostics answer different questions. '
                'Linear vertical scales; small FEM force may be visually near zero, exact values remain in metrics.csv. '
                'No reduced-gradient threshold is applied to the global-force panel.',provenance)
    fig,axs=plt.subplots(1,3,figsize=(15,4.4),layout='constrained')
    any_trace=False
    for state in states:
        cy=state['cycle'];info=state['new_endpoint'];accepted=state.get('accepted',[])
        if info['status']!='completed':continue
        fem=state['metrics_by_method']['FEM']['E_el']
        x=[r.get('evaluations',r.get('call',r.get('evaluation'))) for r in accepted]
        energy=[r.get('E_el',r.get('Eel')) for r in accepted]
        infs=[r.get('reduced_gradient_inf',r.get('gradient_inf',r.get('gradientinf'))) for r in accepted]
        l2s=[r.get('reduced_gradient_l2',r.get('gradient_l2')) for r in accepted]
        valid=[i for i in range(len(x)) if x[i] is not None and energy[i] is not None]
        if valid:
            any_trace=True;axs[0].plot([x[i] for i in valid],[energy[i]/fem-1 for i in valid],'o-',ms=3,label=f'c{cy}s4')
        for ax,ys in [(axs[1],infs),(axs[2],l2s)]:
            valid=[i for i in range(len(x)) if x[i] is not None and ys[i] is not None]
            if valid:ax.plot([x[i] for i in valid],[ys[i] for i in valid],'o-',ms=3,label=f'c{cy}s4 accepted conditioned')
        worker=info['worker'];actual=worker['actual_network'];last_call=worker.get('evaluations')
        if last_call is not None:
            axs[0].plot(last_call,actual['E_el']/fem-1,'x',ms=7,label=f'c{cy} actual installation')
            for ax,key in [(axs[1],'reduced_gradient_inf'),(axs[2],'reduced_gradient_l2')]:
                if actual.get(key) is not None:ax.plot(last_call,actual[key],'x',ms=7,label=f'c{cy} actual installation')
    for ax,title in zip(axs,['Accepted elastic excess / FEM','Retained-coordinate gradient infinity norm','Retained-coordinate gradient L2']):
        ax.set_title(title,fontsize=10);ax.set_xlabel('Objective/gradient evaluations, trials counted');ax.grid(alpha=.2)
        if ax.lines:ax.legend(fontsize=7)
        else:ax.text(.5,.5,'No verified Newton trace',ha='center',transform=ax.transAxes)
    axs[1].axhline(1e-10,color='.4',ls='--',lw=.8)
    for ax in axs[1:]:ax.set_yscale('log')
    fig.suptitle('Newton accepted points only | endpoint crosses show actual installed network | gradients are not global force',fontsize=10)
    save_figure(fig,out/'newton_head_stationarity.png',
                'All available accepted Newton points; rejected line-search trials are not endpoints. '
                'The evaluation axis counts trials and contracts; crosses show the independently checked actual installed endpoint. '
                'The dashed 1e-10 line applies only to the declared reduced infinity-gradient criterion; it does not apply to L2 or global nodal force. '
                'Conditioned-coordinate convergence and actual-network realization are recorded separately in summary.json. '
                'Energy excess uses a linear ordinate and both gradient norms use logarithmic ordinates; zero norms are absent from the logarithmic display, never interpreted as missing convergence evidence. '
                'Small energy increments or budget/deadline stopping do not certify stationarity; missing/partial traces are excluded.',provenance)


def analyze(run,out,inputs_manifest=INPUTS,pbd=PBD,head=HEAD,render=True):
    if out.exists():raise FileExistsError('Refuse overwriting analysis '+str(out))
    out.mkdir(parents=True);sources=[];record(inputs_manifest,'SHA-bound input adapter manifest',sources)
    manifest=read_json(inputs_manifest);op,oppath=independent_operator(ROOT);record(oppath,'independent NumPy Q4 operator',sources)
    record(Path(__file__),'offline analyzer',sources)
    states=[];rows=[]
    for cy in [1,20]:
        item=next(x for x in manifest['cases'] if x['cycle']==cy);path=Path(item['path'])
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('Input SHA/size mismatch')
        record(path,'conditional FEM / original PIDL input c'+str(cy),sources)
        with np.load(path,allow_pickle=False) as z:inp={k:z[k] for k in z.files}
        n=len(inp['nodes']);c=inp['cells'];geo=op.q4_geometry(inp['nodes'],c);N,B,w,_=geo
        mass=np.zeros(n)
        for j in range(4):np.add.at(mass,c[:,j],np.sum(w*N[:,j],axis=1))
        fem={k:np.asarray(inp[k+'_fem'],dtype=float) for k in ['u','v','d']}
        ref=q4_fields(fem,inp,op,geo)
        native_error=float(np.max(np.abs(ref['_nodal_force']-inp['ru_fem'])))
        if native_error>1e-10 or ref['independent_free_u_l2']>1e-8:raise ValueError('FEM force reference contract mismatch')
        physical={'FEM':fem};scored={};metrics={};checks={}
        case=worker_output(pbd)/f'c{cy}_s4'
        for name,filename in [('original_UV_FEMd',case/'fields.npz'),('PBD_full_U_energy',case/'U_energy/fields.npz')]:
            if filename.exists():physical[name]=fields(filename,n,sources,name)
        oldfolder,oldstate=endpoint(head,cy,sources);newfolder,newstate=endpoint(run,cy,sources)
        if oldfolder:physical['UVHEAD_r1']=fields(oldfolder/'fields.npz',n,sources,'verified UVHEAD r1')
        if newfolder:physical['Newton_head']=fields(newfolder/'fields.npz',n,sources,'verified Newton head')
        for name,f in physical.items():
            if not np.array_equal(f['d'],fem['d']):raise ValueError(f'Fixed FEM damage changed: c{cy} {name}')
            r,q=score(f,fem,inp,op,geo,ref,mass);r.update(cycle=cy,substep=4,method=name,fixed_FEM_damage_exact=True)
            metrics[name]=r;scored[name]=q;rows.append(r)
        for name,status in [('UVHEAD_r1',oldstate),('Newton_head',newstate)]:
            if name in metrics:checks[name]=verify_four(status['worker']['actual_network'],metrics[name])
        state=dict(cycle=cy,substep=4,FEM_reference=item['fem'],native_FEM_force_maxabs_error=native_error,
                   metrics_by_method=metrics,old_endpoint=oldstate,new_endpoint=newstate,independent_four_checks=checks,
                   missing_methods=[x for x in METHODS if x not in physical],accepted=[])
        if newfolder and (newfolder/'accepted.json').exists():
            record(newfolder/'accepted.json','Newton accepted points',sources);state['accepted']=read_json(newfolder/'accepted.json')
        if newfolder and (newfolder/'trace.json').exists():
            record(newfolder/'trace.json','Newton all evaluation trace',sources);state['trace']=read_json(newfolder/'trace.json')
        state['decision']=decision(state);states.append(state)
        provenance=f'New Run {run.name}: {worker_output(run)}; previous UVHEAD Run {head.name}; PBD Run {pbd.name}. Exact paths, SHA256, state labels and all metrics: summary.json and metrics.csv. Canonical inputs: {path}.'
        if render:state_maps(out,state,inp,geo,op,physical,scored,provenance)
    provenance=f'New Run {run.name}; two independent states c1s4/c20s4. Earlier Runs {pbd.name} and {head.name}; input SHA-bound by {inputs_manifest}. Source hashes and exact metrics in summary.json/metrics.csv.'
    if render:scalar_figures(out,states,provenance)
    with (out/'metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(protocol='S04-E011-UVHEAD-NEWTON-offline-r1',run=str(run),inputs_manifest=str(inputs_manifest),
                 sources=sources,states=states,rows=rows,claim_boundary=BOUNDARY,
                 gradients_boundary='Actual installed reduced gradient, conditioned reduced gradient and global nodal force are different quantities. A numerical realization limit is not a feature-capacity limit.',
                 unverified_newton_states=[s['cycle'] for s in states if s['new_endpoint']['status']!='completed'])
    dump(out/'summary.json',summary)
    (out/'README_analysis.md').write_text(
        '# UV-head Newton comparison\n\n'+BOUNDARY+'\n\n'
        'Offline NumPy-only readout; no model loading, new optimization, history update or SSH. '
        'Both prescribed states and five named methods are included. Inputs are checked against the preparation manifest SHA and size. '
        'FEM damage equality is exact. Eel/global force/mass-L2/H1 are independently recomputed and the actual worker four metrics checked. '
        'Missing or partial worker endpoints are retained as statuses; their theta0 fallback fields are excluded.\n\n'
        'Read summary.json and metrics.csv first. Each mechanical_fields figure is FEM-first u/v on shared linear colour scales '
        'and log10(max(GP-weighted active cell mean, 1e-12)) on a shared active-row scale. '
        'The fixed active display floor is common to both states; there is no upper clipping and full-GP metrics remain unchanged. '
        'uv_errors contains signed candidate-minus-FEM displacement errors, Newton at right, with five numeric ticks per colourbar. '
        'Decision and stationarity plots separate energy, global force, actual reduced stationarity and conditioned-coordinate behavior. '
        'A completed run is not necessarily a converged head. Only actual reduced infinity-gradient closure can qualify the retained-span endpoint; '
        'energy flatness, finite caps, conditioned closure alone, and full-network expressivity are not interchangeable. '
        'Raw-head installation errors are reported separately, never relabelled as a represented-field floor.\n\n'
        'All six figures have standalone sidecars. Open and inspect rendered images before updating any user-facing report. '
        'B0 Smooth Boundary and constrained-Q4 damage routes remain unchanged; these blocks do not advance either fatigue history or damage.\n')
    return summary


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--dest',type=Path);ap.add_argument('--inputs-manifest',type=Path,default=INPUTS)
    ap.add_argument('--pbd-run',type=Path,default=PBD);ap.add_argument('--head-run',type=Path,default=HEAD)
    a=ap.parse_args();out=a.dest if a.dest else a.run/'analysis_head_newton'
    s=analyze(a.run.resolve(),out.resolve(),a.inputs_manifest.resolve(),a.pbd_run.resolve(),a.head_run.resolve())
    print(json.dumps(dict(out=str(out),unverified_newton_states=s['unverified_newton_states']),indent=2))


if __name__=='__main__':main()
