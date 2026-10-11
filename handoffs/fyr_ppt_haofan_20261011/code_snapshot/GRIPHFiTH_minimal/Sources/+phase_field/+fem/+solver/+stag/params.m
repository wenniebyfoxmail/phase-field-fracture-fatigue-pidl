function [SOL_STAG_PAR] = params(args)
%PARAMS Create staggered-solver parameters structure
%
%   The following output structure fields can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       tol      = 1e-4;
%       max_iter = 1000;
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
    args.tol (1, 1) double {mustBePositive} = 1e-4
    args.max_iter (1, 1) double {mustBeInteger, mustBePositive} = 1000
end

SOL_STAG_PAR = args;  % copy all input args

end

