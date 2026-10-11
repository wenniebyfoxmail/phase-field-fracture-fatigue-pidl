function extrapolation_error(sys, SOL_JUMP_PAR, SOL_JUMP_VAR, p_field, example_name, n_cycle)
%EXTRAPOLATION_ERROR estimate errors of the system extrapolation
%
% sys                   system handle
% SOL_JUMP_PAR          structure containing all parameters of the cycle jump
% SOL_JUMP_VAR          structure containing all variables of the cycle jump
% p_field               phase-field solution array
% example_name          directory where the output should be stored
% n_cycle               current cycle count

% Copyright (C) 2021 ETH Zurich, SIS ID and CompMech D-MAVT
%
% Licensed under the Apache License, Version 2.0 (the "License");
% you may not use this file except in compliance with the License.
% You may obtain a copy of the License at
%
%    http://www.apache.org/licenses/LICENSE-2.0
%
% Unless required by applicable law or agreed to in writing, software
% distributed under the License is distributed on an "AS IS" BASIS,
% WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
% See the License for the specific language governing permissions and
% limitations under the License.


% =========================================================================
%compute prediction error field and norms of it
fat_predicted = SOL_JUMP_VAR.ERROR_PREDICTIONS(:,:,1:end);
fat_predicted(fat_predicted==0) = NaN; %since we enforce Dfat=0 for negative predictions, which might otherwise lead to spurious error estimations
fat_computed = SOL_JUMP_VAR.HISTORY.fat(:,:,2:end);

epsilon_fat = 1/(SOL_JUMP_PAR.n_stencil-1) * sum( (fat_predicted - fat_computed) ./ fat_computed , 3);
epsilon_fat(isnan(epsilon_fat)) = 0;
epsilon_fat_Linf = norm(epsilon_fat(:), "inf");
epsilon_fat_L1 = norm(epsilon_fat(:), 1);
epsilon_fat_L2 = norm(epsilon_fat(:), 2);


% =========================================================================
%output error field

%prepare the L2-projection for the postprocessing
[epsilon_fat_L2_proj, ~] = phase_field.mex.fem.processing.L2_PROJECTION(sys.MESH, sys.DOFS, sys.GEOM.t, sys.num_materials, sys.QUADRATURE, sys.CC, p_field, 1, epsilon_fat);

%write paraview output file
phase_field.output.paraview_step([example_name filesep 'predictionerr_' sprintf('%06d', n_cycle) '.vtk'] ,sys.STIFFNESS_MATRIX, sys.MESH, {'d'}, {p_field}, {'epsilon_fat'}, {epsilon_fat_L2_proj});


% =========================================================================
%output text data
Dn = SOL_JUMP_VAR.jumps(end,2);
phase_field.mex.output.dat_output(...
        [SOL_JUMP_VAR.jumps(end,1) SOL_JUMP_VAR.jumps(end,2) n_cycle], {'n_jump' 'Dn' 'n'}, ...
        [epsilon_fat_Linf epsilon_fat_L1 epsilon_fat_L2 epsilon_fat_Linf/Dn epsilon_fat_L1/Dn epsilon_fat_L2/Dn], ...
        {'||eps_fat||_inf' '||eps_fat||_1' '||eps_fat||_2' '||eps_fat||_inf/DN' '||eps_fat||_1/DN' '||eps_fat||_2/DN'}, ...
        [example_name filesep 'cyclejump_predictionerr.dat']);


end %function
