function [SOL_JUMP_VAR] = vars(SOL_JUMP_PAR, MESH, QUADRATURE, args)
%VARS Create variables structure for cycle jump
%
% see description of the input arguments below

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

arguments
    SOL_JUMP_PAR (1, 1) struct %structure with all parameters of the cycle jump
    MESH (1, 1) struct %stucture containing the mesh
    QUADRATURE (1, 1) struct %structure containing the quadrature
    args.jumps (:, 3) double {mustBeInteger, mustBeNonnegative} = zeros(3,3) %array to monitor the cycle jumps
    args.n_resolved (1, 1) double {mustBeInteger, mustBeNonnegative} = 0 %number of explicitly computed cycles in total
    args.HISTORY (1, 1) struct %history variables used for the system state prediction
    args.RESTORE (1, 1) struct %sturcture storing a state prior to the cycle jump (in case trial-cycle cannot be accepted)
    args.ERROR_PREDICTIONS (:, :) double = [] %array to monitor the system state prediction error estimate (if requested)
end

%copy input paramters
SOL_JUMP_VAR = args;

%only allocate memory if cycle jumping is activated
if SOL_JUMP_PAR.cycl_jump

    %initialize jumps stats
    SOL_JUMP_VAR.jumps(end,:) = [1 0 1];
    
    %set up history struct acting as basis for the extrapolation
    SOL_JUMP_VAR.HISTORY.n = zeros(1, SOL_JUMP_PAR.n_stencil);
    SOL_JUMP_VAR.HISTORY.fat = zeros(MESH.num_elem, QUADRATURE.num_gauss_pts, SOL_JUMP_PAR.n_stencil);

    %optional prediction error estimation
    if SOL_JUMP_PAR.prediction_error_estimation
        SOL_JUMP_VAR.ERROR_PREDICTIONS = zeros(MESH.num_elem, QUADRATURE.num_gauss_pts, SOL_JUMP_PAR.n_stencil-1);
    end

end

end %function

