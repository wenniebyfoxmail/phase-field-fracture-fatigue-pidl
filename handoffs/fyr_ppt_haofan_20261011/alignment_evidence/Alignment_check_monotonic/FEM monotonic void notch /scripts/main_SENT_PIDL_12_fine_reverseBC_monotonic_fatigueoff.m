% Driver for PIDL-aligned monotonic SENT with fatigue degradation disabled.
start_tic = tic;
clearvars -except start_tic pidl_mono_uy_final pidl_mono_n_step pidl_mono_uy_steps;
close all; clc; format shortE;

pidl_mono_example_name = 'SENT_PIDL_12_fine_reverseBC_monotonic_fatigueoff';
pidl_mono_alpha_T = 1e10;
if ~exist('pidl_mono_uy_final', 'var')
    pidl_mono_uy_final = 0.12;
end
if ~exist('pidl_mono_n_step', 'var')
    pidl_mono_n_step = 8;
end

dep_path = genpath(fullfile('..', '..', 'Dependencies/')); addpath(dep_path)
pkg_path = fullfile('..', '..', 'Sources/'); addpath(pkg_path)
ss_paths = {'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/AMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/COLAMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/CCOLAMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/CAMD/MATLAB'};
for i = 1:numel(ss_paths), if exist(ss_paths{i}, 'dir'), addpath(ss_paths{i}); end; end

disp(' ');
disp('PIDL-aligned monotonic SENT, fatigue off');
disp(datetime("now"));
disp(' ');

INPUT_SENT_PIDL_12_fine_reverseBC_monotonic
init_fatigue_fracture
solve_fatigue_fracture
disp(['total computation time: ' num2str(toc(start_tic)) 's'])
