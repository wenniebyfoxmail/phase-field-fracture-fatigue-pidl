#!/usr/bin/env python3
"""Build the reviewed baseline followed by a bounded tight-control intervention."""
import argparse
import hashlib
import json
from pathlib import Path
from prepare_s04_e011_endpoint_baseline import build as build_baseline


def build(driver, solver, hashes):
    baseline=build_baseline(driver,solver,hashes).replace('run_s04_e011_endpoint_baseline(cfg, options)','run_s04_e011_endpoint_tight(cfg, options)',1)
    marker="fprintf('[E011_ENDPOINT_BASELINE_PASS] iterations=%d, no history commit\\n',i_stag);\n"
    if baseline.count(marker)!=1:raise ValueError('baseline admission marker drift')
    start='        for i_stag = 1:SOL_STAG_PAR.max_iter\n';end='            if stag_converged\n'
    if solver.count(start)!=1 or solver.count(end)!=1:raise ValueError('iteration source drift')
    iteration=solver.split(start)[1].split(end)[0]
    insertion=r'''
% The original baseline gate above is mandatory, even though a prior run passed.
SOL_PAR.tol_displ=1e-8;
SOL_PAR.tol_p_field=4e-6;
SOL_STAG_PAR.tol=4e-6;
max_extra=10; baseline_iteration=i_stag;
tight_trace=struct('iteration',{},'free_u_l2',{},'feasible_d_l2',{}, ...
    'projected_stop_sum',{},'cached_stop_sum',{},'converged',{});
last_completed=converged; last_oracle=oracle;
baseline_state=converged; baseline_oracle=oracle;
try
[baseline_metrics,baseline_active]=endpoint_monitor(sys,converged,oracle,frozen,4e-6);
save(fullfile(work_dir,'tight_baseline.mat'),'baseline_state','baseline_oracle','baseline_metrics','baseline_active','frozen','-v7.3');
control_pass=false;
fprintf('[E011_TIGHT_STARTED] inner_u=1e-8 inner_d=4e-6 outer_projected=4e-6 extra_cap=10\n');
for i_stag=baseline_iteration+1:baseline_iteration+max_extra
'''
    post=r'''
    assert(isequal(history_vars_old,frozen_history) && isequal(p_field_old,frozen_damage),'Immutable predecessor changed');
    assert(all(isfinite(displ)) && all(isfinite(p_field)) && all(isfinite(strain_en_undgr),'all'));
    assert(all(p_field>=p_field_old-1e-12) && all(p_field<=1+1e-12),'Damage feasibility failed');
    candidate=struct('displ',displ,'p_field',p_field,'strain_en_undgr',strain_en_undgr);
    candidate_oracle=phase_field.audit.assemble_residual_oracle(sys,assembly_equilibrium_fh,assembly_pf_fh,candidate,frozen,D_RHS_tract);
    [metrics,active_gp]=endpoint_monitor(sys,candidate,candidate_oracle,frozen,4e-6);
    extra=i_stag-baseline_iteration;
    metrics.iteration=i_stag;
    metrics.cached_stop_sum=SOL_STAG_VAR.normal_res_displ(i_stag)+res_pf;
    tight_trace(extra)=struct('iteration',i_stag,'free_u_l2',metrics.free_u_l2, ...
        'feasible_d_l2',metrics.feasible_d_l2,'projected_stop_sum',metrics.projected_stop_sum, ...
        'cached_stop_sum',metrics.cached_stop_sum,'converged',metrics.converged);
    last_completed=candidate; last_oracle=candidate_oracle;
    save(fullfile(work_dir,sprintf('tight_outer_%02d.mat',extra)), ...
        'candidate','candidate_oracle','metrics','active_gp','frozen','-v7.3');
    save(fullfile(work_dir,'tight_progress.mat'),'tight_trace','-v7');
    fprintf('[E011_TIGHT_PROGRESS] extra=%d projected_sum=%.12g cached_sum=%.12g\n',extra,metrics.projected_stop_sum,metrics.cached_stop_sum);
    if metrics.converged,control_pass=true;break;end
end
catch exception
    tight_result=struct('status','FAIL_INNER_OR_CONTRACT','control_pass',false, ...
        'completed_extra_iterations',numel(tight_trace),'history_commits',0,'error',exception.message);
    save(fullfile(work_dir,'tight_failure.mat'),'tight_result','tight_trace','last_completed','last_oracle','frozen','-v7.3');
    write_result(fullfile(work_dir,'tight_result.json'),tight_result);
    rethrow(exception);
end
if control_pass,status='PASS_PROJECTED_ABSOLUTE_SCREEN';else,status='EXTRA_BUDGET_EXHAUSTED';end
tight_result=struct('status',status,'control_pass',control_pass, ...
    'completed_extra_iterations',numel(tight_trace),'history_commits',0, ...
    'inner_u_tolerance',1e-8,'inner_phase_tolerance',4e-6,'outer_projected_tolerance',4e-6, ...
    'baseline_metrics',baseline_metrics,'final_metrics',metrics, ...
    'scope','fixed-s3-history c83s4 solver-control sensitivity; not a teacher certificate');
write_result(fullfile(work_dir,'tight_result.json'),tight_result);
fprintf('[E011_TIGHT_FINISHED] status=%s extra=%d\n',status,numel(tight_trace));
'''
    helpers=r'''
function [m,active]=endpoint_monitor(sys,state,oracle,frozen,tol)
assert(all(isfinite(oracle.R_d_free)) && all(isfinite(oracle.R_u_free)),'Nonfinite native residual');
idx=oracle.free_dof_d; d=state.p_field(idx); lower=frozen.p_field_old(idx);
g=oracle.R_d_free; at_lower=d<=lower+1e-10; at_upper=d>=1-1e-10;
g(at_lower)=min(g(at_lower),0);g(at_upper)=max(g(at_upper),0);g(at_lower & at_upper)=0;
u_norm=norm(oracle.R_u_free); d_norm=norm(g);
assert(all(isfinite(g)) && isfinite(u_norm) && isfinite(d_norm));
dgp=state.p_field(sys.MESH.elem(:,1:sys.MESH.nel))*sys.QUADRATURE.Nxi;
active=(1-dgp).^2.*state.strain_en_undgr;
assert(all(isfinite(active),'all'));
m=struct('free_u_l2',u_norm,'feasible_d_l2',d_norm,'projected_stop_sum',u_norm+d_norm, ...
    'raw_free_d_l2',norm(oracle.R_d_free),'converged',u_norm+d_norm<=tol);
end

function write_result(path,value)
fid=fopen(path,'w');if fid<0,error('Cannot write result');end
cleanup=onCleanup(@()fclose(fid));fprintf(fid,'%s\n',jsonencode(value));
end
'''
    return baseline.replace(marker,marker+insertion+iteration+post)+helpers


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();paths=['Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m','Scripts/fatigue_fracture/solve_fatigue_fracture.m','Scripts/fatigue_fracture/init_fatigue_fracture.m','Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m']
    hashes={p:hashlib.sha256((a.source_root/p).read_bytes()).hexdigest() for p in paths}
    text=build((a.source_root/paths[0]).read_text(),(a.source_root/paths[1]).read_text(),hashes)
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'run_s04_e011_endpoint_tight.m').write_text(text)
    (a.output/'source_lock.json').write_text(json.dumps(hashes,indent=2)+'\n')
if __name__=='__main__':main()
