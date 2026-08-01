classdef ToyRoadSolverDouble < handle
    properties
        DamageMode = 'hit'
        FailNewton = false
        UseNativeExporter = true
        FailAllWrites = false
        FailRunWritesRemaining = 0
        UmaxCycles = zeros(1, 0)
        StepOrdinals = zeros(1, 0)
        LoadFactorsObserved = zeros(1, 0)
        NewtonArgumentCounts = zeros(1, 0)
        PostArgumentCounts = zeros(1, 0)
        ExportStepCounts = zeros(1, 0)
        ExportInputs = cell(1, 0)
        EventCycles = zeros(1, 0)
        WriteNames = strings(1, 0)
        Trace = strings(1, 0)
    end

    methods
        function value = umaxForCycle(self, cycle)
            self.UmaxCycles(end + 1) = cycle;
            value = 0.12;
        end

        function [displ, externalForce, traction] = preIterUpdate(self, iStep, sys, displ, stepPar) %#ok<INUSD>
            self.StepOrdinals(end + 1) = iStep;
            self.LoadFactorsObserved(end + 1) = ...
                sum(stepPar.uy_increment(1:iStep)) / stepPar.uy_final;
            self.Trace(end + 1) = "step_" + iStep;
            externalForce = zeros(size(displ));
            traction = zeros(size(displ));
        end

        function vars = staggeredVars(~, parameters)
            vars = struct('parameters', parameters);
        end

        function [initialResidual, residual, field, rawDriver, auxiliary, failed] = ...
                newtonRaphson(self, assembly, sys, field, varargin) %#ok<INUSD>
            self.NewtonArgumentCounts(end + 1) = 3 + numel(varargin);
            if self.FailNewton
                error('toyRoad:InjectedSolverFailure', 'Injected controlled solver failure.');
            end
            if numel(field) == sys.MESH.num_node
                if strcmp(self.DamageMode, 'hit')
                    field([2 3 5]) = 0.96;
                else
                    field(:) = 0.0;
                end
            end
            initialResidual = 1.0;
            residual = 0.0;
            rawDriver = ones(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
            auxiliary = [];
            failed = false;
        end

        function [vars, rawDriver, converged, stiffness] = postIterUpdate( ...
                self, assembly, iStag, vars, sys, traction, pField, displ, ...
                firstPfResidual, pfResidual, initialDisplResidual, parameters) %#ok<INUSD>
            self.PostArgumentCounts(end + 1) = 11;
            rawDriver = ones(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);
            converged = true;
            stiffness = sys.STIFFNESS_MATRIX.KK;
        end

        function [lhs, residual, tangent, history] = assemblyPf(~, varargin)
            assert(numel(varargin) == 11);
            lhs = [];
            residual = [];
            tangent = [];
            history = varargin{11};
        end

        function [lhs, reaction, rawDriver, tangent] = assemblyEquilibrium(~, varargin)
            assert(numel(varargin) == 11);
            mesh = varargin{1};
            lhs = [];
            reaction = zeros(2 * mesh.num_node, 1);
            rawDriver = ones(mesh.num_elem, 4);
            tangent = [];
        end

        function state = exportPeakState(self, input, outputRoot)
            self.ExportStepCounts(end + 1) = numel(self.StepOrdinals);
            self.ExportInputs{end + 1} = input;
            self.Trace(end + 1) = "export_" + input.metadata.cycle;
            if self.UseNativeExporter
                state = export_toy_road_peak_state(input, outputRoot);
                state.d_node(:) = 0.0;
                state.u(:) = 1e9;
            else
                meshHash = toy_road_mesh_sha256(input.node_coords, input.connectivity);
                state = struct('cycle_index', struct( ...
                    'cycle', input.metadata.cycle, ...
                    'Umax_N', input.metadata.Umax_N, ...
                    'peak_substep_ordinal', input.metadata.peak_substep_ordinal, ...
                    'raw_step_1_based', input.metadata.raw_step_1_based, ...
                    'branch', string(input.metadata.branch), ...
                    'phase', string(input.metadata.phase), ...
                    'file', string(sprintf('states/cycle_%04d.mat', input.metadata.cycle)), ...
                    'mesh_sha256', meshHash));
            end
        end

        function state = advanceEvent(self, state, coords, connectivity, cycle, damage)
            self.EventCycles(end + 1) = cycle;
            self.Trace(end + 1) = "event_" + cycle;
            state = advance_toy_road_event(state, coords, connectivity, cycle, damage);
        end

        function writeJson(self, path, payload)
            [~, name, extension] = fileparts(path);
            fileName = string([name extension]);
            self.WriteNames(end + 1) = fileName;
            self.Trace(end + 1) = "write_" + fileName;
            if self.FailAllWrites
                error('toyRoad:InjectedPublicationFailure', ...
                    'Injected failure publishing %s.', path);
            end
            if fileName == "RUN_RESULT.json" && self.FailRunWritesRemaining > 0
                self.FailRunWritesRemaining = self.FailRunWritesRemaining - 1;
                error('toyRoad:InjectedPublicationFailure', ...
                    'Injected failure publishing %s.', path);
            end
            write_toy_road_json(path, payload);
        end
    end
end
