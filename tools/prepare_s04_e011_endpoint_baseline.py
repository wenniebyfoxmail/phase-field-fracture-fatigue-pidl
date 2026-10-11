#!/usr/bin/env python3
"""Generate an isolated c83s3->s4 baseline from the exact frozen FEM driver blocks."""
import argparse
import hashlib
import json
from pathlib import Path


def unique_before(text, marker):
    if text.count(marker)!=1: raise ValueError(f'nonunique source marker: {marker}')
    return text.split(marker)[0]


def build(driver, solver, source_hashes):
    prefix=unique_before(driver,'\nstrain_en_undgr = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);')
    prefix=prefix.replace('run_SENS_hard_recovery_native_q4_capture(cfg, options)','run_s04_e011_endpoint_baseline(cfg, options)',1)
    anchor="repo_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));"
    if prefix.count(anchor)!=1: raise ValueError('repo root anchor changed')
    prefix=prefix.replace(anchor,"repo_root = char(options.source_root);\naddpath(fullfile(repo_root, 'Scripts', 'fatigue_fracture'));")
    guard="work_dir = string(options.work_dir);"
    prefix=prefix.replace(guard,guard+"\nif isfolder(work_dir), error('E011:OutputExists','Refusing existing output root'); end")
    start='        for i_stag = 1:SOL_STAG_PAR.max_iter\n'
    end='            if stag_converged\n'
    if solver.count(start)!=1 or solver.count(end)!=1: raise ValueError('outer-loop source marker changed')
    loop=solver.split(start)[1].split(end)[0]
    checks='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,'{p}')), '{sha}'), 'Frozen source hash mismatch: {p}');" for p,sha in source_hashes.items())
    # Check source before executing the exact initialization script.
    prefix=prefix.replace('\ninit_fatigue_fracture\n', '\n'+checks+'\ninit_fatigue_fracture\n')
    suffix=r'''
assert(string(options.topology)=="q4", 'This baseline runner is locked to Q4');
assert(cfg.displacement_tol==1e-6 && cfg.pf_tol==4e-4 && cfg.staggered_tol==4e-4);
assert(cfg.max_iter_staggered==1000 && cfg.max_iter_phase==250 && cfg.max_iter_displacement==250);
assert(strcmpi(phase_field.audit.sha256_file(options.predecessor),options.predecessor_sha256));
assert(strcmpi(phase_field.audit.sha256_file(options.reference_peak),options.reference_peak_sha256));
a = load(options.predecessor,'request28_snapshot'); predecessor = a.request28_snapshot;
b = load(options.reference_peak,'pre_phase_input','converged_peak_solution','matlab_residual');
assert(predecessor.cycle==83 && predecessor.substep==3 && b.converged_peak_solution.cycle==83 && b.converged_peak_solution.step==4);
assert(b.converged_peak_solution.staggered_iteration==20, 'Frozen Q4 reference must be iter20');
assert(isequal(sys.MESH.node(:,1:2),predecessor.node_coords));
assert(isequal(sys.MESH.elem(:,1:sys.MESH.nel),predecessor.connectivity));
assert(isequal(predecessor.d_node,b.pre_phase_input.p_field_old));
assert(isequal(predecessor.history_vars_old,b.pre_phase_input.history_vars_old));
displ = predecessor.u_node(:); p_field = predecessor.d_node; p_field_old=p_field;
history_vars_old=predecessor.history_vars_old;
frozen_history=history_vars_old; frozen_damage=p_field_old;
strain_en_undgr=predecessor.psi_raw_gp;
SOL_CYCL_VAR.n_cycle=83;
i_step=4;
native_q4_capture=struct('enabled',false);
% Restore the accepted s3 tangent before the load predictor: System was constructed at c0.
[K_pre,~,psi_pre,~]=assembly_equilibrium_fh(sys.MESH,sys.DOFS,sys.GEOM.t, ...
    sys.QUADRATURE,sys.MAT_CHAR,sys.CC,displ,0.0,p_field,sys.stress_state.as_number,0.0);
assert(max(abs(psi_pre-predecessor.psi_raw_gp),[],'all')<=1e-10,'Predecessor raw strain energy mismatch');
sys.STIFFNESS_MATRIX.KK=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,K_pre);
[displ,res_displ,D_RHS_tract]=phase_field.fem.solver.step.pre_iter_update(i_step,sys,displ,SOL_STEP_PAR);
res_displ_0=norm(res_displ(sys.DOFS.active_dof,1));
trace=struct([]); stopped=false;
fprintf('[E011_ENDPOINT_BASELINE_STARTED] c83s3 -> c83s4 U=%.12g\n',sum(SOL_STEP_PAR.uy_increment(1:4)));
for i_stag=1:SOL_STAG_PAR.max_iter
'''
    tail=r'''
    assert(isequal(history_vars_old,frozen_history) && isequal(p_field_old,frozen_damage), 'Immutable predecessor changed');
    assert(all(isfinite(displ)) && all(isfinite(p_field)) && all(isfinite(strain_en_undgr),'all'));
    trace(i_stag)=struct('iteration',i_stag,'cached_damage_residual',res_pf, ...
        'refreshed_u_residual',SOL_STAG_VAR.normal_res_displ(i_stag), ...
        'stop_sum',SOL_STAG_VAR.normal_res_displ(i_stag)+res_pf, 'converged',stag_converged);
    save(fullfile(work_dir,'progress.mat'),'trace','-v7');
    fprintf('[E011_ENDPOINT_PROGRESS] iteration=%d stop_sum=%.12g\n',i_stag,trace(i_stag).stop_sum);
    if stag_converged, stopped=true; break; end
end
if ~stopped, error('E011:BaselineCap','Baseline exhausted frozen 1000-outer cap'); end
uv=reshape(displ,[sys.MESH.num_node,2]); reference=b.converged_peak_solution;
err_u=max(abs(uv(:,1)-reference.u)); err_v=max(abs(uv(:,2)-reference.v)); err_d=max(abs(p_field-reference.d));
ref_displ=[reference.u;reference.v];
rel_u=norm(displ-ref_displ)/max(norm(ref_displ),eps);
rel_d=norm(p_field-reference.d)/max(norm(reference.d),eps);
frozen=struct('p_field_old',p_field_old,'history_vars_old',history_vars_old,'load_factor',.11999988/.12);
converged=struct('displ',displ,'p_field',p_field,'strain_en_undgr',strain_en_undgr);
oracle=phase_field.audit.assemble_residual_oracle(sys,assembly_equilibrium_fh,assembly_pf_fh,converged,frozen,D_RHS_tract);
residual_u_error=max(abs(oracle.R_u_free-b.matlab_residual.R_u_free));
residual_d_error=max(abs(oracle.R_d_free-b.matlab_residual.R_d_free));
baseline_pass=(i_stag==reference.staggered_iteration && err_u<=1e-10 && err_v<=1e-10 && err_d<=1e-10 ...
    && rel_u<=1e-8 && rel_d<=1e-8 && residual_u_error<=1e-10 && residual_d_error<=1e-10);
result=struct('schema','s04e011-c83-single-step-baseline-v1','baseline_pass',baseline_pass, ...
    'iterations',i_stag,'expected_iterations',reference.staggered_iteration, ...
    'max_abs_u',err_u,'max_abs_v',err_v,'max_abs_d',err_d,'relative_displacement',rel_u, ...
    'relative_damage',rel_d,'native_ru_max_error',residual_u_error,'native_rd_max_error',residual_d_error, ...
    'history_commits',0,'physical_cycle',83,'substep',4, 'source_root',repo_root, ...
    'predecessor_sha256',options.predecessor_sha256,'reference_peak_sha256',options.reference_peak_sha256);
save(fullfile(work_dir,'baseline_endpoint.mat'),'result','trace','converged','frozen','oracle','-v7.3');
fid=fopen(fullfile(work_dir,'result.json'),'w'); fprintf(fid,'%s\n',jsonencode(result)); fclose(fid);
if ~baseline_pass, error('E011:BaselineMismatch','Original-settings baseline did not reproduce'); end
fprintf('[E011_ENDPOINT_BASELINE_PASS] iterations=%d, no history commit\n',i_stag);
end

function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''
    return prefix+suffix.replace(r'\\n',r'\n')+loop+tail.replace(r'\\n',r'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.source_root
    paths=['Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m','Scripts/fatigue_fracture/solve_fatigue_fracture.m','Scripts/fatigue_fracture/init_fatigue_fracture.m','Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m']
    hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    generated=build((root/paths[0]).read_text(),(root/paths[1]).read_text(),hashes)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'run_s04_e011_endpoint_baseline.m').write_text(generated)
    (a.output/'source_lock.json').write_text(json.dumps(hashes,indent=2)+'\n')

if __name__=='__main__':main()
