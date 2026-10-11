function [CRACK_VAR] = crack_regularized(n_cycle, sys, CRACK_PAR, CRACK_VAR, p_field, example_name, args)
%CRACK_REGULARIZED obtain smeared crack growth based on phase-field integral
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
    CRACK_VAR (1, 1) struct   %Variables of the crack growth rate tracking
    p_field (:, 1) double   %phase-field variable
    example_name {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
    args.output logical = true;
end

%get cycle increment
dn = n_cycle-CRACK_VAR.crack_regularized(end,1);

% =========================================================================
switch CRACK_PAR.smeared_computation
    case 'integration'
        
        %integrate the phase-field over the whole domain
        int_d = phase_field.mex.fem.processing.PF_INTEGRATION(sys.MESH, sys.GEOM.t, sys.QUADRATURE, p_field, CRACK_PAR.rel_pf);

    case 'approximation'

        %approximate in terms of L1-norm
        p_field(p_field<CRACK_PAR.rel_pf)=0.0;
        int_d = CRACK_PAR.d_int_approx_fac * norm(p_field(:),1);

end

%compute smeared crack (rate)
a_smeared = (int_d-CRACK_PAR.crack_tips*CRACK_PAR.int_d_tip)/CRACK_PAR.int_d_segment;
a_smeared = a_smeared + CRACK_VAR.crack_discretized(1,3); %add the initial crack length
da_smeared = a_smeared - CRACK_VAR.crack_regularized(end,3);

% =========================================================================
%save results
% CRACK_VAR.crack_regularized(end+1,:) = [n_cycle dn a_smeared da_smeared/dn int_d a_smeared_approx da_smeared_approx/dn int_d_approx];
CRACK_VAR.crack_regularized(end+1,:) = [n_cycle dn a_smeared da_smeared/dn int_d];

%output results
if args.output
    phase_field.mex.output.dat_output(...
        [n_cycle dn], {'n' 'dn'}, ...
        CRACK_VAR.crack_regularized(end,3:end), {'a_ell' 'da_ell/dn' 'int_d'}, ...
        [example_name filesep 'crack_regularized.dat']);
end

end %function

