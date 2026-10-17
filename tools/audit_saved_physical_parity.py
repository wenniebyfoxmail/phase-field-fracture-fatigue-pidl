"""Read saved nodal fields on paired physical probes; never solve or train.

Q4 uses native bilinear interpolation, with the existing cell diagonal used
only for point location. T3 uses native barycentric interpolation. History is
a declared GP/Jacobian-weighted cell mean, never a nodal nearest-neighbour map.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np
from scipy.io import loadmat
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


def q4_shape(z):
    x, y = z.T
    n = np.stack(((1-x)*(1-y), (1+x)*(1-y), (1+x)*(1+y), (1-x)*(1+y)), 1)/4
    dn = np.stack((np.stack((-(1-y), 1-y, 1+y, -(1+y)), 1),
                   np.stack((-(1-x), -(1+x), 1+x, 1-x), 1)), 1)/4
    return n, dn


class Probe:
    def __init__(self, points, cells, query):
        self.points, self.cells, self.query = points, cells, query
        self.q4 = cells.shape[1] == 4
        tris = np.stack((cells[:, [0,1,2]], cells[:, [0,2,3]]), 1).reshape(-1,3) if self.q4 else cells
        self.tri = mtri.Triangulation(*points.T, tris)
        index = self.tri.get_trifinder()(*query.T)
        if np.any(index < 0):
            raise ValueError('query outside saved mesh')
        self.parent = index//2 if self.q4 else index
        self.conn = cells[self.parent]
        xy = points[self.conn]
        if self.q4:
            z = np.zeros_like(query)
            for _ in range(16):
                n, dn = q4_shape(z)
                residual = np.einsum('pn,pni->pi', n, xy)-query
                jac = np.einsum('pin,pnj->pij', dn, xy)
                step = np.linalg.solve(jac.transpose(0,2,1), residual[...,None])[...,0]
                z -= step
                if np.max(abs(step)) < 1e-12:
                    break
            self.n, dn = q4_shape(z)
            jac = np.einsum('pin,pnj->pij', dn, xy)
            self.gradn = np.einsum('pij,pjn->pin', np.linalg.inv(jac), dn)
            if np.max(abs(z)) > 1+1e-9:
                raise ValueError('Q4 inverse map escaped cell')
            g = 1/np.sqrt(3)
            _, dg = q4_shape(np.array([[g,g],[-g,g],[g,-g],[-g,-g]]))
            self.gpw = np.linalg.det(np.einsum('gin,pnj->pgij',dg,xy))
        else:
            a = np.stack((xy[:,1]-xy[:,0], xy[:,2]-xy[:,0]), 2)
            rs = np.linalg.solve(a, (query-xy[:,0])[...,None])[...,0]
            self.n = np.column_stack((1-rs.sum(1),rs))
            self.gradn = np.einsum('pij,jn->pin',np.linalg.inv(a).transpose(0,2,1),
                                   np.array([[-1,1,0],[-1,0,1]]))
            self.gpw = np.ones((len(query),3))
        self.map_error = float(np.max(abs(np.einsum('pn,pni->pi',self.n,xy)-query)))
        if self.map_error > 1e-10 or np.any(self.gpw <= 0):
            raise ValueError('invalid interpolation geometry')

    def value(self, f):
        return np.einsum('pn,pn->p', self.n, np.asarray(f)[self.conn])

    def gradient(self, f):
        return np.einsum('pin,pn->pi',self.gradn,np.asarray(f)[self.conn])

    def cell_mean(self, f):
        f = np.asarray(f)[self.parent]
        return np.sum(self.gpw*f,axis=1)/self.gpw.sum(1)

    def fields(self, u, v, d, load):
        gu, gv = self.gradient(u), self.gradient(v)
        ex, ey, shear = gu[:,0], gv[:,1], gu[:,1]+gv[:,0]
        # The existing common-operator AMOR plane-strain formula, E=1, nu=.3.
        mu, bulk = 1/(2*1.3), 1/(3*(1-2*.3))
        raw = .5*bulk*np.maximum(ex+ey,0)**2 + mu*((2/3)*(ex**2+ey**2-ex*ey)+.5*shear**2)
        dd = self.value(d)
        return dict(u=self.value(u), v_correction=self.value(v)-load*(self.query[:,1]+.5),
                    d=dd, eps_xx=ex, eps_yy=ey, gamma_xy=shear,
                    raw=raw, active=(1-dd)**2*raw)


def grid(bounds, nx, ny):
    x0,x1,y0,y1 = bounds
    x = np.linspace(x0,x1,nx+1); y = np.linspace(y0,y1,ny+1)
    x,y = (x[:-1]+x[1:])/2, (y[:-1]+y[1:])/2
    xx,yy = np.meshgrid(x,y)
    return x,y,np.column_stack((xx.ravel(),yy.ravel()))


def main(args):
    root, out = args.root, args.out
    out.mkdir(parents=True,exist_ok=False)
    pair = root/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z'
    ncp = root/'local_archive/experiments/S04-E011/runs/pf_s04e011_ncp_348be4b_20261017T2029Z'
    mcs = root/'local_archive/experiments/S04-E011/runs/pf_s04e011_mcs_20261017_v1'
    sources=[]
    def record(p):
        if str(p) not in [a['path'] for a in sources]:
            sources.append(dict(path=str(p),bytes=p.stat().st_size))
    # Reuse the owner's retrieval receipt and recheck only the four files read.
    verify=json.loads((ncp/'retrieval_verification.json').read_text())
    assert verify['all_hashes_and_sizes_match']
    records={r['relative']:r for r in verify['manifest']}
    def ncpfile(rel):
        p=ncp/'retrieved'/rel; record(p); r=records[rel]
        assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
        return p
    meshpath=pair/'analysis/trajectory_error/raw/mesh_for_fem_trajectory.mat';record(meshpath)
    mesh=loadmat(meshpath);points=mesh['points'];cells=mesh['q4cells'].astype(int)-1
    check=np.load(ncpfile('archive/readout/mesh.npz'))
    assert np.array_equal(check['connectivity'],cells) and np.max(abs(check['node_coords']-points))<2e-8
    mirrored=points*np.array([1,-1]);dist,idx=cKDTree(points).query(mirrored)
    support=dict(nodes=len(points),mirror_match_tol=1e-12,matched_nodes=int(np.sum(dist<1e-12)),
                 max_nearest_reflection_distance=float(dist.max()),nearest_unique=int(len(np.unique(idx))),
                 nearest_is_involution=bool(np.array_equal(idx[idx],np.arange(len(idx)))))
    print(json.dumps(support),flush=True)
    ncpdata={s:dict(np.load(ncpfile(f'archive/readout/fields/c1_s{s}.npz'))) for s in [2,4]}
    # Saved original FEM snapshots, not the owner's new local re-solves.
    fem={}
    fm=json.loads((mcs/'retrieval_verification.json').read_text())
    assert fm['all_hashes_and_sizes_match']
    frecords={r['relative'].replace('\\','/'):r for r in fm['manifest']}
    for s in [1,2,4]:
        p=mcs/'retrieved/inputs'/f'c0001_s00{s}_post_commit.mat';record(p)
        receipt=frecords['inputs/'+p.name]
        assert p.stat().st_size==receipt['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==receipt['sha256']
        with h5py.File(p) as h:
            z=h['request28_snapshot']; assert int(z['cycle'][0,0])==1 and int(z['substep'][0,0])==s
            assert np.array_equal(np.array(z['connectivity']).T.astype(int)-1,cells)
            assert np.max(abs(np.array(z['node_coords']).T-points))<1e-14
            uv=np.array(z['u_node']);load=.12*float(z['load_factor'][0,0])
            assert np.max(abs(uv[1,abs(points[:,1]-.5)<1e-12]-load))<1e-12
            fem[s]=dict(u=uv[0],v=uv[1],d=np.array(z['d_node']).ravel(),
                        hist=np.array(z['alpha_bar_gp']).T,load=load)
    rows=[];maps={};coordinates={};mapping={}
    for region,bounds,nx,ny in [('domain',(-.49,.49,-.49,.49),81,80),
                                ('front',(0,.5,-.04,.04),151,80),
                                ('front_fine',(0,.5,-.04,.04),302,160)]:
        x,y,query=grid(bounds,nx,ny);pr=Probe(points,cells,query);mapping[region]=pr.map_error
        coordinates[region]=(x,y)
        def measure(label,fields,load,timing):
            for name,val in fields.items():
                a=val.reshape(ny,nx);parity=-1 if name in ['v_correction','gamma_xy'] else 1
                delta=a-parity*a[::-1]
                rms=float(np.sqrt(np.mean(delta**2)));scale=.12 if name in ['u','v_correction'] else 1
                norm=float(np.sqrt(np.mean(a*a)))
                rows.append(dict(region=region,state=label,field=name,load=load,timing=timing,
                                 parity='odd' if parity==-1 else 'even',mirror_RMS=rms,
                                 mirror_RMS_scaled=rms/scale,field_RMS=norm,
                                 mirror_relative_L2=rms/norm if norm>1e-30 else None))
                if region=='front_fine':maps[(label,name)]=a
        for s in [2,4]:
            p=ncpdata[s];load=.05999988 if s==2 else .11999988
            field=pr.fields(p['u'],p['v'],p['d'],load)
            measure(f'PIDL-Q4-c1s{s}',field,load,'post-solve, native nodal reconstruction')
            measure(f'PIDL-Q4-c1s{s}-history',dict(hist_pre=pr.cell_mean(p['hist_fat_pre']),
                        hist_post=pr.cell_mean(p['hist_fat_post']),f_pre=pr.cell_mean(p['f_pre'])),
                        load,'pre=input previous commit; post=current commit; GP weighted cell means')
        measure('PIDL-Q4-c1s1-inherited',dict(d=pr.value(ncpdata[2]['hist_alpha_pre']),
                    hist_post=pr.cell_mean(ncpdata[2]['hist_fat_pre'])),fem[1]['load'],
                    'c1s1 accepted d/history inherited by c1s2; no saved s1 u/v in this readout')
        for s,p in fem.items():
            field=pr.fields(p['u'],p['v'],p['d'],p['load']);field['hist_post']=pr.cell_mean(p['hist'])
            measure(f'FEM-Q4-c1s{s}',field,p['load'],'original post-commit snapshot; FEM reference unqualified')
    with (out/'parity_metrics.csv').open('w') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
    summary=dict(source_commit='ad749c8bbba8120b3961add989b11427fab86254',support=support,
                 probe_map_error=mapping,sources=sources,optimizer_steps=0,history_updates=0,FEM_solves=0,
                 timing='first complete Q4 PIDL observed block c1s2; d/history available from c1s1; no causal onset order',
                 representation='Q4 native bilinear reconstruction at paired probes; history native weighted cell means',
                 reference_role='original FEM numerical comparator, not qualified teacher',
                 script=str(Path(__file__).resolve()))
    (out/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    np.savez_compressed(out/'front_fields.npz',x=coordinates['front_fine'][0],y=coordinates['front_fine'][1],
                       **{'__'.join(k):v for k,v in maps.items()})
    x,y=coordinates['front_fine'];fig,axes=plt.subplots(4,4,figsize=(12,10),layout='constrained')
    for row,name in enumerate(['d','v_correction','gamma_xy','active']):
        f=maps[('FEM-Q4-c1s2',name)];p=maps[('PIDL-Q4-c1s2',name)]
        scale=.12 if name=='v_correction' else 1;f=f/scale;p=p/scale
        delta=p-f;odd=name in ['v_correction','gamma_xy'];mir=p-(-1 if odd else 1)*p[::-1]
        lo,hi=min(f.min(),p.min()),max(f.max(),p.max())
        for j,a in enumerate([f,p,delta,mir]):
            if j<2:vmin,vmax=lo,hi;cmap='magma' if name in ['d','active'] else 'coolwarm'
            else:vmax=max(float(abs(a).max()),1e-15);vmin=-vmax;cmap='coolwarm'
            im=axes[row,j].pcolormesh(x,y,a,shading='auto',cmap=cmap,vmin=vmin,vmax=vmax,rasterized=True)
            axes[row,j].axhline(0,color='gray',ls='--',lw=.5)
            axes[row,j].set(aspect='equal',xlim=(0,.08),ylim=(-.04,.04),xlabel='x',ylabel='y')
            axes[row,j].set_title(['FEM saved','PIDL saved','PIDL - FEM','PIDL mirror residual'][j]+'\n'+name+('/Uref' if scale!=1 else ''),fontsize=8)
            fig.colorbar(im,ax=axes[row,j],shrink=.65,pad=.01).ax.tick_params(labelsize=6)
    fig.suptitle('Earliest complete saved PIDL block: Q4 c1s2, U=0.05999988\nNative Q4 reconstruction; unqualified FEM comparator; no field symmetrisation',fontsize=10)
    fig.savefig(out/'earliest_physical_fields.png',dpi=180);plt.close(fig)
    print('saved',out,'rows',len(rows),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
