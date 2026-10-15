function result = run_s04_e011_damage_repair(cfg, options)
%RUN_SENS_HARD_RECOVERY_NATIVE_Q4_CAPTURE Run an isolated native-Q4 capture.

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

assert(strcmpi(phase_field.audit.sha256_file(options.capture_path),options.capture_sha256));
c=load(options.capture_path);
assert(c.summary.cycle==options.cycle && strcmp(c.summary.stage,options.stage));
assert(isequal(c.initial.displ,initial.displ) && isequal(c.initial.p_field,initial.p_field));
assert(isequal(c.frozen.p_field_old,original_lower) && isequal(c.frozen.history_vars_old,original_history));
assert(isequal(c.node_coords,sys.MESH.node(:,1:2)) && isequal(c.connectivity,sys.MESH.elem(:,1:4)));
fixed_u=c.u_return;fixed_raw=c.raw_return;
assert(all(isfinite(fixed_u)) && all(isfinite(fixed_raw),'all'));
idx=sys.DOFS.active_dof_pf(:);upper=ones(size(original_lower));
evaluate=@(d)evaluate_native(d,assembly_pf_fh,sys,original_lower,fixed_raw,original_history);
[~,rref,href]=evaluate(c.d_clipped);
assert(max(abs(rref-c.r_clipped))<1e-10,'Capture phase replay mismatch');
assert(all(isfinite(href(:,:,2:4)),'all'));
if options.cycle==1,assert(max(abs(href(:,:,4)-1),[],'all')<1e-12,'c1 must have f=1');end
arms=[];
for arm_name=["fresh_only","constrained"]
 % 248 callback slots plus same-field audit and clipped audit = 250 total.
 out=e011_damage_solve(evaluate,initial.p_field,original_lower,upper,idx,arm_name,248,4e-6);
 arm_dir=fullfile(work_dir,char(arm_name));mkdir(arm_dir);
 % Persist before terminal audits; their failure must not erase this solve.
 save(fullfile(arm_dir,'returned_solve_before_audit.mat'),'out','initial','frozen','fixed_u','fixed_raw','-v7.3');
 assert(out.returned_residual_available,'E011:InitialAssemblyFailed','Initial phase assembly failed, attempt preserved');
 [~,r_fresh,h_fresh]=evaluate(out.d);
 assert(max(abs(r_fresh-out.r))<1e-10,'Fresh returned-state mismatch');
 dc=min(max(out.d,original_lower),upper);
 [~,r_clip,h_clip]=evaluate(dc);
 if arm_name=="constrained",assert(isequal(dc,out.d));end
 candidate=struct('displ',fixed_u,'p_field',dc,'strain_en_undgr',fixed_raw);
 % Mechanical assembly only: does not consume phase-solve budget.
 [~,ru,raw_check,~]=assembly_equilibrium_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
  fixed_u,0.0,dc,sys.stress_state.as_number,0.0);
 assert(all(isfinite(ru)) && all(isfinite(raw_check),'all'));
 arm=struct('mode',arm_name,'stop',out.stop,'failure',out.failure,'optimization_calls',out.calls, ...
  'total_phase_calls',out.calls+2,'shared_admission_phase_calls',2,'fresh_raw_l2',norm(r_fresh(idx)), ...
  'fresh_filtered_l2',feasible(out.d,r_fresh,idx,original_lower),'infeasible_nodes',out.infeasible_nodes, ...
  'clipped_filtered_l2',feasible(dc,r_clip,idx,original_lower),'mechanical_l2',norm(ru(sys.DOFS.active_dof)), ...
  'phase_pass',out.infeasible_nodes==0 && feasible(out.d,r_fresh,idx,original_lower)<=4e-6 && strlength(out.failure)==0, ...
  'd_vs_old_clipped_maxabs',max(abs(dc-c.d_clipped)),'history_commits',0,'raw_refresh_maxabs',max(abs(raw_check-fixed_raw),[],'all'));
 if options.cycle==1,assert(max(abs(h_fresh(:,:,4)-1),[],'all')<1e-12,'c1 fatigue factor changed');end
 assert(isequal(frozen.history_vars_old,original_history) && isequal(frozen.p_field_old,original_lower));
 assert(isequal(candidate.displ,fixed_u) && isequal(candidate.strain_en_undgr,fixed_raw));
 save(fullfile(arm_dir,'damage_repair.mat'),'arm','out','dc','r_fresh','h_fresh','r_clip','h_clip','ru','raw_check','candidate','initial','frozen','fixed_u','fixed_raw','-v7.3');
 fid=fopen(fullfile(arm_dir,'result.json'),'w');assert(fid>=0);fprintf(fid,'%s\n',jsonencode(arm));fclose(fid);
 if isempty(arms),arms=arm;else,arms(end+1)=arm;end %#ok<AGROW>
end
result=struct('cycle',options.cycle,'stage',options.stage,'arms',arms,'history_commits',0, ...
 'scope','fixed captured u/raw; independent phase diagnostic, not accepted coupled update');
fid=fopen(fullfile(work_dir,'damage_repair_result.json'),'w');assert(fid>=0);fprintf(fid,'%s\n',jsonencode(result));fclose(fid);
fprintf('[E011_DAMAGE_REPAIR_DONE] cycle=%d stage=%s history_commits=0\n',options.cycle,options.stage);
end

function [K,r,h]=evaluate_native(d,assembly_pf_fh,sys,original_lower,fixed_raw,original_history)
  [kv,r,~,h]=assembly_pf_fh(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC, ...
   d,original_lower,fixed_raw,sys.stress_state.as_number,original_history);
  K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
  assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'),'Nonfinite native phase assembly');
end

function v=feasible(d,r,idx,lower)
assert(all(isfinite(d)) && all(isfinite(r)) && all(isfinite(lower)),'Nonfinite phase before filtering');
x=r(idx);lo=d(idx)<=lower(idx)+1e-10;hi=d(idx)>=1-1e-10;
x(lo)=min(x(lo),0);x(hi)=max(x(hi),0);x(lo&hi)=0;assert(all(isfinite(x)));v=norm(x);
end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
