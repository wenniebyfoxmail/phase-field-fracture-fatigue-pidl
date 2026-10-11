% Driver for reverseBC u=0.12 diffuse pre-crack diagnostic.
start_tic = tic;
clearvars -except start_tic
close all
clc
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

currenttime = datetime("now");
disp(' ');
disp('        GRIPHFITH (reverseBC u=0.12 diffuse pre-crack)');
disp(currenttime);
disp(' ');

INPUT_SENT_PIDL_12_diffuse_precrack_reverseBC

init_fatigue_fracture

% PIDL-like pre-crack fatigue history initialization. The phase-field d=1
% nodes are fixed through non_hom_pf; alpha_bar is initialized once here.
history_vars_old(precrack_elems,:,2) = 1.0;
history_vars_old(precrack_elems,:,3) = 0.0;
history_vars_old(precrack_elems,:,4) = (2 * sys.MAT_CHAR(1).alpha_T / (1.0 + sys.MAT_CHAR(1).alpha_T)) ^ sys.MAT_CHAR(1).p;

save([example_name filesep 'diffuse_precrack_metadata.mat'], ...
    'diffuse_precrack_metadata', 'precrack_nodes', 'precrack_elems', 'precrack_centroids');

solve_fatigue_fracture

disp(['total computation time: ' num2str(toc(start_tic)) 's'])
