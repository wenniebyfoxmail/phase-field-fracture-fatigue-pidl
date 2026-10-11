function [Nxi, dNdxi] = shape_fcts(elem_type, dim, gauss_pts)
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
    %===============================================================================
    % [ gauss_pts, gauss_weights ] = fe_quadrature( elem_type, quad_order )
    %===============================================================================
    % Purpose: Compute the quadrature points and weights for different elements
    %
    % INPUTS:
    % elem_type:  Type of element (see below)
    % quad_order: Desidered order of quadrature
    % dim:        Spatial dimension of the problem
    %
    % OUTPUTS:
    % gauss_pts:     Matrix containing the coordinates of the Gauss points
    %                (parametric space)
    % gauss_weights: Vector with the numerical integration weights
    %===============================================================================
    %
    % Supported element types: (name is composed by a prefix with the element type followed by the number
    %                           of nodes)
    %        ID     Quad.         Description
    %     - LINE2  [Gauss]  -> linear 1D element
    %     - LINE3  [Gauss]  -> quadratic 1D element
    %     - QUAD4  [Gauss]  -> linear 2D quadrilateral element with 4 nodes
    %     - TRIA3  [Simpl]  -> linear 2D triangular element with 3 nodes
    %     - TRIA6  [Simpl]  -> quadratic 2D triangular element with 6 nodes
    %     - HEXA8  [Gauss]  -> linear 3D prismatic element with 8 nodes
    %     - TETR4  [Simpl]  -> linear 3D tetrahedral element with 4 nodes
    %
    % NOTE: THE FOLLOWING ELEMENTS ARE NOT YET IMPLEMENTED:
    %     - QUAD9  [Gauss]  -> quadratc 2D element with 9 nodes (lagrangian)
    %     - QUAD8  [Gauss]  -> quadratc 2D element with 8 nodes (serendipity)
    %     - HEXA20 [Gauss]  -> quadratic 3D prismatic element with 20 nodes (serendipity)
    %     - HEXA27 [Gauss]  -> quadratic 3D prismatic element with 27 nodes (lagrangian)
    %     - TETR10 [Simpl]  -> quadratic 3D tetrahedral element with 10 nodes

    arguments
        elem_type phase_field.init.ElementType = phase_field.init.ElementType.QUAD4
        dim (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(dim, 3)} = 2
        gauss_pts (:,:) double = [0,0]
    end

    switch dim

        case 1

            [Nxi, dNdxi] = phase_field.fem.shape_functions.N_dN_1D(elem_type, gauss_pts);

        case 2

            [Nxi, dNdxi] = phase_field.fem.shape_functions.N_dN_2D(elem_type, gauss_pts);

        case 3

            [Nxi, dNdxi] = phase_field.fem.shape_functions.N_dN_3D(elem_type, gauss_pts);

    end

end
