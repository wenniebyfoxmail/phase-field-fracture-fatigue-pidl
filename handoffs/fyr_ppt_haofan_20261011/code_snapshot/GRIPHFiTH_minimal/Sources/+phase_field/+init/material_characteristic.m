function [MAT_CHAR] = material_characteristic(L_max, diss_fct, args)
%MATERIAL_MODEL_PROPS Material and model characteristic.
%
%   The following output structure fields can be set by keyword arguments, otherwise,
%   they are set with default values:
%
%       E         = 210.0;     % GPa Young's Modulus G*(3*lambda + 2*G)/(lambda+G)
%       ni        = 0.3;       % Poisson ratio lambda/(2*(lambda+G))
%       Gc        = 0.0027;    % Fracture energy
%       ell       = 0.1;       % Regularization length
%       res_stiff = 0;         % Residual stiffness
%       traction_p = 2.5;      % Wu PF-CZM traction-order exponent (separate from fatigue exponent p)
%       a1        = NaN;       % Wu PF-CZM cracking-function coefficient
%       a2        = NaN;       % Wu PF-CZM cracking-function coefficient
%       a3        = 0;         % Wu PF-CZM concrete/cubic cracking-function coefficient
%
%   The following output structure fields are additionaly computed as follows:
%
%       G         = E/(2*(1+ni));           % Shear modulus
%       K         = E/(3*(1-2*ni));         % Bulk modulus
%       lambda    = E*ni/((1+ni)*(1-2*ni)); % 1st Lame parameter
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
    L_max (1, 1) double
    diss_fct {mustBeMember(diss_fct, {'AT1', 'AT2', 'PF_CZM'})}
    args.E (1, 1) double {mustBePositive} = 210.0
    args.ni (1, 1) double {mustBeNonnegative, mustBeLessThanOrEqual(args.ni, 0.5)} = 0.3
    args.Gc (1, 1) double {mustBePositive} = 0.0027
    args.ell (1, 1) double {mustBePositive} = 0.1
    args.res_stiff (1,1) double {mustBeNonnegative} = 0
    args.alpha_T (1,1) double {mustBeNonnegative} = 1e10
    args.p (1,1) double {mustBeNonnegative} = 2
    args.traction_p (1,1) double {mustBePositive} = 2.5
    args.a1 (1,1) double = NaN
    args.a2 (1,1) double = NaN
    args.a3 (1,1) double = 0
    args.tol_AT1_recovery (1, 1) double {mustBePositive} = 1e-3
    args.tol_irrev (1, 1) double {mustBePositive} = 1e-3
end

MAT_CHAR.E         = args.E;
MAT_CHAR.ni        = args.ni;
MAT_CHAR.G         = args.E/(2*(1+args.ni));
MAT_CHAR.K         = args.E / (3 * (1 - (2 * args.ni)));
MAT_CHAR.lambda    = args.E * args.ni / ((1 + args.ni) * (1 - (2 * args.ni)));
MAT_CHAR.Gc        = args.Gc;
MAT_CHAR.ell       = args.ell;
MAT_CHAR.res_stiff = args.res_stiff;
MAT_CHAR.alpha_T   = args.alpha_T;
MAT_CHAR.p         = args.p;
MAT_CHAR.traction_p = args.traction_p;
MAT_CHAR.a1        = args.a1;
MAT_CHAR.a2        = args.a2;
MAT_CHAR.a3        = args.a3;

if strcmp(diss_fct, 'AT1')
    MAT_CHAR.penalty_irrev = (MAT_CHAR.Gc * 27) / (MAT_CHAR.ell * 64 * args.tol_irrev ^ 2);
    MAT_CHAR.penalty_recov = (MAT_CHAR.Gc / MAT_CHAR.ell) * (9 * ((L_max / MAT_CHAR.ell) - 2)) / (64 * args.tol_AT1_recovery);
elseif strcmp(diss_fct, 'AT2')
    MAT_CHAR.penalty_irrev = (MAT_CHAR.Gc / MAT_CHAR.ell) * ((1 / args.tol_irrev ^ 2) - 1);
    MAT_CHAR.penalty_recov = 0;
elseif strcmp(diss_fct, 'PF_CZM')
    % Wu PF-CZM: no PENALTY-style penalty params; rational-fraction g(d) handles
    % irreversibility internally. Zero out for safety; the kernel ignores them.
    MAT_CHAR.penalty_irrev = 0;
    MAT_CHAR.penalty_recov = 0;
else
    error('Uknown dissipation function name "%s"', diss_fct);
end

end
