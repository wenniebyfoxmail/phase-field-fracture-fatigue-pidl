classdef System < handle
    %SYSTEM System configuration for a simulation
    %   ...
    %

    % Copyright (C) 2022 ETH Zurich, SIS ID and CompMech D-MAVT
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

    properties(SetAccess = immutable)
        MAT_CHAR
        BOUNDARY_CONDS
        MESH
        GEOM
        stress_state
        QUADRATURE
        DOFS
        NODE_BOUNDARIES
        diss_fct
        % dependent properties computed in a constructor
        CC (3, 3, :) double
    end
    properties (Dependent)
        num_materials (1, 1) int
        STIFFNESS_MATRIX (1, 1) struct
    end
    properties (Access = private)
        cache_stiffness_matrix
        p_field
    end

    methods
        function value = get.num_materials(obj)
            value = size(obj.MAT_CHAR, 2);
        end

        function value = get.STIFFNESS_MATRIX(obj)
            if isempty(obj.cache_stiffness_matrix)
                obj.cache_stiffness_matrix = phase_field.init.stiffness_matrix(obj, obj.p_field);
            end
            value = obj.cache_stiffness_matrix;
        end
        function set.STIFFNESS_MATRIX(obj, val)
            obj.cache_stiffness_matrix = val;
        end

        function obj = System(MAT_CHAR, GEOM, QUADRATURE, DOFS, ...
            NODE_BOUNDARIES, SOL_STEP_PAR, MESH, stress_state, ...
            p_field, diss_fct...
        )
            %SYSTEM Construct an instance of this class
            arguments
                MAT_CHAR (1, :) struct
                GEOM (1, 1) struct
                QUADRATURE (1, 1) struct
                DOFS (1, 1) struct
                NODE_BOUNDARIES (1, 1) struct
                SOL_STEP_PAR
                MESH (1, 1) struct
                stress_state {compatiblity.r2020b.mustBeA(stress_state, 'phase_field.StressState')}
                p_field (:, 1) double
                diss_fct (1, :) char {mustBeMember(diss_fct, {'AT1', 'AT2', 'PF_CZM'})}
            end

            obj.p_field = p_field;

            obj.MAT_CHAR = MAT_CHAR;
            obj.CC = phase_field.init.elastic_stiffness_matrix([MAT_CHAR.E], [MAT_CHAR.ni], obj.num_materials, stress_state);

            obj.BOUNDARY_CONDS = phase_field.init.boundary_conditions(...
                MESH.elem, NODE_BOUNDARIES.tract_unique, DOFS, SOL_STEP_PAR...
            );
            obj.QUADRATURE = QUADRATURE;
            obj.DOFS = DOFS;
            obj.NODE_BOUNDARIES = NODE_BOUNDARIES;
            obj.MESH = MESH;
            obj.GEOM = GEOM;
            obj.stress_state = stress_state;

            obj.cache_stiffness_matrix = [];
            obj.diss_fct = diss_fct;
        end
    end
end
