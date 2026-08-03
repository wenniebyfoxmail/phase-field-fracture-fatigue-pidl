classdef ToyRoadP0SolverDouble < handle
    properties
        C5StaggerCount = 3
        C5FinalDelta = 5e-4
        C5MetricFailure = ''
        FailReassemblyOrdinal = 0
        Trace = strings(1, 0)
        CompletedC5Staggers = zeros(1, 0)
        EquilibriumReassemblyCount = 0
        PhaseReassemblyCount = 0
        HistoryCommitCycleStep = zeros(0, 2)
        CycleStarts = zeros(1, 0)
        SubstepStarts = zeros(0, 2)
        GatePassed = false
        FailedRunPublished = false
        ExpectedGateDlb = []
        ExpectedGateHistory = []
        ExpectedGateTraction = []
        ExpectedRawDriver = []
    end

    methods
        function context = makeContext(self, outputRoot, caseId)
            coords = [0 0; 1 0; 1 1; 0 1];
            connectivity = [1 2 3 4];
            meshSha = self.meshSha256(coords, connectivity);
            mesh = struct( ...
                'node_coords', coords, ...
                'connectivity', connectivity, ...
                'connectivity_sha256', self.connectivitySha256(connectivity), ...
                'mesh_sha256', meshSha, ...
                'element_ordering_id', 'q4_connectivity_1_based_v1', ...
                'gp_ordering_id', 'q4_2x2_native_order_v1');
            contract = struct( ...
                'eta', 0, 'alpha_T', 0.5, 'p', 2, ...
                'mesh_sha256', meshSha, ...
                'element_ordering_id', 'q4_connectivity_1_based_v1', ...
                'gp_ordering_id', 'q4_2x2_native_order_v1', ...
                'state_semantics_id', 'five_substep_post_commit_history_v1', ...
                'runtime_lock_sha256', repmat('2', 1, 64), ...
                'family_contract_sha256', repmat('3', 1, 64), ...
                'case_physics_contract_sha256', repmat('4', 1, 64), ...
                'execution_input_lock_sha256', repmat('5', 1, 64));
            state0 = struct('d_node', 0.1 * ones(4,1), ...
                'alpha_bar_gp', zeros(1,4));
            initialState = struct('u', zeros(4,1), ...
                'd', state0.d_node, 'history', state0.alpha_bar_gp);
            operators = struct( ...
                'begin_substep', @(varargin) self.beginSubstep(varargin{:}), ...
                'completed_stagger_update', ...
                    @(varargin) self.completedStaggerUpdate(varargin{:}), ...
                'reassemble_equilibrium', ...
                    @(varargin) self.reassembleEquilibrium(varargin{:}), ...
                'reassemble_phase', ...
                    @(varargin) self.reassemblePhase(varargin{:}), ...
                'commit_history', @(varargin) self.commitHistory(varargin{:}), ...
                'observe', @(varargin) self.observe(varargin{:}), ...
                'publish_failed_run', ...
                    @(varargin) self.publishFailedRun(varargin{:}));
            context = struct( ...
                'authorization_scope', 'TEST_ONLY_NON_AUTHORIZING_SCOPE', ...
                'case_id', caseId, ...
                'output_root', outputRoot, ...
                'cycle_limit', 5, ...
                'active_u_dofs', [1;2], ...
                'active_d_dofs', [1;2], ...
                'state0', state0, ...
                'mesh', mesh, ...
                'contract', contract, ...
                'initial_state', initialState, ...
                'sol_step_template', struct('n_step', 99, 'line_search', false), ...
                'sol_stag_par', struct('max_iter', 8), ...
                'operators', operators);
        end

        function [state, traction] = beginSubstep(self, cycle, ordinal, ...
                state, stepTemplate)
            assert(stepTemplate.n_step == 5 && ~stepTemplate.line_search, ...
                'toyRoadP0:ControlledContractMismatch', ...
                'The solver did not force the five-step template.');
            if ordinal == 1
                self.CycleStarts(end + 1) = cycle;
            end
            self.SubstepStarts(end + 1,:) = [cycle ordinal];
            state.u = state.u + (cycle * 10 + ordinal) * 1e-6;
            traction = (cycle * 10 + ordinal) + (1:numel(state.u)).' / 100;
            if cycle == 5 && ordinal == 4
                self.ExpectedGateDlb = state.d;
                self.ExpectedGateHistory = state.history;
                self.ExpectedGateTraction = traction;
            end
        end

        function [state, psiRaw, converged] = completedStaggerUpdate( ...
                self, cycle, ordinal, stagger, state, traction, dLb, historyPre)
            assert(isequal(traction, (cycle * 10 + ordinal) + ...
                (1:numel(state.u)).' / 100));
            assert(isequal(dLb, state.d) || cycle == 5 && ordinal == 4);
            assert(isequal(historyPre, state.history));
            if cycle == 5 && ordinal == 4
                target = self.C5StaggerCount;
                assert(stagger <= target);
                if stagger < target
                    delta = 2e-3;
                elseif strcmp(self.C5MetricFailure, 'stagger')
                    delta = 2e-3;
                else
                    delta = self.C5FinalDelta;
                end
                state.d(1) = state.d(1) + delta;
                if strcmp(self.C5MetricFailure, 'primal') && stagger == target
                    state.d(1) = 1 + 2e-12;
                end
                self.CompletedC5Staggers(end + 1) = stagger;
                converged = stagger == target;
            else
                state.d(1) = state.d(1) + 1e-4;
                converged = true;
            end
            state.u(1) = state.u(1) + 1e-6;
            psiRaw = (cycle + ordinal / 10) * ones(1,4);
            self.ExpectedRawDriver = psiRaw;
        end

        function [residual, rawDriver] = reassembleEquilibrium(self, snapshot, u, d)
            self.assertGateSnapshot(snapshot);
            assert(isequal(size(u), [4 1]) && isequal(size(d), [4 1]));
            self.EquilibriumReassemblyCount = self.EquilibriumReassemblyCount + 1;
            residual = zeros(size(u));
            if strcmp(self.C5MetricFailure, 'displacement')
                residual(1) = 8e-4;
            else
                residual(1) = 1e-5;
            end
            rawDriver = self.ExpectedRawDriver;
        end

        function residual = reassemblePhase(self, snapshot, u, d, rawDriver)
            self.assertGateSnapshot(snapshot);
            assert(isequal(size(u), [4 1]) && isequal(size(d), [4 1]));
            assert(isequal(rawDriver, self.ExpectedRawDriver));
            ordinal = self.PhaseReassemblyCount + 1;
            if self.FailReassemblyOrdinal == ordinal
                error('toyRoadP0:InjectedReassemblyFailure', ...
                    'Injected controlled phase reassembly failure.');
            end
            self.PhaseReassemblyCount = ordinal;
            residual = zeros(size(d));
            if strcmp(self.C5MetricFailure, 'kkt')
                residual(1) = 8e-4;
            else
                residual(1) = 1e-5;
            end
        end

        function historyPost = commitHistory(self, cycle, ordinal, historyPre, snapshot)
            assert(snapshot.cycle == cycle && snapshot.substep_ordinal == ordinal);
            if cycle == 5 && ordinal == 4
                assert(self.GatePassed, 'toyRoadP0:ControlledContractMismatch', ...
                    'c5/s4 history commit happened before the PASS receipt.');
            end
            self.HistoryCommitCycleStep(end + 1,:) = [cycle ordinal];
            historyPost = historyPre + 1e-3;
        end

        function observe(self, event)
            event = string(event);
            if startsWith(event, "c5_")
                self.Trace(end + 1) = event;
            end
            if event == "c5_gate_receipt_passed"
                self.GatePassed = true;
            end
        end

        function publishFailedRun(self, outputRoot, authorizationScope, caseId, exception)
            path = fullfile(outputRoot, 'RUN_RESULT.json');
            if isfile(path) || isfolder(path) || ~java.io.File(path).createNewFile()
                error('toyRoadP0:PublicationClobber', ...
                    'Refusing to overwrite the controlled failed run receipt.');
            end
            payload = struct( ...
                'authorization_scope', authorizationScope, ...
                'case_id', caseId, ...
                'complete', false, ...
                'status', 'failed', ...
                'error_identifier', exception.identifier, ...
                'error_message', exception.message);
            fileId = fopen(path, 'wt');
            assert(fileId >= 0);
            cleanup = onCleanup(@() fclose(fileId));
            fprintf(fileId, '%s\n', jsonencode(payload));
            self.FailedRunPublished = true;
        end
    end

    methods (Access = private)
        function assertGateSnapshot(self, snapshot)
            assert(isequal(snapshot.d_lb, self.ExpectedGateDlb));
            assert(isequal(snapshot.d_entry, self.ExpectedGateDlb));
            assert(isequal(snapshot.history_pre, self.ExpectedGateHistory));
            assert(isequal(snapshot.traction, self.ExpectedGateTraction));
            assert(isequal(snapshot.active_u_dofs, [1;2]));
            assert(isequal(snapshot.active_d_dofs, [1;2]));
        end

        function digest = connectivitySha256(~, connectivity)
            payload = sprintf('%dx%d:', size(connectivity,1), size(connectivity,2));
            payload = [payload sprintf('%d,', connectivity.')];
            digest = ToyRoadP0SolverDouble.sha256(unicode2native(payload, 'UTF-8'));
        end

        function digest = meshSha256(~, coords, connectivity)
            bytes = [reshape(typecast(double(coords(:)), 'uint8'), 1, []) ...
                reshape(typecast(int64(connectivity(:)), 'uint8'), 1, [])];
            digest = ToyRoadP0SolverDouble.sha256(bytes);
        end
    end

    methods (Static, Access = private)
        function digest = sha256(bytes)
            hasher = java.security.MessageDigest.getInstance('SHA-256');
            hasher.update(bytes);
            digestBytes = typecast(hasher.digest(), 'uint8');
            digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
        end
    end
end
