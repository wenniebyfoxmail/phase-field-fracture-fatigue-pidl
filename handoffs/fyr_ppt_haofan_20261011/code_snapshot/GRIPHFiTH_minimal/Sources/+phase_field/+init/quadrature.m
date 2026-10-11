function [QUADRATURE] = quadrature(dim, args)
    %QUADRATURE Get quadrature points
    %   ...
    %
    %   The following keyword arguments can be set, otherwise, are set with default values:
    %
    %       elem_type = phase_field.init.ElementType.QUAD4;
    %                               % Bulk element type (see
    %                               % phase_field.init.ElementType for possible values)
    %
    %       bound_type = 'LINE2';   % Boundary element type (for the integration of,
    %                               % tractions, reactions, ...; see `dshape` for possible
    %                               % values)
    %
    %       order = 2;              % Quadrature order
    %

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

    arguments
        dim (1, 1) double {mustBeInteger, mustBePositive} = 2
        args.elem_type phase_field.init.ElementType = phase_field.init.ElementType.QUAD4
        args.bound_type {compatiblity.r2020b.mustBeTextScalar, compatiblity.r2020b.mustBeNonzeroLengthText} = 'LINE2'
        args.order (1, 1) double {mustBeInteger, mustBePositive} = 2
    end

    [gauss_pts, gauss_W] = phase_field.fem.quadrature.fe_quadrature(args.elem_type, args.order, dim);
    [gauss_pts_tract, gauss_W_tract] = phase_field.fem.quadrature.fe_quadrature(args.bound_type, args.order, dim-1);

    [Nxi, dNdxi] = phase_field.fem.shape_functions.shape_fcts(args.elem_type, dim, gauss_pts);
    [Nxi_tract, dNdxi_tract] = phase_field.fem.shape_functions.shape_fcts(args.bound_type, dim-1, gauss_pts_tract);

    QUADRATURE.elem_type       = args.elem_type;
    QUADRATURE.bound_type      = args.bound_type;
    QUADRATURE.order           = args.order;
    QUADRATURE.gauss_pts       = gauss_pts;
    QUADRATURE.num_gauss_pts   = size(gauss_pts, 1);
    QUADRATURE.gauss_W         = gauss_W;
    QUADRATURE.dNdxi           = dNdxi;
    QUADRATURE.Nxi             = Nxi;
    QUADRATURE.gauss_pts_tract = gauss_pts_tract;
    QUADRATURE.gauss_W_tract   = gauss_W_tract;
    QUADRATURE.dNdxi_tract     = dNdxi_tract;
    QUADRATURE.Nxi_tract       = Nxi_tract;

end
