function export_latest_align_fem_state_fields()
% Export selected latest-aligned FEM states with explicit stress definitions.
%
% Latest aligned setting:
%   retained-material soft diffuse precrack / hist0 reverseBC
%   AT1 + AMOR + PENALTY, E=1, nu=0.3, Gc=0.01, ell=0.01.

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

start_tic = tic;
target_cycles = [1 2 3 20 40 60 69];
late_cycles = [2 3 20 40 60 69];

soft_hist0_example_name = 'FEM23_replay_latest_align_state_fields';
soft_hist0_max_cycle = 69;
INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC
SOL_CYCL_PAR.max_cycle = 69;

if exist(example_name, 'dir'), rmdir(example_name, 's'); end
init_fatigue_fracture

% Latest aligned initial state: soft precrack, alpha_bar=0, f=1.
p_field = precrack_soft_profile;
p_field_old = precrack_soft_profile;
history_vars_old(:,:,2) = 0.0;
history_vars_old(:,:,3) = 0.0;
history_vars_old(:,:,4) = 1.0;

node_coords = sys.MESH.node;
connectivity = sys.MESH.elem(:, 1:sys.MESH.nel);
[element_centroids, element_area] = elem_geometry(node_coords, connectivity);
[gauss_coords, quad_weights] = gauss_geometry(sys.MESH, sys.QUADRATURE, sys.GEOM.t);

states = {};
zero_psi = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
states{end+1} = capture_state('state0_initial_unloaded_prehistory', 0, 0, ...
    0.0, 0.0, false, false, displ, p_field, history_vars_old, zero_psi, sys, ...
    'Initial unloaded soft precrack before any load/history refresh; alpha_bar=0, f=1.');

for i_cycle = 1:max(target_cycles)
    fprintf('[FEM23] cycle %d/%d\n', i_cycle, max(target_cycles));
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
                [~, ~, ~, history_vars_old] = assembly_pf_fh( ...
                    sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, sys.CC, ...
                    p_field, p_field_old, strain_en_undgr, sys.stress_state.as_number, history_vars_old);
                peak_psi_plus = max(peak_psi_plus, strain_en_undgr);
                break;
            end
            if i_stag == SOL_STAG_PAR.max_iter
                error('staggered loop did not converge at cycle %d step %d', i_cycle, i_step);
            end
        end

        if should_capture(i_cycle, i_step, late_cycles, SOL_STEP_PAR.n_step)
            label = state_label(i_cycle, i_step, SOL_STEP_PAR.n_step);
            states{end+1} = capture_state(label, i_cycle, i_step, load_factor, uy_value, ...
                true, true, displ, p_field, history_vars_old, strain_en_undgr, sys, ...
                'Post converged displacement/damage solve and post history/fatigue refresh.');
            fprintf('[FEM23] captured %s\n', label);
        end

        SOL_STEP_VAR = phase_field.fem.solver.step.post_iter_update( ...
            i_step, SOL_STEP_VAR, sys.STIFFNESS_MATRIX, displ, sys.NODE_BOUNDARIES, ...
            sys.MESH.num_node, SOL_STEP_PAR, example_name);
        SOL_STAG_VAR = phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
    end
end

fields = stack_states(states, sys);
T_states = state_table(states);

metadata = struct();
metadata.request = 'Mac request 2026-06-08: latest aligned FEM cycles/states with raw vs degraded stress separated';
metadata.setting = 'retained-material soft diffuse precrack / hist0 reverseBC; no void slit; no duplicated crack-face nodes';
metadata.input = 'INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC';
metadata.replay_example_name = example_name;
metadata.cycles_requested = target_cycles;
metadata.states_requested = 'state0; c1 step1/step2/step3/peak/unloaded; c2,c3,c20,c40,c60,c69 peak/unloaded';
metadata.loading = 'cyclic R=0, retained steps uy=[0.03 0.06 0.09 0.12 0] after unloading-prune';
metadata.material = 'AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2, tol_irrev=1e-3, res_stiff=1e-6';
metadata.raw_stress_definition = 'sigma_raw_gp = C * epsilon_gp, with C the plane-strain elastic matrix.';
metadata.degraded_stress_definition = 'sigma_degraded_effective_gp = sigma_minus_gp + g_stiffness_gp * sigma_plus_gp from the AMOR split used by the FEM equilibrium kernel.';
metadata.g_stiffness_definition = 'g_stiffness_gp = (1-d_gp)^2 + res_stiff; this is the stiffness degradation in AMOR equilibrium.';
metadata.fatigue_definition = 'f_fatigue_gp is history slot 4 from AT1_PENALTY_FATIGUE; fatigue affects phase-field fracture resistance/history, not the equilibrium stress.';
metadata.psi_plus_definition = 'psi_plus_gp is AMOR tensile/positive strain energy from the equilibrium kernel, recomputed in MATLAB to match strain_en_undgr.';
metadata.psi_minus_definition = 'psi_minus_gp is AMOR compressive/negative strain energy, i.e. 0 when trace(eps)>=0 and 0.5*eps^T*C_neg*eps otherwise.';
metadata.g_psi_note = 'g_psi_plus_gp = g_stiffness_gp .* psi_plus_gp; f_g_psi_plus_gp is exported as diagnostic f*g*psi_plus, not as an equilibrium stress term.';
metadata.existing_vtk_sigma_warning = 'GRIPHFiTH L2_PROJECTION VTK sigma is degraded by (1-d)^2 and is not a clean raw stress; use this MAT for raw/degraded separation.';
metadata.epsilon_xy_note = 'epsilon_xy_gp stores GRIPHFiTH Voigt engineering shear gamma_xy=du/dy+dv/dx; epsilon_xy_tensor_gp stores gamma_xy/2 for principal strain calculation.';
metadata.von_mises_note = 'von_mises_*_gp uses the 2D formula sqrt(sxx^2 - sxx*syy + syy^2 + 3*sxy^2).';
metadata.gauss_order_note = 'Gauss index order follows sys.QUADRATURE.gauss_pts/Nxi in GRIPHFiTH.';
metadata.runtime_seconds = toc(start_tic);

package_name = 'latest_align_soft_hist0_state_field_export_20260608';
out_root = fullfile(getenv('USERPROFILE'), 'Downloads', '_pidl_handoff_v2', package_name);
if exist(out_root, 'dir'), rmdir(out_root, 's'); end
mkdir(out_root);
mat_file = fullfile(out_root, 'latest_align_soft_hist0_state_fields.mat');
state_csv = fullfile(out_root, 'latest_align_soft_hist0_state_index.csv');
mesh_file = fullfile(out_root, 'mesh_geometry.mat');
readme_file = fullfile(out_root, 'README_latest_align_soft_hist0_state_fields.md');

save(mat_file, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'gauss_coords', 'quad_weights', 'T_states', 'fields', 'metadata', '-v7.3');
save(mesh_file, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'gauss_coords', 'quad_weights', '-v7.3');
writetable(T_states, state_csv);
write_readme(readme_file, metadata, fields);
copyfile(fullfile(root_dir, 'export_latest_align_fem_state_fields.m'), out_root);

dst_root = fullfile(getenv('USERPROFILE'), 'OneDrive - University of Cambridge', ...
    'PIDL result', ['_pidl_handoff_' package_name]);
if exist(dst_root, 'dir'), rmdir(dst_root, 's'); end
copyfile(out_root, dst_root);

fprintf('[FEM23] wrote package:\n  %s\nOneDrive:\n  %s\n', out_root, dst_root);
fprintf('[FEM23] runtime %.1f s, states %d\n', metadata.runtime_seconds, numel(states));
end

function tf = should_capture(cycle, step, late_cycles, n_step)
if cycle == 1
    tf = true;
elseif ismember(cycle, late_cycles)
    tf = (step == n_step - 1) || (step == n_step);
else
    tf = false;
end
end

function label = state_label(cycle, step, n_step)
if cycle == 1
    names = {'step1', 'step2', 'step3', 'peak', 'unloaded'};
    label = sprintf('c1_%s', names{step});
elseif step == n_step - 1
    label = sprintf('c%d_peak', cycle);
elseif step == n_step
    label = sprintf('c%d_unloaded', cycle);
else
    label = sprintf('c%d_step%d', cycle, step);
end
end

function state = capture_state(label, cycle, step, load_factor, uy, after_damage, after_history, displ, p, h, psi_from_solver, sys, note)
gp = compute_gp_fields(sys, displ, p, h);
state = struct('label', string(label), 'cycle', cycle, 'step', step, ...
    'load_factor', load_factor, 'uy', uy, 'after_damage', after_damage, ...
    'after_history', after_history, 'displ', single(reshape(displ, [sys.MESH.num_node, 2])), ...
    'd_node', single(p), 'history', single(h), 'psi_solver_gp', single(psi_from_solver), ...
    'gp', gp, 'note', string(note));
end

function gp = compute_gp_fields(sys, displ, p, h)
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

alpha_bar = single(h(:,:,2));
f_fatigue = single(h(:,:,4));
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
gp.psi_minus_gp = psi_minus;
gp.d_gp = d_gp;
gp.g_stiffness_gp = g_stiffness;
gp.alpha_bar_gp = alpha_bar;
gp.f_fatigue_gp = f_fatigue;
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

function fields = stack_states(states, sys)
n_state = numel(states);
n_node = sys.MESH.num_node;
n_elem = sys.MESH.num_elem;
n_gp = sys.QUADRATURE.num_gauss_pts;

fields = struct();
fields.state_label = strings(n_state, 1);
fields.cycle = zeros(n_state, 1, 'int32');
fields.step = zeros(n_state, 1, 'int32');
fields.load_factor = zeros(n_state, 1, 'single');
fields.uy = zeros(n_state, 1, 'single');
fields.u_node = zeros(n_node, 2, n_state, 'single');
fields.d_node = zeros(n_node, n_state, 'single');

sample_gp = states{1}.gp;
gp_names = fieldnames(sample_gp);
for i = 1:numel(gp_names)
    name = gp_names{i};
    sample_val = ensure_3d(sample_gp.(name));
    n_comp = size(sample_val, 3);
    fields.(name) = zeros(n_elem, n_gp, n_comp, n_state, 'single');
    elem_name = strrep(name, '_gp', '_elem');
    if ~strcmp(elem_name, name)
        fields.(elem_name) = zeros(n_elem, n_comp, n_state, 'single');
    end
end

for k = 1:n_state
    fields.state_label(k) = states{k}.label;
    fields.cycle(k) = int32(states{k}.cycle);
    fields.step(k) = int32(states{k}.step);
    fields.load_factor(k) = single(states{k}.load_factor);
    fields.uy(k) = single(states{k}.uy);
    fields.u_node(:,:,k) = states{k}.displ;
    fields.d_node(:,k) = states{k}.d_node;
    for i = 1:numel(gp_names)
        name = gp_names{i};
        val = ensure_3d(states{k}.gp.(name));
        fields.(name)(:,:,:,k) = val;
        elem_name = strrep(name, '_gp', '_elem');
        if ~strcmp(elem_name, name)
            elem_val = squeeze(mean(val, 2));
            if isvector(elem_val)
                elem_val = elem_val(:);
            end
            fields.(elem_name)(:,:,k) = elem_val;
        end
    end
end
end

function a = ensure_3d(a)
if ndims(a) == 2
    a = reshape(a, size(a,1), size(a,2), 1);
end
end

function T = state_table(states)
n = numel(states);
state_label = strings(n,1);
cycle = zeros(n,1);
step = zeros(n,1);
load_factor = zeros(n,1);
uy = zeros(n,1);
after_damage = false(n,1);
after_history = false(n,1);
note = strings(n,1);
for i = 1:n
    state_label(i) = states{i}.label;
    cycle(i) = states{i}.cycle;
    step(i) = states{i}.step;
    load_factor(i) = states{i}.load_factor;
    uy(i) = states{i}.uy;
    after_damage(i) = states{i}.after_damage;
    after_history(i) = states{i}.after_history;
    note(i) = states{i}.note;
end
T = table(state_label, cycle, step, load_factor, uy, after_damage, after_history, note);
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

function write_readme(path, metadata, fields)
fid = fopen(path, 'w');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '# Latest Aligned FEM State Field Export\n\n');
fprintf(fid, '- Request: %s\n', metadata.request);
fprintf(fid, '- Setting: %s\n', metadata.setting);
fprintf(fid, '- Loading: %s\n\n', metadata.loading);
fprintf(fid, '## Stress Definitions\n\n');
fprintf(fid, '- Raw stress: %s\n', metadata.raw_stress_definition);
fprintf(fid, '- Degraded/effective stress: %s\n', metadata.degraded_stress_definition);
fprintf(fid, '- Existing VTK warning: %s\n\n', metadata.existing_vtk_sigma_warning);
fprintf(fid, '## State Count\n\n');
fprintf(fid, '- n_state = %d\n', numel(fields.state_label));
fprintf(fid, '- states = %s\n', strjoin(cellstr(fields.state_label'), ', '));
end
