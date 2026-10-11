function [displ, res_displ, D_RHS_tract] = pre_iter_update(...
    i_step, sys, displ, SOL_STEP_PAR...
)
%PRE_ITER_UPDATE Step-iteration pre processing update
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

arguments
    i_step (1, 1) double {mustBeInteger, mustBePositive}
    sys (1, 1) handle
    displ (:, 1) double
    SOL_STEP_PAR (1, 1) struct
end

%Dirichlet BCs
D_displ  = zeros(sys.DOFS.num_dof, 1);
D_DIR_BC = [...
    ones(length(sys.NODE_BOUNDARIES.disp_X), 1) * SOL_STEP_PAR.ux_increment(i_step);...
    ones(length(sys.NODE_BOUNDARIES.disp_Y), 1) * SOL_STEP_PAR.uy_increment(i_step)...
];
D_displ(sys.DOFS.non_hom_dirichlet_bc, 1) = D_DIR_BC;

displ(sys.DOFS.non_hom_dirichlet_bc, 1) = displ(sys.DOFS.non_hom_dirichlet_bc, 1) + D_displ(sys.DOFS.non_hom_dirichlet_bc, 1);

%Neumann BCs
if ~isempty(sys.DOFS.neumann_bc)
    if ~isempty(sys.BOUNDARY_CONDS.elem_tract) %Neumann boundary condition along an edge
        D_RHS_tract = phase_field.mex.fem.processing.D_tract_assembly(...
            sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.BOUNDARY_CONDS, i_step...
        );
    else %concentrated force on one DOF (this works either for tx or ty but not both)
        D_RHS_tract = zeros(sys.DOFS.num_dof, 1);
        if sys.BOUNDARY_CONDS.tx_increment(i_step) ~= 0
            D_RHS_tract(sys.DOFS.neumann_bc)=sys.BOUNDARY_CONDS.tx_increment(i_step);
        elseif sys.BOUNDARY_CONDS.ty_increment*i_step ~= 0
            D_RHS_tract(sys.DOFS.neumann_bc)=sys.BOUNDARY_CONDS.ty_increment(i_step);
        end
    end
else
    D_RHS_tract = zeros(sys.DOFS.num_dof, 1);
end

%compute the residual
res_displ = sys.STIFFNESS_MATRIX.KK * D_displ - D_RHS_tract;

%solve the system equation
Ddispl = cholmod2(sys.STIFFNESS_MATRIX.KK(sys.DOFS.active_dof, sys.DOFS.active_dof), -res_displ(sys.DOFS.active_dof, 1));
displ(sys.DOFS.active_dof, 1) = displ(sys.DOFS.active_dof, 1) + Ddispl;


end

