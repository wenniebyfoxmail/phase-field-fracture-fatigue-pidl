function [STIFFNESS_MATRIX] = stiffness_matrix(sys, field_vars)
%STIFFNESS_MATRIX ...
%   ...
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
[ ...
    K_vect, i_row, j_col, ...
    M_vector, i_row_sig, j_col_sig, ...
    eps_vector, i_row_eps, j_col_eps, ...
    sig0_vector, i_row_pf, j_col_pf ...
] = phase_field.mex.fem.assembly.equilibrium.initial( ...
    sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, sys.CC, field_vars ...
);

KK = sparse(i_row, j_col, K_vect);
M_sig = sparse(i_row_sig, j_col_sig, M_vector);
eps_   = sparse(i_row_eps, j_col_eps, eps_vector);
sig0  = sparse(i_row_eps, j_col_eps, sig0_vector);

STIFFNESS_MATRIX.KK = KK;
STIFFNESS_MATRIX.i_row = i_row;
STIFFNESS_MATRIX.j_col = j_col;
STIFFNESS_MATRIX.M_sig = M_sig;
STIFFNESS_MATRIX.eps = eps_;
STIFFNESS_MATRIX.i_row_eps = i_row_eps;
STIFFNESS_MATRIX.j_col_eps = j_col_eps;
STIFFNESS_MATRIX.sig0 = sig0;
STIFFNESS_MATRIX.i_row_pf = i_row_pf;
STIFFNESS_MATRIX.j_col_pf = j_col_pf;

end
