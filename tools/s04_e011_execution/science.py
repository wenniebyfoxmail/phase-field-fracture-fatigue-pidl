"""Execution-only orchestration of frozen ae01bfed APIs; import is stdlib-only.

No real objects or numerical imports until preflight(), after guardian gate.
No new numerical policy: initial chart is reused only with an exact token.
"""
from pathlib import Path
import hashlib,json,os,time
from control import write_json,digest


class Context:
    def __init__(self,card,science,root,archive,reporter,started):
        self.card=card;self.science=science;self.root=Path(root);self.archive=Path(archive)
        self.reporter=reporter;self.started=started;self.runtime=None;self.algebra=None;self.accepted=[]
    def preflight(self):
        # All loading, import, native readout and derivative work is charged to
        # phase1 in the already-running independent guardian.
        import sys,shutil
        here=Path(__file__).resolve().parents[1]/'s04_e011_analysis';sys.path.insert(0,str(here))
        import numpy as np
        import torch
        import run_pidl_persisted_phi_hidden_newton as base
        from profiled_hidden_adapter import Guard,probe_algebra
        from profiled_hidden_e011_runtime import Runtime,startup_checks,verify_source_assets
        self.np=np;self.torch=torch;self.base=base;self.Runtime=Runtime;self.startup_checks=startup_checks;self.probe_algebra=probe_algebra
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        # One visible UUID. This is the ONLY process allowed to create CUDA.
        if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise RuntimeError('single bound CUDA device unavailable')
        torch.cuda.init();self.device=torch.device('cuda:0')
        self.reporter.cuda=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0))
        self.reporter.ratio()
        self.guard=Guard(self.science['aggregate_work_caps'],3000.,memory=self.reporter.ratio,max_bytes=1.)
        self.guard.start=self.started
        inputs=self.root/'inputs';inputs.mkdir()
        paths={r['role']:r['source'] for r in self.science['input_bindings']}
        source_receipts=verify_source_assets(self.science,paths,self.guard);write_json(self.archive/'source_assets.json',source_receipts)
        staged={}
        for item in self.science['input_bindings']:
            source=Path(item['source'])
            if source.is_symlink() or not source.is_file():raise RuntimeError('input symlink or missing asset')
            target=inputs/(item['role']+source.suffix)
            with source.open('rb') as a,target.open('xb') as b:shutil.copyfileobj(a,b,1048576)
            staged[item['role']]=str(target);self.guard.check()
        verify_source_assets(self.science,staged,self.guard)
        data=dict(np.load(staged['input'],allow_pickle=False));self.problem=base.LocalProblem(data,self.device)
        original=torch.load(staged['original_model'],map_location=self.device,weights_only=True)
        initial=torch.load(staged['initial_model'],map_location=self.device,weights_only=True)
        self.guard.charge('raw_feature_forward')
        self.field=base.make_smooth(original,self.problem);self.field.net.load_state_dict(initial);self.field.net.requires_grad_(False)
        self.initial_state=base.snapshot(self.field.net)
        head=torch.cat((self.field.net.output_layer.weight[:2],self.field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
        self.initial_space=base.load_actual_space(staged['source_phi'],staged['source_transform'],head,self.device,self.problem.n)
        base.persist_space(self.initial_space,self.archive/'initial_basis',self.field,staged['source_phi'],staged['source_transform'])
        self.space=self.initial_space
        source_fields=dict(np.load(staged['source_fields'],allow_pickle=False))
        self.budget=base.phase_budget(self.archive,'production',self.started)
        self.budget.cap=self.science['aggregate_work_caps']['energy_force_field'];self.budget.seconds=3000.
        (self.archive/'readouts').mkdir();self.work=base.PhaseWork(self.budget)
        # Existing native operator contract: charge its four physical-energy
        # constructions; never run a new FEM or damage solve.
        for _ in range(4):self.guard.charge('energy_force_field')
        native=self.problem.contract();write_json(self.archive/'native_operator.json',native)
        self.runtime=Runtime(self.field,self.problem,self.space,self.budget,self.work,self.archive/'point_0',self.guard)
        self.source_rows=startup_checks(self.runtime,source_fields)
        self.scales=self.runtime.bridge.scales.detach().clone()
        self.mass=torch.cat((self.problem.mass,self.problem.mass))[self.problem.fu].cpu().numpy()
        q=self.runtime.bridge.q(self.runtime.bridge.zero).detach().cpu().numpy()
        self.physical_radius=.01*float(np.sqrt(np.sum(self.mass*q*q)))
        self.initial_E=self.source_rows[0]['E'];self.initial_Ru=None
        self._qualify(self.runtime)
        self.initial_Ru=self.runtime.root_Ru
        self.source_qualification=self._token(self.runtime)
        write_json(self.archive/'preflight_qualification.json',self.source_qualification)
        write_json(self.archive/'runtime_versions.json',dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,scipy=__import__('scipy').__version__))
        self.guard.check()
        return dict(completed=True,admitted=True,accepted_hidden_updates=0,root_state_restored=True,
            qualification_sha256=digest(self.archive/'preflight_qualification.json'),counts=dict(self.guard.counts),
            scientific_success=False)
    def _qualify(self,runtime):
        self.algebra=runtime.form_chart()
        rows,dirs=self.probe_algebra(self.algebra,runtime.head_H,self.guard)
        write_json(runtime.folder/'local_dot_checks.json',dict(rows=rows))
        checked=runtime.verify_profile(self.algebra,dirs)
        write_json(runtime.folder/'actual_full_profile_checks.json',dict(rows=checked))
    def _token(self,runtime):
        from profiled_hidden_e011_runtime import tensor_identity
        return dict(weights=tensor_identity(self.field.net.state_dict()),phi=tensor_identity({'Phi':runtime.bridge.phi}),
            transform=hashlib.sha256(runtime.bridge.T.cpu().numpy().tobytes()).hexdigest(),
            point=tensor_identity({'xi':runtime.bridge.zero,'q':runtime.chart.point.q.detach(),'R':runtime.chart.force}),
            head_H=hashlib.sha256(runtime.head_H.tobytes()).hexdigest(),scaling=tensor_identity({'D':runtime.bridge.scales}),physics=tensor_identity(runtime.bridge.physics),
            B0=tensor_identity(runtime.bridge.anchor),counts=dict(self.guard.counts),source_admitted=runtime.source_admitted,profile_verified=runtime.profile_verified)
    def candidate(self):
        from profiled_hidden_e011_runtime import candidate_direction
        from profiled_hidden_kernel import finite_trial_decision
        if self._token(self.runtime)!=self.source_qualification:raise RuntimeError('cached preflight chart qualification changed')
        for step in range(1,5):
            rt=self.runtime
            try:
                def record(name,**arrays):self.np.savez_compressed(rt.folder/(name+'.npz'),**arrays)
                direction,info=candidate_direction(self.algebra,rt.chart.array(rt.chart.force),self.mass,self.physical_radius,recorder=record)
                accepted=None
                for alpha in self.science['candidate_B']['alpha']:
                    trial=rt.trial(alpha*direction)
                    decision=finite_trial_decision(dict(E=rt.root_E,Ru=rt.root_Ru),trial)
                    write_json(Path(trial['folder'])/'candidate_decision.json',dict(status=decision,alpha=alpha,direction=info))
                    if decision in ['rejected_contract','rejected_head_or_realization']:self.guard.stop(decision)
                    if decision=='accepted':accepted=trial;self.space=rt.promote(trial);break
                if accepted is None:self.guard.stop('no_accepted_finite_alpha')
                self.accepted.append(dict(step=step,E=accepted['E'],Ru=accepted['Ru'],folder=accepted['folder']))
                self.last_candidate=accepted;self.last_state=self.base.snapshot(self.field.net)
                write_json(self.archive/'accepted_macrosteps.json',self.accepted)
            finally:rt.close()
            if step<4:
                self.runtime=self.Runtime(self.field,self.problem,self.space,self.budget,self.work,self.archive/('point_'+str(step)),self.guard,scales=self.scales)
                previous_fields=dict(self.np.load(accepted['actual_readout']['path'],allow_pickle=False))
                self.startup_checks(self.runtime,previous_fields,source_energy=accepted['E']);self._qualify(self.runtime)
        self.guard.check()
        return dict(completed=True,accepted_hidden_updates=len(self.accepted),last_closed=self.accepted[-1],counts=dict(self.guard.counts))
    def bounded_witness(self):
        from profiled_hidden_kernel import bounded_tangent_witness
        self.field.net.load_state_dict(self.initial_state)
        rt=self.Runtime(self.field,self.problem,self.initial_space,self.budget,self.work,self.archive/'witness_point',self.guard,scales=self.scales)
        self.runtime=rt
        try:
            source_fields=dict(self.np.load(self.root/'inputs/source_fields.npz',allow_pickle=False))
            self.startup_checks(rt,source_fields,source_energy=self.initial_E)
            # Recreate the source physical graph, not its completed diagnostic.
            # Reuse qualification only for exact same bound source/chart/D/H.
            self.algebra=rt.form_chart();current=self._token(rt)
            for key,value in self.source_qualification.items():
                if key not in ['counts','profile_verified'] and current[key]!=value:raise RuntimeError('source witness qualification changed')
            if any(current['counts'][k]<v for k,v in self.source_qualification['counts'].items()):raise RuntimeError('shared work ledger reset')
            rt.profile_verified=True  # identity-bound reuse of prior true FD
            write_json(rt.folder/'reused_source_qualification.json',dict(source=digest(self.archive/'preflight_qualification.json'),identity_exact=True,new_FD=False))
            force=rt.chart.array(rt.chart.force);length=self.card['witness_source_nodal_step_l2']
            target=-force/self.np.linalg.norm(force)*length;sqrt_mass=self.np.sqrt(self.mass)
            A=lambda v:sqrt_mass*self.algebra.q(v)
            AT=lambda w:self.algebra.qt(sqrt_mass*w)
            step,info=bounded_tangent_witness(A,AT,sqrt_mass*target,self.algebra.parameters,.01,max_steps=96,relative_gap=.001)
            self.np.savez_compressed(self.archive/'bounded_witness.npz',step=step,target=target)
            write_json(self.archive/'bounded_witness.json',info)
            trial=rt.trial(step)  # exactly one finite implementation; never promote
            if trial['head_gradient_inf']>1e-10 or trial['realization_maxabs']>1e-10 or not trial['fixed_state']:self.guard.stop('witness_actual_contract_failure')
            write_json(self.archive/'bounded_witness_actual.json',{k:trial[k] for k in ['E','Ru','rank','head_gradient_inf','realization_maxabs','folder']})
        finally:
            rt.close();self.field.net.load_state_dict(self.last_state)
        return dict(completed=True,bounded_status=info['status'],candidate_endpoint_selected=False,counts=dict(self.guard.counts))
    def readout(self):
        # Scoring uses only the same conditional FEM d and current accepted NN.
        # A and common initial remain separate controls. No further update.
        from q4_quadrature import q4_interpolate
        from compute_energy import strain_energy_with_split
        torch=self.torch;np=self.np;p=self.problem
        self.guard.charge('raw_feature_forward');self.guard.charge('energy_force_field');self.guard.charge('hidden_vjp')
        obs,fields,g=self.base.persisted_readout(self.field,p,np.eye(401),self.budget,'final',self.space)
        if obs['reduced_gradient_inf']>1e-10:self.guard.stop('final_head_closure_miss')
        self.guard.charge('energy_force_field');self.guard.charge('energy_force_field')
        with torch.no_grad():
            u=torch.as_tensor(fields['u'],device=self.device);v=torch.as_tensor(fields['v'],device=self.device)
            def active(u,v):
                gu,gv=p.grad(u),p.grad(v);d=q4_interpolate(p.df,p.cells,p.N)
                _,raw=strain_energy_with_split(gu[:,:,0],gv[:,:,1],.5*(gu[:,:,1]+gv[:,:,0]),d,p.mat,p.model)
                return (1-d).square()*raw
            a=active(u,v);f=active(p.uf,p.vf);w=p.w
            relative=torch.sqrt((w*(a-f).square()).sum()/(w*f.square()).sum())
            ma=(w*a).sum()/w.sum();mf=(w*f).sum()/w.sum()
            corr=(w*(a-ma)*(f-mf)).sum()/torch.sqrt((w*(a-ma).square()).sum()*(w*(f-mf).square()).sum())
            aq=a.cpu().numpy();fq=f.cpu().numpy()
        import csv
        baseline=json.loads((self.root/'code'/self.card['baseline_compact']).read_text())['actual_network']
        with (self.root/'code'/self.card['baseline_metrics']).open() as stream:
            controls={row['method']:row for row in csv.DictReader(stream)}
        result=dict(state='c20/substep4/rawstep99/U=.11999988/FEM_outer18_original_s3_history',method='PIDL profiled-hidden joint policy',
            primary_Ru_B_over_A=obs['free_u_l2']/baseline['free_u_l2'],Ru_B_over_initial=obs['free_u_l2']/self.initial_Ru,
            E_B_over_A=obs['E_el']/baseline['E_el'],previous_two_block_energy_minus_B=.005267089573071509-obs['E_el'],old_energy_margin=1e-10,
            actual_network=obs,active_relL2=float(relative),active_correlation=float(corr),active_integral=float((w*a).sum()),
            A=baseline,archived_same_operator_controls=controls,active_relL2_ratio_B_over_A=float(relative)/float(controls['new_last_closed']['active_vs_FEM_relative_L2']),common_initial=dict(E=self.initial_E,Ru=self.initial_Ru),accepted_hidden_updates=len(self.accepted),
            counts=dict(self.guard.counts),physics_or_capacity_certificate=False,equal_cost_claim=False)
        if not np.isfinite([result['primary_Ru_B_over_A'],float(relative),float(corr)]).all():self.guard.stop('nonfinite_final_metrics')
        np.savez_compressed(self.archive/'final_native_fields.npz',**fields,active=aq,active_FEM=fq,weights=w.cpu().numpy())
        write_json(self.archive/'comparison.json',result)
        self._figure(fields,aq,fq,result)
        self.guard.check()
        return dict(completed=True,comparison='comparison.json',accepted_hidden_updates=len(self.accepted),counts=dict(self.guard.counts))
    def _figure(self,fields,active,ref,result):
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.collections import PolyCollection
        import numpy as np
        p=self.problem;nodes=p.x.cpu().numpy();cells=p.cells.cpu().numpy();poly=nodes[cells]
        weight=p.w.cpu().numpy();a=(weight*active).sum(1)/weight.sum(1);f=(weight*ref).sum(1)/weight.sum(1)
        fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
        common=max(float(a.max()),float(f.max()));delta=a-f;limit=max(float(abs(delta).max()),1e-30)
        for ax,value,title,limits,cmap in zip(axes,[f,a,delta],['conditional FEM','PIDL accepted B','PIDL - FEM'],[(0,common),(0,common),(-limit,limit)],['viridis','viridis','coolwarm']):
            c=PolyCollection(poly,array=value,cmap=cmap,edgecolors='none',antialiaseds=False);c.set_clim(*limits);ax.add_collection(c);ax.autoscale_view();ax.set_aspect('equal');ax.set_title(title);fig.colorbar(c,ax=ax)
        fig.savefig(self.archive/'active_comparison.png',dpi=180);plt.close(fig)
        (self.archive/'active_comparison.md').write_text('Question: does accepted PIDL active field approach the same conditional FEM?\nSource: final_native_fields.npz, frozen c20s4; Q4 GP-area-weighted element mean shown.\nPanels: FEM | PIDL B share physical density scale; signed difference has symmetric scale.\nSee: compare the full left crack band, not only the integral.\nTherefore: field improvement must be read with Ru, energy and weighted GP metrics in comparison.json.\nLimit: fixed FEM damage; no evolution or physical-truth/capacity certificate; A is retained scalar/archived-field control, not rerun.\n')
        with (self.archive/'active_comparison.md').open('a') as sidecar:sidecar.write(f"Numerical takeaway: GP-weighted active relL2={result['active_relL2']:.9g}, correlation={result['active_correlation']:.9g}; Ru B/A={result['primary_Ru_B_over_A']:.9g}, energy B/A={result['E_B_over_A']:.9g}. Active density is g(d)*psi_plus.\n")
    def failure_cleanup(self):
        if self.runtime is not None:self.runtime.close()
        if hasattr(self,'field') and hasattr(self,'last_state'):self.field.net.load_state_dict(self.last_state)
        elif hasattr(self,'field') and hasattr(self,'initial_state'):self.field.net.load_state_dict(self.initial_state)
        if hasattr(self,'guard'):write_json(self.archive/'work_terminal.json',dict(counts=self.guard.counts,stopped=self.guard.stopped))
