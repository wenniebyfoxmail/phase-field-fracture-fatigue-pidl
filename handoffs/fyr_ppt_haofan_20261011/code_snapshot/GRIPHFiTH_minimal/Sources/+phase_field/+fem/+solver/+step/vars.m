function [SOL_STEP_VAR] = vars(SOL_STEP_PAR, args)
%VARS Create step-solver variables table
%
%   The following output table columns can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       F_X = zeros(SOL_STEP_PAR.n_step,1);
%       F_Y = zeros(SOL_STEP_PAR.n_step,1);
%       u_X = zeros(SOL_STEP_PAR.n_step,1);
%       u_Y = zeros(SOL_STEP_PAR.n_step,1);
%

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
    SOL_STEP_PAR (1, 1) struct
    args.F_X (:, 1) double = zeros(SOL_STEP_PAR.n_step, 1);
    args.F_Y (:, 1) double = zeros(SOL_STEP_PAR.n_step, 1);
    args.u_X (:, 1) double = zeros(SOL_STEP_PAR.n_step, 1);
    args.u_Y (:, 1) double = zeros(SOL_STEP_PAR.n_step, 1);
end

SOL_STEP_VAR = struct2table(args);  % copy all input args as table columns

end

