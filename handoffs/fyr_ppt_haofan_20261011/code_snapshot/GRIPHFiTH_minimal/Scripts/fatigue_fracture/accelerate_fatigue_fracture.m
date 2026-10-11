% Copyright (C) 2021-2022 ETH Zurich, SIS ID and CompMech D-MAVT
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

% this script implements the adaptive acceleration scheme proposed in
% Heinzmann et al. (2024): An adaptive acceleration scheme for phase-field fatigue computations
% https://doi.org/10.48550/arXiv.2404.07003

% =========================================================================
%   PREPARATION
% =========================================================================

acceleration_tic = tic;

%count up explicitly computed cycles for statistics (here this counts the high-fidelity cycles from solve_fatigue_fracture)
SOL_JUMP_VAR.n_resolved = SOL_JUMP_VAR.n_resolved + 1;
phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle], {'n'}, [SOL_JUMP_VAR.n_resolved], {'n_resolved'}, [example_name filesep 'explicitcycles.dat']);


%save last n_stencil values of the state variables and their cycle count to act as basis for the extrapolation
for n_state=1:SOL_JUMP_PAR.n_stencil-1
    SOL_JUMP_VAR.HISTORY.n(1,n_state) = SOL_JUMP_VAR.HISTORY.n(1,n_state+1);
    SOL_JUMP_VAR.HISTORY.fat(:,:,n_state) = SOL_JUMP_VAR.HISTORY.fat(:,:,n_state+1);
end
SOL_JUMP_VAR.HISTORY.n(1,end) = SOL_CYCL_VAR.n_cycle;
SOL_JUMP_VAR.HISTORY.fat(:,:,end) = history_vars_old(:,:,2);


% =========================================================================
%   ESTIMATE EXTRAPOLATION ERROR
% =========================================================================
if (SOL_JUMP_PAR.prediction_error_estimation) && (SOL_CYCL_VAR.n_cycle>SOL_JUMP_PAR.n_stencil) && (SOL_CYCL_VAR.n_cycle==(SOL_JUMP_VAR.jumps(end,3)+SOL_JUMP_PAR.n_stencil-1))
    
    disp([' evaluating prediction error for last cycle jump at cycle ', num2str(SOL_JUMP_VAR.jumps(end,1)) ' with Dn=' num2str(SOL_JUMP_VAR.jumps(end,2))]);
    
    %estimate error of the fatigue history variable and output it
    phase_field.fem.solver.cycl_jump.extrapolation_error(sys, SOL_JUMP_PAR, SOL_JUMP_VAR, p_field, example_name, SOL_CYCL_VAR.n_cycle);
    
end


% =========================================================================
%   CHECK FOR CURRENT CYCLE COUNT
% =========================================================================
%only jump if required n_stencil cycles has been resolved explicitly since last jump
if SOL_CYCL_VAR.n_cycle>=(SOL_JUMP_VAR.jumps(end,3)+SOL_JUMP_PAR.n_stencil-1)
    
    % =========================================================================
    %   DETERMINE N_JUMP BASED ON METHOD
    % =========================================================================
    
    %initialize variables
    Dn = 0;
    cycl_jump_stage = 0;
    DLambda_jump = 0;
    DLambda_predicted = 0;

    %choose method for cycle jumping
    switch SOL_JUMP_PAR.jumpmethod

        % =========================================================================
        %fixed cycle jump
        case 'fixed'
            
            %set fixed Dn
            Dn = SOL_JUMP_PAR.cycl_jump_parameter_1;

        % =========================================================================
        %cycle jump based on maximum relative error estimate
        % [Seleš et al. (2021): A general phase-field model for fatigue failure in brittle and ductile solids, https://doi.org/10.1007/s00466-021-01996-5]
        case 'rel_error'

            %compute incremental changes of the fatigue history variable
            Theta_12 = SOL_JUMP_VAR.HISTORY.fat(:,:,end-1) - SOL_JUMP_VAR.HISTORY.fat(:,:,end-2);
            Theta_23 = SOL_JUMP_VAR.HISTORY.fat(:,:,end) - SOL_JUMP_VAR.HISTORY.fat(:,:,end-1);
            
            %obtain feasible cycle jump for each individual Gauss point
            Dn_GP = abs(Theta_23)./(abs(Theta_23 - Theta_12));
            
            %find minimum feasible cycle jump
            Dn = round(min(Dn_GP(:))*SOL_JUMP_PAR.cycl_jump_parameter_1);
            
            %check for maximum allowed value of Dn
            if Dn > SOL_JUMP_PAR.cycl_jump_parameter_2
                Dn = SOL_JUMP_PAR.cycl_jump_parameter_2;
            end
            
        % =========================================================================
        %cycle jump based on maximum estimated crack growth during cycle jump
        case 'adaptive'
            
            %determine stage
            if max(SOL_CYCL_VAR.MONITOR.fat(:,3)) < sys.MAT_CHAR(1).alpha_T
                %stage I: pre-fatigue impact
                cycl_jump_stage = 1;
                
                %max of alpha_bar for each of the cycles
                Lambda = SOL_CYCL_VAR.MONITOR.fat(:,3);
                DLambda_jump = sys.MAT_CHAR(1).alpha_T - Lambda(end);
            end
            
            if (max(SOL_CYCL_VAR.MONITOR.fat(:,3))>=sys.MAT_CHAR(1).alpha_T) && (max(SOL_CYCL_VAR.MONITOR.d(:,3)) < 0.99)
                %stage II: fatigue crack nucleation
                cycl_jump_stage = 2;
                
                %max of phase-field for each of the cycles
                Lambda = SOL_CYCL_VAR.MONITOR.d(:,3);
                DLambda_jump = SOL_JUMP_PAR.cycl_jump_parameter_1*0.02;
            end

            if (max(SOL_CYCL_VAR.MONITOR.fat(:,3))>=sys.MAT_CHAR(1).alpha_T) && (max(SOL_CYCL_VAR.MONITOR.d(:,3)) >= 0.99)
                %stage III: fatigue crack growth
                cycl_jump_stage = 3;
                
                %smeared crack length for each of the cycles
                Lambda = CRACK_VAR.crack_regularized(2:end,3); %2:end since the first row was the initial state (might case issues otherwise if we start in stage III)
                DLambda_jump = SOL_JUMP_PAR.cycl_jump_parameter_2*sys.MAT_CHAR(1).ell/2;
            end

            %obtain Dn based on current computation stage
            if cycl_jump_stage ~= 0
                %get cycle counts
                n = SOL_CYCL_VAR.MONITOR.n(:,1);

                %perform LLSQ fit (n and Lambda are directly subtracted, giving a more favourable data set)
                if length(n)<3*SOL_JUMP_PAR.n_stencil
                    x = n(:) - n(end);
                    y = Lambda(:) - Lambda(end);
                else
                    x = n(end-(3*SOL_JUMP_PAR.n_stencil-1):end) - n(end);
                    y = Lambda(end-(3*SOL_JUMP_PAR.n_stencil-1):end) - Lambda(end);
                end
                
                %use quadratic ansatz to determine Dn
                V = [x.^2 x ones(size(x))];
                p = V\y;
                discriminant = p(2)^2 - 4*p(1)*(p(3)-DLambda_jump);
                Dn = (-p(2) + sqrt(discriminant) )/(2*p(1));
                
                %if equation has no solution (imaginary Dn/ negative discriminant), fall back to quadratic approximation
                if discriminant <= 0
                    Dn_old = Dn; %just for output purposes
                    V = [x ones(size(x))];
                    p = V\y;
                    p = [0; p];
                    Dn = (DLambda_jump - p(3)) / p(2);
                    phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle], {'n'}, [Dn_old Dn p(1) p(2) p(3)], {'Dn' 'Dn_lin' 'Lambda2' 'Lambda1' 'Lambda0'}, [example_name filesep 'cyclejump_linear.dat']);
                end
                
                %if equation has negative solution (Lambda is not monotonically increasing), fall back to conservative jump
                if Dn < 0
                    Dn_old = Dn; %just for output purposes
                    Dn = SOL_JUMP_VAR.jumps(end,2) / 2; %take half of the last accepted cycle jump
                    p = [0; 0; 0];
                    phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle], {'n'}, [Dn_old Dn p(1) p(2) p(3)], {'Dn' 'Dn_con' 'Lambda2' 'Lambda1' 'Lambda0'}, [example_name filesep 'cyclejump_conservative.dat']);
                end
                
                %round obtained Dn to nearest integer
                Dn = round(Dn);

                %predict change of Lambda based on fitted ansatz
                DLambda_predicted = p(1)*Dn^2 + p(2)*Dn + p(3);
            end

    end %switch SOL_JUMP_PAR.jumpmethod

    % =========================================================================
    %   JUMP CYCLES (makes only sense for Dn>1 since the trial-cycle is in place)
    % =========================================================================
    if Dn > 1
        jump_cycles;
        
        %check whether the jump can be accepted
        if ~accept_jump
            
            %for adaptive cycle jump, try again a smaller cycle jump
            if strcmp(SOL_JUMP_PAR.jumpmethod,'adaptive')

                attempt = 1;

                %adjust the cycle jump size
                if ~cyclejump_criterion_satisfied
                    Dn = round(Dn*(DLambda_jump/DLambda_trial)); %linear interpolation
                else
                    Dn = round(Dn / 2);
                end
                
                while attempt <= 15

                    %count up attempt
                    attempt = attempt + 1;
                    
                    %check for max. number of attempts
                    if attempt == 16
                        %stop computation
                        phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);
                        error('cycle jump not acceptable, stopping computation');
                    end

                    if Dn<2
                        %stop correction loop
                        break;
                    end
                    
                    %try adjusted cycle jump
                    disp(['adjusted cycle jump attempt: ', attempt])
                    jump_cycles;

                    if accept_jump
                        %output data
                        phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle-Dn Dn SOL_CYCL_VAR.n_cycle cycl_jump_stage], {'n' 'Dn' 'n+Dn' 'stage'}, [attempt DLambda_jump DLambda_trial], {'attempt' 'DLambda_jump' 'DLambda_trial'}, [example_name filesep 'cyclejump_restored.dat']);
                        
                        %stop correction loop
                        break;
                    else
                        %adjust the cycle jump size
                        if ~cyclejump_criterion_satisfied
                            Dn = round(Dn*(DLambda_jump/DLambda_trial)); %linear interpolation
                        else
                            Dn = round(Dn / 2);
                        end
                    end
                    
                end

            else
                %stop computation
                phase_field.fem.crack.fatigue_life(SOL_CYCL_VAR.n_cycle, sys, CRACK_PAR, SOL_STEP_PAR, example_name);
                error('cycle jump not acceptable, stopping computation');
            end
        end
        
    end %if Dn > 1
    
end %if SOL_CYCL_VAR.n_cycle>=(SOL_JUMP_VAR.jumps(end,3)+SOL_JUMP_PAR.n_stencil-1)


%display elapsed time for the cycle jump
disp(['acceleration overhead time: ' num2str(toc(acceleration_tic)) 's'])

%output cputime for the cycle
phase_field.mex.output.dat_output([SOL_CYCL_VAR.n_cycle 0], {'cycle' 'type'}, [cputime toc(acceleration_tic)], {'totaltime' 'cycletime'}, [example_name filesep 'cputime.dat']);
