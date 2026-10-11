% Driver for Request 21 n_step=3 soft-hist0 reverseBC diagnostic.
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

disp(' ');
disp('        GRIPHFITH (reverseBC u=0.12 soft diffuse pre-crack hist0, nstep3)');
disp(datetime("now"));
disp(' ');

INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_nstep3
init_fatigue_fracture
initialize_soft_hist0_request21_state
solve_fatigue_fracture
disp(['total computation time: ' num2str(toc(start_tic)) 's'])
