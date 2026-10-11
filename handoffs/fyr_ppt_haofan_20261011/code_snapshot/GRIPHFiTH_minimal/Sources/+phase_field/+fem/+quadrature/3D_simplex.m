function [gauss_pts, gauss_weights] = 3D_simplex(quad_order)
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
    % [gauss_pts, gauss_weights] = simplicial_quad(quad_order, dim);
    %===============================================================================
    % Purpose: Library of quadrature points coordinates and weights for numerical integr.
    %          of 3D Simplex elements
    %
    % INPUTS:
    % quad_order: Desidered order of quadrature
    %
    % OUTPUTS:
    % gauss_pts:     Vector containing the 1D coordinates of the Gauss points
    %                (parametric space)
    % gauss_weights: Vector with the 1D numerical integration weights
    %===============================================================================

    arguments
        quad_order (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(quad_order, 3)} = 2
    end

    switch quad_order
        case 1
            gauss_pts = [1/4 1/4 1/4];
            gauss_weights = 1;

        case 2
            gauss_pts = [0.5854101966249685, 0.1381966011250105, 0.1381966011250105;
                    0.1381966011250105, 0.5854101966249685, 0.1381966011250105;
                    0.1381966011250105, 0.1381966011250105, 0.5854101966249685;
                    0.1381966011250105, 0.1381966011250105, 0.1381966011250105];
            gauss_weights = [1/4; 1/4; 1/4; 1/4];

        case 3
            gauss_pts = [1/4 1/4 1/4;
                    1/2 1/6 1/6;
                    1/6 1/2 1/6;
                    1/6 1/6 1/2;
                    1/6 1/6 1/6];
            gauss_weights = [-4/5 9/20 9/20 9/20 9/20]';

    end

    gauss_weights = gauss_weights ./ 6;

end
