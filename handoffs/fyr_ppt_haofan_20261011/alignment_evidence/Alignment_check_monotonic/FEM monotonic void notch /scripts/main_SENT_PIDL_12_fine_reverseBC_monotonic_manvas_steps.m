% Driver for PIDL-aligned monotonic SENT using the Manvas/Mac uy sequence.
start_tic = tic;
clearvars -except start_tic;
close all; clc; format shortE;

pidl_mono_example_name = 'SENT_PIDL_12_fine_reverseBC_monotonic_manvas_steps';
pidl_mono_alpha_T = 0.5;
pidl_mono_uy_steps = [ ...
    0.025, 0.050, 0.075, 0.100, 0.105, 0.110, 0.115, 0.120, ...
    0.125, 0.130, 0.135, 0.140, 0.145, 0.150, 0.155, 0.160, ...
    0.165, 0.170, 0.175, 0.180, 0.185, 0.190, 0.195, 0.200 ...
];

dep_path = genpath(fullfile('..', '..', 'Dependencies/')); addpath(dep_path)
pkg_path = fullfile('..', '..', 'Sources/'); addpath(pkg_path)
ss_paths = {'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/AMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/COLAMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/CCOLAMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/CAMD/MATLAB'};
for i = 1:numel(ss_paths), if exist(ss_paths{i}, 'dir'), addpath(ss_paths{i}); end; end

disp(' ');
disp('PIDL-aligned monotonic SENT, Manvas/Mac uy steps');
disp(datetime("now"));
disp(' ');

INPUT_SENT_PIDL_12_fine_reverseBC_monotonic
init_fatigue_fracture
solve_fatigue_fracture
disp(['total computation time: ' num2str(toc(start_tic)) 's'])
