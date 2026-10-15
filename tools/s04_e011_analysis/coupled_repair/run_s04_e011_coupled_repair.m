function result = run_s04_e011_coupled_repair(cfg, options)
%RUN_S04_E011_COUPLED_REPAIR Frozen-history native-Q4 coupled diagnostic.

arguments
    cfg (1,1) struct
    options (1,1) struct
end

required_cfg = ["output_identity", "initial_crack", "initialization", ...
    "reset_fatigue_after_recovery", "res_stiff", "n_step", ...
    "requested_n_step", "effective_load_factor", "requested_cycles", ...
    "defer_stop_until_cycle"];
missing_cfg = required_cfg(~isfield(cfg, required_cfg));
if ~isempty(missing_cfg)
    invalidConfig("Missing configuration fields: " + strjoin(missing_cfg, ", "));
end
if ~isfield(options, 'work_dir') || ~isscalar(string(options.work_dir)) || ...
        strlength(string(options.work_dir)) == 0
    invalidConfig('options.work_dir is required.');
end
if ~isfield(options, 'validate_only')
    options.validate_only = false;
end

work_dir = string(options.work_dir);
if isfolder(work_dir), error('E011:OutputExists','Refusing existing output root'); end
if strlength(work_dir) > 180
    error('phase_field:audit:UnsafeCapturePathLength', ...
        'Capture work_dir exceeds the conservative Windows MEX path limit.');
end
if ~strcmp(string(cfg.initial_crack), "hard") || ...
        ~strcmp(string(cfg.initialization), "separate_zero_load_phase_recovery") || ...
        ~logical(cfg.reset_fatigue_after_recovery) || cfg.res_stiff ~= 0
    invalidConfig('Capture requires hard zero-load recovery with eta=0.');
end
if cfg.n_step ~= numel(cfg.effective_load_factor)
    invalidConfig('n_step must match the effective load schedule.');
end
if any(~isfinite(cfg.effective_load_factor)) || ...
        any(~isfinite(cfg.requested_cycles)) || ...
        any(cfg.requested_cycles < 1) || ...
        any(fix(cfg.requested_cycles) ~= cfg.requested_cycles)
    invalidConfig('Load factors and requested cycles must be finite and valid.');
end

peak_step = phase_field.audit.find_peak_step(cfg.effective_load_factor);
checkpoint_candidates = [fullfile(work_dir, "checkpoint.mat"), ...
    fullfile(work_dir, "step_checkpoint.mat")];
if any(isfile(checkpoint_candidates))
    error('phase_field:audit:PrepopulatedCaptureWorkspace', ...
        'Capture workspace contains a cycle or step checkpoint: %s', work_dir);
end

result = struct( ...
    'status', "validated", ...
    'work_dir', work_dir, ...
    'peak_step', peak_step, ...
    'requested_cycles', reshape(double(cfg.requested_cycles), 1, []), ...
    'output_identity', string(cfg.output_identity));
if options.validate_only
    return;
end

if ~isfield(options, 'max_cycle') || ~isscalar(options.max_cycle) || ...
        ~isfinite(options.max_cycle) || options.max_cycle < 1 || ...
        fix(options.max_cycle) ~= options.max_cycle
    invalidConfig('Execution requires a positive integer options.max_cycle.');
end
if max(cfg.requested_cycles) > options.max_cycle
    invalidConfig('All requested capture cycles must be within options.max_cycle.');
end
[output_root, work_identity] = fileparts(work_dir);
if string(work_identity) ~= string(cfg.output_identity)
    error('phase_field:audit:WorkspaceIdentityMismatch', ...
        'The work_dir leaf must equal cfg.output_identity.');
end
if ~isfolder(output_root)
    mkdir(output_root);
end
original_dir = pwd;
directory_cleanup = onCleanup(@() cd(original_dir)); %#ok<NASGU>
cd(output_root);

repo_root = char(options.source_root);
addpath(fullfile(repo_root, 'Scripts', 'fatigue_fracture'));
addpath(genpath(fullfile(repo_root, 'Dependencies')));
addpath(fullfile(repo_root, 'Sources'));
addpath(fullfile(repo_root, 'Scripts', 'brittle_fracture'));

run(fullfile(repo_root, 'Scripts', 'brittle_fracture', 'INPUT_SENS_tensile.m'));

if ~isfield(options, 'mesh_file') || ~isfile(options.mesh_file)
    invalidConfig('options.mesh_file must name an existing Abaqus mesh.');
end
if ~isfield(options, 'topology') || ~ismember(string(options.topology), ["q4" "t3"])
    invalidConfig('options.topology must be q4 or t3.');
end
[MESH, GEOM] = specimen.external.abaqus_import(options.mesh_file, 't', 1.0);
mesh_tol = 1e-12;
NODESET = struct();
NODESET.top_edge = find(abs(MESH.node(:,2) - max(MESH.node(:,2))) <= mesh_tol);
NODESET.bot_edge = find(abs(MESH.node(:,2) - min(MESH.node(:,2))) <= mesh_tol);
NODESET.crack = find(abs(MESH.node(:,2)) <= mesh_tol & MESH.node(:,1) <= mesh_tol);
if isempty(NODESET.top_edge) || isempty(NODESET.bot_edge) || isempty(NODESET.crack)
    invalidConfig('Imported mesh is missing top, bottom, or crack nodes.');
end
NODE_BOUNDARIES = phase_field.fem.bc.set_boundaries( ...
    'fix_X', [NODESET.bot_edge; NODESET.top_edge], ...
    'fix_Y', NODESET.bot_edge, 'disp_Y', NODESET.top_edge, ...
    'non_hom_pf', NODESET.crack);
DOFS = phase_field.init.dofs(MESH, NODE_BOUNDARIES);
if string(options.topology) == "q4"
    if MESH.nel ~= 4
        invalidConfig('Q4 arm requires four-node connectivity.');
    end
    e011_elem_type = phase_field.init.ElementType.QUAD4;
    e011_label = "q4";
else
    if MESH.nel ~= 3
        invalidConfig('T3 arm requires three-node connectivity.');
    end
    e011_elem_type = phase_field.init.ElementType.TRIA3;
    e011_label = "t3";
end
QUADRATURE = phase_field.init.quadrature(MESH.dim, ...
    'elem_type', e011_elem_type, 'order', 2);
example_name = char(cfg.output_identity);
MAT_CHAR(1) = phase_field.init.material_characteristic( ...
    GEOM.L, diss_fct, 'E', 1.0, 'ni', 0.3, 'Gc', 0.01, 'ell', 0.01, ...
    'res_stiff', cfg.res_stiff, 'alpha_T', cfg.alpha_T, 'p', 2.0);
SOL_PAR = phase_field.fem.solver.params( ...
    'tol_displ', cfg.displacement_tol, 'tol_p_field', cfg.pf_tol, ...
    'max_iter_displ', cfg.max_iter_displacement, ...
    'max_iter_pf', cfg.max_iter_phase);
SOL_STAG_PAR = phase_field.fem.solver.stag.params( ...
    'tol', cfg.staggered_tol, 'max_iter', cfg.max_iter_staggered);
SOL_STEP_PAR = phase_field.fem.solver.step.params( ...
    'n_step', cfg.requested_n_step, 'loading', cfg.loading, ...
    'discretization', cfg.discretization, 'uy_final', cfg.u_max, ...
    'R', cfg.R, 'line_search', false);
actual_load_factor = cumsum(SOL_STEP_PAR.uy_increment) / cfg.u_max;
if SOL_STEP_PAR.n_step ~= cfg.n_step || ...
        ~isequal(size(actual_load_factor), size(cfg.effective_load_factor)) || ...
        any(abs(actual_load_factor - cfg.effective_load_factor) > 1e-14)
    invalidConfig('Constructed solver cadence does not match the locked effective path.');
end
SOL_CYCL_PAR = phase_field.fem.solver.cycl.params( ...
    'max_cycle', options.max_cycle, 'da_paraview', 0.01);
SOL_JUMP_PAR = phase_field.fem.solver.cycl_jump.params('cycl_jump', false);
CRACK_PAR = phase_field.fem.crack.params( ...
    MAT_CHAR, diss_fct, 'crack_thres', cfg.penetration_threshold);

checkpoint_freq = 1;
enable_step_checkpoint = true;
step_checkpoint_freq = 1;
vtk_freq = 10;
regularize_pf_newton = true;
damage_upper_bound = 1.0;
penetration_boundary_mode = 'right_layer';
penetration_right_x_min = cfg.penetration_right_x_min;
penetration_threshold = cfg.penetration_threshold;
penetration_min_nodes = cfg.penetration_min_nodes;
penetration_confirm_cycles = cfg.penetration_confirm_cycles;

assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,'Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m')), 'b08b0187657a019c941cd707a904cb8e39623ac7d56f22e00158625aee5110b9'), 'Frozen source hash mismatch: Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m');
assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,'Scripts/fatigue_fracture/solve_fatigue_fracture.m')), 'd3603548b392d01d64c8a32c78aaa5247b92ae24d8b7645886d190b240687d91'), 'Frozen source hash mismatch: Scripts/fatigue_fracture/solve_fatigue_fracture.m');
assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,'Scripts/fatigue_fracture/init_fatigue_fracture.m')), 'cd3ba4bd77e321da53ae733a40c6ef69537864c622f0eaf53f912f91c08c415d'), 'Frozen source hash mismatch: Scripts/fatigue_fracture/init_fatigue_fracture.m');
assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,'Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m')), '6313b4ad7b1bd7bbad6a1b793d6b54992bcf4d97089c82a81b360567e2c965b0'), 'Frozen source hash mismatch: Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m');
assert(isfield(options,'binary_checks'));
for k=1:numel(options.binary_checks)
 bc=options.binary_checks(k);bp=which(bc.name);assert(strcmpi(bp,bc.path));assert(strcmpi(phase_field.audit.sha256_file(bp),bc.sha256));
end
assert(isfield(options,'source_checks'));
for k=1:numel(options.source_checks)
 sc=options.source_checks(k);assert(strcmpi(phase_field.audit.sha256_file(fullfile(repo_root,sc.path)),sc.sha256));
end
init_fatigue_fracture


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


assert(strcmpi(phase_field.audit.sha256_file(options.prior_repair_path),options.prior_repair_sha256));
p=load(options.prior_repair_path);
assert(strcmp(p.arm.mode,'constrained') && p.arm.phase_pass && p.arm.history_commits==0);
assert(isequal(p.initial.displ,initial.displ) && isequal(p.initial.p_field,initial.p_field));
assert(isequal(p.frozen.p_field_old,original_lower) && isequal(p.frozen.history_vars_old,original_history));
assert(isequal(p.candidate.displ,p.fixed_u) && isequal(p.candidate.p_field,p.dc));
assert(isequal(p.candidate.strain_en_undgr,p.fixed_raw));
assert(all(p.dc>=original_lower-1e-12 & p.dc<=1+1e-12));
eq=@(u,d)equilibrium_native(u,d,assembly_equilibrium_fh,sys);
pf=@(d,raw)phase_native(d,raw,assembly_pf_fh,sys,original_lower,original_history);
% Root old-state oracle above:1u/1d. Prior phase replay adds1d.
[~,prior_r,prior_h]=pf(p.dc,p.fixed_raw);
assert(max(abs(prior_r-p.r_clip))<1e-10 && max(abs(prior_h(:,:,2:4)-p.h_clip(:,:,2:4)),[],'all')<1e-10,'Prior repair replay mismatch');
limits=struct('admission_u',1,'admission_d',2,'max_u',249,'max_d',249, ...
 'max_outer',20,'u_tol',1e-8,'d_tol',4e-6,'joint_tol',4e-6);
checkpoint=@(state,trace,counts)save_checkpoint(work_dir,state,trace,counts);
out=e011_coupled_solve(eq,pf,p.fixed_u,p.dc,original_lower,ones(size(original_lower)), ...
 sys.DOFS.active_dof,sys.DOFS.active_dof_pf,limits,checkpoint);
out.stop_char=char(out.stop);out.failure_char=char(out.failure);
source_identity=struct('input_state',options.input_state,'input_sha256',options.input_sha256, ...
 'prior_repair_path',options.prior_repair_path,'prior_repair_sha256',options.prior_repair_sha256, ...
 'cycle',options.cycle,'stage',options.stage,'history_commits',0);
% Preserve every returned field/failure record before any terminal audit.
save(fullfile(work_dir,'before_final_audit.mat'),'out','frozen','source_identity','limits','-v7.3');
assert(~isempty(out.initial) && ~isempty(out.final),'E011:NoCompletePoint','No initial complete joint state; see saved failure');
assert(max(abs(out.initial.ru-p.ru))<1e-10,'Prior mechanical identity mismatch');
raw_identity=max(abs(out.initial.raw-p.raw_check)./max(1,abs(p.raw_check)),[],'all');
assert(raw_identity<1e-10,'Prior refreshed raw identity mismatch');
raw_input_delta=max(abs(out.initial.raw-p.fixed_raw),[],'all');
root_audits=struct('u',0,'d',0);
try
 root_audits.u=1;[~,ru,raw]=eq(out.final.u,out.final.d);
 root_audits.d=1;[~,rd,h]=pf(out.final.d,raw);
 assert(max(abs(ru-out.final.ru))<1e-10 && max(abs(rd-out.final.rd))<1e-10,'Same-field final audit mismatch');
 assert(max(abs(h(:,:,2:4)-out.final.history234),[],'all')<1e-10,'Same-field history audit mismatch');
 assert(isequal(frozen.p_field_old,original_lower) && isequal(frozen.history_vars_old,original_history));
 assert(isequal(frozen.p_field_old,p.frozen.p_field_old) && isequal(frozen.history_vars_old,p.frozen.history_vars_old));
 % Norms are freshly computed, not trusted from the controller return.
 idx=sys.DOFS.active_dof_pf(:);x=rd(idx);lo=out.final.d(idx)<=original_lower(idx)+1e-10;hi=out.final.d(idx)>=1-1e-10;
 x(lo)=min(x(lo),0);x(hi)=max(x(hi),0);x(lo&hi)=0;
 ur=norm(ru(sys.DOFS.active_dof));dr=norm(x);criterion=max((ur+dr)/4e-6,ur/1e-8);
 assert(all(isfinite([ur dr criterion])));
 summary=struct('cycle',options.cycle,'stage',options.stage,'stop',out.stop,'failure',out.failure, ...
  'completed_outer',out.completed_outer,'u_l2',ur,'d_feasible_l2',dr,'sum_l2',ur+dr,'criterion',criterion, ...
  'joint_pass',out.joint_pass && criterion<=1,'phase_pass',dr<=4e-6, ...
  'total_u_calls',out.counts.u+1,'total_d_calls',out.counts.d+1,'admission_u_calls',1,'admission_d_calls',2, ...
  'raw_initial_vs_prior_fixed_maxabs',raw_input_delta,'raw_prior_fresh_identity_scaled',raw_identity, ...
  'history_commits',0,'scope','independent same-peak frozen-s3-history coupled numerical diagnostic');
 assert(summary.total_u_calls<=250 && summary.total_d_calls<=250);
 free_dof_u=sys.DOFS.active_dof;free_dof_d=sys.DOFS.active_dof_pf;
 audited_final=struct('ru',ru,'rd',rd,'raw',raw,'history234',h(:,:,2:4));
 save(fullfile(work_dir,'coupled_result.mat'),'out','audited_final','frozen','source_identity','summary','limits','free_dof_u','free_dof_d','-v7.3');
 fid=fopen(fullfile(work_dir,'coupled_result.json'),'w');assert(fid>=0);fprintf(fid,'%s\n',jsonencode(summary));fclose(fid);
 fprintf('[E011_COUPLED_REPAIR_DONE] cycle=%d stage=%s joint_pass=%d history_commits=0\n',options.cycle,options.stage,summary.joint_pass);
 result=summary;
catch exception
 save(fullfile(work_dir,'final_audit_failure.mat'),'out','frozen','source_identity','root_audits','-v7.3');
 rethrow(exception);
end
end

function [K,r,raw]=equilibrium_native(u,d,assembly_fh,sys)
[kv,r,raw,~]=assembly_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
 u,0.0,d,sys.stress_state.as_number,0.0);
K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(raw),'all'),'Nonfinite native equilibrium assembly');
end
function [K,r,h]=phase_native(d,raw,assembly_fh,sys,lower,history)
[kv,r,~,h]=assembly_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
 d,lower,raw,sys.stress_state.as_number,history);
K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'),'Nonfinite native phase assembly');
end
function save_checkpoint(work_dir,state,trace,counts)
save(fullfile(work_dir,'last_completed_joint.mat'),'state','trace','counts','-v7.3');
end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
