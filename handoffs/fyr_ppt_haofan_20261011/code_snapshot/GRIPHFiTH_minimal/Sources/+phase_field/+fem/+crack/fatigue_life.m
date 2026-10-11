function fatigue_life(n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name)
%FATIGUE_LIFE output information for woehler curve
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
    n_cycle (1, 1) double   %current cycle number
    sys (1, 1) handle       %system handle
    CRACK_PAR (1, 1) struct   %Parameters of the crack growth rate tracking
    SOL_STEP_PAR (1, 1) struct %Parameters of the step-wise solver
    example_name {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
end


%get cross-section area in case of bar specimen
if strcmp(CRACK_PAR.specimen,'bar')
    A = sys.GEOM.L * sys.GEOM.t;
else
    A = 1;
end

%compute nominal stress for Woehler curve
S_max = SOL_STEP_PAR.ty_final/A;

%output data
phase_field.mex.output.dat_output([n_cycle], {'N'}, [S_max], {'S_max'}, [example_name filesep 'fatigue_life.dat']);

end
