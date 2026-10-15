#!/usr/bin/env python3
"""Render the exact scored Q4 coupled-repair fields; no solve or interpolation."""
import argparse,csv,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm,Normalize
from run_multicycle_cross_replay import q4_geometry,interp,amor_raw


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--mesh',type=Path,required=True);a=p.parse_args()
    out=a.run/'analysis';summary=json.loads((out/'coupled_analysis.json').read_text());assert summary['status']=='offline_checked'
    scored={(int(r['cycle']),r['stage'],r['snapshot']):r for r in csv.DictReader((out/'coupled_snapshots.csv').open())}
    with h5py.File(a.mesh) as h:points=np.asarray(h['node_coords']).T;c=np.asarray(h['connectivity_q4']).T.astype(int)-1
    N,B,w,_=q4_geometry(points,c);polys=points[c];mask=(polys[:,:,1].min(axis=1)<=.035)&(polys[:,:,1].max(axis=1)>=-.035)
    fields={};reductions=[]
    for cycle in [1,83]:
        for stage in ['baseline','last_accepted']:
            with h5py.File(a.run/'retrieved/output'/f'c{cycle}_{stage}'/'coupled_result.mat') as h:
                for snap in ['initial','final']:
                    g=h['out/'+snap];d=np.asarray(g['d']).reshape(-1);u=np.asarray(g['u']).reshape(-1);raw=np.asarray(g['raw']).T
                    assert np.isfinite(d).all() and np.isfinite(raw).all()
                    active=raw*(1-interp(d,c,N))**2
                    integral=float(np.sum(w*active));assert abs(integral-float(scored[cycle,stage,snap]['active_integral']))<1e-12
                    fields[cycle,stage,snap]=(d,u,active)
                    reductions.append(dict(cycle=cycle,stage=stage,snapshot=snap,d_min=float(d.min()),d_max=float(d.max()),active_integral=integral,active_gp_max=float(active.max())))
    vmax=max(x[2].max() for x in fields.values());norm=LogNorm(vmin=1e-10,vmax=vmax)
    fig,axs=plt.subplots(4,4,figsize=(16,9),layout='constrained')
    for ri,(cycle,stage) in enumerate([(1,'baseline'),(1,'last_accepted'),(83,'baseline'),(83,'last_accepted')]):
        for ci,(snap,channel) in enumerate([('initial','damage'),('final','damage'),('initial','active'),('final','active')]):
            d,_,active=fields[cycle,stage,snap];values=d[c].mean(axis=1) if channel=='damage' else np.sum(w*active,axis=1)/w.sum(axis=1)
            ax=axs[ri,ci];pc=PolyCollection(polys[mask],array=values[mask],cmap='Blues' if channel=='damage' else 'magma',norm=Normalize(0,1) if channel=='damage' else norm,rasterized=True,edgecolors='none');ax.add_collection(pc)
            ax.set_xlim(-.5,.5);ax.set_ylim(-.035,.035);ax.set_yticks([-.03,0,.03]);ax.set_xlabel('x (model length)');ax.grid(alpha=.12)
            if ci==0:ax.set_ylabel(f'c{cycle} {stage}\ny (model length)')
            if ri==0:ax.set_title(('Prior DR' if snap=='initial' else 'Coupled final')+' | '+channel)
            if ci==1:dmap=pc
            if ci==3:amap=pc
    fig.colorbar(dmap,ax=axs[:,:2],label='Nodal damage, Q4 cell mean [0,1]',shrink=.7)
    fig.colorbar(amap,ax=axs[:,2:],label='Active driver, GP-weighted cell mean (log scale)',shrink=.7,extend='min')
    fig.suptitle('All four frozen-history starts | native Q4 cell rendering | crack-band crop, vertical scale magnified\n'+a.run.name,fontsize=12)
    fig.savefig(out/'coupled_fields.png',dpi=180);plt.close(fig)
    with (out/'field_map_reductions.csv').open('w',newline='') as f:writer=csv.DictWriter(f,fieldnames=list(reductions[0]),lineterminator='\n');writer.writeheader();writer.writerows(reductions)
    between={}
    for cycle in [1,83]:
        da,ua,aa=fields[cycle,'baseline','final'];db,ub,ab=fields[cycle,'last_accepted','final']
        between[str(cycle)]=dict(d_maxabs=float(np.max(np.abs(da-db))),u_maxabs=float(np.max(np.abs(ua-ub))),active_relative_l2_baseline_denominator=float(np.sqrt(np.sum(w*(ab-aa)**2)/np.sum(w*aa**2))))
    (out/'final_start_sensitivity.json').write_text(json.dumps(between,indent=2)+'\n')
    (out/'coupled_fields.md').write_text('''# Coupled-repair damage and active fields\n\nQuestion: where did the scored fields change as the same-field joint residual closed? All four declared starts are shown, prior DR endpoint (coherent fresh initial audit) versus final coupled state. Data provenance: verified coupled_result.mat, coupled_analysis.json and coupled_snapshots.csv. No new field solve.\n\nDamage uses arithmetic nodal means on each native Q4 cell; active uses the physical GP/Jacobian-weighted cell mean. This rendering changes neither scored GP fields nor topology. Integrals independently match the scored CSV within 1e-12; see field_map_reductions.csv. Common damage limits [0,1] and common logarithmic active limits across all rows. Positive active values below 1e-10 are under-range (colorbar arrow); zero values are masked on the log scale; no threshold is used in scoring. Domain is cropped to |y|<=.035, full x; vertical scale is magnified.\n\nHow to read: c1 changes are modest; both c83 final fields show near-through right ligament damage and greatly reduced active support. Limitations: numerical joint closure alone does not establish improved PIDL agreement, history propagation, a preferred physical branch, teacher qualification or physical truth.\n''')
    print(json.dumps(between,indent=2))

if __name__=='__main__':main()
