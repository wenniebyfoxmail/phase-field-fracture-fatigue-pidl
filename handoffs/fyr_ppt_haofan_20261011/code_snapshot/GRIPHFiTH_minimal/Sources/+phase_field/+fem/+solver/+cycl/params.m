function [SOL_CYCL_PAR] = params(args)
%PARAMS Create cyclic-solver parameters structure
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
    args.max_cycle (1,1) double {mustBeInteger, mustBePositive} = 1 %number of cycles to compute at most
    args.da_paraview double {mustBeReal} = 0.0 %increment of (smeared) crack length after which paraview output file is generated
end

%copy all input args
SOL_CYCL_PAR = args;

end %function

