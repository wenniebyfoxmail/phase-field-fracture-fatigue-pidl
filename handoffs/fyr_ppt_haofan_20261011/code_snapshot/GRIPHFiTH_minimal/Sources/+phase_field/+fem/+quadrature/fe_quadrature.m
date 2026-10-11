function [gauss_pts, gauss_weights] = fe_quadrature(elem_type, quad_order, dim)
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
    % Supported element types: See phase_field.init.ElementType

    arguments
        elem_type phase_field.init.ElementType = phase_field.init.ElementType.QUAD4
        quad_order (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(quad_order, 8)} = 2
        dim (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(dim, 3)} = 2
    end

    switch elem_type

        case {phase_field.init.ElementType.LINE2, phase_field.init.ElementType.LINE3, phase_field.init.ElementType.QUAD4, phase_field.init.ElementType.QUAD8, phase_field.init.ElementType.QUAD9, phase_field.init.ElementType.HEXA8, phase_field.init.ElementType.HEXA20, phase_field.init.ElementType.HEXA27} %Gauss quadrature

            [gauss_pts, gauss_weights] = phase_field.fem.quadrature.gauss_quad(quad_order);
            [gauss_pts, gauss_weights] = phase_field.fem.quadrature.quad_composition(gauss_pts, gauss_weights, dim);

        case {phase_field.init.ElementType.TRIA3, phase_field.init.ElementType.TRIA6, phase_field.init.ElementType.TETR4, phase_field.init.ElementType.TETR10} % Simplex elements

            [gauss_pts, gauss_weights] = phase_field.fem.quadrature.simplex_quad(quad_order, dim);

    end

end
