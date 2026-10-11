dep_path = genpath(fullfile('..', '..', 'Dependencies/')); addpath(dep_path)
pkg_path = fullfile('..', '..', 'Sources/'); addpath(pkg_path)
ss_paths = {'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/AMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/COLAMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/CCOLAMD/MATLAB','C:/SuiteSparse/SuiteSparse-dev/CAMD/MATLAB'};
for i = 1:numel(ss_paths), if exist(ss_paths{i}, 'dir'), addpath(ss_paths{i}); end; end

run INPUT_SENT_PIDL_12_reverseBC
init_fatigue_fracture
solve_fatigue_fracture
