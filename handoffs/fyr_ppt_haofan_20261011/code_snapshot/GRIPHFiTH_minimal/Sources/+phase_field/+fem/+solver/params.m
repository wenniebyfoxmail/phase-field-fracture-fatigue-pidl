function [SOL_PAR] = params(args)
%PARAMS Create solver parameters structure
%
%   The following output structure fields can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       tol_displ   = 1e-6;
%       tol_p_field = 1e-6;
%
%       max_iter_displ = 500;
%       max_iter_pf    = 500;
%
%   The following output structure fields are additionaly computed from the input
%   arguments:
%
%       penalty_irrev
%       penalty_recov
%
%   The following keyword arguments are used to compute `penalty_irrev` and
%   `penalty_recov` output fields and can be set, otherwise, are set with default
%   values:
%
%       L_rec            = 0;
%       tol_AT1_recovery = 1e-3;
%       tol_irrev        = 1e-3;
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
    args.tol_displ (1, 1) double {mustBePositive} = 1e-6
    args.tol_p_field (1, 1) double {mustBePositive} = 1e-6
    args.max_iter_displ (1, 1) double {mustBeInteger, mustBePositive} = 500
    args.max_iter_pf (1, 1) double {mustBeInteger, mustBePositive} = 500
end

SOL_PAR.tol_displ = args.tol_displ;
SOL_PAR.tol_p_field = args.tol_p_field;
SOL_PAR.max_iter_displ = args.max_iter_displ;
SOL_PAR.max_iter_pf = args.max_iter_pf;

end

