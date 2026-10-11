function [gauss_pts, gauss_weights] = gauss_quad(quad_order);
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
    % [gauss_pts, gauss_weights] = gauss_quad(quad_order, dim);
    %===============================================================================
    % Purpose: Library of gauss points coordinates and weights for numerical integr.
    %          for Gaussian quadrature
    %
    % INPUTS:
    % quad_order: Desidered order of quadrature
    % dim: spatial dimension of the problem
    %
    % OUTPUTS:
    % gauss_pts:     Vector containing the 1D coordinates of the Gauss points
    %                (parametric space)
    % gauss_weights: Vector with the 1D numerical integration weights
    %===============================================================================

    arguments
        quad_order (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(quad_order, 8)} = 2
    end

    pts = ceil(0.5 * (quad_order + 1));

    gauss_pts = zeros(pts, 1);
    gauss_weights = zeros(pts, 1);

    switch (pts) %Definition of the quadrature points coord in 1D
        case 1
            gauss_pts(1, 1) = 0.000000000000000;
            gauss_weights(1, 1) = 2.000000000000000;

        case 2
            gauss_pts(1, 1) = 0.577350269189626;
            gauss_pts(2, 1) = -0.577350269189626;

            gauss_weights(1, 1) = 1.000000000000000;
            gauss_weights(2, 1) = 1.000000000000000;

        case 3
            gauss_pts(1, 1) = 0.774596669241483;
            gauss_pts(2, 1) = -0.774596669241483;
            gauss_pts(3, 1) = 0.000000000000000;

            gauss_weights(1, 1) = 0.555555555555556;
            gauss_weights(2, 1) = 0.555555555555556;
            gauss_weights(3, 1) = 0.888888888888889;

        case 4
            gauss_pts(1, 1) = 0.861134311594053;
            gauss_pts(2, 1) = -0.861134311594053;
            gauss_pts(3, 1) = 0.339981043584856;
            gauss_pts(4, 1) = -0.339981043584856;

            gauss_weights(1, 1) = 0.347854845137454;
            gauss_weights(2, 1) = 0.347854845137454;
            gauss_weights(3, 1) = 0.652145154862546;
            gauss_weights(4, 1) = 0.652145154862546;

        case 5
            gauss_pts(1, 1) = 0.906179845938664;
            gauss_pts(2, 1) = -0.906179845938664;
            gauss_pts(3, 1) = 0.538469310105683;
            gauss_pts(4, 1) = -0.538469310105683;
            gauss_pts(5, 1) = 0.000000000000000;

            gauss_weights(1, 1) = 0.236926885056189;
            gauss_weights(2, 1) = 0.236926885056189;
            gauss_weights(3, 1) = 0.478628670499366;
            gauss_weights(4, 1) = 0.478628670499366;
            gauss_weights(5, 1) = 0.568888888888889;

        case 6
            gauss_pts(1, 1) = 0.932469514203152;
            gauss_pts(2, 1) = -0.932469514203152;
            gauss_pts(3, 1) = 0.661209386466265;
            gauss_pts(4, 1) = -0.661209386466265;
            gauss_pts(5, 1) = 0.238619186003152;
            gauss_pts(6, 1) = -0.238619186003152;

            gauss_weights(1, 1) = 0.171324492379170;
            gauss_weights(2, 1) = 0.171324492379170;
            gauss_weights(3, 1) = 0.360761573048139;
            gauss_weights(4, 1) = 0.360761573048139;
            gauss_weights(5, 1) = 0.467913934572691;
            gauss_weights(6, 1) = 0.467913934572691;

        case 7
            gauss_pts(1, 1) = 0.949107912342759;
            gauss_pts(2, 1) = -0.949107912342759;
            gauss_pts(3, 1) = 0.741531185599394;
            gauss_pts(4, 1) = -0.741531185599394;
            gauss_pts(5, 1) = 0.405845151377397;
            gauss_pts(6, 1) = -0.405845151377397;
            gauss_pts(7, 1) = 0.000000000000000;

            gauss_weights(1, 1) = 0.129484966168870;
            gauss_weights(2, 1) = 0.129484966168870;
            gauss_weights(3, 1) = 0.279705391489277;
            gauss_weights(4, 1) = 0.279705391489277;
            gauss_weights(5, 1) = 0.381830050505119;
            gauss_weights(6, 1) = 0.381830050505119;
            gauss_weights(7, 1) = 0.417959183673469;

        case 8
            gauss_pts(1, 1) = 0.960289856497536;
            gauss_pts(2, 1) = -0.960289856497536;
            gauss_pts(3, 1) = 0.796666477413627;
            gauss_pts(4, 1) = -0.796666477413627;
            gauss_pts(5, 1) = 0.525532409916329;
            gauss_pts(6, 1) = -0.525532409916329;
            gauss_pts(7, 1) = 0.183434642495650;
            gauss_pts(8, 1) = -0.183434642495650;

            gauss_weights(1, 1) = 0.101228536290376;
            gauss_weights(2, 1) = 0.101228536290376;
            gauss_weights(3, 1) = 0.222381034453374;
            gauss_weights(4, 1) = 0.222381034453374;
            gauss_weights(5, 1) = 0.313706645877887;
            gauss_weights(6, 1) = 0.313706645877887;
            gauss_weights(7, 1) = 0.362683783378362;
            gauss_weights(8, 1) = 0.362683783378362;

    end

end
