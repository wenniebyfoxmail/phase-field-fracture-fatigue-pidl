function [CRACK_VAR] = fatigue_crack_growth(sys, CRACK_PAR, CRACK_VAR, SOL_STEP_PAR, example_name)
%FATIGUE_CRACK_GROWTH compute crack growth rate for specific specimens
%COMPUTATIONS BASED ON ASTM E647/ ASTM E1820/
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
    sys (1, 1) handle           %system handle
    CRACK_PAR (1, 1) struct     %Parameters of the crack growth rate tracking
    CRACK_VAR (1, 1) struct     %Variables of the crack growth rate tracking
    SOL_STEP_PAR (1, 1) struct  %Parameters of the step solver for load ratio R
    example_name {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
end

% =========================================================================

%compute fatigue crack growth rate for different methods
CRACK_VAR.cgr_discretized = crack_growth_rate(CRACK_PAR, sys, CRACK_VAR.crack_discretized, CRACK_VAR.cgr_discretized, SOL_STEP_PAR.R, example_name, 'discretized');
CRACK_VAR.cgr_regularized = crack_growth_rate(CRACK_PAR, sys, CRACK_VAR.crack_regularized, CRACK_VAR.cgr_regularized, SOL_STEP_PAR.R, example_name, 'regularized');
CRACK_VAR.cgr_interpolated = crack_growth_rate(CRACK_PAR, sys, CRACK_VAR.crack_interpolated, CRACK_VAR.cgr_interpolated, SOL_STEP_PAR.R, example_name, 'interpolated');

end %function




% =========================================================================
%   FUNCTIONS
% =========================================================================
function cgr_struct = crack_growth_rate(CRACK_PAR, sys, crack_struct, cgr_struct, R, example_name, method)
    %generalized function to be used for various crack- and cgr-structs

    %compute crack increment
    n = crack_struct(end,1);
    da = crack_struct(end,3) - cgr_struct(end,2);

    if da >= CRACK_PAR.cgr_da
        
        %perform computations at averaged point between two cycles n_{i+1/2}
        a_avg = (crack_struct(end,3) + crack_struct(end-1,3))/2;
        gamma_avg = a_avg/sys.GEOM.B;
        dn = n - cgr_struct(end,1);
        
        %compute geometric factor   
        geometric_factor_fh = str2func(sprintf('cgr_%s_geometric_factor', CRACK_PAR.specimen));
        Y_nhalf = geometric_factor_fh(gamma_avg);
        
        %compute load factor (this only includes f_min = 0 so far!)
        load_factor = (abs(sys.BOUNDARY_CONDS.ty_final*(1-R)))/(sys.GEOM.t*sqrt(sys.GEOM.B));
        dK = load_factor*Y_nhalf*sqrt(1/1000); %tranfrom into MPa*sqrt(m)
        
        %save data
        cgr_struct(end+1,:) = [n crack_struct(end,3)]; %n, a

        %output data
        phase_field.mex.output.dat_output(...
            [n-1/2, dn], {'n_eval' 'dn'}, ...
            [crack_struct(end,3), da, da/dn, dK], {'a' 'da' 'dadn' 'dK'}, ...
            [example_name filesep 'cgr_' method '.dat']);
        
    end
    
end



% ============================GEOMETRIC FACTORS=============================
%functions to compute the geometric factor
function Y_nhalf = cgr_ct_geometric_factor(gamma_avg)
    %[ASTM E647]
    fac1 = (2+gamma_avg)/((1-gamma_avg)^(3/2));
    fac2 = 0.886 + (4.64*gamma_avg) - (13.32*gamma_avg^2) + (14.72*gamma_avg^3) - (5.6*gamma_avg^4);

    Y_nhalf = fac1*fac2;
end

function Y_nhalf = cgr_tpb_geometric_factor(gamma_avg)
    %[ASTM E1820]
    S_B = 4.5;%this is only for the internally included specimen with S=180mm and B=40mm
    nom = 3*S_B*sqrt(gamma_avg);
    denom = 2*(1+2*gamma_avg)*((1-gamma_avg)^(3/2));
    fac2 = 1.99 - gamma_avg*(1-gamma_avg)*(2.15-3.93*gamma_avg+2.7*gamma_avg^2);

    Y_nhalf = (nom/denom)*fac2;
end

function Y_nhalf = cgr_sent_geometric_factor(gamma_avg)
    %[Tada 1939 'The stress analysis of cracks handbook', p.52]
    fac = sqrt((2/pi) * (1/gamma_avg) * tan((pi/2)*gamma_avg));
    nom = 0.752 + 2.02*gamma_avg + 0.37*(1-sin((pi/2)*gamma_avg))^3;
    denom = cos((pi/2)*gamma_avg);

    Y_nhalf = fac*(nom/denom);
end

function Y_nhalf = cgr_dent_geometric_factor(gamma_avg)
    %[Tada 1939 'The stress analysis of cracks handbook', p.47]
    %accuracy 0.5% for any a/b for h/b>3
    nom = 1.122 - 0.561*gamma_avg + 0.205*gamma_avg^2 + 0.471*gamma_avg^3 - 0.19*gamma_avg^4;
    denom = sqrt(1-gamma_avg);

    Y_nhalf = nom/denom;
end

function Y_nhalf = cgr_cct_geometric_factor(gamma_avg)
    %[Tada 1939 'The stress analysis of cracks handbook', p.41]
    %accuracy 0.1% for any a/b for h/b>3
    fac1 = 1 - 0.025*gamma_avg^2 + 0.06*gamma_avg^4;
    fac2 = sec((pi/2)*gamma_avg);

    Y_nhalf = fac1*fac2;
end




