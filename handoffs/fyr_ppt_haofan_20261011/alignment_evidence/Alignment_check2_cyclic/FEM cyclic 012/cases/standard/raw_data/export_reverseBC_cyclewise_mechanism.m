function export_reverseBC_cyclewise_mechanism(run_case)
% Cyclewise mechanism export for PIDL/FEM field comparison.
if nargin < 1
    run_case = 'reverseBC_u12';
end

root_dir = fileparts(mfilename('fullpath'));
switch run_case
    case 'reverseBC_u12'
        run_name = 'SENT_PIDL_12_reverseBC';
        request_label = 'docs/handovers/fem_cyclewise_mechanism_request_2026-05-28.md commit 0272625';
        out_name = 'reverseBC_u12_cyclewise_mechanism_2026-05-28';
        mat_name = 'reverseBC_u12_cyclewise_element_fields_c1_c74.mat';
        csv_name = 'reverseBC_u12_cyclewise_mechanism_metrics.csv';
        readme_name = 'README_reverseBC_u12_cyclewise_mechanism.md';
        mesh_note = 'Same SENT_mesh / mesh_geometry.mat used in prior reverseBC u=0.12 handoffs';
        mesh = load(fullfile(root_dir, 'mesh_geometry.mat'));
        node_coords = mesh.node_coords;
        connectivity = mesh.connectivity;
        element_centroids = mesh.element_centroids;
        mesh_copy_source = fullfile(root_dir, 'mesh_geometry.mat');
    case 'fine_reverseBC_u12'
        run_name = 'SENT_PIDL_12_fine_reverseBC';
        request_label = 'Follow-up to cyclewise mechanism request: PIDL fine mesh + AT1/AMOR/PENALTY + reverseBC';
        out_name = 'fine_reverseBC_u12_cyclewise_mechanism_2026-05-28';
        mat_name = 'fine_reverseBC_u12_cyclewise_element_fields_c1_c69.mat';
        csv_name = 'fine_reverseBC_u12_cyclewise_mechanism_metrics.csv';
        readme_name = 'README_fine_reverseBC_u12_cyclewise_mechanism.md';
        mesh_note = 'PIDL fine mesh from Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp; coarser than SENT_mesh.inp';
        cwd0 = pwd;
        cleanup_cd = onCleanup(@() cd(cwd0));
        cd(root_dir);
        INPUT_SENT_PIDL_12_fine_reverseBC;
        clear cleanup_cd;
        node_coords = MESH.node;
        connectivity = MESH.elem;
        element_centroids = zeros(MESH.num_elem, 2);
        for e = 1:MESH.num_elem
            element_centroids(e,:) = mean(node_coords(connectivity(e,:), :), 1);
        end
        mesh_copy_source = '';
    case 'diffuse_precrack_reverseBC_u12'
        run_name = 'SENT_PIDL_12_diffuse_precrack_reverseBC';
        request_label = 'docs/handovers/fem_diffuse_precrack_request_2026-05-28.md';
        out_name = 'reverseBC_u12_diffuse_precrack_2026-05-28';
        mat_name = 'reverseBC_u12_diffuse_precrack_element_fields_c1_c69.mat';
        csv_name = 'reverseBC_u12_diffuse_precrack_cyclewise_mechanism_metrics.csv';
        readme_name = 'README_reverseBC_u12_diffuse_precrack.md';
        mesh_note = 'Continuous material plate mesh from specimen.internal.plate notch_type=phase_field; no void slit or duplicated crack faces; hard d=1 Dirichlet band x<=0.5, |y-0.5|<=0.02';
        cwd0 = pwd;
        cleanup_cd = onCleanup(@() cd(cwd0));
        cd(root_dir);
        INPUT_SENT_PIDL_12_diffuse_precrack_reverseBC;
        clear cleanup_cd;
        node_coords = MESH.node;
        connectivity = MESH.elem;
        element_centroids = zeros(MESH.num_elem, 2);
        for e = 1:MESH.num_elem
            element_centroids(e,:) = mean(node_coords(connectivity(e,:), :), 1);
        end
        mesh_copy_source = '';
        diffuse_info = diffuse_precrack_metadata;
        diffuse_info.n_precrack_nodes = numel(precrack_nodes);
        diffuse_info.n_precrack_elems = numel(precrack_elems);
        diffuse_info.initial_alpha_bar = 1.0;
        diffuse_info.initial_f_alpha = (2 * MAT_CHAR(1).alpha_T / (1 + MAT_CHAR(1).alpha_T)) ^ MAT_CHAR(1).p;
    case 'diffuse_precrack_soft_hist0_reverseBC_u12'
        run_name = 'SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC';
        request_label = 'docs/handovers/windows_fem_inbox.md Request 18';
        out_name = 'reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28';
        mat_name = 'reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_cXX.mat';
        csv_name = 'reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv';
        readme_name = 'README_reverseBC_u12_diffuse_precrack_soft_hist0.md';
        mesh_note = 'Continuous material plate mesh from specimen.internal.plate notch_type=phase_field; no void slit or duplicated crack faces; soft AT1-like initial d profile, alpha_bar=0 everywhere';
        cwd0 = pwd;
        cleanup_cd = onCleanup(@() cd(cwd0));
        cd(root_dir);
        INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC;
        clear cleanup_cd;
        node_coords = MESH.node;
        connectivity = MESH.elem;
        element_centroids = zeros(MESH.num_elem, 2);
        for e = 1:MESH.num_elem
            element_centroids(e,:) = mean(node_coords(connectivity(e,:), :), 1);
        end
        mesh_copy_source = '';
        diffuse_info = diffuse_precrack_metadata;
        diffuse_info.n_precrack_nodes = numel(precrack_nodes);
        diffuse_info.n_precrack_elems = numel(precrack_elems);
        diffuse_info.n_precrack_core_nodes = numel(precrack_core_nodes);
        diffuse_info.n_precrack_core_elems = numel(precrack_core_elems);
        diffuse_info.initial_alpha_bar = 0.0;
        diffuse_info.initial_f_alpha = 1.0;
    otherwise
        error('Unknown run_case: %s', run_case);
end

run_dir = fullfile(root_dir, run_name);
psi_dir = fullfile(run_dir, 'psi_fields');
out_dir = fullfile(getenv('USERPROFILE'), 'Downloads', ...
    '_pidl_handoff_v2', out_name);
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

element_area = quad_area(node_coords, connectivity);

files = dir(fullfile(psi_dir, 'cycle_*.mat'));
cycles = zeros(numel(files), 1);
for i = 1:numel(files)
    tok = regexp(files(i).name, 'cycle_(\d+)\.mat', 'tokens', 'once');
    cycles(i) = str2double(tok{1});
end
cycles = sort(cycles);
mat_name = strrep(mat_name, 'cXX', sprintf('c%d', cycles(end)));
n_cycle = numel(cycles);
n_elem = size(connectivity, 1);

d_elem = zeros(n_elem, n_cycle, 'single');
alpha_bar_elem = zeros(n_elem, n_cycle, 'single');
f_fatigue_elem = zeros(n_elem, n_cycle, 'single');
psi_plus_elem = zeros(n_elem, n_cycle, 'single');

T_energy = build_energy_table(run_dir);
monitor_alpha = read_monitor_alpha(run_dir, cycles);

nominal_mask = abs(element_centroids(:,2)) > 0.3 & element_centroids(:,1) > -0.3;
if ~any(nominal_mask)
    warning('Nominal Kt mask is empty; psi_nominal_mean will be NaN.');
end

rows = cell(n_cycle, 1);
for k = 1:n_cycle
    cyc = cycles(k);
    src = fullfile(psi_dir, sprintf('cycle_%04d.mat', cyc));
    S = load(src, 'd_elem', 'alpha_elem', 'f_alpha_elem', 'psi_elem');

    d = double(S.d_elem(:));
    alpha = double(S.alpha_elem(:));
    f = double(S.f_alpha_elem(:));
    psi = double(S.psi_elem(:));

    d_elem(:,k) = single(d);
    alpha_bar_elem(:,k) = single(alpha);
    f_fatigue_elem(:,k) = single(f);
    psi_plus_elem(:,k) = single(psi);

    erow = T_energy(T_energy.cycle == cyc, :);
    if isempty(erow)
        E_el = NaN; E_d = NaN; total_energy = NaN;
    else
        E_el = erow.E_el(1);
        E_d = erow.E_d(1);
        total_energy = erow.total_energy(1);
    end

    [d_max, d_max_x, d_max_y] = max_with_location(d, element_centroids);
    [alpha_max, alpha_max_x, alpha_max_y] = max_with_location(alpha, element_centroids);
    [f_min, f_min_x, f_min_y] = min_with_location(f, element_centroids);
    [psi_max, psi_max_x, psi_max_y] = max_with_location(psi, element_centroids);

    psi_top10 = mean_top_n(psi, 10);
    psi_nominal = mean(psi(nominal_mask), 'omitnan');
    Kt_proxy = sqrt(psi_top10 ./ psi_nominal);

    tip095 = crack_tip(d, element_centroids, 0.95);
    tip090 = crack_tip(d, element_centroids, 0.90);
    tip050 = crack_tip(d, element_centroids, 0.50);
    near095 = tip095;
    if isnan(near095.x)
        near095 = tip090;
    end
    if isnan(near095.x)
        near095 = tip050;
    end
    width050 = process_width(d, element_centroids, element_area, 0.50, near095.x);
    width090 = process_width(d, element_centroids, element_area, 0.90, near095.x);
    rb = right_boundary_diagnostic(d, element_centroids, 0.95);

    rows{k} = {cyc, E_el, E_d, total_energy, ...
        d_max, mean(d, 'omitnan'), qtile(d, 0.99), qtile(d, 0.999), ...
        monitor_alpha(k), alpha_max, qtile(alpha, 0.999), qtile(alpha, 0.99), mean(alpha, 'omitnan'), ...
        f_min, qtile(f, 0.001), mean(f, 'omitnan'), ...
        psi_max, qtile(psi, 0.999), qtile(psi, 0.99), mean(psi, 'omitnan'), ...
        psi_top10, psi_nominal, Kt_proxy, ...
        d_max_x, d_max_y, alpha_max_x, alpha_max_y, f_min_x, f_min_y, psi_max_x, psi_max_y, ...
        tip095.x, tip095.y, tip090.x, tip090.y, tip050.x, tip050.y, ...
        width050.yspan, width090.yspan, width050.count, width090.count, ...
        rb.count, rb.yspan};

    fprintf('[OK] cycle %04d d_max=%.4g alpha_elem_max=%.4g psi_max=%.4g Kt=%.4g\n', ...
        cyc, d_max, alpha_max, psi_max, Kt_proxy);
end

var_names = {'cycle','E_el','E_d','total_energy', ...
    'd_max','d_mean','d_p99','d_p999', ...
    'alpha_bar_monitor_max','alpha_bar_elem_max','alpha_bar_elem_p999','alpha_bar_elem_p99','alpha_bar_elem_mean', ...
    'f_fatigue_min','f_fatigue_p001','f_fatigue_mean', ...
    'psi_plus_elem_max','psi_plus_elem_p999','psi_plus_elem_p99','psi_plus_elem_mean', ...
    'psi_tip_top10_mean','psi_nominal_mean','Kt_proxy', ...
    'x_max_d','y_max_d','x_max_alpha_bar_elem','y_max_alpha_bar_elem', ...
    'x_min_f_fatigue_elem','y_min_f_fatigue_elem','x_max_psi_plus_elem','y_max_psi_plus_elem', ...
    'x_tip_d095','y_tip_d095','x_tip_d090','y_tip_d090','x_tip_d050','y_tip_d050', ...
    'width_y_d050_near_tip','width_y_d090_near_tip','n_elem_d050_near_tip','n_elem_d090_near_tip', ...
    'right_boundary_d095_count','right_boundary_d095_yspan'};
T = cell2table(vertcat(rows{:}), 'VariableNames', var_names);

csv_file = fullfile(out_dir, csv_name);
writetable(T, csv_file);

metadata = struct();
metadata.request = request_label;
metadata.run_name = run_name;
metadata.run_dir = run_dir;
metadata.cycles = cycles(:)';
metadata.mesh = mesh_note;
metadata.n_node = size(node_coords, 1);
metadata.n_elem = n_elem;
metadata.element_type = 'Q4 quadrilateral';
metadata.integration_rule = '2x2 Gauss in solve; exported fields are element means over Gauss/history data';
metadata.material = 'AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2';
metadata.loading = 'u=0.12, R=0, reverseBC fix_X top+bottom, fix_Y bottom, disp_Y top';
metadata.field_state = 'psi_fields/cycle_XXXX.mat are post-cycle element-averaged history exports; psi is peak-over-cycle; VTK nodal fields are unloaded step 5 and are not used here';
metadata.nominal_region = 'abs(y) > 0.3 and x > -0.3';
metadata.tip_definition = 'x_tip_dXXX is the maximum centroid x among elements with d_elem >= threshold; y is the y of the highest-x threshold element';
metadata.width_definition = 'near-tip width uses elements with d >= threshold and |x - x_tip| <= 2*sqrt(mean(element_area)); yspan is max(y)-min(y)';
metadata.right_boundary_definition = 'right boundary means x >= max(element_centroids(:,1)) - 2*sqrt(mean(element_area)); d >= 0.95';
metadata.monitor_alpha_note = 'monitorcycle.dat column ||fat||_inf is retained as alpha_bar_monitor_max, but it is a monitor norm/internal-state maximum and differs from exported alpha_bar_elem, which is an element mean over Gauss/history data.';
if exist('diffuse_info', 'var')
    metadata.diffuse_precrack = diffuse_info;
end
initial_audit_file = fullfile(run_dir, 'diffuse_precrack_metadata.mat');
if exist(initial_audit_file, 'file') == 2
    A = load(initial_audit_file);
    if isfield(A, 'initial_state_audit')
        metadata.initial_state_audit = A.initial_state_audit;
    end
end

mat_file = fullfile(out_dir, mat_name);
save(mat_file, 'node_coords', 'connectivity', 'element_centroids', ...
    'element_area', 'cycles', 'd_elem', 'alpha_bar_elem', ...
    'f_fatigue_elem', 'psi_plus_elem', 'T', 'metadata', '-v7.3');
mesh_geometry_file = fullfile(out_dir, 'mesh_geometry.mat');
save(mesh_geometry_file, 'node_coords', 'connectivity', 'element_centroids', '-v7');
if ~isempty(mesh_copy_source)
    copyfile(mesh_copy_source, mesh_geometry_file);
end

readme_file = fullfile(out_dir, readme_name);
write_readme(readme_file, metadata, csv_file, mat_file);

fprintf('\nWrote:\n  %s\n  %s\n  %s\n', csv_file, mat_file, readme_file);
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
if isempty(x)
    v = NaN;
    return;
end
pos = 1 + (numel(x) - 1) * q;
lo = floor(pos);
hi = ceil(pos);
if lo == hi
    v = x(lo);
else
    v = x(lo) + (pos - lo) * (x(hi) - x(lo));
end
end

function v = mean_top_n(x, n)
x = sort(x(isfinite(x)), 'descend');
if isempty(x)
    v = NaN;
else
    v = mean(x(1:min(n, numel(x))));
end
end

function [v, x, y] = max_with_location(field, centroids)
[v, idx] = max(field);
x = centroids(idx, 1);
y = centroids(idx, 2);
end

function [v, x, y] = min_with_location(field, centroids)
[v, idx] = min(field);
x = centroids(idx, 1);
y = centroids(idx, 2);
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

function w = process_width(d, centroids, area, threshold, x_tip)
if isnan(x_tip)
    w = struct('yspan', NaN, 'count', 0);
    return;
end
h = sqrt(mean(area, 'omitnan'));
mask = d >= threshold & abs(centroids(:,1) - x_tip) <= 2*h;
count = nnz(mask);
if count == 0
    yspan = NaN;
else
    yspan = max(centroids(mask,2)) - min(centroids(mask,2));
end
w = struct('yspan', yspan, 'count', count);
end

function rb = right_boundary_diagnostic(d, centroids, threshold)
h = sqrt(mean(diff(unique(round(centroids(:,1), 12))).^2, 'omitnan'));
if ~isfinite(h) || h == 0
    h = 2 * eps(max(centroids(:,1)));
end
xmax = max(centroids(:,1));
mask = d >= threshold & centroids(:,1) >= xmax - 2*h;
count = nnz(mask);
if count == 0
    yspan = 0;
else
    yspan = max(centroids(mask,2)) - min(centroids(mask,2));
end
rb = struct('count', count, 'yspan', yspan);
end

function monitor_alpha = read_monitor_alpha(run_dir, cycles)
mon = readmatrix(fullfile(run_dir, 'monitorcycle.dat'), 'NumHeaderLines', 1);
monitor_alpha = nan(numel(cycles), 1);
for i = 1:numel(cycles)
    idx = find(mon(:,1) == cycles(i), 1);
    if ~isempty(idx)
        monitor_alpha(i) = mon(idx, 11);
    end
end
end

function T = build_energy_table(run_dir)
mon = readmatrix(fullfile(run_dir, 'monitorcycle.dat'), 'NumHeaderLines', 1);
n_cycle = size(mon, 1);
cycle = mon(:,1);
[E_el, E_d, total_energy] = read_peak_conv_energy(run_dir, n_cycle);
T = table(cycle, E_el, E_d, total_energy);
end

function [E_el, E_d, total_energy] = read_peak_conv_energy(run_dir, n_cycle)
run_name = string(get_last_path_part(run_dir));
log_file = fullfile(run_dir, sprintf('CONV_%s00004.log', run_name));
A = readmatrix(log_file, 'FileType', 'text', 'NumHeaderLines', 1);
iter = A(:,2);
starts = find(iter == 1);
starts = [starts; size(A,1)+1];
E_el = nan(n_cycle,1);
E_d = nan(n_cycle,1);
total_energy = nan(n_cycle,1);
n_groups = min(n_cycle, numel(starts)-1);
for g = 1:n_groups
    idx = starts(g+1) - 1;
    E_el(g) = A(idx,5);
    E_d(g) = A(idx,6);
    total_energy(g) = A(idx,7);
end
end

function name = get_last_path_part(path)
[~, name] = fileparts(path);
end

function write_readme(path, metadata, csv_file, mat_file)
fid = fopen(path, 'w');
if fid < 0
    error('Cannot open README for writing: %s', path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '# reverseBC u=0.12 cyclewise FEM mechanism export\n\n');
fprintf(fid, 'Request: `%s`.\n\n', metadata.request);
fprintf(fid, 'Files:\n');
fprintf(fid, '- `%s`: one row per available cycle, c%d-c%d.\n', csv_file, metadata.cycles(1), metadata.cycles(end));
fprintf(fid, '- `%s`: compact all-cycle element fields.\n', mat_file);
fprintf(fid, '- `mesh_geometry.mat`: copied mesh geometry.\n\n');
fprintf(fid, 'Field definitions:\n');
fprintf(fid, '- `d_elem`, `alpha_bar_elem`, `f_fatigue_elem`, `psi_plus_elem` are element means over Gauss/history data from `psi_fields/cycle_XXXX.mat`.\n');
fprintf(fid, '- Source files store fatigue history as `alpha_elem`; this export aliases it to `alpha_bar_elem`.\n');
fprintf(fid, '- `psi_plus_elem` is the saved per-cycle peak/summary field, not a raw nodal projection.\n');
fprintf(fid, '- The fields are post-cycle history exports. The available VTK nodal fields are unloaded step-5 snapshots and are not used in this scalar CSV.\n\n');
fprintf(fid, 'Monitor note:\n');
fprintf(fid, '- `alpha_bar_monitor_max` comes from `monitorcycle.dat` column `||fat||_inf`.\n');
fprintf(fid, '- It differs from `alpha_bar_elem_max` because monitor output is a solver/internal-state maximum or norm, while `alpha_bar_elem` is an element-averaged field exported from Gauss/history data.\n\n');
fprintf(fid, 'Mesh and parameters:\n');
fprintf(fid, '- Nodes: %d; elements: %d; element type: Q4.\n', metadata.n_node, metadata.n_elem);
fprintf(fid, '- Mesh: %s.\n', metadata.mesh);
fprintf(fid, '- Material/fatigue: %s.\n', metadata.material);
fprintf(fid, '- Loading/BC: %s.\n\n', metadata.loading);
if isfield(metadata, 'diffuse_precrack')
    dp = metadata.diffuse_precrack;
    fprintf(fid, 'Diffuse pre-crack diagnostic:\n');
    fprintf(fid, '- Centered request mask: `%s`; implemented plate mask: `%s`.\n', dp.centered_mask, dp.plate_mask);
    fprintf(fid, '- Material treatment: %s.\n', dp.material_or_void);
    fprintf(fid, '- Initial/fixed profile: %s.\n', dp.profile);
    fprintf(fid, '- Pre-crack support nodes: %d; support elements: %d.\n', dp.n_precrack_nodes, dp.n_precrack_elems);
    if isfield(dp, 'n_precrack_core_nodes')
        fprintf(fid, '- Pre-crack core nodes with `d>=0.95`: %d; core elements: %d.\n', dp.n_precrack_core_nodes, dp.n_precrack_core_elems);
    end
    fprintf(fid, '- Initial `alpha_bar`: %.12g.\n', dp.initial_alpha_bar);
    fprintf(fid, '- Initial `f_alpha` in those elements: %.12g.\n', dp.initial_f_alpha);
    if isfield(dp, 'tol_irrev')
        fprintf(fid, '- GRIPHFiTH `tol_irrev`: %.12g; AT1 penalty coefficient: %.12g.\n', dp.tol_irrev, dp.penalty_irrev);
    end
    fprintf(fid, '- `E_d` includes the fracture/damage energy of the prescribed diffuse pre-crack band; there is no PIDL-style separate irreversibility penalty term in this FEM export.\n\n');
end
if isfield(metadata, 'initial_state_audit')
    ia = metadata.initial_state_audit;
    fprintf(fid, 'Initial-state audit:\n');
    fprintf(fid, '- Pre-crack `d` mean/max at initialization: %.12g / %.12g.\n', ia.precrack_d_mean, ia.precrack_d_max);
    fprintf(fid, '- Pre-crack element-mean `d` mean/max at initialization: %.12g / %.12g.\n', ia.precrack_elem_d_mean, ia.precrack_elem_d_max);
    fprintf(fid, '- Pre-crack `alpha_bar` mean/max at initialization: %.12g / %.12g.\n', ia.precrack_alpha_bar_mean, ia.precrack_alpha_bar_max);
    fprintf(fid, '- Pre-crack `f_alpha` mean/min at initialization: %.12g / %.12g.\n', ia.precrack_f_alpha_mean, ia.precrack_f_alpha_min);
    fprintf(fid, '- Outside-precrack `alpha_bar` mean/max at initialization: %.12g / %.12g.\n', ia.outside_alpha_bar_mean, ia.outside_alpha_bar_max);
    fprintf(fid, '- Energy values are absolute FEM energies unless a CSV column explicitly forms an increment; `E_d` is not shifted by the initial pre-crack energy.\n\n');
end
fprintf(fid, 'Metric definitions:\n');
fprintf(fid, '- Nominal Kt denominator: `%s`.\n', metadata.nominal_region);
fprintf(fid, '- Crack tip: `%s`.\n', metadata.tip_definition);
fprintf(fid, '- Process-zone width: `%s`.\n', metadata.width_definition);
fprintf(fid, '- Right-boundary diagnostic: `%s`.\n', metadata.right_boundary_definition);
clear cleanup;
end
