function [gauss_pts, gauss_weights] = quad_composition(pts, weights, dim)
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
    % [gauss_pts, gauss_weights] = quad_composition(pts, weights, dim);
    %===============================================================================
    % Purpose: Builds the 2D and 3D matrices with Gauss points and integration weights.
    %
    % INPUTS:
    % pts:     1D Coordinates of the Gauss points
    % weights: Weights of the 1D Gauss points
    % dim:     Spatial dimension of the problem
    %
    % OUTPUTS:
    % gauss_pts:     Matrix containing the coordinates of the Gauss points (parametric space)
    % gauss_weights: Vector with the numerical integration weights
    %===============================================================================
    arguments
        pts (:, :) double
        weights (:, 1) double
        dim (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(dim, 3)} = 2
    end

    idx = 1;
    num_pts = length(pts)^dim;

    gauss_weights = zeros(num_pts, 1);
    gauss_pts = zeros(num_pts, dim);

    if (dim == 2) %2D quadrature

        for i = 1:length(weights)

            for j = 1:length(weights)
                gauss_pts(idx, 1:dim) = [pts(j), pts(i)];
                gauss_weights(idx) = weights(j) * weights(i);
                idx = idx + 1;
            end

        end

    elseif (dim == 3) % 3D quadrature

        for i = 1:length(weights)

            for j = 1:length(weights)

                for k = 1:length(weights)
                    gauss_pts(idx, 1:dim) = [pts(k), pts(j), pts(i)];
                    gauss_weights(ids) = weights(k) * weights(j) * weights(i);
                    idx = idx + 1;
                end

            end

        end

    elseif (dim == 1) % 1D quadrature

        gauss_pts = pts; 
        gauss_weights = weights;

    end
