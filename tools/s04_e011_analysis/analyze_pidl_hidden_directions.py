#!/usr/bin/env python3
"""Saved-field c20 direction audit. No NN, Phi reconstruction, or equilibrium solve."""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm
from run_multicycle_cross_replay import q4_geometry, grad, interp

BASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011')
RUN=BASE/'runs/pf_s04e011_tightcouple_137cb03_20261019T122720Z_production'
MU=1/2.6; BULK=1/1.2
DEV=2*MU*np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]])


def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha256(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ratio(a,b):return float(a/b) if b else None
def centroid(values,coordinates):
    total=float(np.sum(values))
    return (np.sum(values[...,None]*coordinates,axis=tuple(range(values.ndim)))/total).tolist() if total else None
def signed_localization(delta,coordinates,weights=None,support=None):
    weighted=delta if weights is None else weights*delta
    out={}
    total=float(np.sum(np.abs(weighted)))
    for name,part in [('positive',np.maximum(weighted,0)),('negative',np.maximum(-weighted,0))]:
        amount=float(np.sum(part));out[name]=dict(magnitude=amount,absolute_increment_share=ratio(amount,total),centroid=centroid(part,coordinates),reference_top1_share=ratio(np.sum(part[support]),amount) if support is not None else None)
    out['signed_total']=float(np.sum(weighted));return out
def diagonal_statistics(values,residual):
    nz=values[values>0];r2=dot(residual,residual)
    lower=float(np.quantile(nz,.01)) if len(nz) else None
    return dict(zero_diagonal_free=int(np.count_nonzero(values==0)),negative_diagonal_free=int(np.count_nonzero(values<0)),zero_diagonal_residual_squared_share=ratio(dot(residual[values==0],residual[values==0]),r2),positive_diagonal_percentiles=np.quantile(nz,[0,.01,.5,.99,1]).tolist() if len(nz) else None,diagonal_max_over_min=float(nz.max()/nz.min()) if len(nz) else None,residual_squared_share_in_lowest_diagonal_percentile=ratio(dot(residual[values<=lower],residual[values<=lower]),r2) if lower is not None else None,undefined_reason='zero_residual' if r2==0 else ('no_positive_diagonal' if not len(nz) else None))
def dot(a,b):return float(np.einsum('i,i->',a,b,optimize=False))
def cosine(a,b):
    den=np.linalg.norm(a)*np.linalg.norm(b)
    return dot(a,b)/den if den else None
def decompose(a,b,w=None):
    w=1 if w is None else w
    delta=b-a;cross=float(np.sum(w*2*a*delta));sq=float(np.sum(w*delta**2))
    change=float(np.sum(w*b**2)-np.sum(w*a**2))
    return dict(change=change,cross=cross,increment_squared=sq,closure_error=change-cross-sq)


class Operator:
    def __init__(self,inp,cap=240,seconds=300):
        self.started=time.monotonic();self.cap=cap;self.seconds=seconds;self.calls=0;self.actions=0
        self.p=inp['nodes'];self.c=inp['cells'];self.n=len(self.p)
        self.N,self.B,self.w,self.xy=q4_geometry(self.p,self.c)
        self.d=inp['d_fem'];self.g=(1-interp(self.d,self.c,self.N))**2
        self.free=inp['freeu'].astype(int);self.fixed=np.setdiff1d(np.arange(2*self.n),self.free)
        self.mass=np.zeros(self.n)
        for j in range(4):np.add.at(self.mass,self.c[:,j],np.sum(self.w*self.N[:,j],axis=1))
        self.check()
    def check(self):
        if time.monotonic()-self.started>=self.seconds:
            self.persist_work();raise RuntimeError('saved_array_wall_budget_exhausted_no_retry')
    def persist_work(self):
        if hasattr(self,'audit_out'):dump(self.audit_out/'work_partial.json',dict(field_evaluations=self.calls,cap=self.cap,tangent_actions=self.actions,elapsed_seconds=time.monotonic()-self.started,seconds=self.seconds))
    def strains(self,q):
        gu=grad(q[:self.n],self.c,self.B);gv=grad(q[self.n:],self.c,self.B)
        return np.stack((gu[...,0],gv[...,1],gu[...,1]+gv[...,0]),axis=-1)
    def scatter(self,sig):
        B,w=self.B,self.w
        fx=np.sum(w[...,None]*(sig[...,0,None]*B[:,:,0,:]+sig[...,2,None]*B[:,:,1,:]),axis=1)
        fy=np.sum(w[...,None]*(sig[...,2,None]*B[:,:,0,:]+sig[...,1,None]*B[:,:,1,:]),axis=1)
        r=np.zeros(2*self.n)
        np.add.at(r,self.c.ravel(),fx.ravel());np.add.at(r,self.n+self.c.ravel(),fy.ravel())
        return r
    def evaluate(self,q):
        self.check()
        if self.calls>=self.cap:
            self.persist_work();raise RuntimeError('saved_array_budget_exhausted_no_retry')
        self.calls+=1;e=self.strains(q);tr=e[...,:2].sum(-1)
        sd=np.einsum('ij,egj->egi',DEV,e)
        raw=.5*np.sum(e*sd,axis=-1)+.5*BULK*np.maximum(tr,0)**2
        active=self.g*raw
        total=active+.5*BULK*np.minimum(tr,0)**2
        sig=self.g[...,None]*sd;sig[...,:2]+=BULK*(self.g*np.maximum(tr,0)+np.minimum(tr,0))[...,None]
        R=self.scatter(sig);rf=R[self.free]
        if not all(np.isfinite(x).all() for x in [q,e,tr,R,raw,active,total]):raise ValueError('nonfinite_replay')
        E=float(np.sum(self.w*total));ai=float(np.sum(self.w*active));ce=float(np.sum(self.w*.5*BULK*np.minimum(tr,0)**2));ru=float(np.linalg.norm(rf))
        if not np.isfinite([E,ai,ce,ru]).all():raise ValueError('nonfinite_integral')
        return dict(q=q,e=e,tr=tr,R=R,rf=rf,active=active,raw=raw,E=E,Ru=ru,active_integral=ai,compression_energy=ce,energy_component_closure_error=E-ai-ce)
    def action(self,s,v,directional_zero=False):
        self.check();self.actions+=1;de=self.strains(v);dt=de[...,:2].sum(-1)
        q=np.where(s['tr']>=0,self.g,1.)
        if directional_zero:q=np.where(s['tr']==0,np.where(dt>=0,self.g,1.),q)
        ds=self.g[...,None]*np.einsum('ij,egj->egi',DEV,de);ds[...,:2]+=BULK*(q*dt)[...,None]
        sp=np.einsum('ij,egj->egi',DEV,s['e']);sp[...,:2]+=BULK*np.maximum(s['tr'],0)[...,None]
        da=self.g*np.sum(sp*de,axis=-1)
        return self.scatter(ds),da
    def diagonal(self,s):
        self.check();q=np.where(s['tr']>=0,self.g,1.);xx=self.g*DEV[0,0]+BULK*q;ss=self.g*MU
        bx,by=self.B[:,:,0,:],self.B[:,:,1,:]
        dx=np.sum(self.w[...,None]*(xx[...,None]*bx**2+ss[...,None]*by**2),axis=1)
        dy=np.sum(self.w[...,None]*(xx[...,None]*by**2+ss[...,None]*bx**2),axis=1)
        d=np.zeros(2*self.n);np.add.at(d,self.c.ravel(),dx.ravel());np.add.at(d,self.n+self.c.ravel(),dy.ravel())
        return d
    def integrated_curvature(self,s,v):
        """Exact integral_0^1 (1-t) v.K(q+t*v).v dt, including trace crossings."""
        self.check();de=self.strains(v);dt=de[...,:2].sum(-1);tr=s['tr']
        first=np.where(tr>0,self.g,np.where(tr<0,1.,np.where(dt>=0,self.g,1.)))
        last=np.where(tr+dt>=0,self.g,1.)
        cut=np.zeros_like(dt);np.divide(-tr,dt,out=cut,where=dt!=0)
        crossing=(cut>0)&(cut<1)&(first!=last)
        weighted=.5*first+np.where(crossing,.5*(last-first)*(1-cut)**2,0.)
        average=first+np.where(crossing,(last-first)*(1-cut),0.)
        dev=np.einsum('ij,egj->egi',DEV,de)
        gp=.5*self.g*np.sum(de*dev,axis=-1)+BULK*dt**2*weighted
        ds=self.g[...,None]*dev;ds[...,:2]+=BULK*(average*dt)[...,None]
        return float(np.sum(self.w*gp)),self.scatter(ds)
    def free_vector(self,v):
        x=np.zeros(2*self.n);x[self.free]=v[self.free];return x


def transition(op,a,b,ref,label):
    v=b['q']-a['q'];kv,da=op.action(a,v);kd,_=op.action(a,v,True)
    dr=b['rf']-a['rf'];rdec=decompose(a['rf'],b['rf']);adec=decompose(a['active']-ref['active'],b['active']-ref['active'],op.w)
    work=dot(a['rf'],v[op.free]);curv=dot(v[op.free],kv[op.free]);de=b['E']-a['E']
    integrated,exact_secant=op.integrated_curvature(a,v)
    eerr=a['active']-ref['active']
    row=dict(transition=label,E_change=de,energy_work=work,selected_curvature=curv,energy_taylor_remainder=de-work-.5*curv,
        exact_integrated_curvature=integrated,exact_energy_work_closure_error=de-work-integrated,
        exact_secant_force_maxerr=float(np.max(np.abs(dr-exact_secant[op.free]))),
        Ru_before=a['Ru'],Ru_after=b['Ru'],residual_half_squared_merit_selected_directional=dot(a['rf'],kv[op.free]),
        residual_half_squared_merit_forward_directional=dot(a['rf'],kd[op.free]),
        active_squared_error_forward_directional=float(2*np.sum(op.w*eerr*da)),
        active_integral_change=b['active_integral']-a['active_integral'],compression_energy_change=b['compression_energy']-a['compression_energy'],
        energy_component_change_closure_error=de-(b['active_integral']-a['active_integral'])-(b['compression_energy']-a['compression_energy']),
        cosine_negative_force=cosine(v[op.free],-a['rf']),displacement_step_l2=float(np.linalg.norm(v[op.free])),
        R_change_l2=float(np.linalg.norm(dr)),selected_tangent_secant_error=float(np.linalg.norm(dr-kv[op.free])/max(np.linalg.norm(dr),1e-30)),
        selected_trace_label_changes=int(np.count_nonzero((a['tr']>=0)!=(b['tr']>=0))),strict_interior_trace_crossings=int(np.count_nonzero(a['tr']*b['tr']<0)),zero_trace_GPs=int(np.count_nonzero(a['tr']==0)),
        boundary_increment_maxabs=float(np.max(np.abs(v[op.fixed]))) if len(op.fixed) else 0.,residual_decomposition=rdec,active_decomposition=adec,FD=[])
    if '_hidden' in label or '_head' in label:
        for eps in [1e-3,1e-4]:
            z=op.evaluate(a['q']+eps*v);fd=(z['rf']-a['rf'])/eps
            row['FD'].append(dict(epsilon=eps,force_action_relative_error=float(np.linalg.norm(fd-kd[op.free])/max(np.linalg.norm(kd[op.free]),1e-30)),
                energy_derivative_error=abs((z['E']-a['E'])/eps-work)))
    if abs(rdec['closure_error'])>1e-12 or abs(adec['closure_error'])>1e-12 or abs(de-work-integrated)>1e-12 or row['exact_secant_force_maxerr']>1e-10:raise ValueError('exact_difference_decomposition_failed')
    return row


def control_lines(op,s,hidden,ref,label):
    r=op.free_vector(s['R']);diag=op.diagonal(s);positive=diag>0
    jac=np.zeros_like(r);jac[positive]=-r[positive]/diag[positive]
    kr,_=op.action(s,r)
    raw={'observed_hidden':hidden,'nodal_energy':-r,'nodal_Jacobi':jac,'nodal_residual':-kr,'FEM_reference_chord':ref['q']-s['q']}
    size=np.linalg.norm(hidden[op.free]);rows=[];dirs=[]
    for name,v in raw.items():
        v=op.free_vector(v);norm=np.linalg.norm(v[op.free])
        if not np.isfinite(v).all() or not np.isfinite(norm):raise ValueError('nonfinite_control_direction_no_floor')
        if not norm or not size:
            dirs.append(dict(anchor=label,direction=name,status='undefined_zero_direction_or_reference_step',nodal_step_l2=float(size)));continue
        v=v*(size/norm);kv,da=op.action(s,v);kd,_=op.action(s,v,True);k=kv[op.free];g=dot(s['rf'],v[op.free]);h=dot(v[op.free],k)
        rg=dot(s['rf'],k);rh=dot(k,k);ae=float(np.sum(op.w*(s['active']-ref['active'])*da))
        alphaE=-g/h if h>0 and g<0 else None;alphaR=-rg/rh if rh>0 and rg<0 else None
        desc=dict(anchor=label,direction=name,status='evaluated',nodal_step_l2=float(size),energy_derivative=g,selected_energy_curvature=h,
            residual_half_squared_merit_selected_derivative=rg,residual_half_squared_merit_forward_derivative=dot(s['rf'],kd[op.free]),active_half_squared_error_merit_derivative=ae,
            prediction_semantics='Selected symmetric tangent quadratic predictions, one actual evaluation each; exact-zero trace forward derivative reported separately.',
            cosine_negative_force=cosine(v[op.free],-s['rf']),cosine_negative_Kforce=cosine(v[op.free],-kr[op.free]),
            alpha_energy_quadratic=alphaE,alpha_residual_quadratic=alphaR)
        dirs.append(desc);alphas=sorted(set([0.,.25,.5,1.,2.]+[x for x in [alphaE,alphaR] if x is not None and np.isfinite(x)]))
        for alpha in alphas:
            z=s if alpha==0 else op.evaluate(s['q']+alpha*v)
            rows.append(dict(anchor=label,direction=name,alpha=alpha,E=z['E'],Ru=z['Ru'],active_relL2=float(np.sqrt(np.sum(op.w*(z['active']-ref['active'])**2)/np.sum(op.w*ref['active']**2))),
                energy_change=z['E']-s['E'],Ru_relative_change=(ratio(z['Ru'],s['Ru'])-1) if s['Ru'] else None,trace_crossings=int(np.count_nonzero((s['tr']>=0)!=(z['tr']>=0)))))
    return dirs,rows,dict(anchor=label,**diagonal_statistics(diag[op.free],s['rf']))


def csvwrite(path,rows):
    if not rows:return
    with path.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)


def plot(out,stages,trans,controls,op,ref):
    # Deliberately separate scalar sign evidence from spatial localization.
    fig,ax=plt.subplots(2,2,figsize=(11,7.5),layout='constrained');x=np.arange(1,9)
    for kind,color in [('hidden','#D55E00'),('head','#0072B2'),('net','#009E73')]:
        r=[t for t in trans if t['transition'].endswith('_'+kind)]
        for a,key,title in [(ax[0,0],'E_change','Actual elastic energy change'),(ax[0,1],'residual_decomposition','Change of ||free R||²'),(ax[1,0],'active_decomposition','Change of weighted active error²')]:
            y=[v[key]['change'] if isinstance(v[key],dict) else v[key] for v in r]
            a.plot(x,y,'o-',ms=3,lw=1.3,label=kind,color=color);a.set_title(title);a.axhline(0,color='.5',lw=.6);a.set_xlabel('pair');a.grid(alpha=.2)
    for name,col in [('nodal_energy','#E69F00'),('nodal_Jacobi','#0072B2'),('nodal_residual','#CC79A7'),('observed_hidden','#D55E00')]:
        r=[v for v in controls if v['direction']==name and v['alpha']==1 and v['Ru_relative_change'] is not None]
        ax[1,1].plot([{'initial':0,'head_4':1,'head_7':2}[v['anchor']] for v in r],[v['Ru_relative_change']*100 for v in r],'o-',label=name,color=col,lw=1.3)
    ax[1,1].set_xticks([0,1,2],['initial','head4','head7']);ax[1,1].set_ylabel('Ru change at matched nodal L2 step (%)');ax[1,1].set_yscale('symlog',linthresh=.1);ax[1,1].axhline(0,color='.5',lw=.6);ax[1,1].set_title('Physical-space controls; not NN updates')
    for a in ax.flat:a.legend(fontsize=7)
    fig.suptitle('Frozen c20s4 PIDL: energy descent need not reduce force or active error',fontsize=12)
    fig.savefig(out/'direction_decision.png',dpi=190);plt.close(fig)
    n=op.n;initial=stages['initial'];final=stages['head_8'];start=stages['head_7'];end=final
    fields=[(initial['R'][:n]**2+initial['R'][n:]**2,final['R'][:n]**2+final['R'][n:]**2,'Nodal free-force squared',False),
        ((initial['active']-ref['active'])**2,(final['active']-ref['active'])**2,'Active squared error (GP mean)',True)]
    fig,axs=plt.subplots(2,3,figsize=(12.5,7.5),layout='constrained')
    for row,(a,b,title,isgp) in enumerate(fields):
        if not isgp:
            # Reaction DOFs are excluded before maps and statistics.
            def ns(z):
                r=op.free_vector(z['R']);return r[:n]**2+r[n:]**2
            a=ns(initial);b=ns(final)
            vals=[a,b,ns(end)-ns(start)];coords=op.p
        else:
            vals=[a,b,(end['active']-ref['active'])**2-(start['active']-ref['active'])**2];coords=op.xy
        display=[]
        for v in vals:
            display.append(np.sum(op.w*v,axis=1)/op.w.sum(1) if isgp else np.mean(v[op.c],axis=1))
        common=max(float(np.max(display[0])),float(np.max(display[1])),1e-30)
        for j,v in enumerate(display):
            lim=common if j<2 else max(float(np.max(np.abs(v))),1e-30)
            norm=SymLogNorm(max(lim*1e-6,1e-30),vmin=-lim if j==2 else 0,vmax=lim)
            pc=PolyCollection(op.p[op.c],array=v,cmap='RdBu_r' if j==2 else 'magma',norm=norm,edgecolors='none',rasterized=True)
            axy=axs[row,j];axy.add_collection(pc);axy.autoscale_view();axy.set_aspect('equal');axy.set_title(['Initial '+title,'Final head8','Last pair signed change'][j],fontsize=9);fig.colorbar(pc,ax=axy,shrink=.7)
    fig.suptitle('c20s4: physical residual / active error location; unmodified scored fields',fontsize=11)
    fig.savefig(out/'direction_locations.png',dpi=190);plt.close(fig)


def main(args):
    started=time.monotonic()
    if args.out.exists():raise FileExistsError('Do not overwrite a scored audit')
    args.out.mkdir(parents=True);old=json.loads((args.run/'analysis_tight_coupling/summary.json').read_text())
    inpfile=BASE/'pidl_block_preparation_20261017_v1/inputs/c20_peak.npz'
    st=old['state'];worker=st['endpoint']['worker']
    names=['initial']+[x for i in range(1,9) for x in [f'hidden_{i}',f'head_{i}']]
    if Path(old['run']).name!=RUN.name or args.run.resolve()!=RUN.resolve():raise ValueError('wrong_frozen_source_run')
    if (st['cycle'],st['substep'],st['step'],st['U'])!=(20,4,99,.11999988):raise ValueError('wrong_frozen_state')
    if worker['status']!='completed' or worker['closed_pairs']!=8 or worker['operational_coupling_closure'] is not True or st['last_closed_checkpoint']!='head_8':raise ValueError('source_not_eight_closed_pairs')
    if [r['stage'] for r in st['stage_metrics']]!=names:raise ValueError('source_stage_order_mismatch')
    bound=[r for r in old['sources'] if Path(r['path']).resolve()==inpfile.resolve()]
    if len(bound)!=1 or inpfile.stat().st_size!=bound[0]['bytes'] or sha256(inpfile)!=bound[0]['sha256']:raise ValueError('bound_input_identity_mismatch')
    dump(args.out/'input_identity.json',dict(source_summary_sha256=sha256(args.run/'analysis_tight_coupling/summary.json'),input=bound[0],state=[20,4,99,.11999988],stage_order=names))
    with np.load(inpfile) as z:inp={k:z[k] for k in z.files}
    op=Operator(inp);op.started=started;op.audit_out=args.out;op.check();case=args.run/'retrieved/archive/output/c20_s4';states={};metrics=[];rows=[]
    names=['initial']+[x for i in range(1,9) for x in [f'hidden_{i}',f'head_{i}']]
    for label in names:
        with np.load(case/'checkpoints'/label/'fields.npz') as z:
            assert np.array_equal(z['d'],op.d);q=np.r_[z['u'],z['v']]
        s=op.evaluate(q);states[label]=s
        refrow=next(a for a in old['state']['stage_metrics'] if a['stage']==label)
        if abs(s['E']-refrow['E_el'])>1e-12 or abs(s['Ru']-refrow['free_u_l2'])>1e-12:raise ValueError('old_stage_replay_mismatch')
        saved='initial_learned_head' if label=='initial' else label
        with np.load(case/'readouts'/(saved+'.npz')) as z:err=float(np.max(np.abs(s['R']-np.r_[z['gu'],z['gv']])))
        if err>1e-10:raise ValueError('saved_force_mismatch')
        headg=None
        if label=='initial' or label.startswith('head_'):
            g=np.load(case/'readouts'/(saved+'_actual_projected_gradient.npy'))
            record=next(r for r in st['stage_records'] if r['stage']==label)
            if g.shape!=(2*record['identity']['rank'],) or not np.isfinite(g).all():raise ValueError('saved_closed_gradient_shape_or_finite')
            headg=float(np.max(np.abs(g)))
            if headg>1e-10 or abs(headg-refrow['conditioned_head_gradient_inf'])>1e-20:raise ValueError('saved_head_not_closed')
        metrics.append(dict(stage=label,E=s['E'],Ru=s['Ru'],active_integral=s['active_integral'],compression_energy=s['compression_energy'],energy_component_closure_error=s['energy_component_closure_error'],saved_force_maxerr=err,saved_closed_head_gradient_inf=headg))
        dump(args.out/'stages_partial.json',metrics);dump(args.out/'work_partial.json',dict(field_evaluations=op.calls,tangent_actions=op.actions,elapsed_seconds=time.monotonic()-op.started))
    ref=op.evaluate(np.r_[inp['u_fem'],inp['v_fem']])
    if ref['Ru']>1e-8:raise ValueError('conditional_FEM_not_equilibrated')
    denominator=np.sum(op.w*ref['active']**2)
    for m,s in zip(metrics,states.values()):
        m['active_relL2']=float(np.sqrt(np.sum(op.w*(s['active']-ref['active'])**2)/denominator))
        rr=next(a for a in old['state']['stage_metrics'] if a['stage']==m['stage'])
        if abs(m['active_relL2']-rr['active_vs_FEM_relative_L2'])>1e-10:raise ValueError('active_metric_mismatch')
        if np.max(np.abs(s['q'][op.fixed]-ref['q'][op.fixed]))>1e-12:raise ValueError('boundary_mismatch')
    for i in range(1,9):
        a=states['initial' if i==1 else f'head_{i-1}'];h=states[f'hidden_{i}'];b=states[f'head_{i}']
        for aa,bb,label in [(a,h,f'p{i}_hidden'),(h,b,f'p{i}_head'),(a,b,f'p{i}_net')]:
            rows.append(transition(op,aa,bb,ref,label));dump(args.out/'transitions_partial.json',rows);op.persist_work()
    dirs=[];lines=[];diags=[]
    for label,hi in [('initial',1),('head_4',5),('head_7',8)]:
        dd,ll,diag=control_lines(op,states[label],states[f'hidden_{hi}']['q']-states[label]['q'],ref,label)
        dirs+=dd;lines+=ll;diags.append(diag)
        dump(args.out/'controls_partial.json',dict(directions=dirs,control_lines=lines,diagonal=diags));dump(args.out/'work_partial.json',dict(field_evaluations=op.calls,tangent_actions=op.actions,elapsed_seconds=time.monotonic()-op.started))
    trace=json.loads((case/'trace.json').read_text());trials=[]
    for i in range(1,9):
        t=[r for r in trace if r.get('pair')==i and r.get('role')=='hidden_LBFGS_closure'];es=[r['E_el'] for r in t]
        trials.append(dict(pair=i,closure_energies=es,max_trial_over_start=max(es)/es[0],accepted=states[f'hidden_{i}']['E'],no_across_step_curvature=True))
    # Fixed reference-only GP top1% area; ties at the threshold are retained.
    order=np.argsort(ref['active'].ravel());cw=np.cumsum(op.w.ravel()[order]);tau=ref['active'].ravel()[order[np.searchsorted(cw,.99*cw[-1])]];mask=ref['active']>=tau
    localization=[];rmap={};amap={}
    for label in ['initial','head_4','head_7','head_8']:
        s=states[label];r=op.free_vector(s['R']);rsq=r[:op.n]**2+r[op.n:]**2;asq=(s['active']-ref['active'])**2
        localization.append(dict(stage=label,residual_squared_centroid=centroid(rsq,op.p),
            active_error_squared_centroid=centroid(op.w*asq,op.xy),active_error_sq_share_ref_top1=ratio(np.sum(op.w[mask]*asq[mask]),np.sum(op.w*asq))))
        rmap[label]=rsq;amap[label]=asq
    increments=[]
    for start,end in [('initial','head_8'),('head_7','head_8')]:
        increments.append(dict(transition=start+'->'+end,residual_squared=signed_localization(rmap[end]-rmap[start],op.p),active_error_squared=signed_localization(amap[end]-amap[start],op.xy,op.w,mask)))
    op.check()
    result=dict(protocol='E011-hidden-direction-saved-array-r1',source_run=str(args.run),state='conditional c20s4/raw99/U.11999988/nativeQ4GP4/FEMouter18/history0',
        scope='Saved fields only. No NN forward/gradient/SVD/Phi reconstruction/FEM solve/parameter update. Physical controls are not NN parameter preconditioners or attainable network updates.',
        fixed=dict(actual_Phi='unchanged archived identities; no re-readout/reconstruction',FEM_damage=True,UV_boundary=True,head_threshold=1e-10),
        stages=metrics,transitions=rows,directions=dirs,control_lines=lines,diagonal=diags,trace_trials=trials,localization=localization,signed_increment_localization=increments,reference_top1_threshold=float(tau),
        reference_top1_actual_area_fraction=float(op.w[mask].sum()/op.w.sum()),
        work=dict(field_evaluations=op.calls,cap=op.cap,tangent_actions=op.actions,elapsed_seconds=time.monotonic()-op.started,seconds=op.seconds),
        zero_trace_policy='Selected symmetric K uses g at trace=0; forward FD uses sign(direction trace) at exact0. Branch-changing finite secants need not equal frozen K.',
        limits=['No hidden Jacobian or full hidden gradient vector used: cannot identify hidden spectrum/preconditioning causality.','−K R uses the selected symmetric free-DOF tangent: it is a half-squared residual descent direction where differentiable; exact-zero trace one-sided derivatives are reported separately. Jacobi is physical nodal energy metric.','FEM chord is reference oracle, not learned/Phi-attainable.','No time evolution, capacity, teacher truth or independent-state generalization.'])
    dump(args.out/'summary.json',result);csvwrite(args.out/'stages.csv',metrics);csvwrite(args.out/'directions.csv',dirs);csvwrite(args.out/'control_lines.csv',lines)
    flat=[{k:v for k,v in t.items() if k not in ['FD','residual_decomposition','active_decomposition']}|{'R_'+k:v for k,v in t['residual_decomposition'].items()}|{'active_'+k:v for k,v in t['active_decomposition'].items()} for t in rows]
    csvwrite(args.out/'transitions.csv',flat)
    np.savez_compressed(args.out/'localization.npz',nodes=op.p,cells=op.c,gp_xy=op.xy,weights=op.w,**{'R2_'+k:v for k,v in rmap.items()},**{'active_error2_'+k:v for k,v in amap.items()})
    op.check();plot(args.out,states,rows,lines,op,ref)
    note='# Frozen c20 PIDL direction and physical preconditioning audit\n\nQuestion: why can energy fall while free force and active error do not?\n\nSource: '+str(args.run)+';17 saved fields/forces, old scored summary, conditional FEM c20s4 outer18 input. Exact values: summary.json and CSVs. No new NN/solve.\n\nReading order: direction_decision.png shows actual hidden/head/net changes and matched-nodal-size physical controls; direction_locations.png shows initial/final spatial squared errors and signed last-pair changes. Coordinates and metrics retain native support; maps average node squared forces to Q4 cells and GP squared active errors to weighted cell means. First two columns share row scale; signed final column has its own symmetric limit. Symmetric-log display threshold=1e-6 of the displayed maximum, no score clipping.\n\nAllowed: case-local direction, secant and metric-mismatch explanation. Jacobi controls concern nodal metric only; they are not trained network endpoints. Actual Phi is not reconstructed; saved initial/head projected vectors are explicitly checked at the unchanged 1e-10 threshold. E=active integral+compression energy and signed squared-error increment centroids are reported without extra field evaluations. Undefined zero residual/diagonal statistics are null, without floors. Blocked: hidden curvature spectrum, architecture ceiling, preconditioned NN efficacy, evolution or physical teacher claim.\n'
    (args.out/'README_analysis.md').write_text(note)
    for stem in ['direction_decision','direction_locations']:(args.out/(stem+'.md')).write_text(note+'\nFigure: '+stem+'.png\n')
    print(json.dumps(result['work']))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,default=RUN);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    try:main(args)
    except Exception as e:
        if args.out.exists():dump(args.out/'failure.json',dict(type=type(e).__name__,error=str(e),no_automatic_retry=True))
        raise
