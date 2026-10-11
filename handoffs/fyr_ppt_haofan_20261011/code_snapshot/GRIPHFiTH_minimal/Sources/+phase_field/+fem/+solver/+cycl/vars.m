function [SOL_CYCL_VAR] = vars(SOL_CYCL_PAR, args)
%VARS Create cyclic-solver variables table
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
    SOL_CYCL_PAR (1, 1) struct %structure containing all parameters of the cyclic solver
    args.n_cycle (:, 1) double {mustBeInteger, mustBeNonnegative} = 0 %current cycle count
    args.da_paraview_last double {mustBeReal} = -inf; %variable to track at which crack length the last paraview output file was written
    args.MONITOR (1, 1) struct %structure containing all monitoring variables, see contents below
end

%copy input paramters
SOL_CYCL_VAR = args;

%prepare monitoring struct if requested
SOL_CYCL_VAR.MONITOR.n = []; %n Dn
SOL_CYCL_VAR.MONITOR.u = []; %||u||_1 ||u||_2 ||u||_inf
SOL_CYCL_VAR.MONITOR.d = []; %||d||_1 ||d||_2 ||d||_inf
SOL_CYCL_VAR.MONITOR.fat = []; %||fat||_1 ||fat||_2 ||fat||_inf

end

