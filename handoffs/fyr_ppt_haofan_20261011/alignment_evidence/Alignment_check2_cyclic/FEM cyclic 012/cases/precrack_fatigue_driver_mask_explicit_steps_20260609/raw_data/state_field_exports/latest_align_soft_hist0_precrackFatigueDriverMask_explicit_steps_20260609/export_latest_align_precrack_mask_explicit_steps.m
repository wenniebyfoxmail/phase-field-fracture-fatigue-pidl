function export_latest_align_precrack_mask_explicit_steps(max_cycle_override, package_name_override)
% Export Request 22/23 masked soft-hist0 FEM fields at every cyclic substep.
%
% Primary setting:
%   retained-material soft diffuse precrack / hist0 reverseBC
%   AT1 + AMOR + PENALTY, E=1, nu=0.3, Gc=0.01, ell=0.01
%   PIDL-equivalent fatigue-driver/history mask:
%     mask_fatigue=true, mask_energy=false on x <= 0.5, |y-0.5| <= 2*ell.

root_dir = fileparts(mfilename('fullpath'));
cwd0 = pwd;
cleanup_cd = onCleanup(@() cd(cwd0));
cd(root_dir);

addpath(genpath(fullfile('..', '..', 'Dependencies')));
addpath(fullfile('..', '..', 'Sources'));
ss_paths = { ...
    'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/AMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/COLAMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/CCOLAMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/CAMD/MATLAB'};
for i = 1:numel(ss_paths)
    if exist(ss_paths{i}, 'dir'), addpath(ss_paths{i}); end
end

if nargin < 1 || isempty(max_cycle_override)
    max_cycle_override = 69;
end
if nargin < 2 || isempty(package_name_override)
    package_name_override = 'latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609';
end

start_tic = tic;
package_name = package_name_override;
out_root = fullfile(getenv('USERPROFILE'), 'Downloads', '_pidl_handoff_v2', package_name);
if exist(out_root, 'dir'), rmdir(out_root, 's'); end
mkdir(out_root);
diary_file = fullfile(out_root, 'run_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.log');
diary(diary_file);
diary_cleanup = onCleanup(@() diary('off'));

soft_hist0_example_name = 'FEM23_precrackFatigueDriverMask_explicit_steps_replay';
soft_hist0_max_cycle = max_cycle_override;
INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask
SOL_CYCL_PAR.max_cycle = max_cycle_override;

if exist(example_name, 'dir'), rmdir(example_name, 's'); end
init_fatigue_fracture

% Latest aligned initial state: soft precrack, alpha_bar=0, f=1.
p_field = precrack_soft_profile;
p_field_old = precrack_soft_profile;
history_vars_old(:,:,2) = 0.0;
history_vars_old(:,:,3) = 0.0;
history_vars_old(:,:,4) = 1.0;

if ~exist('precrack_fatigue_driver_mask_elem', 'var')
    precrack_fatigue_driver_mask_elem = ...
        (precrack_centroids(:,1) <= L_crack + 1e-12) & ...
        (abs(precrack_centroids(:,2) - 0.5) <= 2 * ell + 1e-12);
end
history_vars_old = apply_precrack_fatigue_mask(history_vars_old, precrack_fatigue_driver_mask_elem);

if SOL_STEP_PAR.n_step ~= 5
    error('Request 23 expects exactly five retained substeps; got SOL_STEP_PAR.n_step=%d', SOL_STEP_PAR.n_step);
end

node_coords = sys.MESH.node;
connectivity = sys.MESH.elem(:, 1:sys.MESH.nel);
[element_centroids, element_area] = elem_geometry(node_coords, connectivity);
[gauss_coords, quad_weights] = gauss_geometry(sys.MESH, sys.QUADRATURE, sys.GEOM.t);
mask_support_elem = logical(precrack_fatigue_driver_mask_elem(:));

n_state = 1 + SOL_CYCL_PAR.max_cycle * SOL_STEP_PAR.n_step;
mat_file = fullfile(out_root, 'latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat');
state_csv = fullfile(out_root, 'latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_index.csv');
mesh_file = fullfile(out_root, 'mesh_geometry.mat');
audit_csv = fullfile(out_root, 'precrack_fatigue_driver_mask_region_audit.csv');
readme_file = fullfile(out_root, 'README_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.md');

metadata = build_metadata(package_name, example_name, n_state, SOL_STEP_PAR, mask_support_elem);
save(mat_file, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'gauss_coords', 'quad_weights', 'mask_support_elem', 'metadata', '-v7.3');
save(mesh_file, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'gauss_coords', 'quad_weights', 'mask_support_elem', '-v7.3');

M = matfile(mat_file, 'Writable', true);
zero_psi = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
gp0 = compute_gp_fields(sys, displ, p_field, history_vars_old, history_vars_old, mask_support_elem);
[gp_field_names, elem_field_names] = initialize_matfile_fields(M, sys, gp0, n_state);

state_rows = cell(n_state, 1);
audit_rows = {};
state_idx = 1;
[state_rows{state_idx}, elem0] = write_state(M, state_idx, ...
    'state0_initial_unloaded_prehistory', 0, 0, 0.0, 0.0, ...
    displ, p_field, history_vars_old, history_vars_old, zero_psi, sys, mask_support_elem, ...
    'Initial unloaded soft precrack before load/history refresh; alpha_bar=0 and f=1 everywhere.');
audit_rows = append_audit_if_needed(audit_rows, state_rows{state_idx}, elem0, element_centroids, element_area, mask_support_elem);
fprintf('[FEM23-mask] captured %s (%d/%d)\n', state_rows{state_idx}.state_label, state_idx, n_state);

for i_cycle = 1:SOL_CYCL_PAR.max_cycle
    fprintf('[FEM23-mask] cycle %d/%d\n', i_cycle, SOL_CYCL_PAR.max_cycle);
    SOL_CYCL_VAR.n_cycle = i_cycle;
    peak_psi_plus = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);

    for i_step = 1:SOL_STEP_PAR.n_step
        [displ, res_displ, D_RHS_tract] = phase_field.fem.solver.step.pre_iter_update( ...
            i_step, sys, displ, SOL_STEP_PAR);
        res_displ_0 = norm(res_displ(sys.DOFS.active_dof, 1));
        uy_value = sum(SOL_STEP_PAR.uy_increment(1:i_step));
        load_factor = uy_value / SOL_STEP_PAR.uy_final;

        for i_stag = 1:SOL_STAG_PAR.max_iter
            [res_displ_0, res_displ, displ, strain_en_undgr, ~, non_conv] = ...
                phase_field.fem.solver.newton_raphson( ...
                assembly_equilibrium_fh, sys, displ, 0.0, p_field, 0.0, ...
                sys.DOFS.active_dof, sys.STIFFNESS_MATRIX.i_row, sys.STIFFNESS_MATRIX.j_col, ...
                'D_RHS_tract', D_RHS_tract, ...
                'max_iter', SOL_PAR.max_iter_displ, ...
                'res_tol', SOL_PAR.tol_displ, ...
                'line_search', SOL_STEP_PAR.line_search);
            if isnan(res_displ) || non_conv
                error('displacement solve did not converge at cycle %d step %d', i_cycle, i_step);
            end

            [i_res_pf_0, res_pf, p_field, ~, ~, non_conv] = ...
                phase_field.fem.solver.newton_raphson( ...
                assembly_pf_fh, sys, p_field, p_field_old, strain_en_undgr, history_vars_old, ...
                sys.DOFS.active_dof_pf, sys.STIFFNESS_MATRIX.i_row_pf, sys.STIFFNESS_MATRIX.j_col_pf, ...
                'max_iter', SOL_PAR.max_iter_pf, ...
                'res_tol', SOL_PAR.tol_p_field, ...
                'line_search', SOL_STEP_PAR.line_search, ...
                'regularize_pf_only', strcmp(sys.diss_fct, 'PF_CZM'));
            if isnan(res_pf) || non_conv
                error('phase-field solve did not converge at cycle %d step %d', i_cycle, i_step);
            end
            if i_stag == 1
                res_pf_0 = i_res_pf_0;
            end

            [SOL_STAG_VAR, strain_en_undgr, stag_converged, sys.STIFFNESS_MATRIX.KK] = ...
                phase_field.fem.solver.stag.post_iter_update( ...
                assembly_equilibrium_fh, i_stag, SOL_STAG_VAR, sys, D_RHS_tract, ...
                p_field, displ, res_pf_0, res_pf, res_displ_0, SOL_STAG_PAR);

            if stag_converged
                p_field_old = p_field;
                [~, ~, ~, history_raw_candidate] = assembly_pf_fh( ...
                    sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, sys.CC, ...
                    p_field, p_field_old, strain_en_undgr, sys.stress_state.as_number, history_vars_old);
                history_vars_old = apply_precrack_fatigue_mask(history_raw_candidate, mask_support_elem);
                peak_psi_plus = max(peak_psi_plus, strain_en_undgr);
                break;
            end
            if i_stag == SOL_STAG_PAR.max_iter
                error('staggered loop did not converge at cycle %d step %d', i_cycle, i_step);
            end
        end

        label = state_label(i_cycle, i_step, SOL_STEP_PAR.n_step);
        state_idx = state_idx + 1;
        [state_rows{state_idx}, elem] = write_state(M, state_idx, ...
            label, i_cycle, i_step, load_factor, uy_value, ...
            displ, p_field, history_vars_old, history_raw_candidate, strain_en_undgr, sys, mask_support_elem, ...
            'Post converged substep and post PIDL-equivalent fatigue-history mask enforcement.');
        audit_rows = append_audit_if_needed(audit_rows, state_rows{state_idx}, elem, element_centroids, element_area, mask_support_elem);
        fprintf('[FEM23-mask] captured %s (%d/%d)\n', label, state_idx, n_state);

        SOL_STEP_VAR = phase_field.fem.solver.step.post_iter_update( ...
            i_step, SOL_STEP_VAR, sys.STIFFNESS_MATRIX, displ, sys.NODE_BOUNDARIES, ...
            sys.MESH.num_node, SOL_STEP_PAR, example_name);
        SOL_STAG_VAR = phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
    end
end

if state_idx ~= n_state
    error('Captured %d states, expected %d states.', state_idx, n_state);
end

T_states = rows_to_table(state_rows);
T_audit = rows_to_table(audit_rows);
metadata.runtime_seconds = toc(start_tic);
metadata.n_state_written = state_idx;
metadata.gp_field_names_computed_not_written = gp_field_names;
metadata.elem_field_names = elem_field_names;
save(mat_file, 'T_states', 'T_audit', 'gp_field_names', 'elem_field_names', 'metadata', '-append');
writetable(T_states, state_csv);
writetable(T_audit, audit_csv);
write_readme(readme_file, metadata, T_states, T_audit);

copyfile(fullfile(root_dir, 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask.m'), out_root);
copyfile(fullfile(root_dir, 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m'), out_root);
copyfile(fullfile(root_dir, 'solve_fatigue_fracture.m'), out_root);
copyfile(fullfile(root_dir, 'export_latest_align_precrack_mask_explicit_steps.m'), out_root);

diary('off');
dst_root = fullfile(getenv('USERPROFILE'), 'OneDrive - University of Cambridge', ...
    'PIDL result', ['_pidl_handoff_' package_name]);
if exist(dst_root, 'dir'), rmdir(dst_root, 's'); end
copyfile(out_root, dst_root);

fprintf('[FEM23-mask] wrote package:\n  %s\nOneDrive:\n  %s\n', out_root, dst_root);
fprintf('[FEM23-mask] runtime %.1f s, states %d\n', metadata.runtime_seconds, state_idx);
end

function metadata = build_metadata(package_name, example_name, n_state, SOL_STEP_PAR, mask_support_elem)
metadata = struct();
metadata.request = 'Mac Requests 22/23, 2026-06-09: PIDL-equivalent precrack fatigue-driver mask and explicit five-substep export';
metadata.package_name = package_name;
metadata.input = 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask';
metadata.base_input = 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC';
metadata.replay_example_name = example_name;
metadata.setting = 'retained-material soft diffuse precrack / hist0 reverseBC; no void slit; no duplicated crack-face nodes';
metadata.loading = 'cyclic R=0, retained five-substep schedule load=[0.25 0.50 0.75 1.00 0.00], uy=[0.03 0.06 0.09 0.12 0]';
metadata.material = 'AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2, tol_irrev=1e-3, res_stiff=1e-6';
metadata.n_state_expected = n_state;
metadata.requested_mapping = 'fem_global_step = 5*(cycle - 1) + (substep - 1); c1_peak=3, c1_unloaded=4, c69_peak=343, c69_unloaded=344';
metadata.retained_load_factors = cumsum(SOL_STEP_PAR.uy_increment) ./ SOL_STEP_PAR.uy_final;
metadata.retained_uy_values = cumsum(SOL_STEP_PAR.uy_increment);
metadata.mask_policy = 'PIDL-equivalent mask_fatigue=true, mask_energy=false; mechanics, displacement, strain, raw psi_plus, and H/fracture history remain unmasked.';
metadata.mask_region = 'x <= 0.5 and |y - 0.5| <= 2*ell = 0.02';
metadata.mask_n_elem = nnz(mask_support_elem);
metadata.mask_implementation = 'Post-refresh fatigue-history state enforcement. The AT1_PENALTY_FATIGUE MEX does not expose separate energy and fatigue-driver inputs; masking strain_en_undgr inside the phase-field solve would also mask the variational damage energy and violate mask_energy=false.';
metadata.mask_enforcement = 'history(:,:,2)=alpha_bar -> 0, history(:,:,3)=fatigue driver/Dalpha-like slot -> 0, history(:,:,4)=f_alpha -> 1 on mask elements after each converged substep.';
metadata.storage_policy = 'All 346 states are written as element-mean fields plus nodal u/d and mesh/GP geometry. GP fields are computed during export before element averaging, but full all-state GP tensors are intentionally not written to keep the handoff tractable for OneDrive/Mac.';
metadata.raw_stress_definition = 'sigma_raw_gp = C * epsilon_gp, with C the plane-strain elastic matrix.';
metadata.degraded_stress_definition = 'sigma_degraded_effective_gp = sigma_minus_gp + g_stiffness_gp * sigma_plus_gp from the AMOR split used by the FEM equilibrium kernel.';
metadata.g_stiffness_definition = 'g_stiffness_gp = (1-d_gp)^2 + res_stiff; this is the stiffness degradation in AMOR equilibrium.';
metadata.fatigue_definition = 'alpha_bar_gp/f_fatigue_gp/masked_Dalpha_gp are post-mask fatigue-history states. raw_alpha_bar_gp/raw_f_fatigue_gp/raw_Dalpha_gp are the unmasked refresh candidate stored for audit.';
metadata.psi_plus_definition = 'psi_plus_gp is raw AMOR tensile/positive strain energy from the equilibrium kernel; raw_psi_plus_gp is an alias.';
metadata.g_psi_note = 'g_psi_plus_gp = g_stiffness_gp .* psi_plus_gp; f_g_psi_plus_gp is diagnostic f*g*psi_plus, not an equilibrium stress term.';
metadata.existing_vtk_sigma_warning = 'GRIPHFiTH L2_PROJECTION VTK sigma is degraded by (1-d)^2 and is not a clean raw stress; use this MAT for raw/degraded separation.';
metadata.epsilon_xy_note = 'epsilon_xy_gp stores GRIPHFiTH Voigt engineering shear gamma_xy=du/dy+dv/dx; epsilon_xy_tensor_gp stores gamma_xy/2 for principal strain calculation.';
metadata.von_mises_note = 'von_mises_*_gp uses the 2D formula sqrt(sxx^2 - sxx*syy + syy^2 + 3*sxy^2).';
end

function h = apply_precrack_fatigue_mask(h, mask_elem)
h(mask_elem,:,2) = 0.0;
h(mask_elem,:,3) = 0.0;
h(mask_elem,:,4) = 1.0;
end

function [gp_field_names, elem_field_names] = initialize_matfile_fields(M, sys, gp, n_state)
n_node = sys.MESH.num_node;
n_elem = sys.MESH.num_elem;

M.u_node(n_node, 2, n_state) = single(0);
M.d_node(n_node, n_state) = single(0);

gp_field_names = string(fieldnames(gp));
elem_field_names = strings(0, 1);
for i = 1:numel(gp_field_names)
    name = char(gp_field_names(i));
    val = ensure_3d(gp.(name));
    n_comp = size(val, 3);
    elem_name = strrep(name, '_gp', '_elem');
    if ~strcmp(elem_name, name) && ~strcmp(elem_name, 'mask_support_elem')
        eval(sprintf('M.%s(%d,%d,%d) = single(0);', elem_name, n_elem, n_comp, n_state));
        elem_field_names(end+1, 1) = string(elem_name); %#ok<AGROW>
    end
end
end

function [row, elem] = write_state(M, idx, label, cycle, step, load_factor, uy, displ, p, h_masked, h_raw, psi_from_solver, sys, mask_support_elem, note)
gp = compute_gp_fields(sys, displ, p, h_masked, h_raw, mask_support_elem);
M.u_node(:,:,idx) = single(reshape(displ, [sys.MESH.num_node, 2]));
M.d_node(:,idx) = single(p);

names = fieldnames(gp);
elem = struct();
for i = 1:numel(names)
    name = names{i};
    val = ensure_3d(gp.(name));
    elem_name = strrep(name, '_gp', '_elem');
    if ~strcmp(elem_name, name) && ~strcmp(elem_name, 'mask_support_elem')
        elem_val = squeeze(mean(val, 2));
        if isvector(elem_val)
            elem_val = elem_val(:);
        end
        eval(sprintf('M.%s(:,:,idx) = elem_val;', elem_name));
        elem.(elem_name) = elem_val;
    end
end
elem.psi_solver_elem = mean(single(psi_from_solver), 2);

[is_peak, is_unloaded] = peak_unload_flags(step);
if cycle >= 1
    fem_global_step = 5 * (cycle - 1) + (step - 1);
else
    fem_global_step = NaN;
end
row = struct();
row.row_index = idx;
row.state_label = string(label);
row.physical_cycle = cycle;
row.substep = step;
row.load_factor = load_factor;
row.uy = uy;
row.fem_global_step = fem_global_step;
row.pidl_global_step_expected = fem_global_step;
row.is_peak = is_peak;
row.is_unloaded = is_unloaded;
row.mask_applied = true;
row.time_or_increment_index = idx - 1;
row.source_notes = string(note);
end

function rows = append_audit_if_needed(rows, state_row, elem, centroids, area, mask_support_elem)
target_cycles = [1 2 3 20 40 60 69];
if ~state_row.is_peak || ~ismember(state_row.physical_cycle, target_cycles)
    return;
end

left_line = (centroids(:,1) <= 0.5 + 1e-12) & (abs(centroids(:,2) - 0.5) <= 0.014 + 1e-12);
regions = { ...
    'left_precrack_line_audit', left_line; ...
    'mask_support', mask_support_elem; ...
    'outside_left_precrack_line_audit', ~left_line ...
};

for i = 1:size(regions, 1)
    mask = regions{i, 2};
    r = struct();
    r.state_label = state_row.state_label;
    r.physical_cycle = state_row.physical_cycle;
    r.substep = state_row.substep;
    r.fem_global_step = state_row.fem_global_step;
    r.region = string(regions{i, 1});
    r.n_elem = nnz(mask);
    r.area = sum(area(mask));
    r.d_mean = mean(elem.d_elem(mask), 'omitnan');
    r.d_max = max(elem.d_elem(mask));
    r.alpha_bar_mean = mean(elem.alpha_bar_elem(mask), 'omitnan');
    r.alpha_bar_max = max(elem.alpha_bar_elem(mask));
    r.f_fatigue_mean = mean(elem.f_fatigue_elem(mask), 'omitnan');
    r.f_fatigue_min = min(elem.f_fatigue_elem(mask));
    r.raw_Dalpha_mean = mean(elem.raw_Dalpha_elem(mask), 'omitnan');
    r.raw_Dalpha_max = max(elem.raw_Dalpha_elem(mask));
    r.masked_Dalpha_mean = mean(elem.masked_Dalpha_elem(mask), 'omitnan');
    r.masked_Dalpha_max = max(elem.masked_Dalpha_elem(mask));
    r.psi_plus_raw_mean = mean(elem.psi_plus_elem(mask), 'omitnan');
    r.psi_plus_raw_max = max(elem.psi_plus_elem(mask));
    r.g_psi_plus_raw_mean = mean(elem.g_psi_plus_elem(mask), 'omitnan');
    r.g_psi_plus_raw_max = max(elem.g_psi_plus_elem(mask));
    r.f_g_psi_plus_masked_mean = mean(elem.f_g_psi_plus_elem(mask), 'omitnan');
    r.f_g_psi_plus_masked_max = max(elem.f_g_psi_plus_elem(mask));
    rows{end+1, 1} = r; %#ok<AGROW>
end
end

function label = state_label(cycle, step, n_step)
if n_step == 5
    names = {'step1', 'step2', 'step3', 'peak', 'unloaded'};
    label = sprintf('c%d_%s', cycle, names{step});
elseif step == n_step - 1
    label = sprintf('c%d_peak', cycle);
elseif step == n_step
    label = sprintf('c%d_unloaded', cycle);
else
    label = sprintf('c%d_step%d', cycle, step);
end
end

function [is_peak, is_unloaded] = peak_unload_flags(step)
is_peak = (step == 4);
is_unloaded = (step == 5);
end

function gp = compute_gp_fields(sys, displ, p, h_masked, h_raw, mask_support_elem)
n_elem = sys.MESH.num_elem;
n_gp = sys.QUADRATURE.num_gauss_pts;
nel = sys.MESH.nel;
num_node = sys.MESH.num_node;
C = sys.CC(:,:,1);
E = sys.MAT_CHAR(1).E;
nu = sys.MAT_CHAR(1).ni;
G = E / (2 * (1 + nu));
K = E / (3 * (1 - 2 * nu));
res_stiff = sys.MAT_CHAR(1).res_stiff;
I_vol = [1 1 0; 1 1 0; 0 0 0];
I_dev = [2/3 -1/3 0; -1/3 2/3 0; 0 0 1/2];

epsilon = zeros(n_elem, n_gp, 3, 'single');
sigma_raw = zeros(n_elem, n_gp, 3, 'single');
sigma_degraded = zeros(n_elem, n_gp, 3, 'single');
sigma_plus = zeros(n_elem, n_gp, 3, 'single');
sigma_minus = zeros(n_elem, n_gp, 3, 'single');
principal_strain = zeros(n_elem, n_gp, 2, 'single');
principal_stress_raw = zeros(n_elem, n_gp, 2, 'single');
principal_stress_degraded = zeros(n_elem, n_gp, 2, 'single');
von_mises_raw = zeros(n_elem, n_gp, 'single');
von_mises_degraded = zeros(n_elem, n_gp, 'single');
psi_plus = zeros(n_elem, n_gp, 'single');
psi_minus = zeros(n_elem, n_gp, 'single');
d_gp = zeros(n_elem, n_gp, 'single');
g_stiffness = zeros(n_elem, n_gp, 'single');

for e = 1:n_elem
    nodes = sys.MESH.elem(e, 1:nel);
    coords = sys.MESH.node(nodes, 1:sys.MESH.dim);
    el_p = p(nodes);
    el_u = displ([nodes, nodes + num_node]);
    for q = 1:n_gp
        jac = sys.QUADRATURE.dNdxi(:,:,q) * coords;
        dN_glob = jac \ sys.QUADRATURE.dNdxi(:,:,q);
        B = zeros(3, 2*nel);
        B(1, 1:nel) = dN_glob(1,:);
        B(2, nel+1:2*nel) = dN_glob(2,:);
        B(3,:) = [dN_glob(2,:), dN_glob(1,:)];

        epsv = B * el_u;
        trace_eps = epsv(1) + epsv(2);
        dval = sys.QUADRATURE.Nxi(:,q)' * el_p;
        gd = (1 - dval)^2 + res_stiff;
        if trace_eps >= 0
            C_plus = C;
            C_neg = zeros(3,3);
        else
            C_plus = 2 * G * I_dev;
            C_neg = K * I_vol;
        end
        sig_raw = C * epsv;
        sig_p = C_plus * epsv;
        sig_m = C_neg * epsv;
        sig_deg = sig_m + gd * sig_p;

        epsilon(e,q,:) = single(epsv);
        sigma_raw(e,q,:) = single(sig_raw);
        sigma_degraded(e,q,:) = single(sig_deg);
        sigma_plus(e,q,:) = single(sig_p);
        sigma_minus(e,q,:) = single(sig_m);
        psi_plus(e,q) = single(0.5 * epsv' * C_plus * epsv);
        psi_minus(e,q) = single(0.5 * epsv' * C_neg * epsv);
        d_gp(e,q) = single(dval);
        g_stiffness(e,q) = single(gd);

        gamma = epsv(3);
        principal_strain(e,q,:) = single(principal_2x2(epsv(1), epsv(2), gamma/2));
        principal_stress_raw(e,q,:) = single(principal_2x2(sig_raw(1), sig_raw(2), sig_raw(3)));
        principal_stress_degraded(e,q,:) = single(principal_2x2(sig_deg(1), sig_deg(2), sig_deg(3)));
        von_mises_raw(e,q) = single(von_mises_2d(sig_raw));
        von_mises_degraded(e,q) = single(von_mises_2d(sig_deg));
    end
end

alpha_bar = single(h_masked(:,:,2));
masked_Dalpha = single(h_masked(:,:,3));
f_fatigue = single(h_masked(:,:,4));
raw_alpha_bar = single(h_raw(:,:,2));
raw_Dalpha = single(h_raw(:,:,3));
raw_f_fatigue = single(h_raw(:,:,4));
mask_support_gp = single(repmat(mask_support_elem(:), 1, n_gp));

gp = struct();
gp.epsilon_gp = epsilon;
gp.epsilon_xy_tensor_gp = single(0.5 * epsilon(:,:,3));
gp.sigma_raw_gp = sigma_raw;
gp.sigma_degraded_effective_gp = sigma_degraded;
gp.sigma_plus_raw_gp = sigma_plus;
gp.sigma_minus_raw_gp = sigma_minus;
gp.principal_strain_gp = principal_strain;
gp.principal_stress_raw_gp = principal_stress_raw;
gp.principal_stress_degraded_effective_gp = principal_stress_degraded;
gp.von_mises_raw_gp = von_mises_raw;
gp.von_mises_degraded_effective_gp = von_mises_degraded;
gp.psi_plus_gp = psi_plus;
gp.raw_psi_plus_gp = psi_plus;
gp.psi_minus_gp = psi_minus;
gp.d_gp = d_gp;
gp.g_stiffness_gp = g_stiffness;
gp.alpha_bar_gp = alpha_bar;
gp.masked_Dalpha_gp = masked_Dalpha;
gp.f_fatigue_gp = f_fatigue;
gp.raw_alpha_bar_gp = raw_alpha_bar;
gp.raw_Dalpha_gp = raw_Dalpha;
gp.raw_f_fatigue_gp = raw_f_fatigue;
gp.mask_support_gp = mask_support_gp;
gp.g_psi_plus_gp = single(g_stiffness .* psi_plus);
gp.f_g_psi_plus_gp = single(f_fatigue .* g_stiffness .* psi_plus);
end

function p = principal_2x2(a, b, c)
avg = 0.5 * (a + b);
rad = sqrt((0.5 * (a - b))^2 + c^2);
p = [avg + rad, avg - rad];
end

function vm = von_mises_2d(sig)
vm = sqrt(sig(1)^2 - sig(1)*sig(2) + sig(2)^2 + 3*sig(3)^2);
end

function a = ensure_3d(a)
if ndims(a) == 2
    a = reshape(a, size(a,1), size(a,2), 1);
end
end

function T = rows_to_table(rows)
rows = rows(~cellfun('isempty', rows));
if isempty(rows)
    T = table();
    return;
end
T = struct2table(vertcat(rows{:}));
end

function [centroids, area] = elem_geometry(node, elem)
n_elem = size(elem,1);
centroids = zeros(n_elem, 2);
area = zeros(n_elem, 1);
for e = 1:n_elem
    xy = node(elem(e,:), :);
    centroids(e,:) = mean(xy, 1);
    x = xy(:,1); y = xy(:,2);
    area(e) = 0.5 * abs(sum(x .* y([2:end 1]) - y .* x([2:end 1])));
end
end

function [coords, weights] = gauss_geometry(MESH, QUADRATURE, thickness)
n_elem = MESH.num_elem;
n_gp = QUADRATURE.num_gauss_pts;
coords = zeros(n_elem, n_gp, 2, 'single');
weights = zeros(n_elem, n_gp, 'single');
for e = 1:n_elem
    nodes = MESH.elem(e, 1:MESH.nel);
    xy = MESH.node(nodes, 1:MESH.dim);
    for q = 1:n_gp
        jac = QUADRATURE.dNdxi(:,:,q) * xy;
        coords(e,q,:) = single(QUADRATURE.Nxi(:,q)' * xy);
        weights(e,q) = single(thickness * QUADRATURE.gauss_W(q) * det(jac));
    end
end
end

function write_readme(path, metadata, T_states, T_audit)
fid = fopen(path, 'w');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '# Latest Aligned FEM Precrack-Fatigue-Mask Explicit-Step Export\n\n');
fprintf(fid, '- Request: %s\n', metadata.request);
fprintf(fid, '- Setting: %s\n', metadata.setting);
fprintf(fid, '- Loading: %s\n', metadata.loading);
fprintf(fid, '- State count: %d\n', height(T_states));
fprintf(fid, '- Audit rows: %d\n\n', height(T_audit));
fprintf(fid, '## Step Mapping\n\n');
fprintf(fid, '%s\n\n', metadata.requested_mapping);
fprintf(fid, '## Mask Definition\n\n');
fprintf(fid, '- Policy: %s\n', metadata.mask_policy);
fprintf(fid, '- Region: %s\n', metadata.mask_region);
fprintf(fid, '- Mask elements: %d\n', metadata.mask_n_elem);
fprintf(fid, '- Implementation: %s\n\n', metadata.mask_implementation);
fprintf(fid, '## Definitions\n\n');
fprintf(fid, '- Raw stress: %s\n', metadata.raw_stress_definition);
fprintf(fid, '- Degraded/effective stress: %s\n', metadata.degraded_stress_definition);
fprintf(fid, '- Fatigue fields: %s\n', metadata.fatigue_definition);
fprintf(fid, '- Existing VTK warning: %s\n\n', metadata.existing_vtk_sigma_warning);
fprintf(fid, '- Storage policy: %s\n\n', metadata.storage_policy);
fprintf(fid, '## Files\n\n');
fprintf(fid, '- latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat\n');
fprintf(fid, '- latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_index.csv\n');
fprintf(fid, '- mesh_geometry.mat\n');
fprintf(fid, '- precrack_fatigue_driver_mask_region_audit.csv\n');
fprintf(fid, '- INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_precrackFatigueDriverMask.m\n');
fprintf(fid, '- INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m\n');
fprintf(fid, '- solve_fatigue_fracture.m\n');
fprintf(fid, '- export_latest_align_precrack_mask_explicit_steps.m\n');
fprintf(fid, '- run_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps.log\n');
end
