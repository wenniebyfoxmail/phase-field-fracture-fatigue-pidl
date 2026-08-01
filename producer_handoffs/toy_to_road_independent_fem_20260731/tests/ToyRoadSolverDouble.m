classdef ToyRoadSolverDouble < handle
    properties
        DamageMode = 'hit'
        FailNewton = false
        UseNativeExporter = true
        FailAllWrites = false
        FailRunWritesRemaining = 0
        InjectRunCleanupFailure = false
        LastRunPublication = struct()
        Contract = struct()
        ExpectedDispl = []
        ExpectedPField = []
        ExpectedPFieldOld = []
        ExpectedHistory = []
        ExpectedStiffness = []
        ExpectedTraction = []
        LastStagVars = struct()
        InsideNewtonAssembly = false
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
        PreIterContractChecks = 0
        StagVarsContractChecks = 0
        DisplacementNewtonContractChecks = 0
        PhaseNewtonContractChecks = 0
        StaggeredPostContractChecks = 0
        EquilibriumAssemblyContractChecks = 0
        PhaseAssemblyContractChecks = 0
        HistoryUpdateContractChecks = 0
        StateFlowContractChecks = 0
    end

    methods
        function configure(self, contract)
            self.Contract = contract;
            self.ExpectedDispl = contract.initial_displ;
            self.ExpectedPField = contract.initial_p_field;
            self.ExpectedPFieldOld = contract.initial_p_field_old;
            self.ExpectedHistory = contract.initial_history;
            self.ExpectedStiffness = contract.initial_stiffness;
        end

        function value = umaxForCycle(self, cycle)
            self.UmaxCycles(end + 1) = cycle;
            value = 0.12;
        end

        function [displ, externalForce, traction] = preIterUpdate( ...
                self, iStep, sys, displ, stepPar)
            expectedStep = mod(numel(self.StepOrdinals), 5) + 1;
            self.assertContract(iStep == expectedStep, 'pre_iter_update current step');
            self.assertSystem(sys);
            self.assertSame(displ, self.ExpectedDispl, 'pre_iter_update displacement');
            self.assertSame(sys.STIFFNESS_MATRIX.KK, self.ExpectedStiffness, ...
                'pre_iter_update current stiffness');
            self.assertContract(stepPar.n_step == 5, 'SOL_STEP_PAR.n_step');
            self.assertContract(stepPar.line_search == false, 'SOL_STEP_PAR.line_search');
            self.assertContract(stepPar.uy_final == 0.12, 'SOL_STEP_PAR.uy_final');
            self.assertSame(stepPar.ux_increment, zeros(1, 5), ...
                'SOL_STEP_PAR.ux_increment');
            self.assertSame(stepPar.uy_increment, ...
                0.12 * [0.25 0.25 0.25 0.25 -1.0], ...
                'SOL_STEP_PAR.uy_increment');
            self.assertSame(stepPar.tx_increment, zeros(1, 5), ...
                'SOL_STEP_PAR.tx_increment');
            self.assertSame(stepPar.ty_increment, zeros(1, 5), ...
                'SOL_STEP_PAR.ty_increment');
            self.assertContract(stepPar.contract_tag == 818, ...
                'SOL_STEP_PAR identity sentinel');

            dirichletIncrement = [ ...
                repmat(stepPar.ux_increment(iStep), ...
                    numel(sys.NODE_BOUNDARIES.disp_X), 1); ...
                repmat(stepPar.uy_increment(iStep), ...
                    numel(sys.NODE_BOUNDARIES.disp_Y), 1)];
            displ(sys.DOFS.non_hom_dirichlet_bc) = ...
                displ(sys.DOFS.non_hom_dirichlet_bc) + dirichletIncrement;
            self.ExpectedDispl = displ;

            self.StepOrdinals(end + 1) = iStep;
            self.LoadFactorsObserved(end + 1) = ...
                sum(stepPar.uy_increment(1:iStep)) / stepPar.uy_final;
            self.Trace(end + 1) = "step_" + iStep;
            externalForce = 8100 + (1:numel(displ))' / 100;
            traction = 8200 + numel(self.StepOrdinals) + (1:numel(displ))' / 100;
            self.ExpectedTraction = traction;
            self.PreIterContractChecks = self.PreIterContractChecks + 1;
            self.StateFlowContractChecks = self.StateFlowContractChecks + 1;
        end

        function vars = staggeredVars(self, parameters)
            self.assertSame(parameters, self.Contract.sol_stag_par, ...
                'stag.vars SOL_STAG_PAR');
            vars = struct('contract_tag', 8300 + numel(self.StepOrdinals), ...
                'parameters', parameters);
            self.LastStagVars = vars;
            self.StagVarsContractChecks = self.StagVarsContractChecks + 1;
        end

        function [initialResidual, residual, field, couplingOut, historyNew, failed] = ...
                newtonRaphson(self, assembly, sys, field, fieldOld, couplingIn, ...
                historyOld, activeDof, iRow, jCol, varargin)
            self.NewtonArgumentCounts(end + 1) = 9 + numel(varargin);
            self.assertSystem(sys);
            self.assertSame(sys.STIFFNESS_MATRIX.KK, self.ExpectedStiffness, ...
                'newton current stiffness');
            if isequal(assembly, self.Contract.assembly_equilibrium_fh)
                self.assertSame(field, self.ExpectedDispl, 'equilibrium field_vars');
                self.assertSame(fieldOld, 0.0, 'equilibrium field_vars_old');
                self.assertSame(couplingIn, self.ExpectedPField, ...
                    'equilibrium coupling_vars_in');
                self.assertSame(historyOld, 0.0, 'equilibrium history_vars_old');
                self.assertSame(activeDof, self.Contract.active_dof, ...
                    'equilibrium active_dof');
                self.assertSame(iRow, self.Contract.i_row, 'equilibrium i_row');
                self.assertSame(jCol, self.Contract.j_col, 'equilibrium j_col');
                expectedOptions = {'D_RHS_tract', self.ExpectedTraction, ...
                    'max_iter', self.Contract.sol_par.max_iter_displ, ...
                    'res_tol', self.Contract.sol_par.tol_displ, ...
                    'line_search', false};
                self.assertSame(varargin, expectedOptions, ...
                    'equilibrium Newton name-value order');
                self.InsideNewtonAssembly = true;
                [stiffnessVector, assemblyResidual, couplingOut, historyNew] = ...
                    assembly(sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, ...
                    sys.MAT_CHAR, sys.CC, field, fieldOld, couplingIn, ...
                    sys.stress_state.as_number, historyOld);
                self.InsideNewtonAssembly = false;
                self.assertSize(stiffnessVector, [numel(self.Contract.i_row) 1], ...
                    'equilibrium stiffness vector');
                self.assertSize(assemblyResidual, [numel(field) 1], ...
                    'equilibrium residual vector');
                self.assertSize(couplingOut, [2 4], ...
                    'equilibrium coupling output');
                initialResidual = 1001.0;
                residual = 0.001;
                self.DisplacementNewtonContractChecks = ...
                    self.DisplacementNewtonContractChecks + 1;
            else
                self.assertContract(isequal(assembly, self.Contract.assembly_pf_fh), ...
                    'phase assembly handle');
                self.assertSame(field, self.ExpectedPField, 'phase field_vars');
                self.assertSame(fieldOld, self.ExpectedPFieldOld, ...
                    'phase field_vars_old');
                self.assertSame(couplingIn, self.Contract.raw_driver, ...
                    'phase coupling_vars_in');
                self.assertSame(historyOld, self.ExpectedHistory, ...
                    'phase history_vars_old');
                self.assertSame(activeDof, self.Contract.active_dof_pf, ...
                    'phase active_dof');
                self.assertSame(iRow, self.Contract.i_row_pf, 'phase i_row');
                self.assertSame(jCol, self.Contract.j_col_pf, 'phase j_col');
                expectedOptions = {'max_iter', self.Contract.sol_par.max_iter_pf, ...
                    'res_tol', self.Contract.sol_par.tol_p_field, ...
                    'line_search', false, 'regularize_pf_only', true};
                self.assertSame(varargin, expectedOptions, ...
                    'phase Newton name-value order');
                self.InsideNewtonAssembly = true;
                [stiffnessVector, assemblyResidual, couplingOut, historyNew] = ...
                    assembly(sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, ...
                    sys.MAT_CHAR, sys.CC, field, fieldOld, couplingIn, ...
                    sys.stress_state.as_number, historyOld);
                self.InsideNewtonAssembly = false;
                self.assertSize(stiffnessVector, [numel(self.Contract.i_row_pf) 1], ...
                    'phase stiffness vector');
                self.assertSize(assemblyResidual, [numel(field) 1], ...
                    'phase residual vector');
                self.assertSize(historyNew, size(self.ExpectedHistory), ...
                    'phase history output');
                if strcmp(self.DamageMode, 'hit')
                    field([2 3 5]) = 0.96;
                else
                    field(:) = 0.0;
                end
                self.ExpectedPField = field;
                initialResidual = 2002.0;
                residual = 0.002;
                self.PhaseNewtonContractChecks = self.PhaseNewtonContractChecks + 1;
            end
            if self.FailNewton
                error('toyRoad:InjectedSolverFailure', 'Injected controlled solver failure.');
            end
            failed = false;
        end

        function [vars, rawDriver, converged, stiffness] = postIterUpdate( ...
                self, assembly, iStag, vars, sys, traction, pField, displ, ...
                firstPfResidual, pfResidual, initialDisplResidual, parameters)
            self.PostArgumentCounts(end + 1) = 11;
            self.assertContract(isequal(assembly, self.Contract.assembly_equilibrium_fh), ...
                'stag.post_iter_update assembly handle');
            self.assertContract(iStag == 1, 'stag.post_iter_update i_stag');
            self.assertSame(vars, self.LastStagVars, 'stag.post_iter_update variables');
            self.assertSystem(sys);
            self.assertSame(traction, self.ExpectedTraction, ...
                'stag.post_iter_update D_RHS_tract');
            self.assertSame(pField, self.ExpectedPField, ...
                'stag.post_iter_update p_field');
            self.assertSame(displ, self.ExpectedDispl, ...
                'stag.post_iter_update displ');
            self.assertContract(firstPfResidual == 2002.0, ...
                'stag.post_iter_update res_pf_0');
            self.assertContract(pfResidual == 0.002, ...
                'stag.post_iter_update res_pf');
            self.assertContract(initialDisplResidual == 1001.0, ...
                'stag.post_iter_update res_displ_0');
            self.assertSame(parameters, self.Contract.sol_stag_par, ...
                'stag.post_iter_update SOL_STAG_PAR');

            [stiffnessVector, reaction, rawDriver, historyOut] = assembly( ...
                sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, ...
                sys.CC, displ, 0.0, pField, sys.stress_state.as_number, 0.0);
            self.assertSize(stiffnessVector, [numel(self.Contract.i_row) 1], ...
                'post-update stiffness vector');
            self.assertSize(reaction, [numel(displ) 1], ...
                'post-update residual vector');
            self.assertSize(rawDriver, [2 4], 'post-update coupling output');
            self.assertSame(historyOut, 0.0, 'post-update history output');
            stiffness = sparse(self.Contract.i_row, self.Contract.j_col, ...
                stiffnessVector, numel(displ), numel(displ));
            self.ExpectedStiffness = stiffness;
            converged = true;
            self.StaggeredPostContractChecks = self.StaggeredPostContractChecks + 1;
        end

        function [stiffnessVector, residual, coupling, history] = assemblyPf( ...
                self, mesh, dofs, thickness, quadrature, matChar, cc, pField, ...
                pFieldOld, rawDriver, stressState, historyOld)
            self.assertAssemblySystem(mesh, dofs, thickness, quadrature, matChar, ...
                cc, stressState);
            self.assertSame(historyOld, self.ExpectedHistory, ...
                'phase assembly history_vars_old');
            if self.InsideNewtonAssembly
                self.assertSame(pField, self.ExpectedPField, ...
                    'phase Newton assembly p_field');
                self.assertSame(pFieldOld, self.ExpectedPFieldOld, ...
                    'phase Newton assembly p_field_old');
                self.assertSame(rawDriver, self.Contract.raw_driver, ...
                    'phase Newton assembly coupling');
            else
                self.assertSame(pField, self.ExpectedPField, ...
                    'global history update p_field');
                self.assertSame(pFieldOld, self.ExpectedPField, ...
                    'global history update p_field_old');
                self.assertSame(rawDriver, self.Contract.raw_driver, ...
                    'global history update coupling');
                self.ExpectedPFieldOld = pFieldOld;
                self.HistoryUpdateContractChecks = self.HistoryUpdateContractChecks + 1;
            end
            stiffnessVector = 30 + (1:numel(self.Contract.i_row_pf))' / 100;
            residual = 40 + (1:numel(pField))' / 100;
            coupling = self.Contract.raw_driver + 0.25;
            history = historyOld;
            history(:, :, 2) = history(:, :, 2) + 0.001;
            if ~self.InsideNewtonAssembly
                self.ExpectedHistory = history;
            end
            self.PhaseAssemblyContractChecks = self.PhaseAssemblyContractChecks + 1;
        end

        function [stiffnessVector, residual, rawDriver, history] = ...
                assemblyEquilibrium(self, mesh, dofs, thickness, quadrature, ...
                matChar, cc, displ, displOld, pField, stressState, historyOld)
            self.assertAssemblySystem(mesh, dofs, thickness, quadrature, matChar, ...
                cc, stressState);
            self.assertSame(displ, self.ExpectedDispl, ...
                'equilibrium assembly displ');
            self.assertSame(displOld, 0.0, 'equilibrium assembly displ_old');
            self.assertSame(pField, self.ExpectedPField, ...
                'equilibrium assembly coupling p_field');
            self.assertSame(historyOld, 0.0, ...
                'equilibrium assembly history input');
            stiffnessVector = 50 + (1:numel(self.Contract.i_row))' / 100;
            residual = 60 + (1:numel(displ))' / 100;
            rawDriver = self.Contract.raw_driver;
            history = 0.0;
            self.EquilibriumAssemblyContractChecks = ...
                self.EquilibriumAssemblyContractChecks + 1;
        end

        function state = exportPeakState(self, input, outputRoot)
            self.ExportStepCounts(end + 1) = numel(self.StepOrdinals);
            self.ExportInputs{end + 1} = input;
            self.Trace(end + 1) = "export_" + input.metadata.cycle;
            self.assertSame(input.displ, self.ExpectedDispl, 'export displacement');
            self.assertSame(input.p_field, self.ExpectedPField, 'export phase field');
            self.assertSame(input.history_vars, self.ExpectedHistory, 'export history');
            self.assertSame(input.psi_raw_gp, self.Contract.raw_driver, ...
                'export peak raw driver');
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
            self.assertSame(damage, self.ExpectedPField, 'event peak damage');
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
            if fileName == "RUN_RESULT.json" && self.InjectRunCleanupFailure
                operations = struct('delete_temp', @self.throwRunCleanupFailure);
                self.LastRunPublication = write_toy_road_json(path, payload, operations);
            else
                write_toy_road_json(path, payload);
            end
        end

        function throwRunCleanupFailure(~, varargin)
            error('toyRoad:InjectedPostLinkCleanupFailure', ...
                'Injected RUN_RESULT cleanup failure after commit.');
        end
    end

    methods (Access = private)
        function assertSystem(self, sys)
            self.assertAssemblySystem(sys.MESH, sys.DOFS, sys.GEOM.t, ...
                sys.QUADRATURE, sys.MAT_CHAR, sys.CC, ...
                sys.stress_state.as_number);
            self.assertSame(sys.STIFFNESS_MATRIX.i_row, self.Contract.i_row, ...
                'System stiffness i_row');
            self.assertSame(sys.STIFFNESS_MATRIX.j_col, self.Contract.j_col, ...
                'System stiffness j_col');
            self.assertSame(sys.STIFFNESS_MATRIX.i_row_pf, self.Contract.i_row_pf, ...
                'System phase stiffness i_row');
            self.assertSame(sys.STIFFNESS_MATRIX.j_col_pf, self.Contract.j_col_pf, ...
                'System phase stiffness j_col');
            self.assertSame(sys.NODE_BOUNDARIES, self.Contract.node_boundaries, ...
                'System NODE_BOUNDARIES');
        end

        function assertAssemblySystem(self, mesh, dofs, thickness, quadrature, ...
                matChar, cc, stressState)
            self.assertSame(mesh, self.Contract.mesh, 'assembly MESH');
            self.assertSame(dofs, self.Contract.dofs, 'assembly DOFS');
            self.assertSame(thickness, self.Contract.thickness, 'assembly GEOM.t');
            self.assertSame(quadrature, self.Contract.quadrature, ...
                'assembly QUADRATURE');
            self.assertSame(matChar, self.Contract.mat_char, 'assembly MAT_CHAR');
            self.assertSame(cc, self.Contract.cc, 'assembly CC');
            self.assertSame(stressState, self.Contract.stress_state_number, ...
                'assembly stress_state.as_number');
        end

        function assertSame(~, actual, expected, label)
            assert(isequaln(actual, expected), 'toyRoad:ControlledContractMismatch', ...
                'Controlled clean-API contract mismatch: %s.', label);
        end

        function assertSize(~, value, expectedSize, label)
            assert(isequal(size(value), expectedSize), ...
                'toyRoad:ControlledContractMismatch', ...
                'Controlled clean-API return-shape mismatch: %s.', label);
        end

        function assertContract(~, condition, label)
            assert(condition, 'toyRoad:ControlledContractMismatch', ...
                'Controlled clean-API contract mismatch: %s.', label);
        end
    end
end
