function [SOL_STEP_VAR] = post_iter_update(...
    i_step, SOL_STEP_VAR,...
    STIFFNESS_MATRIX, displ, NODE_BOUNDARIES, num_node,...
    SOL_STEP_PAR, example_name...
)
%POST_ITER_UPDATE Step-iteration post processing vectors update
%   ...

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
    i_step (1, 1) double {mustBeInteger, mustBePositive}
    SOL_STEP_VAR (:, 4) table
    STIFFNESS_MATRIX (1, 1) struct
    displ (:, 1) double
    NODE_BOUNDARIES (1, 1) struct
    num_node (1, 1) double {mustBeInteger, mustBePositive}
    SOL_STEP_PAR (1, 1) struct
    example_name {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
end

%get previous displacement
if (i_step > 1)
    ux_prev = SOL_STEP_VAR.u_X(i_step-1);
    uy_prev = SOL_STEP_VAR.u_Y(i_step-1);
else
    ux_prev = 0;
    uy_prev = 0;
end

%get forces and displacement
SOL_STEP_VAR.F_X(i_step) = - sum(STIFFNESS_MATRIX.KK(NODE_BOUNDARIES.fix_X, :) * displ);
SOL_STEP_VAR.F_Y(i_step) = - sum(STIFFNESS_MATRIX.KK(NODE_BOUNDARIES.fix_Y + num_node, :) * displ);
SOL_STEP_VAR.u_X(i_step) = ux_prev + SOL_STEP_PAR.ux_increment(i_step);
SOL_STEP_VAR.u_Y(i_step) = uy_prev + SOL_STEP_PAR.uy_increment(i_step);


%output data
phase_field.mex.output.dat_output(...
    i_step,...
    {'step'},...
    [SOL_STEP_VAR.u_X(i_step), SOL_STEP_VAR.F_X(i_step), SOL_STEP_VAR.u_Y(i_step), SOL_STEP_VAR.F_Y(i_step)],...
    {'u_x', 'F_x', 'u_y', 'F_y'},...
    [example_name filesep 'load_displ_' example_name '.out']...
);

end

