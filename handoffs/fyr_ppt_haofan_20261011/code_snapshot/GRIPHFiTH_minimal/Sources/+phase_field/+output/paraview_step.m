function [] = paraview_step(...
    filename, STIFFNESS_MATRIX, MESH, ...
    names_node, values_node, ...
    names_gausspt, values_gausspt...
)
%PARAVIEW_STEP Write a VTK file for simulation step visualisation in paraview
% Inputs:
% filename            -->  String with a name of a file to which output should be written 
% STIFFNESS_MATRIX    -->  Stiffness matrix struct
% MESH                -->  Mesh struct
% names_nodes         -->  Cell array containing the names corresponding to the values
%                          specified in values_nodes. The number of names must match the number of value arrays.
%                          Allowed to be empty.
% values_nodes        -->  Cell array containing value arrays at nodes.
%                          Allowed to be empty.
%                          The shapes of the value arrays must be [1,:] (scalar field),
%                          [:,2] (vector field), or [:,3] (tensor field).
% names_gausspt       -->  Cell array containing the names corresponding to the values
%                          specified in values_gausspt. The number of names must match the number of value arrays.
%                          Allowed to be empty.
% values_gausspt      -->  Cell array containing value arrays at Gauss points.
%                          Allowed to be empty.
%                          The shapes of the value arrays must be [1,:] (scalar field),
%                          [:,2] (vector field), or [:,3] (tensor field).

% Copyright (C) 2021-2023 ETH Zurich, SIS ID and CompMech D-MAVT
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
    filename {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText}
    STIFFNESS_MATRIX (1, 1) struct
    MESH (1, 1) struct
    names_node (1, :) cell
    values_node (1, :) cell
    names_gausspt (1, :) cell
    values_gausspt (1, :) cell
end

raw_output(1).values = values_node;
raw_output(1).names = names_node;
raw_output(1).interpolate = false;
raw_output(2).values = values_gausspt;
raw_output(2).names = names_gausspt;
raw_output(2).interpolate = true;

% Prepare a 3-sized (1: scalars, 2: vectors, 3: tensors) array of structs with fields
% 'names' and 'values':
output_by_dim = struct('names', {{}, {}, {}}, 'values', {[], [], []});
% Dimension along which values are concatenated, so it can be passed to fortran
% For scalars just concatenate m (n,1) arrays to (n,m) arrays => concat_dim=2,
% for vectors and tensors, concatenate m (2,n) -> (2,n,m) and m (3,n) -> (3,n,m)
% => concat_dim=3:
concat_dim = [2, 3, 3];

num_node = MESH.num_node;

for out = raw_output
    if length(out.values) ~= length(out.names)
        error('paraview_step: number of value arrays and value names must match');
    end
    for i = 1:length(out.values)
        raw_values = out.values{i};
        node_values = zeros(size(raw_values));
        dim = size(raw_values, 2);
        if dim < 1 || dim > 3
            error('paraview_step: Unsupported output data shape: %s for %s', num2str(size(raw_values)), out.names{i});
        end
        if out.interpolate
            for d = 1:dim
                node_values(:, d) = cholmod2(STIFFNESS_MATRIX.M_sig(1:num_node, 1:num_node), raw_values(:, d));
            end
        else
            node_values = raw_values;
        end
        output_by_dim(dim).names{end+1} = out.names{i};
        if concat_dim(dim) == 2
            output_by_dim(dim).values(:, end+1) = node_values;
        elseif concat_dim(dim) == 3
            % end + 1 wont work here, as f*ing MATLAB sets a dimension of 1 in the
            % 3rd dimension:
            insert_incr = ~isempty(output_by_dim(dim).values);
            output_by_dim(dim).values(:, :, end + insert_incr) = node_values;
        end
    end
end

phase_field.mex.output.paraview_out(...
    filename,...
    num_node, size(MESH.elem, 1),...
    size(MESH.elem, 2), MESH.node, MESH.elem,...
    MESH.elem_material_id,...
    output_by_dim(1).names,...% scalars
    output_by_dim(1).values,...
    output_by_dim(2).names,...% vectors ...
    output_by_dim(2).values,...
    output_by_dim(3).names,...% vectors ...
    output_by_dim(3).values...
);

end
