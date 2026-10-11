function [SOL_STAG_VAR] = vars(SOL_STAG_PAR, args)
%VARS Create staggered-solver variables table
%
%   The following output table columns can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       el_en             = zeros(SOL_STAG_PAR.max_iter, 1);
%       fract_en          = zeros(SOL_STAG_PAR.max_iter, 1);
%       tot_en            = zeros(SOL_STAG_PAR.max_iter, 1);
%       normal_var_en_tot =  ones(SOL_STAG_PAR.max_iter, 1);
%       normal_var_res    =  ones(SOL_STAG_PAR.max_iter, 1);
%       normal_res        =  ones(SOL_STAG_PAR.max_iter, 1);
%       normal_res_displ    = zeros(SOL_STAG_PAR.max_iter, 1);
%       normal_res_pf       = zeros(SOL_STAG_PAR.max_iter, 1);
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
    SOL_STAG_PAR (1, 1) struct
    args.el_en (:, 1) double             = zeros(SOL_STAG_PAR.max_iter, 1);
    args.fract_en (:, 1) double          = zeros(SOL_STAG_PAR.max_iter, 1);
    args.tot_en (:, 1) double            = zeros(SOL_STAG_PAR.max_iter, 1);
    args.normal_var_en_tot (:, 1) double =  ones(SOL_STAG_PAR.max_iter, 1);
    args.normal_var_res (:, 1) double    =  ones(SOL_STAG_PAR.max_iter, 1);
    args.normal_res (:, 1) double        =  ones(SOL_STAG_PAR.max_iter, 1);
    args.normal_res_displ (:, 1) double  = zeros(SOL_STAG_PAR.max_iter, 1);
    args.normal_res_pf (:, 1) double     = zeros(SOL_STAG_PAR.max_iter, 1);
end

SOL_STAG_VAR = struct2table(args);  % copy all input args as table columns

end

