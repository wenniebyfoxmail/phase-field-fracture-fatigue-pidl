% =========================================================================
% SENT fatigue - reverseBC u=0.12 with soft diffuse pre-crack, hist0
%
% Strict alignment diagnostic requested by Mac Request 18:
%   - Retain material in the initial crack corridor.
%   - No void slit, duplicated crack-face nodes, or traction-free internal
%     crack boundary.
%   - Initialize a soft AT1-like phase-field pre-crack profile matching PIDL
%     hist_alpha_init as closely as possible.
%   - Initialize fatigue history alpha_bar = 0 everywhere, so f_alpha starts
%     undegraded (=1) everywhere.
%
% Coordinates from specimen.internal.plate are [0,1] x [0,1]. The PIDL crack
% from x_centered=-0.5 to 0 at y=0 is x_plate in [0,0.5], y_plate=0.5.
% =========================================================================

split_type = 'AMOR';
diss_fct   = 'AT1';
irrev      = 'PENALTY';

if ~exist('soft_hist0_example_name', 'var')
    soft_hist0_example_name = 'SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC';
end
if ~exist('soft_hist0_alpha_T', 'var')
    soft_hist0_alpha_T = 0.5;
end
if ~exist('soft_hist0_uy_final', 'var')
    soft_hist0_uy_final = 0.12;
end
if ~exist('soft_hist0_n_step', 'var')
    soft_hist0_n_step = 8;
end
if ~exist('soft_hist0_loading', 'var')
    soft_hist0_loading = 'cyclic';
end
if ~exist('soft_hist0_max_cycle', 'var')
    soft_hist0_max_cycle = 120;
end
if exist('soft_hist0_uy_steps', 'var')
    soft_hist0_uy_steps = soft_hist0_uy_steps(:).';
    soft_hist0_uy_final = soft_hist0_uy_steps(end);
    soft_hist0_n_step = numel(soft_hist0_uy_steps);
    soft_hist0_loading = 'monotonic';
end

example_name = soft_hist0_example_name;

[MESH, GEOM, NODESETS, ELEMSETS] = specimen.internal.plate(...
    'L', 1.0, 'B', 1.0, 't', 1.0, ...
    'notch_type', 'phase_field', ...
    'Nx', 250, 'Ny', 20, ...
    'Lref_x', 0.0, 'Lref_y', 0.1, ...
    'Nref_x', 0,   'Nref_y', 50, ...
    'y_notch',  0.5, ...
    'Lnotch_x', 0.5 ...
);
fprintf('soft diffuse pre-crack mesh: %d nodes, %d elements\n', MESH.num_node, MESH.num_elem);

tol_irrev_value = 1e-3;
tol_AT1_recovery_value = 1e-3;
MAT_CHAR(1) = phase_field.init.material_characteristic(...
    GEOM.L, diss_fct, ...
    'E',                1.0, ...
    'ni',               0.3, ...
    'Gc',               0.01, ...
    'ell',              0.01, ...
    'res_stiff',        1e-6, ...
    'alpha_T',          soft_hist0_alpha_T, ...
    'p',                2.0, ...
    'tol_irrev',        tol_irrev_value, ...
    'tol_AT1_recovery', tol_AT1_recovery_value ...
);
MESH.elem_material_id = ones(MESH.num_elem, 1);

ell = MAT_CHAR(1).ell;
x_local = MESH.node(:,1);
y_local = MESH.node(:,2) - 0.5;
L_crack = 0.5;
eps0 = eps;

soft_p1 = double(x_local .* (L_crack - x_local) > 0) .* ...
    double(2*ell - abs(y_local) > 0) .* ...
    (1 - abs(y_local) ./ (2*ell)).^2;

r_tip = sqrt((x_local - L_crack).^2 + y_local.^2);
soft_p2 = double(x_local - L_crack + eps0 > 0) .* ...
    double(2*ell - r_tip + eps0 > 0) .* ...
    (1 - r_tip ./ (2*ell)).^2;

r_left = sqrt(x_local.^2 + y_local.^2);
soft_p3 = double(-x_local + eps0 > 0) .* ...
    double(2*ell - r_left + eps0 > 0) .* ...
    (1 - r_left ./ (2*ell)).^2;

precrack_soft_profile = min(1.0, max(0.0, soft_p1 + soft_p2 + soft_p3));
precrack_nodes = find(precrack_soft_profile > 0);
precrack_core_nodes = find(precrack_soft_profile >= 0.95);

precrack_centroids = zeros(MESH.num_elem, 2);
precrack_elem_profile = zeros(MESH.num_elem, 1);
for e = 1:MESH.num_elem
    xy = MESH.node(MESH.elem(e,:), :);
    precrack_centroids(e,:) = mean(xy, 1);
    precrack_elem_profile(e) = mean(precrack_soft_profile(MESH.elem(e,:)));
end
precrack_elems = find(precrack_elem_profile > 0);
precrack_core_elems = find(precrack_elem_profile >= 0.95);
fprintf('[INPUT] soft precrack nodes d>0 = %d, core nodes d>=0.95 = %d, elems d>0 = %d\n', ...
    numel(precrack_nodes), numel(precrack_core_nodes), numel(precrack_elems));

top_bottom = unique([NODESETS('top'); NODESETS('bottom')]);

NODE_BOUNDARIES = phase_field.fem.bc.set_boundaries(...
    'fix_X',  top_bottom, ...
    'fix_Y',  NODESETS('bottom'), ...
    'disp_Y', NODESETS('top') ...
);

DOFS = phase_field.init.dofs(MESH, NODE_BOUNDARIES);
QUADRATURE = phase_field.init.quadrature(MESH.dim);
stress_state = phase_field.StressState.PlaneStrain;

SOL_PAR = phase_field.fem.solver.params(...
    'tol_displ',      1e-6, ...
    'tol_p_field',    1e-5, ...
    'max_iter_displ', 250, ...
    'max_iter_pf',    250 ...
);
SOL_STAG_PAR = phase_field.fem.solver.stag.params('tol', 1e-4, 'max_iter', 1000);
SOL_STEP_PAR = phase_field.fem.solver.step.params(...
    'n_step',         soft_hist0_n_step, ...
    'loading',        soft_hist0_loading, ...
    'discretization', 'loading', ...
    'uy_final',       soft_hist0_uy_final, ...
    'R',              0.0, ...
    'line_search',    true ...
);
if exist('soft_hist0_uy_steps', 'var')
    SOL_STEP_PAR.uy_values = soft_hist0_uy_steps;
    SOL_STEP_PAR.uy_increment = diff([0, soft_hist0_uy_steps]);
    SOL_STEP_PAR.ux_increment = zeros(1, SOL_STEP_PAR.n_step);
    SOL_STEP_PAR.load_factors = soft_hist0_uy_steps ./ soft_hist0_uy_final;
end
SOL_CYCL_PAR = phase_field.fem.solver.cycl.params(...
    'max_cycle',   soft_hist0_max_cycle, ...
    'da_paraview', 0.01 ...
);
SOL_JUMP_PAR = phase_field.fem.solver.cycl_jump.params('cycl_jump', false);
CRACK_PAR = phase_field.fem.crack.params(MAT_CHAR, diss_fct);

checkpoint_freq = 10;
vtk_freq        = 10;

diffuse_precrack_metadata = struct();
diffuse_precrack_metadata.centered_mask = 'x in [-0.5,0], y = 0, AT1 support radius 2*ell';
diffuse_precrack_metadata.plate_mask = 'x in [0,0.5], y = 0.5, AT1 squared-hat support |distance| <= 2*ell';
diffuse_precrack_metadata.width = 4 * ell;
diffuse_precrack_metadata.profile = 'soft AT1-like squared-hat phase-field initial condition; not a hard Dirichlet band';
diffuse_precrack_metadata.material_or_void = 'material retained; no duplicated crack-face nodes';
diffuse_precrack_metadata.initial_alpha_bar = 0.0;
diffuse_precrack_metadata.initial_f_alpha = 1.0;
diffuse_precrack_metadata.alpha_T = MAT_CHAR(1).alpha_T;
diffuse_precrack_metadata.tol_irrev = tol_irrev_value;
diffuse_precrack_metadata.penalty_irrev = MAT_CHAR(1).penalty_irrev;
diffuse_precrack_metadata.res_stiff = MAT_CHAR(1).res_stiff;
diffuse_precrack_metadata.n_step = SOL_STEP_PAR.n_step;
diffuse_precrack_metadata.loading = soft_hist0_loading;
diffuse_precrack_metadata.uy_final = soft_hist0_uy_final;
if isfield(SOL_STEP_PAR, 'uy_values')
    diffuse_precrack_metadata.uy_values = SOL_STEP_PAR.uy_values;
end
diffuse_precrack_metadata.cycle_update_semantics = 'standard GRIPHFiTH substep history refresh after each converged substep';
