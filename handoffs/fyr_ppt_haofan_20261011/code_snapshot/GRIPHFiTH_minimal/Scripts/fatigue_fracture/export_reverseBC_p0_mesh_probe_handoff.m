function export_reverseBC_p0_mesh_probe_handoff()
% Export the compact reverseBC u=0.12 field bundle requested for the
% field-level P0 mesh-probe row.

root_dir = fileparts(mfilename('fullpath'));
run_dir = fullfile(root_dir, 'SENT_PIDL_12_reverseBC');
psi_dir = fullfile(run_dir, 'psi_fields');
mesh_file = fullfile(root_dir, 'mesh_geometry.mat');

out_dir = fullfile(getenv('USERPROFILE'), 'Downloads', ...
    '_pidl_handoff_v2', 'reverseBC_u12_P0_mesh_probe_2026-05-28');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

cycles = [1 40 70 74];
mesh = load(mesh_file);
n_elem = size(mesh.connectivity, 1);
n_cycle = numel(cycles);

d_elem = zeros(n_elem, n_cycle, 'single');
psi_elem = zeros(n_elem, n_cycle, 'single');
alpha_bar_elem = zeros(n_elem, n_cycle, 'single');
f_alpha_elem = zeros(n_elem, n_cycle, 'single');
cycle_data = struct([]);

for k = 1:n_cycle
    cyc = cycles(k);
    src = fullfile(psi_dir, sprintf('cycle_%04d.mat', cyc));
    if ~isfile(src)
        error('Missing reverseBC psi field file: %s', src);
    end

    s = load(src);
    d_elem(:, k) = single(s.d_elem(:));
    psi_elem(:, k) = single(s.psi_elem(:));
    alpha_bar_elem(:, k) = single(s.alpha_elem(:));
    f_alpha_elem(:, k) = single(s.f_alpha_elem(:));

    cycle_data(k).cycle = cyc; %#ok<AGROW>
    cycle_data(k).d_elem = d_elem(:, k);
    cycle_data(k).psi_elem = psi_elem(:, k);
    cycle_data(k).alpha_bar_elem = alpha_bar_elem(:, k);
    cycle_data(k).f_alpha_elem = f_alpha_elem(:, k);
end

node_coords = mesh.node_coords;
connectivity = mesh.connectivity;
element_centroids = mesh.element_centroids;
element_type = 'Q4';
integration_rule = '2x2 Gauss in source solve; exported fields are element-averaged from Gauss/history data';
source_run_dir = run_dir;
source_psi_dir = psi_dir;
request_note = ['Request 17 / missing P0 row: reverseBC_u12 field-level metric ', ...
    'bundle for SENS_tensile/alignment_mesh_probe_u012_reverseBC.csv.'];

out_mat = fullfile(out_dir, 'reverseBC_u12_full_P0_mesh_probe_handoff.mat');
save(out_mat, 'node_coords', 'connectivity', 'element_centroids', ...
    'element_type', 'integration_rule', 'cycles', 'cycle_data', ...
    'd_elem', 'psi_elem', 'alpha_bar_elem', 'f_alpha_elem', ...
    'source_run_dir', 'source_psi_dir', 'request_note', '-v7.3');

copyfile(mesh_file, fullfile(out_dir, 'mesh_geometry.mat'));

readme_file = fullfile(out_dir, 'README_reverseBC_u12_P0_mesh_probe.md');
fid = fopen(readme_file, 'w');
if fid < 0
    error('Could not open README for writing: %s', readme_file);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '# reverseBC u12 P0 mesh-probe FEM handoff\n\n');
fprintf(fid, 'Purpose: fill the missing P0 row for `SENS_tensile/alignment_mesh_probe_u012_reverseBC.csv`.\n\n');
fprintf(fid, 'Source run: `Scripts/fatigue_fracture/SENT_PIDL_12_reverseBC`.\n');
fprintf(fid, 'Mesh: `mesh_geometry.mat`, 77,730 Q4 elements, 77,900 nodes.\n');
fprintf(fid, 'Cycles: 1, 40, 70, 74.\n\n');
fprintf(fid, 'Main file: `reverseBC_u12_full_P0_mesh_probe_handoff.mat`.\n\n');
fprintf(fid, 'Variables:\n');
fprintf(fid, '- `node_coords`, `connectivity`, `element_centroids`\n');
fprintf(fid, '- `cycles = [1 40 70 74]`\n');
fprintf(fid, '- `d_elem`, `psi_elem`, `alpha_bar_elem`, `f_alpha_elem`: each `77730 x 4`, columns match `cycles`\n');
fprintf(fid, '- `cycle_data(k)`: per-cycle struct with the same four element fields\n\n');
fprintf(fid, 'Note: source files store fatigue history as `alpha_elem`; this handoff aliases it to `alpha_bar_elem`.\n');
clear cleanup;

fprintf('[OK] wrote %s\n', out_mat);
fprintf('[OK] wrote %s\n', readme_file);
end
