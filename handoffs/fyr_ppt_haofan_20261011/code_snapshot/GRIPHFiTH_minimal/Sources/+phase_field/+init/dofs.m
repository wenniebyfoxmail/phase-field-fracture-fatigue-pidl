function [DOFS] = dofs(MESH, NODE_BOUNDARIES, args)
%DOFS Degrees of freedom defitions (DOFs)
%   ...
%
%   The following outpt stucture fields can be set by keyword arguments, otherwise, they
%   are set with default values:
%
%       num_dof_node = 2;  % number of DOF per node
%
%   The following output structure fields are additionally computed from the input
%   arguments:
%
%       num_dof                 % Total number of DOFs `num_node * num_dof_node`;
%       hom_dirichlet_bc        % DOFs with homogeneous Dirichlet BC
%       non_hom_dirichlet_bc    % DOFs with non-homogeneous Dirichlet BC
%       dirichlet_bc            % DOFs with Dirichlet BC
%       neumann_bc              % DOFs with Neumann BC
%       active_dof              % Active DOFs to be solved
%       dirichlet_bc_pf         % Phase field DOFs with imposed Dirichlet BC (for notches)
%       active_dof_pf           % Active phase field DOFs
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
    MESH (1, 1) struct
    NODE_BOUNDARIES (1, 1) struct
    args.num_dof_node (1, 1) double {mustBeInteger, mustBePositive} = 2
end

DOFS.num_dof_node = args.num_dof_node;

num_node = MESH.num_node;

DOFS.num_dof   = num_node * DOFS.num_dof_node;
all_dof = 1:DOFS.num_dof;

DOFS.hom_dirichlet_bc     = [NODE_BOUNDARIES.fix_X; NODE_BOUNDARIES.fix_Y + num_node];
DOFS.non_hom_dirichlet_bc = [NODE_BOUNDARIES.disp_X; NODE_BOUNDARIES.disp_Y + num_node];
DOFS.dirichlet_bc         = [DOFS.hom_dirichlet_bc; DOFS.non_hom_dirichlet_bc];
DOFS.neumann_bc           = [NODE_BOUNDARIES.tract_X; NODE_BOUNDARIES.tract_Y + num_node];
DOFS.active_dof           = setdiff(all_dof, DOFS.dirichlet_bc);

DOFS.hom_dirichlet_bc_pf     = [NODE_BOUNDARIES.hom_pf];
DOFS.non_hom_dirichlet_bc_pf = [NODE_BOUNDARIES.non_hom_pf];
DOFS.dirichlet_bc_pf = [DOFS.hom_dirichlet_bc_pf; DOFS.non_hom_dirichlet_bc_pf];
DOFS.active_dof_pf   = setdiff(1:num_node, DOFS.dirichlet_bc_pf);

end

