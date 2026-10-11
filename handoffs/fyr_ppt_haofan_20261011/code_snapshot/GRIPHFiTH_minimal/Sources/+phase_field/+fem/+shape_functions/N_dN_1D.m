function [Nxi, dNdxi] = N_dN_1D(elem_type, gauss_pts)
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
    %                                              1 =========== 2       
    %                                            xi=-1         xi=1
    %
    %     - LINE3  [Gauss]  -> quadratic 1D element
    %                                              1 ==== 3 ==== 2       
    %                                            xi=-1  xi=0    xi=1

    arguments
        elem_type phase_field.init.ElementType = phase_field.init.ElementType.LINE2
        gauss_pts (:, 1) double = 0.0
    end

    switch elem_type

        case phase_field.init.ElementType.LINE2

            for G_pts = length(gauss_pts):-1:1
                xi = gauss_pts(G_pts, :);

                Nxi(:, G_pts) = 0.5 * [1-xi; 1+xi];

                dNdxi(:, :, G_pts) = [-0.5; 0.5]';
            end

        case phase_field.init.ElementType.LINE3

            for G_pts = length(gauss_pts):-1:1
                xi = gauss_pts(G_pts, :);

                Nxi(:, G_pts) = [-0.5*(1-xi)*xi; 
                                 1-xi^2; 
                                 0.5*(1+xi)*xi];

                dNdxi(:, :, G_pts) = [-0.5; 0.5]';
            end

        otherwise
            error('Unsupported element type: %s', elem_type)

    end

end
