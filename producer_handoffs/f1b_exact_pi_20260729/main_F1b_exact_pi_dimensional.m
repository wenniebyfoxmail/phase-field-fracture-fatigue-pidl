function main_F1b_exact_pi_dimensional
% Fresh dimensional GRIPHFiTH solve for the F1b exact-Pi gate.

start_tic = tic;
close all
clc
format shortE;

output_root = getenv('F1B_OUTPUT_ROOT');
source_commit = getenv('F1B_SOURCE_COMMIT');
input_lock_sha256 = getenv('F1B_INPUT_LOCK_SHA256');
if isempty(output_root) || isempty(source_commit) || isempty(input_lock_sha256)
    error('F1B_OUTPUT_ROOT, F1B_SOURCE_COMMIT, and F1B_INPUT_LOCK_SHA256 are required.');
end
if exist(output_root, 'dir')
    error('Immutable F1b output root already exists: %s', output_root);
end

dep_path = genpath(fullfile('..', '..', 'Dependencies'));
addpath(dep_path)
pkg_path = fullfile('..', '..', 'Sources');
addpath(pkg_path)
brittle_path = fullfile('..', 'brittle_fracture');
addpath(brittle_path)

ss_paths = {
    'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/AMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/COLAMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/CCOLAMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/CAMD/MATLAB' ...
};
for i_path = 1:numel(ss_paths)
    if exist(ss_paths{i_path}, 'dir'), addpath(ss_paths{i_path}); end
end

disp(' ')
disp('        GRIPHFiTH F1b exact-Pi fresh dimensional solve')
disp(datetime("now"))
disp(' ')

INPUT_SENS_tensile

% Exact dimensional realization of the normalized formal eta0 SENS model.
f1b_case_id = 'F1b_exactPi_dimensional_v2';
example_name = output_root;
f1b_geometry_scale = 10.0;
MESH.node(:, 1:2) = f1b_geometry_scale * MESH.node(:, 1:2);
GEOM.L = 10.0;
GEOM.B = 10.0;
GEOM.t = 10.0;

MAT_CHAR(1) = phase_field.init.material_characteristic( ...
    GEOM.L, diss_fct, ...
    'E', 3.0, 'ni', 0.3, 'Gc', 0.3, 'ell', 0.1, ...
    'res_stiff', 0.0, 'alpha_T', 1.5, 'p', 2.0 ...
);
% Preserve the dimensionless nonlinear problem under the exact-Pi map.
% Equilibrium residuals have force units; phase-field residuals/tangents have
% energy units because d is dimensionless.
f1b_force_scale = 3.0 * 10.0 * 10.0;
f1b_energy_scale = 3.0 * 10.0^2 * 10.0;
f1b_tol_displ_norm = 1e-6;
f1b_tol_p_field_norm = 4e-4;
f1b_tol_staggered_norm = 4e-4;
SOL_PAR = phase_field.fem.solver.params( ...
    'tol_displ', f1b_force_scale * f1b_tol_displ_norm, ...
    'tol_p_field', f1b_energy_scale * f1b_tol_p_field_norm, ...
    'max_iter_displ', 250, 'max_iter_pf', 250 ...
);
% The upstream staggered criterion adds force and energy residuals. The
% locked F1b solver overrides that dimensional sum after post_iter_update.
SOL_STAG_PAR = phase_field.fem.solver.stag.params( ...
    'tol', f1b_tol_staggered_norm, 'max_iter', 1000 ...
);
SOL_STEP_PAR = phase_field.fem.solver.step.params( ...
    'n_step', 8, ...
    'loading', 'cyclic', ...
    'discretization', 'loading+unloading', ...
    'uy_final', 1.2, ...
    'R', 0.0, ...
    'line_search', false ...
);
SOL_CYCL_PAR = phase_field.fem.solver.cycl.params('max_cycle', 120, 'da_paraview', 0.1);
SOL_JUMP_PAR = phase_field.fem.solver.cycl_jump.params('cycl_jump', false);
CRACK_PAR = phase_field.fem.crack.params(MAT_CHAR, diss_fct, 'crack_thres', 0.95);

checkpoint_freq = 1;
vtk_freq = 10;
damage_upper_bound = 1.0;
penetration_boundary_mode = 'right_layer';
penetration_right_x_min = 4.8;
penetration_threshold = 0.95;
penetration_min_nodes = 3;
penetration_confirm_cycles = 3;
penetration_first_hit_cycle = NaN;
penetration_confirmed_cycle = NaN;
penetration_consecutive_hits = 0;

initialize_state0 = true;
init_fatigue_fracture

connectivity = sys.MESH.elem(:, 1:sys.MESH.nel);
node_coords = sys.MESH.node;
x = reshape(node_coords(connectivity(:), 1), size(connectivity));
y = reshape(node_coords(connectivity(:), 2), size(connectivity));
element_centroids = [mean(x, 2), mean(y, 2)];
area_per_elem = 0.5 * abs(sum(x .* circshift(y, [0 -1]) - ...
    y .* circshift(x, [0 -1]), 2));
save(fullfile(example_name, 'f1b_mesh_geometry.mat'), ...
    'node_coords', 'connectivity', 'element_centroids', 'area_per_elem', '-v7');

if initialize_state0
    strain_en_undgr = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
    [~, res_pf_recovery, p_field, ~, history_vars_old, non_conv] = ...
        newton_raphson_f1b( ...
        assembly_pf_fh, sys, p_field, p_field_old, strain_en_undgr, ...
        history_vars_old, sys.DOFS.active_dof_pf, ...
        sys.STIFFNESS_MATRIX.i_row_pf, sys.STIFFNESS_MATRIX.j_col_pf, ...
        'max_iter', SOL_PAR.max_iter_pf, ...
        'res_tol', SOL_PAR.tol_p_field, ...
        'line_search', false, ...
        'regularize_pf_only', true, ...
        'tangent_scale', f1b_energy_scale ...
    );
    if non_conv
        error('Zero-load hard recovery phase-field solve did not converge.');
    end
    p_field = min(max(p_field, 0.0), damage_upper_bound);
    p_field_old = p_field;
    history_vars_old(:, :, 2) = 0.0;
    history_vars_old(:, :, 3) = 0.0;
    history_vars_old(:, :, 4) = 1.0;
else
    error('F1b must start from a fresh hard-recovery state.');
end
initial_precrack_exclusion_nodes = sys.DOFS.non_hom_dirichlet_bc_pf;

input_snapshot = struct();
input_snapshot.analysis = 'F1b_exact_pi_solver_invariance_v2';
input_snapshot.fresh_fem_solve = true;
input_snapshot.source_commit = source_commit;
input_snapshot.input_lock_sha256 = input_lock_sha256;
input_snapshot.output_root = output_root;
input_snapshot.E = 3.0;
input_snapshot.nu = 0.3;
input_snapshot.Gc = 0.3;
input_snapshot.ell = 0.1;
input_snapshot.L = 10.0;
input_snapshot.H = 10.0;
input_snapshot.thickness = 10.0;
input_snapshot.Umax = 1.2;
input_snapshot.alpha_T = 1.5;
input_snapshot.w1 = 3.0;
input_snapshot.eta = 0.0;
input_snapshot.R = 0.0;
input_snapshot.plane_state = 'plane_strain';
input_snapshot.pff_model = 'AT1';
input_snapshot.energy_split = 'AMOR';
input_snapshot.boundary_condition = 'top_bottom_ux_clamp_reverse_bc';
input_snapshot.initial_crack = 'non_hom_pf_then_zero_load_hard_recovery';
input_snapshot.loading = 'cyclic_explicit_8_step_loading_unloading';
input_snapshot.event_rule = 'x>=4.8,d>=0.95,>=3nodes,3_post_hit_confirmation_cycles';
input_snapshot.tol_displ = SOL_PAR.tol_displ;
input_snapshot.tol_p_field = SOL_PAR.tol_p_field;
input_snapshot.tol_staggered_dimensionless = f1b_tol_staggered_norm;
input_snapshot.force_residual_scale = f1b_force_scale;
input_snapshot.energy_residual_scale = f1b_energy_scale;
input_snapshot.tol_displ_dimensionless = SOL_PAR.tol_displ / f1b_force_scale;
input_snapshot.tol_p_field_dimensionless = SOL_PAR.tol_p_field / f1b_energy_scale;
input_snapshot.regularization_floor_dimensionless = 1e-8;
input_snapshot.regularization_floor_dimensional = 1e-8 * f1b_energy_scale;
input_snapshot.recovery_residual = res_pf_recovery;
input_snapshot.recovery_residual_dimensionless = res_pf_recovery / f1b_energy_scale;
write_json(fullfile(example_name, 'F1B_INPUT_SNAPSHOT.json'), input_snapshot)
save(fullfile(example_name, 'state0_analysis.mat'), 'node_coords', 'p_field', '-v7');

solve_fatigue_fracture_f1b

event_metadata = struct();
event_metadata.first_hit_cycle = penetration_first_hit_cycle;
event_metadata.confirmed_cycle = penetration_confirmed_cycle;
event_metadata.last_completed_cycle = SOL_CYCL_VAR.n_cycle;
event_metadata.state_phase = 'cycle peak raw; cycle-output damage/history';
event_metadata.event_rule = input_snapshot.event_rule;
event_metadata.fresh_fem_solve = true;
event_metadata.wall_seconds = toc(start_tic);
write_json(fullfile(example_name, 'F1B_EVENT_METADATA.json'), event_metadata)
disp(['total computation time: ' num2str(event_metadata.wall_seconds) 's'])
end

function write_json(path, payload)
fid = fopen(path, 'w');
if fid < 0, error('Cannot open JSON output: %s', path); end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', jsonencode(payload));
end
