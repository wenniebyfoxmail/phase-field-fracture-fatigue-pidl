#!/usr/bin/env python3
"""Build opt-in fixed-state native projection/refresh capture, no history commit."""
import argparse,json,hashlib
from pathlib import Path
from prepare_s04_e011_endpoint_baseline import build as baseline_build

SUFFIX=r'''
assert(string(options.topology)=="q4");
assert(strcmpi(phase_field.audit.sha256_file(options.input_state),options.input_sha256));
z=load(options.input_state); frozen=z.frozen;
if isfield(z,'candidate'),initial=z.candidate; saved_oracle=z.candidate_oracle;
else,initial=z.converged;saved_oracle=z.oracle;end
assert(strcmpi(phase_field.audit.sha256_file(options.predecessor),options.predecessor_sha256));
pre=load(options.predecessor,'request28_snapshot');pre=pre.request28_snapshot;
assert(pre.cycle==options.cycle && pre.substep==3);
assert(isequal(sys.MESH.node(:,1:2),pre.node_coords) && isequal(sys.MESH.elem(:,1:sys.MESH.nel),pre.connectivity));
assert(isequal(frozen.p_field_old,pre.d_node) && isequal(frozen.history_vars_old,pre.history_vars_old));
if isfield(z,'result'),assert(z.result.physical_cycle==options.cycle && z.result.substep==4);
else,assert(z.metrics.iteration==options.expected_iteration);end
assert(numel(initial.p_field)==sys.MESH.num_node);
assert(abs(frozen.load_factor-.11999988/.12)<=1e-12);
assert(isvector(saved_oracle.free_dof_u) && isvector(saved_oracle.free_dof_d) && isvector(sys.DOFS.active_dof) && isvector(sys.DOFS.active_dof_pf));
assert(isequal(saved_oracle.free_dof_u(:),sys.DOFS.active_dof(:)) && isequal(saved_oracle.free_dof_d(:),sys.DOFS.active_dof_pf(:)));
assert(all(isfinite(initial.displ)) && all(isfinite(initial.p_field)) && all(isfinite(initial.strain_en_undgr),'all'));
assert(all(isfinite(frozen.history_vars_old(:,:,2:4)),'all'));
assert(all(initial.p_field>=frozen.p_field_old-1e-12) && all(initial.p_field<=1+1e-12));
D_RHS_tract=zeros(numel(initial.displ),1);
initial_oracle=phase_field.audit.assemble_residual_oracle(sys,assembly_equilibrium_fh,assembly_pf_fh,initial,frozen,D_RHS_tract);
assert(max(abs(initial_oracle.R_u_free-saved_oracle.R_u_free))<=1e-10);
assert(max(abs(initial_oracle.R_d_free-saved_oracle.R_d_free))<=1e-10);
original_history=frozen.history_vars_old;original_lower=frozen.p_field_old;
u_return=[];raw_return=[];last_phase_eval=struct();
try
% One original block direction, never accepted or propagated.
[~,cached_u_res,u_return,raw_return,~,u_failed]=phase_field.fem.solver.newton_raphson( ...
 assembly_equilibrium_fh,sys,initial.displ,0.0,initial.p_field,0.0,sys.DOFS.active_dof, ...
 sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,'D_RHS_tract',D_RHS_tract, ...
 'max_iter',250,'res_tol',1e-8,'line_search',false);
assert(~u_failed && all(isfinite(u_return)) && all(isfinite(raw_return),'all'));
last_phase_eval=struct();
[~,cached_d_res,d_return,~,cached_history,d_failed,last_phase_eval]=native_phase_newton_capture( ...
 assembly_pf_fh,sys,initial.p_field,frozen.p_field_old,raw_return,frozen.history_vars_old, ...
 sys.DOFS.active_dof_pf,sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf, ...
 'max_iter',250,'res_tol',4e-6,'line_search',false,'regularize_pf_only',true);
assert(~d_failed && all(isfinite(d_return)));phase_calls=last_phase_eval.iteration;
assert(all(isfinite(cached_history(:,:,2:4)),'all'));
assert(isequal(u_return(saved_oracle.prescribed_dof_u),initial.displ(saved_oracle.prescribed_dof_u)));
d_clipped=min(max(d_return,frozen.p_field_old),1);
[~,~,raw_refreshed,~]=assembly_equilibrium_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,u_return,0.0,d_clipped,sys.stress_state.as_number,0.0);
[~,r_return,~,h_return]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d_return,frozen.p_field_old,raw_return,sys.stress_state.as_number,frozen.history_vars_old);
[~,r_clipped,~,h_clipped]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d_clipped,frozen.p_field_old,raw_return,sys.stress_state.as_number,frozen.history_vars_old);
full_candidate=struct('displ',u_return,'p_field',d_clipped,'strain_en_undgr',raw_refreshed);
full_oracle=phase_field.audit.assemble_residual_oracle(sys,assembly_equilibrium_fh,assembly_pf_fh,full_candidate,frozen,D_RHS_tract);
[~,~,~,h_refreshed]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d_clipped,frozen.p_field_old,raw_refreshed,sys.stress_state.as_number,frozen.history_vars_old);
assert(isequal(frozen.history_vars_old,original_history) && isequal(frozen.p_field_old,original_lower));
idx=sys.DOFS.active_dof_pf;
rows=struct('label',{'cached_pre_last_newton','returned_pre_clip','clipped_same_raw','clipped_refreshed_raw'}, ...
 'raw_phase_l2',{cached_d_res,norm(r_return(idx)),norm(r_clipped(idx)),norm(full_oracle.R_d_free)}, ...
 'bound_filtered_phase_l2',{feasible(last_phase_eval.d,last_phase_eval.r,idx,original_lower),feasible(d_return,r_return,idx,original_lower),feasible(d_clipped,r_clipped,idx,original_lower),feasible(d_clipped,full_oracle.R_d_full,idx,original_lower)});
for j=1:numel(rows)
 if j==1,rdamage=last_phase_eval.d;elseif j==2,rdamage=d_return;else,rdamage=d_clipped;end
 rows(j).infeasible_node_count=nnz(rdamage<original_lower-1e-12 | rdamage>1+1e-12);
end
summary=struct('cycle',options.cycle,'stage',options.stage,'history_commits',0,'phase_calls',phase_calls, ...
 'cached_u_res',cached_u_res,'original_u_l2',norm(initial_oracle.R_u_free),'direction_u_l2',norm(full_oracle.R_u_free), ...
 'clip_maxabs',max(abs(d_return-d_clipped)),'clipped_nodes',nnz(d_return~=d_clipped), ...
 'cached_to_return_field_maxabs',max(abs(last_phase_eval.d-d_return)), ...
 'cached_to_return_history_234_maxabs',max(abs(cached_history(:,:,2:4)-h_return(:,:,2:4)),[],'all'), ...
 'return_to_clip_history_234_maxabs',max(abs(h_return(:,:,2:4)-h_clipped(:,:,2:4)),[],'all'), ...
 'clip_to_refresh_history_234_maxabs',max(abs(h_clipped(:,:,2:4)-h_refreshed(:,:,2:4)),[],'all'), ...
 'raw_refresh_maxabs',max(abs(raw_return-raw_refreshed),[],'all'),'rows',rows, ...
 'input_sha256',options.input_sha256,'scope','one isolated native block direction; not accepted outer update');
if isfield(options,'direction_reference') && strlength(string(options.direction_reference))>0
 assert(strcmpi(phase_field.audit.sha256_file(options.direction_reference),options.direction_reference_sha256));
 dr=load(options.direction_reference,'trial');
 assert(max(abs(dr.trial.displ-full_candidate.displ))<=1e-10);
 assert(max(abs(dr.trial.p_field-full_candidate.p_field))<=1e-10);
 summary.stalled_direction_reproduced=true;
end
% Saved-state native directional audit: ambient raw residual first, bound merit separately.
du=full_candidate.displ-initial.displ;dd=full_candidate.p_field-initial.p_field;
[Kuv,~,~,~]=assembly_equilibrium_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,initial.displ,0.0,initial.p_field,sys.stress_state.as_number,0.0);
[Kdv,~,~,h0]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,initial.p_field,original_lower,initial.strain_en_undgr,sys.stress_state.as_number,original_history);
Ku=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,Kuv);
Kd=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,Kdv);
fu=sys.DOFS.active_dof;fd=sys.DOFS.active_dof_pf;bd=Kd*dd;bu=Ku*du;native_kdd_jvp=bd;native_kuu_jvp=bu;node_coords=sys.MESH.node(:,1:2);connectivity=sys.MESH.elem(:,1:sys.MESH.nel);material=sys.MAT_CHAR;assembly_identity=struct('equilibrium',functions(assembly_equilibrium_fh),'phase',functions(assembly_pf_fh));
tangent_rows=struct('mode',{},'epsilon',{},'phase_fd_l2',{},'mechanical_fd_l2',{},'phase_picard_relerr',{},'mechanical_block_relerr',{},'phase_residual_l2',{},'mechanical_residual_l2',{},'trial_history_234_maxdelta',{});
for mode=1:3
 for e=[1e-2,1e-3,1e-4,1e-5,1e-6]
  tu=initial.displ;td=initial.p_field;
  if mode~=2,tu=tu+e*du;end
  if mode~=1,td=td+e*dd;end
  if mode==2,traw=initial.strain_en_undgr;else
   [~,~,traw,~]=assembly_equilibrium_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,tu,0.0,td,sys.stress_state.as_number,0.0);
  end
  ts=struct('displ',tu,'p_field',td,'strain_en_undgr',traw);
  to=phase_field.audit.assemble_residual_oracle(sys,assembly_equilibrium_fh,assembly_pf_fh,ts,frozen,D_RHS_tract);
  [~,~,~,th]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,td,original_lower,traw,sys.stress_state.as_number,original_history);
  pd=(to.R_d_free-initial_oracle.R_d_free)/e;pu=(to.R_u_free-initial_oracle.R_u_free)/e;
  bdd=bd(fd);buu=bu(fu);if mode==1,bdd(:)=0;elseif mode==2,buu(:)=0;end
  tangent_rows(end+1)=struct('mode',mode,'epsilon',e,'phase_fd_l2',norm(pd),'mechanical_fd_l2',norm(pu), ...
   'phase_picard_relerr',norm(pd-bdd)/max(norm(pd),eps),'mechanical_block_relerr',norm(pu-buu)/max(norm(pu),eps), ...
   'phase_residual_l2',feasible(td,to.R_d_full,fd,original_lower),'mechanical_residual_l2',norm(to.R_u_free), ...
   'trial_history_234_maxdelta',max(abs(th(:,:,2:4)-h0(:,:,2:4)),[],'all'));
 end
end
assert(isequal(frozen.history_vars_old,original_history) && isequal(frozen.p_field_old,original_lower));
save(fullfile(work_dir,'projection_capture.mat'),'summary','initial','initial_oracle','frozen', ...
 'u_return','raw_return','d_return','d_clipped','last_phase_eval','cached_history','h_return','h_clipped','h_refreshed', ...
 'r_return','r_clipped','full_candidate','full_oracle','tangent_rows','native_kdd_jvp','native_kuu_jvp','node_coords','connectivity','material','assembly_identity','-v7.3');
fid=fopen(fullfile(work_dir,'phase_capture_result.json'),'w');assert(fid>=0);fprintf(fid,'%s\n',jsonencode(summary));fclose(fid);
fprintf('[E011_PHASE_CAPTURE_DONE] cycle=%d stage=%s history_commits=0\n',options.cycle,options.stage);
result=summary;
catch exception
 failure=struct('cycle',options.cycle,'stage',options.stage,'error',exception.message,'history_commits',0);
 save(fullfile(work_dir,'partial_capture.mat'),'initial','frozen','u_return','raw_return','last_phase_eval','failure','-v7.3');
 fid=fopen(fullfile(work_dir,'capture_failure.json'),'w');if fid>=0,fprintf(fid,'%s',jsonencode(failure));fclose(fid);end
 rethrow(exception);
end
end

function v=feasible(d,r,idx,lower)
assert(all(isfinite(r(idx))) && all(isfinite(d)) && all(isfinite(lower)),'Nonfinite field or native phase residual');
x=r(idx);lo=d(idx)<=lower(idx)+1e-10;hi=d(idx)>=1-1e-10;
x(lo)=min(x(lo),0);x(hi)=max(x(hi),0);x(lo&hi)=0;assert(all(isfinite(x)));v=norm(x);
end

function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''


def build(driver,solver,hashes,newton):
    s=baseline_build(driver,solver,hashes)
    anchor='assert(string(options.topology)=="q4",'
    if s.count(anchor)!=1:raise ValueError('Initialization marker changed')
    prefix=s.split(anchor)[0].replace('run_s04_e011_endpoint_baseline','run_s04_e011_phase_capture')
    check="assert(isfield(options,'binary_checks'));\nfor k=1:numel(options.binary_checks)\n bc=options.binary_checks(k);bp=which(bc.name);assert(strcmpi(bp,bc.path));assert(strcmpi(phase_field.audit.sha256_file(bp),bc.sha256));\nend\nassert(isfield(options,'source_checks'));\nfor k=1:numel(options.source_checks)\n sc=options.source_checks(k);assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,sc.path)),sc.sha256));\nend\n"
    nr=newton.replace('history_vars_new, non_conv] = newton_raphson','history_vars_new, non_conv, evaluation_info] = native_phase_newton_capture',1)
    marker='    % diagnose'
    if nr.count(marker)!=1:raise ValueError('Newton capture marker drift')
    nr=nr.replace(marker,"    evaluation_info=struct('d',field_vars,'r',res_field_vars,'history',history_vars_new,'iteration',n_iter);\n"+marker)
    return prefix.replace('init_fatigue_fracture\n',check+'init_fatigue_fracture\n')+SUFFIX+'\n'+nr


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--newton-source',type=Path,required=True);a=p.parse_args()
    paths=['Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m','Scripts/fatigue_fracture/solve_fatigue_fracture.m','Scripts/fatigue_fracture/init_fatigue_fracture.m','Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m']
    hashes={p:hashlib.sha256((a.source_root/p).read_bytes()).hexdigest() for p in paths}
    s=build((a.source_root/paths[0]).read_text(),(a.source_root/paths[1]).read_text(),hashes,a.newton_source.read_text())
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'run_s04_e011_phase_capture.m').write_text(s);(a.output/'source_lock.json').write_text(json.dumps(hashes,indent=2)+'\n')
if __name__=='__main__':main()
