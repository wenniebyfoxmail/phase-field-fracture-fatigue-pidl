% Export cycle-matched FEM mechanism data for SENT_PIDL_12_reverseBC.
%
% Request: cycles [40, 70, 80]. This run penetrated/stopped at cycle 74, so
% cycle 80 is recorded as missing. VTK snapshots are cycle-end step 5
% (unloaded); psi_fields are per-element peak-over-cycle summaries.

clear; clc;

run_dir = fullfile(pwd, 'SENT_PIDL_12_reverseBC');
mesh_file = fullfile(pwd, 'mesh_geometry.mat');
out_dir = fullfile(getenv('USERPROFILE'), 'Downloads', ...
    '_pidl_handoff_v2', 'reverseBC_u12_mechanism');
if ~exist(out_dir, 'dir'), mkdir(out_dir); end

requested_cycles = [40 70 80];
available_cycles = [];
missing_cycles = [];

M = load(mesh_file);
node_coords = M.node_coords;
connectivity = M.connectivity;
connectivity_zero_based = connectivity - 1;
element_centroids = M.element_centroids;
element_type = 'VTK_QUAD / MATLAB quad4 connectivity';
integration_rule = '2x2 Gauss for GRIPHFiTH quad elements; exported quad_weights are area/4 per GP from polygon area';

element_area = quad_area(node_coords, connectivity);
quad_weights = repmat(element_area ./ 4, 1, 4);

cycles = struct([]);
for ci = 1:numel(requested_cycles)
    cyc = requested_cycles(ci);
    psi_file = fullfile(run_dir, 'psi_fields', sprintf('cycle_%04d.mat', cyc));
    vtk_file = fullfile(run_dir, sprintf('fields_%06d_005.vtk', cyc));

    if ~exist(psi_file, 'file') || ~exist(vtk_file, 'file')
        missing_cycles(end+1) = cyc; %#ok<SAGROW>
        fprintf('[MISS] cycle %d: psi=%d vtk=%d\n', cyc, exist(psi_file,'file')==2, exist(vtk_file,'file')==2);
        continue;
    end

    P = load(psi_file);
    V = read_ascii_vtk_fields(vtk_file);

    item = struct();
    item.cycle = cyc;
    item.vtk_file = vtk_file;
    item.psi_file = psi_file;
    item.u_node = single(V.u_node);
    item.u_node_step = int32(5);
    item.u_node_state = 'cycle_end_unloaded_step5';
    item.d_node = single(V.d_node);
    item.d_elem = single(P.d_elem);
    item.alpha_bar_elem = single(P.alpha_elem);
    item.f_fatigue_elem = single(P.f_alpha_elem);
    item.f_alpha_elem = single(P.f_alpha_elem);
    item.psi_plus_elem = single(P.psi_elem);
    item.stress_node = single(V.sigma_node_voigt);
    item.strain_node = single(V.epsilon_node_voigt);
    item.stress_gp = single([]);
    item.strain_gp = single([]);
    item.H_node = single(V.H_node);
    item.alpha_bar_node_projected = single(V.alpha_node);
    item.Dalpha_node_projected = single(V.Dalpha_node);
    item.f_fatigue_node_projected = single(V.f_node);
    item.note = ['stress/strain are nodal L2-projected VTK tensors, not raw Gauss-point fields; ', ...
                 'u_node is saved VTK step 5 unloaded displacement; psi_plus_elem is peak-over-cycle mean over GPs'];

    cycles = [cycles; item]; %#ok<AGROW>
    available_cycles(end+1) = cyc; %#ok<SAGROW>
    fprintf('[OK] cycle %d: nodes=%d elems=%d max_d=%.4g max_alpha=%.4g min_f=%.4g max_psi=%.4g\n', ...
        cyc, size(item.u_node,1), numel(item.d_elem), max(item.d_node), ...
        max(item.alpha_bar_elem), min(item.f_fatigue_elem), max(item.psi_plus_elem));
end

energy_vs_cycle = build_energy_table(run_dir);
energy_csv = fullfile(out_dir, 'energy_vs_cycle.csv');
writetable(energy_vs_cycle, energy_csv);

metadata = struct();
metadata.run_name = 'SENT_PIDL_12_reverseBC';
metadata.run_dir = run_dir;
metadata.requested_cycles = requested_cycles;
metadata.available_cycles = available_cycles;
metadata.missing_cycles = missing_cycles;
metadata.final_cycle_from_monitor = max(energy_vs_cycle.cycle);
metadata.bc = 'fix_X on top+bottom; fix_Y bottom; disp_Y top';
metadata.material = 'AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2';
metadata.loading = 'cyclic R=0, uy_final=0.12, GRIPHFiTH loading branch plus unload; VTK files saved at step 5 unloaded';
metadata.field_caveat = 'cycle 80 unavailable because reverseBC run stopped at penetration cycle 74; stress/strain GP fields are not saved in current artifacts';

out_mat = fullfile(out_dir, 'fem_mechanism_c40_c70_c80.mat');
save(out_mat, 'node_coords', 'connectivity', 'connectivity_zero_based', ...
    'element_centroids', 'element_type', 'integration_rule', 'element_area', ...
    'quad_weights', 'cycles', 'energy_vs_cycle', 'metadata', '-v7.3');

readme_file = fullfile(out_dir, 'README_reverseBC_mechanism.md');
write_readme(readme_file, out_mat, energy_csv, metadata);

fprintf('\nWrote:\n  %s\n  %s\n  %s\n', out_mat, energy_csv, readme_file);

function area = quad_area(node_coords, connectivity)
    n_elem = size(connectivity, 1);
    area = zeros(n_elem, 1);
    for e = 1:n_elem
        xy = node_coords(connectivity(e,:), :);
        x = xy(:,1);
        y = xy(:,2);
        area(e) = 0.5 * abs(sum(x .* y([2:end 1]) - y .* x([2:end 1])));
    end
end

function V = read_ascii_vtk_fields(filename)
    fid = fopen(filename, 'r');
    if fid < 0, error('Cannot open %s', filename); end
    cleaner = onCleanup(@() fclose(fid));

    n_points = [];
    V = struct('u_node', [], 'd_node', [], 'H_node', [], 'alpha_node', [], ...
               'Dalpha_node', [], 'f_node', [], 'epsilon_node_voigt', [], ...
               'sigma_node_voigt', []);

    while true
        line = fgetl(fid);
        if ~ischar(line), break; end
        line = strtrim(line);
        if startsWith(line, 'POINTS')
            parts = split(line);
            n_points = str2double(parts{2});
            fscanf(fid, '%f', [3, n_points]);
        elseif startsWith(line, 'POINT_DATA')
            parts = split(line);
            n_points = str2double(parts{2});
        elseif startsWith(line, 'SCALARS') && ~isempty(n_points)
            parts = split(line);
            raw_name = parts{2};
            fgetl(fid); % LOOKUP_TABLE default
            vals = fscanf(fid, '%f', [n_points, 1]);
            switch raw_name
                case 'd'
                    V.d_node = vals;
                case 'H'
                    V.H_node = vals;
                case 'alpha'
                    V.alpha_node = vals;
                case 'Dalpha'
                    V.Dalpha_node = vals;
                case 'f(alpha)'
                    V.f_node = vals;
            end
        elseif startsWith(line, 'VECTORS u') && ~isempty(n_points)
            vals = fscanf(fid, '%f', [3, n_points])';
            V.u_node = vals(:, 1:2);
        elseif startsWith(line, 'TENSORS epsilon') && ~isempty(n_points)
            vals = fscanf(fid, '%f', [9, n_points])';
            V.epsilon_node_voigt = tensor9_to_voigt(vals);
        elseif startsWith(line, 'TENSORS sigma') && ~isempty(n_points)
            vals = fscanf(fid, '%f', [9, n_points])';
            V.sigma_node_voigt = tensor9_to_voigt(vals);
        end
    end
end

function voigt = tensor9_to_voigt(vals)
    % VTK tensor rows are [xx xy xz yx yy yz zx zy zz].
    xx = vals(:,1);
    xy = 0.5 * (vals(:,2) + vals(:,4));
    yy = vals(:,5);
    voigt = [xx, yy, xy];
end

function T = build_energy_table(run_dir)
    mon = readmatrix(fullfile(run_dir, 'monitorcycle.dat'), 'NumHeaderLines', 1);
    extra = readmatrix(fullfile(run_dir, 'extra_scalars.dat'), 'NumHeaderLines', 1);
    ld = readmatrix(fullfile(run_dir, 'load_displ_SENT_PIDL_12_reverseBC.out'), 'FileType', 'text', 'NumHeaderLines', 1);

    n_cycle = size(mon, 1);
    cycle = mon(:,1);
    max_d = mon(:,8);
    max_alpha_bar = mon(:,11);

    peak_rows = find(ld(:,1) == 4);
    E_el_0p5Fu = nan(n_cycle, 1);
    if numel(peak_rows) >= n_cycle
        peak = ld(peak_rows(1:n_cycle), :);
        E_el_0p5Fu = 0.5 .* peak(:,4) .* peak(:,5);
    end

    [E_el_conv, E_d, total_energy] = read_peak_conv_energy(run_dir, n_cycle);

    f_min = nan(n_cycle, 1);
    max_psi_plus = nan(n_cycle, 1);
    for i = 1:n_cycle
        pf = fullfile(run_dir, 'psi_fields', sprintf('cycle_%04d.mat', cycle(i)));
        if exist(pf, 'file')
            S = load(pf, 'f_alpha_elem', 'psi_elem');
            f_min(i) = min(S.f_alpha_elem);
            max_psi_plus(i) = max(S.psi_elem);
        end
    end

    f_mean = nan(n_cycle,1);
    alpha_bar_mean = nan(n_cycle,1);
    psi_peak_extra = nan(n_cycle,1);
    n_extra = min(size(extra,1), n_cycle);
    f_mean(1:n_extra) = extra(1:n_extra,3);
    alpha_bar_mean(1:n_extra) = extra(1:n_extra,4);
    psi_peak_extra(1:n_extra) = extra(1:n_extra,5);
    max_psi_plus(isnan(max_psi_plus)) = psi_peak_extra(isnan(max_psi_plus));

    E_fatigue_or_history = nan(n_cycle,1);
    fatigue_history_proxy = alpha_bar_mean;

    T = table(cycle, E_el_conv, E_el_0p5Fu, E_d, E_fatigue_or_history, ...
        total_energy, max_d, max_alpha_bar, alpha_bar_mean, f_mean, f_min, ...
        max_psi_plus, fatigue_history_proxy, ...
        'VariableNames', {'cycle','E_el','E_el_0p5Fu','E_d', ...
        'E_fatigue_or_history','total_energy','max_d','max_alpha_bar', ...
        'alpha_bar_mean','f_mean','min_f','max_psi_plus', ...
        'fatigue_history_proxy'});
end

function [E_el, E_d, total_energy] = read_peak_conv_energy(run_dir, n_cycle)
    log_file = fullfile(run_dir, 'CONV_SENT_PIDL_12_reverseBC00004.log');
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

function write_readme(path, out_mat, energy_csv, metadata)
    fid = fopen(path, 'w');
    fprintf(fid, '# reverseBC u=0.12 FEM mechanism export\n\n');
    fprintf(fid, '- MAT: `%s`\n', out_mat);
    fprintf(fid, '- CSV: `%s`\n', energy_csv);
    fprintf(fid, '- Requested cycles: `%s`\n', mat2str(metadata.requested_cycles));
    fprintf(fid, '- Exported cycles: `%s`\n', mat2str(metadata.available_cycles));
    fprintf(fid, '- Missing cycles: `%s`\n\n', mat2str(metadata.missing_cycles));
    fprintf(fid, 'Cycle 80 is missing because the reverseBC run stopped at penetration cycle 74.\n\n');
    fprintf(fid, '## Field caveats\n\n');
    fprintf(fid, '- `u_node`, `d_node`, `stress_node`, and `strain_node` come from `fields_XXXXXX_005.vtk`, the cycle-end unloaded step 5 snapshot.\n');
    fprintf(fid, '- `psi_plus_elem`, `alpha_bar_elem`, and `f_fatigue_elem` come from `psi_fields/cycle_XXXX.mat` and are element means over Gauss points; `psi_plus_elem` is peak-over-cycle.\n');
    fprintf(fid, '- Raw Gauss-point stress/strain were not saved in the available artifacts; `stress_gp` and `strain_gp` are empty.\n');
    fprintf(fid, '- `quad_weights` are reconstructed as `element_area/4` for the 2x2 quadrature rule.\n');
    fclose(fid);
end
