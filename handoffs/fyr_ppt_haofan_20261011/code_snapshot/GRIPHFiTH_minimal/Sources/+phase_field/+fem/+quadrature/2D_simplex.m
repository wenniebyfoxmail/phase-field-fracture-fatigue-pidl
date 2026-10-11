function [gauss_pts, gauss_weights] = 2D_simplex(quad_order)
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
    %          of 2D Simplex elements
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
        quad_order (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(quad_order, 7)} = 2
    end

    switch quad_order

        case 1 % set gauss_points and gauss_weights
            gauss_pts = zeros(1, dim);
            gauss_weights = 0.0;

            gauss_pts(1, 1:dim) = [0.3333333333333, 0.3333333333333];
            gauss_weights = 1;

        case 2
            gauss_pts = zeros(3, dim);
            gauss_weights = zeros(3, 1);

            gauss_pts(1, 1:dim) = [0.1666666666667, 0.1666666666667];
            gauss_pts(2, 1:dim) = [0.6666666666667, 0.1666666666667];
            gauss_pts(3, 1:dim) = [0.1666666666667, 0.6666666666667];

            gauss_weights(1) = 0.3333333333333;
            gauss_weights(2) = 0.3333333333333;
            gauss_weights(3) = 0.3333333333333;

        case {3, 4, 5}
            gauss_pts = zeros(7, dim);
            gauss_weights = zeros(7, 1);

            gauss_pts(1, 1:dim) = [0.1012865073235, 0.1012865073235];
            gauss_pts(2, 1:dim) = [0.7974269853531, 0.1012865073235];
            gauss_pts(3, 1:dim) = [0.1012865073235, 0.7974269853531];
            gauss_pts(4, 1:dim) = [0.4701420641051, 0.0597158717898];
            gauss_pts(5, 1:dim) = [0.4701420641051, 0.4701420641051];
            gauss_pts(6, 1:dim) = [0.0597158717898, 0.4701420641051];
            gauss_pts(7, 1:dim) = [0.3333333333333, 0.3333333333333];

            gauss_weights(1) = 0.1259391805448;
            gauss_weights(2) = 0.1259391805448;
            gauss_weights(3) = 0.1259391805448;
            gauss_weights(4) = 0.1323941527885;
            gauss_weights(5) = 0.1323941527885;
            gauss_weights(6) = 0.1323941527885;
            gauss_weights(7) = 0.2250000000000;

        case {6, 7}
            gauss_pts = zeros(13, dim);
            gauss_weights = zeros(13, 1);

            gauss_pts(1, 1:dim) = [0.0651301029022, 0.0651301029022];
            gauss_pts(2, 1:dim) = [0.8697397941956, 0.0651301029022];
            gauss_pts(3, 1:dim) = [0.0651301029022, 0.8697397941956];
            gauss_pts(4, 1:dim) = [0.3128654960049, 0.0486903154253];
            gauss_pts(5, 1:dim) = [0.6384441885698, 0.3128654960049];
            gauss_pts(6, 1:dim) = [0.0486903154253, 0.6384441885698];
            gauss_pts(7, 1:dim) = [0.6384441885698, 0.0486903154253];
            gauss_pts(8, 1:dim) = [0.3128654960049, 0.6384441885698];
            gauss_pts(9, 1:dim) = [0.0486903154253, 0.3128654960049];
            gauss_pts(10, 1:dim) = [0.2603459660790, 0.2603459660790];
            gauss_pts(11, 1:dim) = [0.4793080678419, 0.2603459660790];
            gauss_pts(12, 1:dim) = [0.2603459660790, 0.4793080678419];
            gauss_pts(13, 1:dim) = [0.3333333333333, 0.3333333333333];

            gauss_weights(1) = 0.0533472356088;
            gauss_weights(2) = 0.0533472356088;
            gauss_weights(3) = 0.0533472356088;
            gauss_weights(4) = 0.0771137608903;
            gauss_weights(5) = 0.0771137608903;
            gauss_weights(6) = 0.0771137608903;
            gauss_weights(7) = 0.0771137608903;
            gauss_weights(8) = 0.0771137608903;
            gauss_weights(9) = 0.0771137608903;
            gauss_weights(10) = 0.1756152576332;
            gauss_weights(11) = 0.1756152576332;
            gauss_weights(12) = 0.1756152576332;
            gauss_weights(13) = -0.1495700444677;

    end

    gauss_weights = gauss_weights ./ 2;

end
