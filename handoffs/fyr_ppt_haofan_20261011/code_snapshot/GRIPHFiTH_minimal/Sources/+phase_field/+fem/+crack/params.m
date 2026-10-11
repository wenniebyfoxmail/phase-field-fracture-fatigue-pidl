function [CRACK_PAR] = params(MAT_CHAR, diss_fct, args)
%PARAMS Create crack parameters structure
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
    MAT_CHAR (1, :) struct  %material characteristics
    diss_fct {mustBeMember(diss_fct, {'AT1', 'AT2', 'PF_CZM'})}   %dissipation function
    args.specimen {mustBeMember(args.specimen, {'other', 'ct', 'tpb', 'sent', 'dent', 'cct', 'bar', 'pulltest'})} = 'other' %selection of a specimen for specifif computations
    args.crack_dir (1,1) double {mustBeInteger,mustBePositive} = 1 %direction of crack growth (1: x-axis, 2: y-axis)
    args.a_offset (1,1) double = 0.0; %offset of the crack
    args.cgr_da (1,1) double = 0.1; %increment of crack length after which to evaluate crack growth rate curve
    args.crack_thres (1,1) double {mustBePositive} = 0.95 %threshold of the phase-field which should be considered as broken
    args.crack_elems (1,:) double = []; %elements where the crack tip interpolation should take place
    args.crack_nodes (1,:) double = []; %nodes where the crack tip interpolation should take place
    args.export_pf_interp (1,1) logical = false %whether to output a file with the interpolated phase-field variables
    args.rel_pf (1,1) double = 0.0; %threshold value for the phase-field above which it is considered for the smeared crack length
    args.int_d_segment (1,1) double = 0.0; %theoretical value for the phase-field integral for a segment
    args.int_d_tip (1,1) double = 0.0; %theoretical value for the phase-field integral for a tip
    args.crack_tips (1,1) double {mustBeInteger, mustBePositive} = 1 %number of crack tips
    args.J_elem (1,1) double = 0.0; %Jacobian of elements in the phase-field support (for the L1-norm approximation of the smeared crack length)
    args.d_int_approx_fac (1,1) double = 1.0; %constant factor for the L1-norm approximation of the smeared crack length (typically the Jacobian of the elements)
    args.smeared_computation {mustBeMember(args.smeared_computation, {'integration', 'approximation'})} = 'integration' %method to compute the smeared crack length
    args.ellh (1,1) double = 5; %number of elements per phase-field length scale (to properly correct the smeared crack length)
end

%copy all input args
CRACK_PAR = args;

%specify parameters based on choice of specimen
if strcmp(CRACK_PAR.specimen,'other') || strcmp(CRACK_PAR.specimen,'bar')
    CRACK_PAR.crack_dir = 1;
elseif strcmp(CRACK_PAR.specimen,'ct')
    CRACK_PAR.crack_dir = 1;
    CRACK_PAR.a_offset = 12.5;
elseif strcmp(CRACK_PAR.specimen,'tpb')
    CRACK_PAR.crack_dir = 2;
elseif strcmp(CRACK_PAR.specimen,'sent') || strcmp(CRACK_PAR.specimen,'dent') || strcmp(CRACK_PAR.specimen,'cct')
    CRACK_PAR.crack_dir = 1;
end

%obtain integrals of optimal phase-field profile
if strcmp(diss_fct,'AT1')
    CRACK_PAR.rel_pf = 0.25;

    %correction factors based on discretization ratio
    if CRACK_PAR.ellh == 2
        corr_tip = 3.171;
        corr_segment = 1.582;
    elseif CRACK_PAR.ellh == 3
        corr_tip = 2.244;
        corr_segment = 1.390;
    elseif CRACK_PAR.ellh == 4
        corr_tip = 1.846;
        corr_segment = 1.302;
    elseif CRACK_PAR.ellh == 5
        corr_tip = 1.680;
        corr_segment = 1.249;
    elseif CRACK_PAR.ellh == 6
        corr_tip = 1.539;
        corr_segment = 1.211;
    elseif CRACK_PAR.ellh == 7
        corr_tip = 1.468;
        corr_segment = 1.187;
    elseif CRACK_PAR.ellh == 8
        corr_tip = 1.416;
        corr_segment = 1.171;
    else
        warning('no correction factors for chosen ell/h available, setting to 1!')
        corr_tip = 1;
        corr_segment = 1;
    end

    CRACK_PAR.int_d_segment = corr_segment*(7/6)*MAT_CHAR(1).ell;
    CRACK_PAR.int_d_tip = corr_tip*pi*(11/48)*(MAT_CHAR(1).ell)^2;

    % uncorrected
    % CRACK_PAR.int_d_segment = corr_segment*(4/3)*MAT_CHAR(1).ell;
    % CRACK_PAR.int_d_tip = corr_tip*pi*(1/3)*(MAT_CHAR(1).ell)^2;
    
elseif strcmp(diss_fct,'AT2')
    CRACK_PAR.rel_pf = exp(-1);
    
    %correction factors based on discretization ratio
    if CRACK_PAR.ellh == 2
        corr_tip = 3.931;
        corr_segment = 1.604;
    elseif CRACK_PAR.ellh == 3
        corr_tip = 2.875;
        corr_segment = 1.411;
    elseif CRACK_PAR.ellh == 4
        corr_tip = 2.410;
        corr_segment = 1.323;
    elseif CRACK_PAR.ellh == 5
        corr_tip = 2.136;
        corr_segment = 1.271;
    elseif CRACK_PAR.ellh == 6
        corr_tip = 2.014;
        corr_segment = 1.228;
    elseif CRACK_PAR.ellh == 7
        corr_tip = 1.893;
        corr_segment = 1.204;
    elseif CRACK_PAR.ellh == 8
        corr_tip = 1.812;
        corr_segment = 1.185;
    else
        warning('no correction factors for chosen ell/h available, setting to 1!')
        corr_tip = 1;
        corr_segment = 1;
    end

    CRACK_PAR.int_d_segment = corr_segment*2*MAT_CHAR(1).ell*(1-exp(-1));
    CRACK_PAR.int_d_tip = corr_tip*pi*(MAT_CHAR(1).ell)^2*(1-2*exp(-1));

    % uncorrected
    % CRACK_PAR.int_d_segment = 2*MAT_CHAR(1).ell;
    % CRACK_PAR.int_d_tip = pi*(MAT_CHAR(1).ell)^2;
end

%obtain factor for approximation of phase-field integral by norm
if args.J_elem == 0.0
    %if no factor is given (during input it takes the default value 0.0), assume that element size of phase-field support is ell/ellh
    J_elem = (MAT_CHAR(1).ell/CRACK_PAR.ellh)^2;
else
    J_elem = args.J_elem;
end
CRACK_PAR.d_int_approx_fac = J_elem;


end

