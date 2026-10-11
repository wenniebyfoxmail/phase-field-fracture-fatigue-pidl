#!/usr/bin/env python3
"""Read saved native final residuals; distinguish boundary reactions from descent violations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import h5py
import matplotlib.pyplot as plt
import numpy as np
from analyze_fem_staggered_endpoints import parse_log
import run_multicycle_cross_replay as cross


def projected_gradient(d, gradient, lower, upper=1.0, tolerance=1e-10):
    """Feasible descent violations for minimization; coincident bounds have no free direction."""
    d, gradient, lower = np.broadcast_arrays(d, gradient, lower)
    if np.any(lower > upper):
        raise ValueError('invalid interval')
    at_lower = d <= lower + tolerance
    at_upper = d >= upper - tolerance
    result = gradient.copy()
    result[at_lower] = np.minimum(result[at_lower], 0.0)
    result[at_upper] = np.maximum(result[at_upper], 0.0)
    result[at_lower & at_upper] = 0.0
    return result


def norms(x):
    return {'l2': float(np.linalg.norm(x)), 'linf': float(np.abs(x).max())}


def read_endpoint(path, points, log, topology, tolerance, cells, geometry, pidl_path):
    with h5py.File(path) as h:
        oracle, endpoint, pre = h['matlab_residual'], h['converged_peak_solution'], h['pre_phase_input']
        cycle = int(endpoint['cycle'][0,0]); iteration = int(endpoint['staggered_iteration'][0,0])
        assert int(endpoint['step'][0,0]) == 4
        assert int(pre['cycle'][0,0]) == cycle and int(pre['step'][0,0]) == 4
        assert int(pre['staggered_iteration'][0,0]) == iteration
        d = np.asarray(endpoint['d']).reshape(-1)
        old = np.asarray(pre['p_field_old']).reshape(-1)
        indices = np.asarray(oracle['free_dof_d']).reshape(-1).astype(int)-1
        ru = np.asarray(oracle['R_u_free']).reshape(-1)
        rd = np.asarray(oracle['R_d_free']).reshape(-1)
        if len(d) != len(points) or not np.all(np.isfinite(rd)) or not np.all(np.isfinite(ru)):
            raise RuntimeError('invalid endpoint arrays')
        np.testing.assert_array_equal(np.asarray(oracle['p_field_old']).reshape(-1),old)
        np.testing.assert_array_equal(np.asarray(oracle['history_vars_old']),np.asarray(pre['history_vars_old']))
        for state in (pre,endpoint,oracle):
            if abs(float(state['load_factor'][0,0])-.11999988/.12)>1e-12: raise RuntimeError('not a peak-load state')
        if abs(float(pre['uy'][0,0])-.11999988)>1e-12 or abs(float(endpoint['uy'][0,0])-.11999988)>1e-12:
            raise RuntimeError('peak displacement mismatch')
        if len(indices)!=len(rd) or len(np.unique(indices))!=len(indices) or np.any(indices<0) or np.any(indices>=len(d)):
            raise RuntimeError('invalid free damage DOF map')
        if np.min(d) < -1e-12 or np.max(d) > 1+1e-12 or np.max(old-d) > 1e-12:
            raise RuntimeError('endpoint violates its nodal feasibility contract')
        box = projected_gradient(d[indices],rd,np.zeros(len(indices)))
        monotone = projected_gradient(d[indices],rd,old[indices])
        _, summaries = parse_log(log,topology,tolerance)
        row = next(x for x in summaries if x['cycle']==cycle)
        if row['iterations'] != iteration:
            raise RuntimeError('log/capture iteration mismatch')
        ru_norm=float(np.linalg.norm(ru)); rd_norm=float(np.linalg.norm(rd))
        # Both oracle and log use the same refreshed mechanical field. Log rounding permits 1e-8 error.
        cached = row['final_residual_sum']-ru_norm
        if cached < -1e-8:
            raise RuntimeError('negative inferred cached phase residual')
        if abs(ru_norm-float(oracle['norms/R_u_free_L2'][0,0]))>1e-12:
            raise RuntimeError('stored mechanical norm mismatch')
        raw_sq=float(np.sum(rd*rd))
        def location(values):
            mass=values**2; denom=float(mass.sum()); xy=points[indices]
            return {'squared_residual_x_centroid':float(np.sum(mass*xy[:,0])/denom) if denom else None,
                    'right_half_squared_share':float(mass[xy[:,0]>0].sum()/denom) if denom else None,
                    'bound_reaction_squared_fraction_removed':1-float(np.sum(values*values))/raw_sq}
        summary={'topology':topology,'cycle':cycle,'substep':4,'iteration':iteration,
                 'log_stop_sum':row['final_residual_sum'],'outer_tolerance':tolerance,
                 'native_free_u':norms(ru),'native_raw_free_d':norms(rd),
                 'inferred_cached_damage_residual':cached,
                 'raw_damage_over_cached':rd_norm/cached,
                 'box_feasible_d':{**norms(box),**location(box)},
                 'nodal_monotone_feasible_d':{**norms(monotone),**location(monotone)},
                 'same_field_box_sum':ru_norm+float(np.linalg.norm(box)),
                 'same_field_monotone_sum':ru_norm+float(np.linalg.norm(monotone)),
                 'lower_bound_node_fraction':float(np.mean(d[indices]<=1e-10)),
                 'accepted_bound_node_fraction':float(np.mean(d[indices]<=old[indices]+1e-10)),
                 'pre_to_endpoint_damage_max_abs':float(np.max(np.abs(d-np.asarray(pre['p_field']).reshape(-1)))),
                 'input':str(path.resolve()),'log':str(log.resolve())}
        shape,dshape,weights,_ = geometry
        mass=np.zeros(len(points))
        for j in range(cells.shape[1]):
            np.add.at(mass,cells[:,j],np.sum(weights*shape[:,j][None,:],axis=1))
        if np.any(mass<=0): raise RuntimeError('nonpositive nodal lumped mass')
        domain_area=float(weights.sum())
        dual=lambda x:float(np.sqrt(np.sum(x*x/mass[indices])))
        # Damage scale from frozen AT1 Gc/(cw*ell), cw=8/3; no new scientific pass gate.
        scale=.01/((8/3)*.01)*np.sqrt(domain_area)
        for name,val in (('box_feasible_d',box),('nodal_monotone_feasible_d',monotone)):
            summary[name]['lumped_mass_dual_l2']=dual(val)
            summary[name]['dual_over_AT1_scale']=dual(val)/scale
        summary['damage_reference_scale']=scale
        summary['domain_area']=domain_area
        with np.load(pidl_path) as z:
            if str(z['topology'].reshape(-1)[0])!=topology: raise RuntimeError('PIDL topology mismatch')
            cy=z['cycles']; at=np.flatnonzero(cy==cycle)
            if len(at)!=1: raise RuntimeError('PIDL cycle missing or duplicated')
            i=int(at[0])
            if int(z['steps'][i])!=5*cycle-1: raise RuntimeError('PIDL step mismatch')
            pu,pv,pd=(z[k][i].astype(float) for k in ('u_node','v_node','d_node'))
            if np.max(np.abs(z['node_coords']-points))>2e-8: raise RuntimeError('PIDL mesh mismatch')
        fu,fv=(np.asarray(endpoint[k]).reshape(-1) for k in ('u','v'))
        fa=cross.amor_raw(fu,fv,cells,dshape)*(1-cross.interp(d,cells,shape))**2
        pa=cross.amor_raw(pu,pv,cells,dshape)*(1-cross.interp(pd,cells,shape))**2
        gap_mass=np.zeros(len(points))
        for j in range(cells.shape[1]):
            np.add.at(gap_mass,cells[:,j],np.sum(weights*shape[:,j][None,:]*(pa-fa)**2,axis=1))
        # Attribute GP squared gap conservatively to nodes via N_i. Scores are diagnostic only.
        gap_density=gap_mass/mass
        residual_density=(monotone/mass[indices])**2
        gap_score=gap_density[indices]
        cut=float(np.quantile(gap_score,.95)); mask=gap_score>=cut
        residual_mass=monotone**2/mass[indices]
        summary['location_vs_active_gap']={
            'node_gap_top5_quantile':cut,
            'nodal_monotone_dual_squared_share_in_gap_top5':float(residual_mass[mask].sum()/residual_mass.sum()),
            'free_dof_mass_share_of_gap_top5':float(mass[indices][mask].sum()/mass[indices].sum()),
            'gap_squared_share_in_gap_top5':float(gap_mass[indices][mask].sum()/gap_mass[indices].sum()),
            'definition':'Native-GP squared active discrepancy assigned to nodes via N_i*w; top5 is diagnostic and has no pass threshold'}
        return summary,(points[indices],rd,box,monotone)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--q4-capture',type=Path,required=True); ap.add_argument('--t3-capture',type=Path,required=True)
    ap.add_argument('--q4-log',type=Path,required=True); ap.add_argument('--t3-log',type=Path,required=True)
    ap.add_argument('--handoff',type=Path,required=True); ap.add_argument('--analysis-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    cross.HANDOFF=args.handoff.resolve()
    summaries=[]; fields=[]
    for top in ('q4','t3'):
        points,cells,geometry=cross.load_mesh(top)
        pidl_path=args.analysis_root/'multicycle_cross_replay'/'pidl_nodal'/f'pidl_{top}_nodal_trajectory.npz'
        summary,field=read_endpoint(getattr(args,top+'_capture'),points,getattr(args,top+'_log'),top,4e-4,cells,geometry,pidl_path)
        summaries.append(summary); fields.append(field)
    payload={'schema':'s04e011-native-final-residual-projection-audit-v1','rows':summaries,
             'scope':'read-only saved native MATLAB oracle; no solve, history refresh, or new stationarity normalization',
             'constraint_warning':'box and nodal monotone projections are distinct diagnostic constraints; neither certifies GP-constrained KKT or fatigue fixed-point closure',
             'verdict':'CACHED_DAMAGE_RESIDUAL_DIFFERS__RAW_RESIDUAL_DOMINATED_BY_BOUND_REACTIONS',
             'blocked_conclusion':'Threshold adjacency or raw residual magnitude does not prove premature termination, physical invalidity, or causation of the FEM-PIDL field gap.'}
    (args.output/'summary.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    fig,axes=plt.subplots(2,3,figsize=(13,7),sharex=True,sharey=True)
    for row,(xy,raw,box,monotone) in enumerate(fields):
        for col,(value,title) in enumerate(((raw,'raw phase residual'),(box,'box feasible violation'),(monotone,'nodal monotone violation'))):
            z=np.log10(np.maximum(np.abs(value),1e-12))
            artist=axes[row,col].scatter(xy[:,0],xy[:,1],c=z,s=1,cmap='viridis',vmin=-12,vmax=-3)
            axes[row,col].set_title(f'{summaries[row]["topology"].upper()} c83 {title}')
            axes[row,col].set_aspect('equal'); axes[row,col].set_xlabel('x')
    fig.colorbar(artist,ax=axes.ravel().tolist(),label='log10 |nodal phase residual|',shrink=.7)
    fig.suptitle('Saved native c83 residuals: bound reactions and feasible descent violations')
    fig.savefig(args.output/'native_final_residual_projection.png',dpi=200,bbox_inches='tight')
    print(json.dumps(payload,indent=2))


if __name__=='__main__': main()
