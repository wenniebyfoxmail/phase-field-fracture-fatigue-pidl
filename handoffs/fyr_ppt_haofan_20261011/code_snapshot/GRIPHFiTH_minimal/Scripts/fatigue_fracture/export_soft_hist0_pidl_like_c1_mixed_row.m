function export_soft_hist0_pidl_like_c1_mixed_row()
% Request 21 extra export: explicit old/PIDL-like mixed c1 timing row.

src_dir = fullfile(getenv('USERPROFILE'), 'Downloads', '_pidl_handoff_v2', ...
    'reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29');
src_file = fullfile(src_dir, 'state_timing_element_fields.mat');
if exist(src_file, 'file') ~= 2
    src_file = fullfile(getenv('USERPROFILE'), 'OneDrive - University of Cambridge', 'PIDL result', ...
        '_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29', ...
        'state_timing_element_fields.mat');
end
if exist(src_file, 'file') ~= 2
    error('State timing MAT not found. Run export_reverseBC_soft_hist0_state_timing first.');
end

S = load(src_file, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'state_label', 'd_elem', 'alpha_bar_elem', 'f_fatigue_elem', ...
    'psi_plus_peak_to_date_elem', 'metadata');
labels = cellstr(S.state_label);
idx = find(strcmp(labels, 'cycle1_unloaded_post_history_refresh'), 1);
if isempty(idx)
    error('cycle1_unloaded_post_history_refresh not found in state timing MAT.');
end

node_coords = S.node_coords;
connectivity = S.connectivity;
element_centroids = S.element_centroids;
element_area = S.element_area;
state_label = "pidl_like_c1_mixed_unloaded_history_peak_psi";
d_elem = S.d_elem(:, idx);
alpha_bar_elem = S.alpha_bar_elem(:, idx);
f_fatigue_elem = S.f_fatigue_elem(:, idx);
psi_plus_elem = S.psi_plus_peak_to_date_elem(:, idx);
psi_plus_peak_to_date_elem = psi_plus_elem;

metadata = struct();
metadata.request = 'docs/handovers/windows_fem_inbox.md Request 21 extra export';
metadata.source_state_timing_file = src_file;
metadata.convention = 'damage/history/f from cycle1_unloaded_post_history_refresh; psi_plus from cycle1 psi_plus_peak_to_date';
metadata.source_metadata = S.metadata;

T = table(state_label, ...
    max(double(d_elem)), max(double(alpha_bar_elem)), min(double(f_fatigue_elem)), max(double(psi_plus_elem)), ...
    'VariableNames', {'state_label','d_max','alpha_bar_max','f_fatigue_min','psi_plus_peak_to_date_max'});

out_csv = fullfile(src_dir, 'pidl_like_c1_mixed_row.csv');
out_mat = fullfile(src_dir, 'pidl_like_c1_mixed_row.mat');
writetable(T, out_csv);
save(out_mat, 'node_coords', 'connectivity', 'element_centroids', 'element_area', ...
    'state_label', 'd_elem', 'alpha_bar_elem', 'f_fatigue_elem', ...
    'psi_plus_elem', 'psi_plus_peak_to_date_elem', 'T', 'metadata', '-v7.3');

dst_dir = fullfile(getenv('USERPROFILE'), 'OneDrive - University of Cambridge', 'PIDL result', ...
    '_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29');
if exist(dst_dir, 'dir') == 7
    copyfile(out_csv, fullfile(dst_dir, 'pidl_like_c1_mixed_row.csv'));
    copyfile(out_mat, fullfile(dst_dir, 'pidl_like_c1_mixed_row.mat'));
end

fprintf('Wrote PIDL-like mixed c1 row:\n  %s\n  %s\n', out_csv, out_mat);
end
