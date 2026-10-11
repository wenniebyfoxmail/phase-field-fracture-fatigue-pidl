function [Theta_extrap] = extrapolate(SOL_JUMP_PAR,HISTORY,Dn)
%EXTRAPOLATE extrapolate system state variables based on backwards finite differences
%
% SOL_JUMP_PAR      structure containing all parameters for the cycle jump
% HISTORY           structure containing the history variables to be extrapolated (cycles in third dimension)

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

% =======================================================================
%reorganize the discrete values for the backward_finite_difference function
%Theta_i = num2cell(HISTORY.fat,[1,2]) is much slower, therefore instead use explicit version
switch SOL_JUMP_PAR.n_stencil
    
    case 3
        Theta_i = {HISTORY.fat(:,:,end-2) HISTORY.fat(:,:,end-1) HISTORY.fat(:,:,end)};
        
    case 4
        Theta_i = {HISTORY.fat(:,:,end-3) HISTORY.fat(:,:,end-2) HISTORY.fat(:,:,end-1) HISTORY.fat(:,:,end)};
        
    case 5
        Theta_i = {HISTORY.fat(:,:,end-4) HISTORY.fat(:,:,end-3) HISTORY.fat(:,:,end-2) HISTORY.fat(:,:,end-1) HISTORY.fat(:,:,end)};

    case 6
        Theta_i = {HISTORY.fat(:,:,end-5) HISTORY.fat(:,:,end-4) HISTORY.fat(:,:,end-3) HISTORY.fat(:,:,end-2) HISTORY.fat(:,:,end-1) HISTORY.fat(:,:,end)};
    
end

% =======================================================================
%approximate the first and second rate with respect to the cycle count
Theta_Dot    = phase_field.fem.solver.cycl_jump.backward_finite_difference(Theta_i,1);
Theta_DotDot = phase_field.fem.solver.cycl_jump.backward_finite_difference(Theta_i,2);


% =======================================================================
%extrapolate the history variables
DTheta = Theta_Dot*Dn + Theta_DotDot*Dn^2/2;
DTheta(DTheta<0) = 0; %correct non-physical extrapolation
Theta_extrap = HISTORY.fat(:,:,end) + DTheta;


end %function
