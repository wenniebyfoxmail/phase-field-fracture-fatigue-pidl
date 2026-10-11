function [SOL_JUMP_PAR] = params(args)
%PARAMS Create parameters structure for cycle jump
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
    args.cycl_jump (1,1) logical = false %boolean whether to jump cycles or not
    args.prediction_error_estimation (1,1) logical = false  %boolean whether to estimate prediction error or not (solely for postprocessing purposes)
    args.jumpmethod {mustBeMember(args.jumpmethod, {'fixed', 'rel_error', 'adaptive'})} = 'adaptive' %selection of approach to determine Dn
    args.cycl_jump_parameter_1 double = NaN %first parameter for the cycle jump approach (depending on the chosen method)
    args.cycl_jump_parameter_2 double = NaN %first parameter for the cycle jump approach (depending on the chosen method)
    args.n_stencil (1, 1) double {mustBeInteger, mustBeNonnegative} = 4 %number of cycles computed in between the individual cycle jumps, used for the extrapolation of the fatigue history variable
end

%copy all input args
SOL_JUMP_PAR = args;


%set default parameters for cycle jumping method if it has not been set
if isnan(SOL_JUMP_PAR.cycl_jump_parameter_1)
    switch SOL_JUMP_PAR.jumpmethod
        case 'fixed'
            %cycl_jump_parameter_1 acts as fixed number of cycles to be jumped
            SOL_JUMP_PAR.cycl_jump_parameter_1 = 10;
        case 'rel_error'
            %cycl_jump_parameter_1 acts as maximum allowable relative error
            SOL_JUMP_PAR.cycl_jump_parameter_1 = 1e-6;
        case 'adaptive'
            %cycl_jump_parameter_1 scales allowed increment in stage II
            SOL_JUMP_PAR.cycl_jump_parameter_1 = 1;
        otherwise
            error('cycle jumping method not known')
        
    end
end

if isnan(SOL_JUMP_PAR.cycl_jump_parameter_2)
    switch SOL_JUMP_PAR.jumpmethod
        case 'fixed'
            %cycl_jump_parameter_2 has no function for fixed cycle jump
            SOL_JUMP_PAR.cycl_jump_parameter_2 = NaN;
        case 'rel_error'
            %cycl_jump_parameter_2 acts as maximum allowable Dn
            SOL_JUMP_PAR.cycl_jump_parameter_2 = 1000;
        case 'adaptive'
            %cycl_jump_parameter_2 scales allowed increment in stage III
            SOL_JUMP_PAR.cycl_jump_parameter_2 = 1;
        otherwise
            error('cycle jumping method not known')
        
    end
end


end %function