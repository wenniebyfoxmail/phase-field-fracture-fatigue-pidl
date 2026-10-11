function [BOUNDARY_CONDS] = boundary_conditions( ...
    elem, node_tract_unique, DOFS, SOL_STEP_PAR ...
)
%BOUNDARY_CONDITIONS ...
%   ...

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

[conn_tract, flag_tract, tract_face, elem_tract] = ...
    phase_field.fem.bc.neumann_prelim(elem, node_tract_unique);

BOUNDARY_CONDS.conn_tract           = conn_tract;
BOUNDARY_CONDS.flag_tract           = flag_tract;
BOUNDARY_CONDS.tract_face           = tract_face;
BOUNDARY_CONDS.elem_tract           = elem_tract;
BOUNDARY_CONDS.non_hom_dirichlet_bc = DOFS.non_hom_dirichlet_bc;
BOUNDARY_CONDS.dirichlet_bc_pf      = DOFS.dirichlet_bc_pf;
BOUNDARY_CONDS.tx_final             = SOL_STEP_PAR.tx_final;
BOUNDARY_CONDS.ty_final             = SOL_STEP_PAR.ty_final;
BOUNDARY_CONDS.tx_increment         = SOL_STEP_PAR.tx_increment;
BOUNDARY_CONDS.ty_increment         = SOL_STEP_PAR.ty_increment;

end
