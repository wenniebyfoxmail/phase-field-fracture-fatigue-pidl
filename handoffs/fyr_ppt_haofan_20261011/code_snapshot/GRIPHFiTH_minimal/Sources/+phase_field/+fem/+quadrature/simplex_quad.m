function [gauss_pts, gauss_weights] = simplex_quad(quad_order, dim)
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
    % Purpose: Builds the 2D and 3D matrices with Gauss points and integration weights
    %          for Simplex elements
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
        quad_order (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(quad_order, 7)} = 2
        dim (1, 1) double {mustBeInteger, mustBePositive, mustBeLessThanOrEqual(dim, 3), mustBeGreaterThan(dim, 1)} = 2
    end

    if (dim == 2) %Triangles

        [gauss_pts, gauss_weights] = phase_field.fem.quadrature.2D_simplex(quad_order);

    else

        [gauss_pts, gauss_weights] = phase_field.fem.quadrature.3D_simplex(quad_order);

    end

end
