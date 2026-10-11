function [MESH, GEOM] = gmsh_import(mesh_file, args)
% GMSH_IMPORT read external mesh file from gmsh
%
% Procedure:
% 1) generate mesh in GMSH
% 2) File > Export... > Save As: "Mesh - Matlab (*.m)"
% 3) call this function with the file path to the generated mesh file as input
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
    mesh_file
    args.t (1, 1) double {mustBePositive} = 1
    args.nel_tract (1, 1) double {mustBeInteger, mustBePositive} = 2
end

%read mesh file from GMSH (get rid of ending .m for this)
run(mesh_file(1:end-2));

%rearrange the input to requested structure
node = msh.POS(:,1:2);
elem = msh.QUADS(:,1:4);

num_elem = size(elem,1);    %number of elements
num_node = size(node,1);    %number of nodes
nel = 4;                    %number of nodes per element

% Size of the problem
dim = size(node, 2);
tensors = dim*(1+(dim-1)/2);

MESH.tensors = dim*(1+(dim-1)/2);
MESH.node = node;
MESH.num_node = num_node;
MESH.elem = elem;
MESH.num_elem = num_elem;
MESH.nel = nel;
MESH.nel_tract = args.nel_tract;
MESH.dim = dim;
MESH.tensors = tensors;
MESH.elem_material_id = ones(MESH.num_elem, 1);

%specify geomertric properties
GEOM.L = max(MESH.node(:,1)) - max(MESH.node(:,1));
GEOM.B = max(MESH.node(:,2)) - max(MESH.node(:,2));
GEOM.t = args.t;

end
