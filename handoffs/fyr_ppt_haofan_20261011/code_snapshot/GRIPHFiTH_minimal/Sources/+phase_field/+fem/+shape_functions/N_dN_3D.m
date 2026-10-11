function [Nxi, dNdxi] = N_dN_3D(elem_type, gauss_pts)
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
    %     - HEXA8  [Gauss]  -> linear 3D prismatic element with 8 nodes
    %                                          8 (-1,1,1)
    %                                       /     \
    %                           (-1,-1,1) 5    .4  7 (1,1,1)
    %                                     | \    / |
    %                          (-1,-1,-1) 1   6    3 (1,1,-1)
    %                                      \  |   /
    %                                        \| /
    %                                         2
    %                                      (1,-1,-1)

    %
    %     - TETR4  [Simpl]  -> linear 3D tetrahedral element with 4 nodes
    %                                         4  (0,0,1)
    %                                       / | \
    %                                      /  |  \
    %                             (0,0,0) 1---|---3 (0,1,0)
    %                                      \  |  /
    %                                         2
    %                                        (1,0,0)

    arguments
        elem_type phase_field.init.ElementType = phase_field.init.ElementType.HEXA8
        gauss_pts (:, 3) double = [0.0, 0.0, 0.0]
    end

    switch elem_type

        case phase_field.init.ElementType.HEXA8

            for G_pts = length(gauss_pts):-1:1
                tmp1 = 0.5 - gauss_pts(G_pts, :) ./ 2;
                tmp2 = 0.5 - gauss_pts(G_pts, :) ./ 2;

                xi   = gauss_pts(G_pts, 1);
                eta  = gauss_pts(G_pts, 2);
                zeta = gauss_pts(G_pts, 3);

                Nxi(:, G_pts) = [tmp1(1,1) * tmp1(1,2) * tmp1(1,3);
                                 tmp2(1,1) * tmp1(1,2) * tmp1(1,3);
                                 tmp2(1,1) * tmp2(1,2) * tmp1(1,3);
                                 tmp1(1,1) * tmp2(1,2) * tmp1(1,3);
                                 tmp1(1,1) * tmp1(1,2) * tmp2(1,3);
                                 tmp2(1,1) * tmp1(1,2) * tmp2(1,3);
                                 tmp2(1,1) * tmp2(1,2) * tmp2(1,3);
                                 tmp1(1,1) * tmp2(1,2) * tmp2(1,3)];

                dNdxi(:, :, G_pts) = [-1+eta+zeta-eta*zeta, -1+xi+zeta-xi*zeta, -1+xi+eta-xi*eta;
                                       1-eta-zeta+eta*zeta, -1-xi+zeta+xi*zeta, -1-xi+eta+xi*eta;
                                       1+eta-zeta-eta*zeta,  1+xi-zeta-xi*zeta, -1-xi-eta-xi*eta;
                                      -1-eta+zeta+eta*zeta,  1-xi-zeta+xi*zeta, -1+xi-eta+xi*eta;      
                                      -1+eta-zeta+eta*zeta, -1+xi-zeta+xi*zeta,  1-xi-eta+xi*eta;
                                       1-eta+zeta-eta*zeta, -1-xi-zeta-xi*zeta,  1+xi-eta-xi*eta;
                                       1+eta+zeta+eta*zeta,  1+xi+zeta+xi*zeta,  1+xi+eta+xi*eta;
                                      -1-eta-zeta-eta*zeta,  1-xi+zeta-xi*zeta,  1-xi+eta-xi*eta]'./8;

            end

        case phase_field.init.ElementType.TETR4

            if gauss_pts == [0, 0, 0]
                gauss_pts = [1, 1, 1]./6;
            end

            for G_pts = length(gauss_pts):-1:1
                xi   = gauss_pts(G_pts, 1);
                eta  = gauss_pts(G_pts, 2);
                zeta = gauss_pts(G_pts, 3);

                Nxi(:, G_pts) = [ 1-xi-eta-zeta;
                                  xi; 
                                  eta; 
                                  zeta ];

                dNdxi(:, :, G_pts) = [ -1.0 -1.0 -1.0; 
                                        1.0  0.0  0.0; 
                                        0.0  1.0  0.0;
                                        0.0  0.0  1.0 ]';
            end

        otherwise
            error('Unsupported element type: %s', elem_type)

    end

end
