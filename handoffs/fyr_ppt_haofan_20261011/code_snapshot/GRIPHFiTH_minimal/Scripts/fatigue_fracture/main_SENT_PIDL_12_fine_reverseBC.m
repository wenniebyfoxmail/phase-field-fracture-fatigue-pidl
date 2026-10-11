% Driver for PIDL fine mesh reverseBC run.
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
disp('        GRIPHFITH (PIDL fine mesh reverseBC, u=0.12)');
disp(currenttime);
disp(' ');

INPUT_SENT_PIDL_12_fine_reverseBC

init_fatigue_fracture
solve_fatigue_fracture

disp(['total computation time: ' num2str(toc(start_tic)) 's'])
