function export_reverseBC_soft_hist0_state_timing()
% Strict state-timing export for Request 20.
%
% Replays cycle 1 of the soft-hist0 reverseBC run and stores pre/post
% history-refresh states so c1 comparisons can separate initialization,
% loading/damage solve, and fatigue-history timing.

root_dir = fileparts(mfilename('fullpath'));
cwd0 = pwd;
cleanup_cd = onCleanup(@() cd(cwd0));
cd(root_dir);

start_tic = tic;
close all
format shortE;

dep_path = genpath(fullfile('..', '..', 'Dependencies/'));
addpath(dep_path)
pkg_path = fullfile('..', '..', 'Sources/');
addpath(pkg_path)

ss_paths = {
    'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/AMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/COLAMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/CCOLAMD/MATLAB', ...
    'C:/SuiteSparse/SuiteSparse-dev/CAMD/MATLAB' ...
};
for i = 1:numel(ss_paths)
    if exist(ss_paths{i}, 'dir'), addpath(ss_paths{i}); end
end

INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
base_run_name = example_name;
example_name = 'SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_state_timing_replay';
init_fatigue_fracture

p_field = precrack_soft_profile;
p_field_old = precrack_soft_profile;
initial_precrack_exclusion_nodes = precrack_nodes;
history_vars_old(:,:,2) = 0.0;
history_vars_old(:,:,3) = 0.0;
history_vars_old(:,:,4) = 1.0;

node_coords = sys.MESH.node;
connectivity = sys.MESH.elem;
element_centroids = elem_centroids(node_coords, connectivity);
element_area = quad_area(node_coords, connectivity);
peak_psi_plus = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);

states = {};
states{end+1} = make_state( ...
    'state0_initial_preload_prehistory', 0, 0, 0.0, 0.0, false, ...
    false, false, false, p_field, history_vars_old, zeros(size(peak_psi_plus)), ...
    zeros(size(peak_psi_plus)), NaN, NaN, NaN, 'initial pre-load/pre-history state');

SOL_CYCL_VAR.n_cycle = 1;
for i_step = 1:SOL_STEP_PAR.n_step
    fprintf('[STATE_TIMING] cycle 1 step %d/%d\n', i_step, SOL_STEP_PAR.n_step);
    [displ, res_displ, D_RHS_tract] = phase_field.fem.solver.step.pre_iter_update(i_step, sys, displ, SOL_STEP_PAR);
    res_displ_0 = norm(res_displ(sys.DOFS.active_dof,1));
    history_before_step = history_vars_old;
    load_factor = sum(SOL_STEP_PAR.uy_increment(1:i_step)) / SOL_STEP_PAR.uy_final;
    uy_value = sum(SOL_STEP_PAR.uy_increment(1:i_step));

    for i_stag = 1:SOL_STAG_PAR.max_iter
        [res_displ_0, res_displ, displ, strain_en_undgr, ~, non_conv] = phase_field.fem.solver.newton_raphson(...
            assembly_equilibrium_fh, sys, displ, 0.0, p_field, 0.0, ...
            sys.DOFS.active_dof, sys.STIFFNESS_MATRIX.i_row, sys.STIFFNESS_MATRIX.j_col, ...
            'D_RHS_tract', D_RHS_tract, 'max_iter', SOL_PAR.max_iter_displ, ...
            'res_tol', SOL_PAR.tol_displ, 'line_search', SOL_STEP_PAR.line_search);
        if isnan(res_displ) || non_conv
            error('displacement solve did not converge at state-timing step %d', i_step);
        end

        [i_res_pf_0, res_pf, p_field, ~, history_vars_candidate, non_conv] = phase_field.fem.solver.newton_raphson(...
            assembly_pf_fh, sys, p_field, p_field_old, strain_en_undgr, history_vars_old, ...
            sys.DOFS.active_dof_pf, sys.STIFFNESS_MATRIX.i_row_pf, sys.STIFFNESS_MATRIX.j_col_pf, ...
            'max_iter', SOL_PAR.max_iter_pf, 'res_tol', SOL_PAR.tol_p_field, ...
            'line_search', SOL_STEP_PAR.line_search, ...
            'regularize_pf_only', strcmp(sys.diss_fct, 'PF_CZM'));
        if isnan(res_pf) || non_conv
            error('phase-field solve did not converge at state-timing step %d', i_step);
        end
        if i_stag == 1
            res_pf_0 = i_res_pf_0;
        end

        [SOL_STAG_VAR, strain_en_undgr, stag_converged, sys.STIFFNESS_MATRIX.KK] = phase_field.fem.solver.stag.post_iter_update(...
            assembly_equilibrium_fh, i_stag, SOL_STAG_VAR, sys, D_RHS_tract, p_field, displ, ...
            res_pf_0, res_pf, res_displ_0, SOL_STAG_PAR);
        if stag_converged
            pre_label = sprintf('cycle1_step%d_pre_history_refresh', i_step);
            post_label = sprintf('cycle1_step%d_post_history_refresh', i_step);
            if i_step == SOL_STEP_PAR.n_step - 1
                pre_label = 'cycle1_peak_pre_history_refresh';
                post_label = 'cycle1_peak_post_history_refresh';
            elseif i_step == SOL_STEP_PAR.n_step
                pre_label = 'cycle1_unloaded_pre_history_refresh';
                post_label = 'cycle1_unloaded_post_history_refresh';
            end

            peak_psi_after = max(peak_psi_plus, strain_en_undgr);
            states{end+1} = make_state(pre_label, 1, i_step, load_factor, uy_value, ...
                true, true, false, false, p_field, history_before_step, strain_en_undgr, ...
                peak_psi_after, SOL_STAG_VAR.el_en(i_stag), SOL_STAG_VAR.fract_en(i_stag), ...
                SOL_STAG_VAR.tot_en(i_stag), 'after converged displacement/damage solve; before this substep history refresh');

            p_field_old = p_field;
            [~, ~, ~, history_vars_old] = assembly_pf_fh(...
                sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, sys.CC, ...
                p_field, p_field_old, strain_en_undgr, sys.stress_state.as_number, history_vars_old);
            peak_psi_plus = peak_psi_after;

            states{end+1} = make_state(post_label, 1, i_step, load_factor, uy_value, ...
                true, true, true, true, p_field, history_vars_old, strain_en_undgr, ...
                peak_psi_plus, SOL_STAG_VAR.el_en(i_stag), SOL_STAG_VAR.fract_en(i_stag), ...
                SOL_STAG_VAR.tot_en(i_stag), 'after this substep history/fatigue refresh');
            break;
        end
        if i_stag == SOL_STAG_PAR.max_iter
            error('staggered loop did not converge at state-timing step %d', i_step);
        end
    end
    SOL_STEP_VAR = phase_field.fem.solver.step.post_iter_update(...
        i_step, SOL_STEP_VAR, sys.STIFFNESS_MATRIX, displ, sys.NODE_BOUNDARIES, ...
        sys.MESH.num_node, SOL_STEP_PAR, example_name);
    SOL_STAG_VAR = phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
end

[d_elem, alpha_bar_elem, f_fatigue_elem, psi_plus_elem, psi_plus_peak_to_date_elem] = stack_fields(states, sys);
state_label = string(cellfun(@(s) s.label, states, 'UniformOutput', false))';
cycle_index = cellfun(@(s) s.cycle, states)';
step_index = cellfun(@(s) s.step, states)';
load_factor = cellfun(@(s) s.load_factor, states)';
u_y = cellfun(@(s) s.uy, states)';
is_loaded = cellfun(@(s) s.is_loaded, states)';
after_damage_solve = cellfun(@(s) s.after_damage, states)';
after_alpha_bar_update = cellfun(@(s) s.after_alpha, states)';
after_f_alpha_update = cellfun(@(s) s.after_f, states)';
E_el = cellfun(@(s) s.E_el, states)';
E_d = cellfun(@(s) s.E_d, states)';
total_energy = cellfun(@(s) s.total_energy, states)';
notes = string(cellfun(@(s) s.note, states, 'UniformOutput', false))';

T = build_metrics_table(states, state_label, d_elem, alpha_bar_elem, f_fatigue_elem, ...
    psi_plus_elem, psi_plus_peak_to_date_elem, element_centroids, element_area);
old_c1_match = compare_old_c1(base_run_name, d_elem, alpha_bar_elem, f_fatigue_elem, psi_plus_elem, psi_plus_peak_to_date_elem, state_label);

metadata = struct();
metadata.request = 'docs/handovers/windows_fem_inbox.md Request 20';
metadata.base_run_name = base_run_name;
metadata.replay_run_name = example_name;
metadata.n_node = size(node_coords, 1);
metadata.n_elem = size(connectivity, 1);
metadata.element_type = 'Q4 quadrilateral';
metadata.integration_rule = '2x2 Gauss in solve; exported fields are element means over Gauss/history data';
metadata.material = 'AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2, tol_irrev=1e-3, res_stiff=1e-6';
metadata.loading = 'reverseBC u=0.12, R=0, fix_X top+bottom, fix_Y bottom, disp_Y top';
metadata.substep_note = 'Standard GRIPHFiTH cycle 1 has five retained substeps after unloading-prune; history is refreshed after each converged substep.';
metadata.peak_timing_note = 'cycle1_peak_pre_history_refresh is before the peak substep refresh, but after earlier loading-substep refreshes.';
metadata.initial_precrack_exclusion_guard_active = exist('initial_precrack_exclusion_nodes', 'var') == 1;
metadata.initial_state_audit = initial_audit(precrack_soft_profile, precrack_nodes, precrack_elem_profile, precrack_elems);
metadata.old_c1_match = old_c1_match;
metadata.runtime_seconds = toc(start_tic);

out_name = 'reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29';
out_dir = fullfile(getenv('USERPROFILE'), 'Downloads', '_pidl_handoff_v2', out_name);
if ~exist(out_dir, 'dir'), mkdir(out_dir); end
csv_file = fullfile(out_dir, 'state_timing_metrics.csv');
mat_file = fullfile(out_dir, 'state_timing_element_fields.mat');
mesh_file = fullfile(out_dir, 'mesh_geometry.mat');
readme_file = fullfile(out_dir, 'README_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing.md');

writetable(T, csv_file);
save(mat_file, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'state_label', 'cycle_index', 'step_index', 'load_factor', 'u_y', 'is_loaded', ...
    'after_damage_solve', 'after_alpha_bar_update', 'after_f_alpha_update', ...
    'E_el', 'E_d', 'total_energy', 'notes', 'd_elem', 'alpha_bar_elem', ...
    'f_fatigue_elem', 'psi_plus_elem', 'psi_plus_peak_to_date_elem', 'T', 'metadata', '-v7.3');
save(mesh_file, 'node_coords', 'connectivity', 'element_centroids', '-v7');
copyfile(fullfile(root_dir, 'export_reverseBC_soft_hist0_state_timing.m'), ...
    fullfile(out_dir, 'export_reverseBC_soft_hist0_state_timing.m'));
copyfile(fullfile(root_dir, 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m'), ...
    fullfile(out_dir, 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m'));
copyfile(fullfile(root_dir, 'solve_fatigue_fracture.m'), ...
    fullfile(out_dir, 'solve_fatigue_fracture.m'));
write_readme(readme_file, metadata, csv_file, mat_file);

dst_root = fullfile(getenv('USERPROFILE'), 'OneDrive - University of Cambridge', 'PIDL result');
dst_dir = fullfile(dst_root, ['_pidl_handoff_' out_name]);
if exist(dst_dir, 'dir'), rmdir(dst_dir, 's'); end
copyfile(out_dir, dst_dir);

fprintf('\nWrote state timing export:\n  %s\n  %s\n  %s\nOneDrive:\n  %s\n', ...
    csv_file, mat_file, readme_file, dst_dir);
end

function state = make_state(label, cycle, step, load_factor, uy, is_loaded, after_damage, after_alpha, after_f, p, h, psi, peak_psi, E_el, E_d, total_energy, note)
state = struct('label', label, 'cycle', cycle, 'step', step, 'load_factor', load_factor, ...
    'uy', uy, 'is_loaded', is_loaded, 'after_damage', after_damage, ...
    'after_alpha', after_alpha, 'after_f', after_f, 'p', p, 'h', h, ...
    'psi', psi, 'peak_psi', peak_psi, 'E_el', E_el, 'E_d', E_d, ...
    'total_energy', total_energy, 'note', note);
end

function [d_elem, alpha_elem, f_elem, psi_elem, psi_peak_elem] = stack_fields(states, sys)
n_elem = sys.MESH.num_elem;
n_state = numel(states);
d_elem = zeros(n_elem, n_state, 'single');
alpha_elem = zeros(n_elem, n_state, 'single');
f_elem = zeros(n_elem, n_state, 'single');
psi_elem = zeros(n_elem, n_state, 'single');
psi_peak_elem = zeros(n_elem, n_state, 'single');
for k = 1:n_state
    d_elem(:,k) = single(mean(states{k}.p(sys.MESH.elem(:, 1:sys.MESH.nel)), 2));
    alpha_elem(:,k) = single(mean(states{k}.h(:,:,2), 2));
    f_elem(:,k) = single(mean(states{k}.h(:,:,4), 2));
    psi_elem(:,k) = single(mean(states{k}.psi, 2));
    psi_peak_elem(:,k) = single(mean(states{k}.peak_psi, 2));
end
end

function T = build_metrics_table(states, state_label, d_elem, alpha_elem, f_elem, psi_elem, psi_peak_elem, centroids, area)
rows = cell(numel(states), 1);
for k = 1:numel(states)
    s = states{k};
    d = double(d_elem(:,k));
    alpha = double(alpha_elem(:,k));
    f = double(f_elem(:,k));
    psi = double(psi_elem(:,k));
    psi_peak = double(psi_peak_elem(:,k));
    tip = crack_tip(d, centroids, 0.95);
    if isnan(tip.x), tip = crack_tip(d, centroids, 0.50); end
    nt_d = near_tip_integral(d, centroids, area, tip, [0.01 0.02 0.04]);
    nt_alpha = near_tip_integral(alpha, centroids, area, tip, [0.01 0.02 0.04]);
    nt_f = near_tip_integral(f, centroids, area, tip, [0.01 0.02 0.04]);
    nt_psi = near_tip_integral(psi, centroids, area, tip, [0.01 0.02 0.04]);
    nt_psi_peak = near_tip_integral(psi_peak, centroids, area, tip, [0.01 0.02 0.04]);
    rows{k} = {state_label(k), s.cycle, s.step, s.load_factor, s.uy, ...
        s.is_loaded, s.after_damage, s.after_alpha, s.after_f, s.E_el, s.E_d, s.total_energy, ...
        max(d), qtile(d, 0.99), qtile(d, 0.999), mean(d, 'omitnan'), ...
        max(alpha), qtile(alpha, 0.99), qtile(alpha, 0.999), mean(alpha, 'omitnan'), ...
        min(f), qtile(f, 0.001), qtile(f, 0.99), qtile(f, 0.999), mean(f, 'omitnan'), ...
        max(psi), qtile(psi, 0.99), qtile(psi, 0.999), mean(psi, 'omitnan'), ...
        max(psi_peak), qtile(psi_peak, 0.99), qtile(psi_peak, 0.999), mean(psi_peak, 'omitnan'), ...
        tip.x, tip.y, nt_d(1), nt_d(2), nt_d(3), nt_alpha(1), nt_alpha(2), nt_alpha(3), ...
        nt_f(1), nt_f(2), nt_f(3), nt_psi(1), nt_psi(2), nt_psi(3), ...
        nt_psi_peak(1), nt_psi_peak(2), nt_psi_peak(3), string(s.note)};
end
vars = {'state_label','cycle_index','step_index','load_factor','u_y', ...
    'is_loaded','after_damage_solve','after_alpha_bar_update','after_f_alpha_update', ...
    'E_el','E_d','total_energy', ...
    'd_max','d_p99','d_p999','d_mean', ...
    'alpha_bar_max','alpha_bar_p99','alpha_bar_p999','alpha_bar_mean', ...
    'f_fatigue_min','f_fatigue_p001','f_fatigue_p99','f_fatigue_p999','f_fatigue_mean', ...
    'psi_plus_max','psi_plus_p99','psi_plus_p999','psi_plus_mean', ...
    'psi_plus_peak_to_date_max','psi_plus_peak_to_date_p99','psi_plus_peak_to_date_p999','psi_plus_peak_to_date_mean', ...
    'x_tip_d095_or_d050','y_tip_d095_or_d050', ...
    'near_tip_int_d_r1ell','near_tip_int_d_r2ell','near_tip_int_d_r4ell', ...
    'near_tip_int_alpha_bar_r1ell','near_tip_int_alpha_bar_r2ell','near_tip_int_alpha_bar_r4ell', ...
    'near_tip_int_f_fatigue_r1ell','near_tip_int_f_fatigue_r2ell','near_tip_int_f_fatigue_r4ell', ...
    'near_tip_int_psi_plus_r1ell','near_tip_int_psi_plus_r2ell','near_tip_int_psi_plus_r4ell', ...
    'near_tip_int_psi_plus_peak_to_date_r1ell','near_tip_int_psi_plus_peak_to_date_r2ell','near_tip_int_psi_plus_peak_to_date_r4ell', ...
    'timing_note'};
T = cell2table(vertcat(rows{:}), 'VariableNames', vars);
end

function centroids = elem_centroids(node_coords, connectivity)
centroids = zeros(size(connectivity, 1), 2);
for e = 1:size(connectivity, 1)
    centroids(e,:) = mean(node_coords(connectivity(e,:), :), 1);
end
end

function area = quad_area(node_coords, connectivity)
area = zeros(size(connectivity, 1), 1);
for e = 1:size(connectivity, 1)
    xy = node_coords(connectivity(e,:), :);
    x = xy(:,1);
    y = xy(:,2);
    area(e) = 0.5 * abs(sum(x .* y([2:end 1]) - y .* x([2:end 1])));
end
end

function v = qtile(x, q)
x = sort(x(isfinite(x)));
if isempty(x), v = NaN; return; end
pos = 1 + (numel(x) - 1) * q;
lo = floor(pos);
hi = ceil(pos);
if lo == hi
    v = x(lo);
else
    v = x(lo) + (pos - lo) * (x(hi) - x(lo));
end
end

function tip = crack_tip(d, centroids, threshold)
mask = d >= threshold;
if ~any(mask)
    tip = struct('x', NaN, 'y', NaN);
    return;
end
idxs = find(mask);
[~, j] = max(centroids(idxs, 1));
idx = idxs(j);
tip = struct('x', centroids(idx, 1), 'y', centroids(idx, 2));
end

function vals = near_tip_integral(field, centroids, area, tip, radii)
vals = nan(1, numel(radii));
if isnan(tip.x) || isnan(tip.y), return; end
r = sqrt((centroids(:,1) - tip.x).^2 + (centroids(:,2) - tip.y).^2);
for j = 1:numel(radii)
    mask = r <= radii(j);
    vals(j) = sum(field(mask) .* area(mask), 'omitnan');
end
end

function audit = initial_audit(precrack_soft_profile, precrack_nodes, precrack_elem_profile, precrack_elems)
audit = struct();
audit.precrack_nodes_d_gt_0 = numel(precrack_nodes);
audit.precrack_elems_d_gt_0 = numel(precrack_elems);
audit.precrack_d_mean = mean(precrack_soft_profile(precrack_nodes), 'omitnan');
audit.precrack_d_max = max(precrack_soft_profile(precrack_nodes));
audit.precrack_elem_d_mean = mean(precrack_elem_profile(precrack_elems), 'omitnan');
audit.precrack_elem_d_max = max(precrack_elem_profile(precrack_elems));
audit.initial_alpha_bar = 0.0;
audit.initial_f_alpha = 1.0;
end

function match = compare_old_c1(base_run_name, d_elem, alpha_elem, f_elem, psi_elem, psi_peak_elem, state_label)
match = struct();
match.old_handoff_found = false;
old_file = fullfile(getenv('USERPROFILE'), 'Downloads', '_pidl_handoff_v2', ...
    'reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28', ...
    'reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat');
if exist(old_file, 'file') ~= 2
    old_file = fullfile(getenv('USERPROFILE'), 'OneDrive - University of Cambridge', 'PIDL result', ...
        '_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28', ...
        'reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat');
end
match.old_file = old_file;
match.base_run_name = base_run_name;
if exist(old_file, 'file') ~= 2
    return;
end
S = load(old_file, 'd_elem', 'alpha_bar_elem', 'f_fatigue_elem', 'psi_plus_elem');
idx_unload = find(state_label == "cycle1_unloaded_post_history_refresh", 1);
idx_peak = find(state_label == "cycle1_peak_post_history_refresh", 1);
match.old_handoff_found = true;
match.old_c1_is_mixed_timing = true;
match.note = 'Old c1 handoff stores end-of-cycle d/alpha/f with peak-over-cycle psi_plus.';
match.max_abs_d_vs_unloaded_post = max(abs(double(S.d_elem(:,1)) - double(d_elem(:,idx_unload))));
match.max_abs_alpha_vs_unloaded_post = max(abs(double(S.alpha_bar_elem(:,1)) - double(alpha_elem(:,idx_unload))));
match.max_abs_f_vs_unloaded_post = max(abs(double(S.f_fatigue_elem(:,1)) - double(f_elem(:,idx_unload))));
match.max_abs_psi_vs_peak_post_current_psi = max(abs(double(S.psi_plus_elem(:,1)) - double(psi_elem(:,idx_peak))));
match.max_abs_psi_vs_unloaded_peak_to_date = max(abs(double(S.psi_plus_elem(:,1)) - double(psi_peak_elem(:,idx_unload))));
end

function write_readme(path, metadata, csv_file, mat_file)
fid = fopen(path, 'w');
if fid < 0, error('Cannot open README for writing: %s', path); end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '# reverseBC u=0.12 soft-hist0 state timing export\n\n');
fprintf(fid, 'Request: `%s`.\n\n', metadata.request);
fprintf(fid, 'Files:\n');
fprintf(fid, '- `%s`: state-level reductions and timing flags.\n', csv_file);
fprintf(fid, '- `%s`: element fields for each state.\n', mat_file);
fprintf(fid, '- `mesh_geometry.mat`: same continuous-material mesh.\n\n');
fprintf(fid, 'Settings:\n');
fprintf(fid, '- Base run: `%s`; replay run: `%s`.\n', metadata.base_run_name, metadata.replay_run_name);
fprintf(fid, '- Nodes/elements: %d / %d; element type: %s.\n', metadata.n_node, metadata.n_elem, metadata.element_type);
fprintf(fid, '- Material/fatigue: %s.\n', metadata.material);
fprintf(fid, '- Loading/BC: %s.\n\n', metadata.loading);
fprintf(fid, 'Timing interpretation:\n');
fprintf(fid, '- `%s`\n', metadata.substep_note);
fprintf(fid, '- `%s`\n', metadata.peak_timing_note);
fprintf(fid, '- `psi_plus_elem` is the current-state tensile elastic energy density for that state.\n');
fprintf(fid, '- `psi_plus_peak_to_date_elem` is the running maximum across cycle-1 substeps up to that state.\n');
fprintf(fid, '- Initial precrack penetration guard active: %d.\n\n', metadata.initial_precrack_exclusion_guard_active);
fprintf(fid, 'Initial precrack audit:\n');
fprintf(fid, '- Precrack support nodes/elements with d>0: %d / %d.\n', metadata.initial_state_audit.precrack_nodes_d_gt_0, metadata.initial_state_audit.precrack_elems_d_gt_0);
fprintf(fid, '- Precrack nodal d mean/max: %.12g / %.12g.\n', metadata.initial_state_audit.precrack_d_mean, metadata.initial_state_audit.precrack_d_max);
fprintf(fid, '- Precrack element d mean/max: %.12g / %.12g.\n', metadata.initial_state_audit.precrack_elem_d_mean, metadata.initial_state_audit.precrack_elem_d_max);
fprintf(fid, '- Initial alpha_bar/f_alpha: %.12g / %.12g.\n\n', metadata.initial_state_audit.initial_alpha_bar, metadata.initial_state_audit.initial_f_alpha);
fprintf(fid, 'Old c1 handoff comparison:\n');
if metadata.old_c1_match.old_handoff_found
    fprintf(fid, '- Old handoff file: `%s`.\n', metadata.old_c1_match.old_file);
    fprintf(fid, '- Old c1 timing note: %s\n', metadata.old_c1_match.note);
    fprintf(fid, '- Max abs d/alpha/f difference vs `cycle1_unloaded_post_history_refresh`: %.12g / %.12g / %.12g.\n', ...
        metadata.old_c1_match.max_abs_d_vs_unloaded_post, metadata.old_c1_match.max_abs_alpha_vs_unloaded_post, metadata.old_c1_match.max_abs_f_vs_unloaded_post);
    fprintf(fid, '- Max abs old psi vs `cycle1_peak_post_history_refresh` current psi: %.12g.\n', metadata.old_c1_match.max_abs_psi_vs_peak_post_current_psi);
    fprintf(fid, '- Max abs old psi vs `cycle1_unloaded_post_history_refresh` peak-to-date psi: %.12g.\n', metadata.old_c1_match.max_abs_psi_vs_unloaded_peak_to_date);
else
    fprintf(fid, '- Old c1 handoff was not found locally; numerical match was not evaluated.\n');
end
clear cleanup;
end
