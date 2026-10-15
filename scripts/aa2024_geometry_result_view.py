#!/usr/bin/env python3
"""E016 completed-validation figures only: no raw nodemap, fit or solve entry."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from aa2024_geometry_prior import ARMS, PREP, FIT, completed, bindings, load, sha, finite_predictions

VALIDATION=('metrics.json','validation_fields.npz')


def closed_form_residual(xy, raw, w):
    """Same global planar rigid subspace, scalar sums instead of BLAS matmul."""
    pos=xy-np.sum(w[:,None]*xy,axis=0)/w.sum()
    rotation=np.column_stack((-pos[:,1],pos[:,0]))
    shift=np.sum(w[:,None]*raw,axis=0)/w.sum()
    denominator=np.sum(w*np.sum(rotation**2,axis=1))
    if not np.isfinite(denominator) or denominator<=0:raise ValueError('rigid support rank')
    theta=np.sum(w*np.sum(rotation*(raw-shift),axis=1))/denominator
    projected=raw-shift-theta*rotation
    if not np.isfinite(projected).all():raise ValueError('nonfinite closed-form residual')
    return projected


def checked_data(prepare, fit, validation):
    pr=completed(prepare,'prepare',PREP)
    fr=completed(fit,'fit',FIT)
    vr=completed(validation,'validate',VALIDATION)
    pb=bindings(prepare,PREP);fb=bindings(fit,FIT);vb=bindings(validation,VALIDATION)
    fm=json.loads((fit/'fit.json').read_text());m=json.loads((validation/'metrics.json').read_text())
    if fr.get('input_bindings')!=pb or fm.get('source_prepare')!=pb:
        raise ValueError('mixed fit/preparation provenance')
    if vr.get('input_bindings')!=fb or m.get('source_fit')!=fb:
        raise ValueError('mixed validation/fit provenance')
    if fm.get('status')!='four_predictions_frozen_before_held_response' or fm.get('cycle')!='292018.5':
        raise ValueError('fit status/cycle')
    if m.get('target_member_sha256')!=fm.get('held_member_sha256'):
        raise ValueError('target identity binding')
    frozen=load(fit/'frozen_predictions.npz');finite_predictions(frozen)
    a=load(validation/'validation_fields.npz');ids=a['ids'];n=len(ids)
    if (n<10 or not np.issubdtype(ids.dtype,np.integer) or
        len(np.unique(ids))!=n or len(np.unique(frozen['ids']))!=len(frozen['ids'])):
        raise ValueError('validation ID identity/count')
    lookup={int(v):i for i,v in enumerate(frozen['ids'])}
    if any(int(v) not in lookup for v in ids):raise ValueError('validation ID outside frozen support')
    idx=np.array([lookup[int(v)] for v in ids])
    if not np.array_equal(ids,frozen['ids'][idx]):raise ValueError('validation ID identity')
    if np.any(np.diff(idx)<=0):raise ValueError('validation ID ordering')
    for name in ('xy','weights'):
        if not np.array_equal(a[name],frozen[name][idx]):raise ValueError('changed validation '+name)
    xy,w=a['xy'],a['weights']
    if xy.shape!=(n,2) or w.shape!=(n,) or not np.isfinite(xy).all() or not np.isfinite(w).all() or not np.all(w>0):
        raise ValueError('validation support finite/shape/weights')
    if a['target'].shape!=(n,2) or not np.isfinite(a['target']).all():raise ValueError('target finite/shape')
    missing=np.ones(len(frozen['ids']),bool);missing[idx]=False
    if (m.get('eligible')!=n or m.get('frozen_support')!=len(missing) or
        m.get('missing_ids')!=frozen['ids'][missing].tolist() or
        not np.isclose(m.get('area_coverage',np.nan),w.sum()/frozen['weights'].sum(),rtol=1e-12,atol=1e-15)):
        raise ValueError('support metadata inconsistency')
    if set(m.get('MAE_mm',{}))!=set(ARMS):raise ValueError('four-arm metrics required')
    cross={}
    for k in ARMS:
        value=a[k];residual=a[k+'_residual']
        if value.shape!=(n,2) or not np.array_equal(value,frozen[k][idx]):raise ValueError('changed frozen prediction '+k)
        if residual.shape!=(n,2) or not np.isfinite(residual).all():raise ValueError('residual finite/shape '+k)
        check=closed_form_residual(xy,value-a['target'],w)
        if not np.allclose(check,residual,rtol=1e-12,atol=1e-15):raise ValueError('residual/projection mismatch '+k)
        score=float(np.sum(w*np.linalg.norm(residual,axis=1))/w.sum())
        declared=m['MAE_mm'][k]
        if not np.isfinite(declared) or declared<0 or not np.isclose(score,declared,rtol=1e-12,atol=1e-15):
            raise ValueError('metric/residual inconsistency '+k)
        cross[k]=dict(stored_residual_MAE_mm=score,
            closed_form_MAE_mm=float(np.sum(w*np.linalg.norm(check,axis=1))/w.sum()),
            closed_form_max_abs_difference_mm=float(np.max(np.abs(check-residual))))
    delta=m['MAE_mm']['old']-m['MAE_mm']['proxy']
    if m.get('primary_old_minus_proxy_mm')!=delta or m.get('descriptive_outcome')!=('improves' if delta>0 else 'equal' if delta==0 else 'worsens'):
        raise ValueError('primary contrast/outcome mismatch')
    lineage=dict(source_prepare=pb,source_fit=fb,source_validation=vb,
        run_ids=dict(prepare=pr['run_id'],fit=fr['run_id'],validation=vr['run_id']),
        plotter_sha256=sha(__file__),cycle=fm['cycle'],stage=15,
        target_member_sha256=m['target_member_sha256'])
    return a,m,lineage,cross


def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=170);fig.savefig(out/(name+'.pdf'));plt.close(fig)


def render(prepare, fit, validation, out):
    # Integrity checks precede creating any output directory or figure.
    a,m,lineage,cross=checked_data(prepare,fit,validation)
    if out.exists():raise ValueError('fresh figure directory required')
    out.mkdir(parents=True)
    provenance=('E016 | controlled experiment | cycle292018.5 | train13/14 -> held15 | '+
        lineage['run_ids']['fit']+' / '+lineage['run_ids']['validation'])
    scores=[m['MAE_mm'][k] for k in ARMS];delta=m['primary_old_minus_proxy_mm']
    fig,ax=plt.subplots(figsize=(9,4.4),constrained_layout=True)
    colors=('#0072B2','#D55E00','#888888','#009E73')
    for i,(k,s,c) in enumerate(zip(ARMS,scores,colors)):
        ax.plot([0,s],[i,i],color=c,lw=1.5);ax.scatter(s,i,color=c,s=35)
        ax.annotate(f'{s:.9g}',(s,i),xytext=(7,0),textcoords='offset points',va='center',fontsize=9)
    ax.set_yticks(range(4),ARMS);ax.invert_yaxis();ax.set_xlim(0,max(max(scores)*1.35,1e-12))
    ax.set_xlabel('area-weighted global-rigid-quotient vector MAE [mm]; lower is better')
    ax.set_title(f'old minus proxy = {delta:.9g} mm ({m["descriptive_outcome"]})\n'+
        f'{m["eligible"]} common points; training-weight coverage {m["area_coverage"]:.3%}; no repeat-based uncertainty',fontsize=10)
    fig.suptitle(provenance,fontsize=9);save(fig,out,'held_scores')

    limit=max(float(np.linalg.norm(a[k+'_residual'],axis=1).max()) for k in ARMS)
    fig,axes=plt.subplots(2,2,figsize=(10,6.8),constrained_layout=True)
    for ax,k in zip(axes.ravel(),ARMS):
        c=ax.scatter(*a['xy'].T,c=np.linalg.norm(a[k+'_residual'],axis=1),s=10,
            cmap='magma',vmin=0,vmax=limit if limit>0 else 1e-15)
        ax.set_title(k+f' | MAE={m["MAE_mm"][k]:.7g} mm',fontsize=10)
        spatial_axes(ax)
    fig.colorbar(c,ax=axes.ravel().tolist(),label='projected vector residual norm [mm]; common scale')
    fig.suptitle(provenance+'\nAll eligible points; missing support blank, not a crack label',fontsize=9)
    save(fig,out,'held_residuals')

    fig,axes=plt.subplots(2,5,figsize=(16,6),constrained_layout=True)
    keys=('target',)+ARMS
    signed=max(float(np.abs(a[k]).max()) for k in keys)
    for col,k in enumerate(keys):
        for row,component in enumerate(('delta U','delta V')):
            ax=axes[row,col]
            bound=signed if signed>0 else 1e-15
            c=ax.scatter(*a['xy'].T,c=a[k][:,row],s=7,cmap='RdBu_r',vmin=-bound,vmax=bound)
            ax.set_title(k+' | '+component,fontsize=9);spatial_axes(ax)
    fig.colorbar(c,ax=axes.ravel().tolist(),label='raw same-reference increment [mm]; common signed scale')
    fig.suptitle(provenance+'\nRaw increments shown without alignment; error metric uses one global rigid quotient',fontsize=9)
    save(fig,out,'held_increment_fields')

    with (out/'scores.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['arm','vector_MAE_mm','eligible','area_coverage'])
        for k in ARMS:writer.writerow([k,m['MAE_mm'][k],m['eligible'],m['area_coverage']])
    (out/'arithmetic_crosscheck.json').write_text(json.dumps(cross,indent=2,allow_nan=False))
    guide=('## Figure question\n\n'
        'Question: does the frozen training-opening-derived prior procedure reduce held response error versus the old prior?\n'
        '\n## How to read / visual grammar and panel guide\n\n'
        'Read held_scores, held_residuals, then held_increment_fields. Scores/Delta in source metrics.json are authoritative.\n'
        'All four frozen arms use identical eligible IDs, inherited training weights and global planar rigid subspace.\n'
        'No fit, parameter search, raw nodemap parsing, smoothing, point deletion or target-selected example in this renderer.\n'
        'Every eligible point is shown; blank support is not interpreted as crack geometry. Axes cover the whole fixed artificial patch.\n'
        'Residual maps share0..globalmax; raw U/V fields share one signed scale and remain unaligned.\n'
        'Only an exactly zero field uses a display-only1e-15mm color range; this is not a numerical/physical acceptance threshold.\n'
        'Delta=old MAE-proxy MAE uses unrounded values; report intact/secant too. No physical/noise threshold or confidence interval.\n'
        '\n## Limitations and claim boundary\n\n'
        'One cycle/specimen, shared origin13 and loading direction: not independent repeat evidence, real tip recovery or future-cycle skill.\n'
        'Auxiliary interpolation/source anomalies and2D/static assumptions remain; no per-side rigid alignment.\n'
        'Source-bound receipt checks do not independently authenticate runtime history or raw target correctness.\n\n'
        '## Data provenance\n\n'
        'Lineage: '+json.dumps(lineage,ensure_ascii=False)+'\n\n'
        '## Key numerical takeaway\n\n'
        'Source metrics: '+json.dumps(m,ensure_ascii=False)+'\n\n'
        '## Related assets\n\n'
        'scores.csv; arithmetic_crosscheck.json; render_receipt.json; same-stem PNG/PDF.\n')
    (out/'README_analysis.md').write_text(guide)
    descriptions=dict(held_scores='Four frozen MAEs in mm and the unrounded primary old-minus-proxy contrast.',
        held_residuals='Four projected residual norms on identical points, shared scale; lower is better.',
        held_increment_fields='Target and four frozen raw planar increments, U/V rows and common signed scale; not a deformed geometry.')
    for name,text in descriptions.items():(out/(name+'.md')).write_text('# '+name+'\n\n'+text+'\n\n'+guide)
    receipt=dict(lineage,artifacts_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()})
    (out/'render_receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False))


def spatial_axes(ax):
    ax.set_aspect('equal');ax.set_xlim(-18,18);ax.set_ylim(-9,9)
    ax.set_xlabel('stage13 reference x [mm]');ax.set_ylabel('stage13 reference y [mm]')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepare','fit','validation','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();render(a.prepare,a.fit,a.validation,a.output)


if __name__=='__main__':main()
