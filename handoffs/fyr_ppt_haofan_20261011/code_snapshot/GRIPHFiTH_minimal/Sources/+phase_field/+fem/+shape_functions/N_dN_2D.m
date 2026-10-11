function [Nxi, dNdxi] = N_dN_2D(elem_type, gauss_pts)
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
    %     - QUAD4  [Gauss]  -> linear 2D quadrilateral element with 4 nodes
    %                             (-1, 1) 4 ===== 3 (1, 1)     
    %                                     |       |                     
    %                                     |       |                     
    %                             (-1,-1) 1 ===== 2 (1,-1)             
    %
    %     - TRIA3  [Simpl]  -> linear 2D triangular element with 3 nodes
    %                              (0, 1) 3               
    %                                     | \                 
    %                                     |  \                
    %                              (0, 0) 1 = 2 (1, 0)
    %
    %     - TRIA6  [Simpl]  -> quadratic 2D triangular element with 6 nodes
    %                              (0, 1) 3               
    %                                     | \             
    %                                     6  5            
    %                                     |    \          
    %                              (0, 0) 1--4--2 (1, 0)  

    arguments
        elem_type phase_field.init.ElementType = phase_field.init.ElementType.QUAD4
        gauss_pts (:, 2) double = [0.0, 0.0]
    end

    switch elem_type

        case phase_field.init.ElementType.QUAD4

            for G_pts = length(gauss_pts):-1:1
                xi  = gauss_pts(G_pts, 1);
                eta = gauss_pts(G_pts, 2);

                Nxi(:, G_pts) = 0.25 * [(1 - xi) * (1 - eta);
                                        (1 + xi) * (1 - eta);
                                        (1 + xi) * (1 + eta);
                                        (1 - xi) * (1 + eta)];

                dNdxi(:, :, G_pts) = 0.25 * [-(1-eta), -(1-xi);
                                             1-eta, -(1+xi);
                                             1+eta, 1+xi;
                                             -(1+eta), 1-xi]';
            end

        case phase_field.init.ElementType.TRIA3

            if gauss_pts == [0, 0]
                gauss_pts = [1, 1] ./ 3;
            end

            for G_pts = length(gauss_pts):-1:1
                xi  = gauss_pts(G_pts, 1);
                eta = gauss_pts(G_pts, 2);

                Nxi(:, G_pts) = [1 - xi - eta;
                                 xi;
                                 eta];

                dNdxi(:, :, G_pts) = [-1.0 -1.0; 1.0 0.0; 0.0 1.0]';
            end

        case phase_field.init.ElementType.TRIA6

            if gauss_pts == [0, 0]
                gauss_pts = [1, 1] ./ 3;
            end

            for G_pts = length(gauss_pts):-1:1
                xi  = gauss_pts(G_pts, 1);
                eta = gauss_pts(G_pts, 2);

                Nxi(:, G_pts) = [ 1-3*(xi+eta)+4*xi*eta+2*(xi^2 + eta^2);
                                  xi*(2*xi-1);
                                  eta*(2*eta-1);
                                  4*xi*(1-xi-eta);
                                  4*xi*eta;
                                  4*eta*(1-xi-eta) ];

                dNdxi(:, :, G_pts) = [ 4*(xi+eta)-3,   4*(xi+eta)-3;
                                       4*xi-1,         0;
                                       0,              4*eta-1;
                                       4*(1-eta-2*xi), -4*xi;
                                       4*eta,          4*xi;
                                       -4*eta,         4*(1-xi-2*eta) ]';
            end

        otherwise
            error('Unsupported element type: %s', elem_type)

    end

end
