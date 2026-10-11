function [SOL_STEP_PAR] = params(args)
%PARAMS Create step-solver parameters structure
%
%   The following output structure fields can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       n_step        = 3;
%       n_step_burnin = 0;
%
%       ux_final = 1.0;
%       uy_final = 0.0;
%
%       tx_final = 0.0;
%       ty_final = 0.0;
%
%   The following output structure fields are additionaly computed from the input
%   arguments as follows:
%
%       ux_increment = ux_final / (n_step - n_step_burnin);  % increment in x direction
%       uy_increment = uy_final / (n_step - n_step_burnin);  % increment in y direction
%
%       tx_increment = tx_final / (n_step - n_step_burnin);  % increment of tractions in x direction
%       ty_increment = ty_final / (n_step - n_step_burnin);  % increment of tractions in y direction
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
    args.n_step (1, 1) double {mustBeInteger, mustBePositive} = 3
    args.n_step_burnin (1, 1) double {mustBeInteger, mustBeNonnegative} = 0
    args.line_search (1,1) logical = false
    args.loading {mustBeMember(args.loading, {'monotonic' 'cyclic'})} = 'monotonic'
    args.discretization {mustBeMember(args.discretization, {'loading+unloading' 'loading'})} = 'loading+unloading'
    args.output_freq (1, 1) double {mustBeReal} = 1
    args.ux_final (1, 1) double {mustBeReal} = 0.0
    args.uy_final (1, 1) double {mustBeReal} = 0.0
    args.tx_final (1, 1) double {mustBeReal} = 0.0
    args.ty_final (1, 1) double {mustBeReal} = 0.0
    args.R (1, 1) double {mustBeReal} = 0.0
end


%copy all input args
SOL_STEP_PAR = args;

%obtain step division
n_step_div = args.n_step - args.n_step_burnin;

%get load function array
if strcmp(args.loading,'monotonic')
    loadfun = linspace(0,1,n_step_div+1);

elseif strcmp(args.loading,'cyclic')

    %make sure that number of load increments is odd
    if mod(n_step_div,2) == 1
        n_step_div = n_step_div + 1;
        SOL_STEP_PAR.n_step = SOL_STEP_PAR.n_step + 1;
        warning('adjusted step count by +1 to ensure that maximum point is met');
    end
    %make sure that at least three load increments are specified
    if n_step_div < 3
        n_step_div = 3;
        SOL_STEP_PAR.n_step = 3;
        warning('adjusted step count to 3 to ensure that loading and unloading phases can be resolved properly');
    end
    
    %load curve always has maximum of 1 and is later scaled by ty_final
    if SOL_STEP_PAR.R < -1
        warning('for loadings predominantly in compressive range with negative txy_final, instead invert sign of R')
    end
    if SOL_STEP_PAR.R == 1
        warning('for R=1, there is no cyclic loading')
    end
    loadfactor_min = SOL_STEP_PAR.R;
    loadfactor_max = 1;
    
    %use sine-curve for smoother loading/ unloading increments
    ramp_up = linspace(loadfactor_min,loadfactor_max,n_step_div/2+1);
    ramp_down = flip(ramp_up);
    loadfun = [ramp_up ramp_down(2:end)];
    
    %substitute zero loadings to prevent numerical issues
    if any(loadfun == 0.0)
        loadfun(loadfun==0) = 1e-6;
    end
    

    %change discretization of loading- and unloading phases if requested
    if strcmp(SOL_STEP_PAR.discretization,'loading')
        
        %get points of the unloading phase
        unloading = [0 sign(loadfun(2:end)).*diff(loadfun)]<0;
        
        %do not delete the very last point to make sure that cycle is fully resolved
        unloading(end) = false;

        %do not delete points close to zero to make sure that change of loading/ unloading is correctly resolved
        unloading(abs(loadfun(1:end-1))<1e-4) = false;
        
        %delete points of the unloading phase
        loadfun(unloading) = [];
    
        %adjust number of steps
        SOL_STEP_PAR.n_step = SOL_STEP_PAR.n_step - nnz(unloading);
        disp(['eliminated ' num2str(nnz(unloading)) ' points of the unloading phase'])
    
    end

    %make sure the load increments match the number of points
    if SOL_STEP_PAR.n_step ~= length(diff(loadfun))
        SOL_STEP_PAR.n_step = length(diff(loadfun));
    end

    % %create plot with the load curve discretization
    % if SOL_STEP_PAR.tx_final ~=0
    %     F_max = SOL_STEP_PAR.tx_final;
    % elseif SOL_STEP_PAR.ty_final ~=0
    %     F_max = SOL_STEP_PAR.ty_final;
    % end
    % plot_steps = 1:SOL_STEP_PAR.n_step;
    % scatter(plot_steps, F_max*loadfun(2:end))
    % grid on; hold on;
    % yline([F_max*loadfactor_min, F_max*loadfactor_max],':')
    % xlabel('load steps'); ylabel('load factors')
    
end


%transform into displacement increments
SOL_STEP_PAR.ux_increment = args.ux_final * diff(loadfun);
SOL_STEP_PAR.uy_increment = args.uy_final * diff(loadfun);

SOL_STEP_PAR.tx_increment = args.tx_final * loadfun(2:end);
SOL_STEP_PAR.ty_increment = args.ty_final * loadfun(2:end);


