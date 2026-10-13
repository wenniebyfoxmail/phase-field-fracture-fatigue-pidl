#!/usr/bin/env python3
"""Exact E015 asset/result figures; no real solve, fit or held scoring."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from aa2024_boundary_basis import load,DOMAINS,ARMS,completed,bindings,FIT_ARTIFACTS

def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=180);fig.savefig(out/(name+'.pdf'));plt.close(fig)

def assets(root,out):
    completed(root,'prepare',('preparation.json','prepared.npz'))
    a=load(root/'prepared.npz');meta=json.loads((root/'preparation.json').read_text())
    fig,axes=plt.subplots(2,4,figsize=(14,6),constrained_layout=True)
    for row,b in enumerate(DOMAINS):
        mesh=a[b+'_mesh'];bd=a[b+'_boundary']
        for col,key in enumerate(('d0','br','bl')):
            ax=axes[row,col];c=ax.scatter(*mesh.T,c=a[b+'_'+key],s=6,cmap='viridis',vmin=0,vmax=1)
            ax.set_title(b+' '+key+' (PRIOR)');fig.colorbar(c,ax=ax)
        ax=axes[row,3];ax.scatter(*a['xy'].T,s=5,color='#0072B2',label='common fit observations')
        ax.scatter(*mesh[bd].T,s=7,color='#D55E00',label='Dirichlet boundary')
        ax.quiver(*mesh[bd].T,*a[b+'_bc'].T,angles='xy',scale_units='xy',scale=1/333,color='#D55E00')
        ax.set_title(b+' training BC; arrows x333');ax.legend(fontsize=7)
        for ax in axes[row]:
            ax.set_aspect('equal');ax.set_xlim(-22.5,22.5);ax.set_ylim(-13.5,13.5)
            ax.set_xlabel('reference x [mm]');ax.set_ylabel('reference y [mm]')
    fig.suptitle('E015 | cycle225211.5 | stages10/11 only | fixed priors and artificial boundaries')
    save(fig,out,'spatial_assets')
    return 'Preparation metadata: '+json.dumps(meta)+'\nNo high response or real mechanics solve in asset plotting.'

def results(fit,validation,out):
    completed(fit,'fit',FIT_ARTIFACTS)
    completed(validation,'validate',('metrics.json','validation_fields.npz'))
    p=json.loads((fit/'profiles.json').read_text());m=json.loads((validation/'metrics.json').read_text())
    if m.get('source_fit')!=bindings(fit,FIT_ARTIFACTS):raise ValueError('mixed fit/validation provenance')
    a=load(validation/'validation_fields.npz')
    for k in ARMS:
        check=float(np.sum(a['weights']*np.linalg.norm(a[k+'_residual'],axis=1))/a['weights'].sum())
        if not np.isclose(check,m['MAE_mm'][k],rtol=1e-12,atol=1e-15):raise ValueError('metric/residual inconsistency')
    train=np.array([[p[b]['profile'][p[b]['selected'][k]]['train_MAE_mm'] for k in ('K0','K1')] for b in DOMAINS])
    held=np.array([[m['MAE_mm'][b+k] for k in ('K0','K1')] for b in DOMAINS])
    fig,axes=plt.subplots(1,2,figsize=(9,3.5),constrained_layout=True)
    for ax,x,title in zip(axes,(train,held),('training loads10/11','held load12')):
        c=ax.imshow(x,cmap='viridis',vmin=0,vmax=max(train.max(),held.max()))
        ax.set_xticks([0,1],['K0 right only','K1 two tips']);ax.set_yticks([0,1],['B0 inner','B1 outer'])
        for row in range(2):
            for col in range(2):ax.text(col,row,f'{x[row,col]:.7g}',ha='center',color='white',fontsize=10,
                bbox=dict(facecolor='black',alpha=.5,edgecolor='none'))
        ax.set_title(title);fig.colorbar(c,ax=ax,label='vector MAE [mm]; shared scale')
    fig.suptitle(f"E015 | cycle225211.5 | D(boundary-only minus basis-only)={m['contrasts']['primary_boundary_only_minus_basis_only_mm']:.7g}mm\nheld secant={m['MAE_mm']['secant']:.7g}mm; conditional diagnostic, NOT causal identification",fontsize=10)
    save(fig,out,'factorial_errors')
    profiles=np.array([[r['train_MAE_mm'] for r in p[b]['profile']] for b in DOMAINS])
    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,b,x in zip(axes,DOMAINS,profiles):
        c=ax.imshow(x.reshape(6,21),origin='lower',aspect='auto',cmap='viridis',vmin=profiles.min(),vmax=profiles.max(),extent=(-.02375,.97375,-.095,1.045))
        for k,marker in (('K0','o'),('K1','x')):
            r=p[b]['profile'][p[b]['selected'][k]];ax.scatter(r['qR'],r['qL'],marker=marker,c='red',s=40,label=k+' frozen')
        ax.set_xlabel('qR');ax.set_ylabel('qL');ax.set_title(b+' training profile, NOT posterior');ax.legend(fontsize=8)
        fig.colorbar(c,ax=ax,label='training vector MAE [mm]; shared scale')
    save(fig,out,'parameter_profiles')
    limit=max(float(np.linalg.norm(a[k+'_residual'],axis=1).max()) for k in ARMS)
    fig,axes=plt.subplots(3,3,figsize=(12,8),constrained_layout=True)
    for ax,k in zip(axes.ravel(),ARMS):
        c=ax.scatter(*a['xy'].T,c=np.linalg.norm(a[k+'_residual'],axis=1),s=8,cmap='magma',vmin=0,vmax=max(limit,1e-15))
        ax.set_aspect('equal');ax.set_xlim(-18,18);ax.set_ylim(-9,9)
        ax.set_title(k+f"\nMAE={m['MAE_mm'][k]:.7g}mm",fontsize=9)
        ax.set_xlabel('reference x [mm]');ax.set_ylabel('reference y [mm]')
    fig.colorbar(c,ax=axes.ravel().tolist(),label='global rigid-quotient residual norm [mm]; shared scale')
    fig.suptitle(f"E015 | cycle225211.5 held12 | all {m['eligible']} common observations | frozen nine arms",fontsize=11)
    save(fig,out,'held_residuals')
    return 'Exact held metrics: '+json.dumps(m)+'\nTraining selection/profile: '+json.dumps(p)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('assets','results'))
    p.add_argument('--input',type=Path,required=True);p.add_argument('--validation',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    if a.mode=='results' and a.validation is None:raise ValueError('validation required')
    text=assets(a.input,a.output) if a.mode=='assets' else results(a.input,a.validation,a.output)
    guide='# E015 exact-output diagnostic figures\n\nSource: '+str(a.input.resolve())+'\n\n'
    guide+='Purpose: conditional boundary-placement/domain-extent versus nested basis-capacity sensitivity.\n'
    guide+='Read spatial assets before solve; after validation read factorial_errors, parameter_profiles, held_residuals.\n'
    guide+='Same0.9mm FEM spacing, same training ROI/areaweights and same held eligibility for every arm.\n'
    guide+='No clipping, smoothing, target-selected examples or outlier deletion. All eligible points/all252profile values displayed.\n'
    guide+='All MAEs use one global weighted planar-rigid quotient. Fields use same frame/common residual scale.\n'
    guide+='One cycle of one released experimental trajectory; nodes are not independent experimental units.\n'
    guide+='Priors and artificial BCs are assumptions, not measured true damage/grips. No DIC noise model or posterior.\n'
    guide+='No causal diagnosis, material/fatigue/phase-field recovery, future-cycle/road skill follows.\n\n'+text
    (a.output/'README_analysis.md').write_text(guide)
    for f in a.output.glob('*.png'):f.with_suffix('.md').write_text(guide)

if __name__=='__main__':main()
