classdef ToyRoadRecoveryDouble < handle
    properties
        Contract = struct()
        Trace = strings(1, 0)
        Systems = cell(1, 0)
        FactoryDamageInputs = cell(1, 0)
        NewtonCallCount = 0
        ReuseInitialSystem = false
        InvalidRecoveredFieldShape = false
        ReturnNonConverged = false
        RecoveredField = [-0.25; 0.2; 0.6; 1.25; -2.0; 3.0]
        InitialResidual = 101.25
        RecoveryResidual = 202.5
        CouplingOutput = (301:306)'
        RecoveredHistory
    end

    methods
        function self = ToyRoadRecoveryDouble(contract)
            self.Contract = contract;
            history = zeros(2, 4, 4);
            history(:, :, 1) = reshape(401:408, 2, 4);
            history(:, :, 2) = 502;
            history(:, :, 3) = 603;
            history(:, :, 4) = 0.25;
            self.RecoveredHistory = history;
        end

        function sys = systemFactory(self, matChar, geom, quadrature, dofs, ...
                nodeBoundaries, solStepPar, mesh, stressState, pField, dissFct)
            self.assertSame(matChar, self.Contract.mat_char, 'System MAT_CHAR');
            self.assertSame(geom, self.Contract.geom, 'System GEOM');
            self.assertSame(quadrature, self.Contract.quadrature, 'System QUADRATURE');
            self.assertSame(dofs, self.Contract.dofs, 'System DOFS');
            self.assertSame(nodeBoundaries, self.Contract.node_boundaries, ...
                'System NODE_BOUNDARIES');
            self.assertSame(solStepPar, self.Contract.sol_step_par, ...
                'System SOL_STEP_PAR');
            self.assertSame(mesh, self.Contract.mesh, 'System MESH');
            self.assertSame(stressState, self.Contract.stress_state, ...
                'System stress_state');
            self.assertSame(dissFct, self.Contract.diss_fct, 'System diss_fct');
            self.FactoryDamageInputs{end + 1} = pField;
            if isempty(self.Systems)
                label = "factory_initial";
            else
                label = "factory_clipped";
            end
            self.Trace(end + 1) = label;
            if self.ReuseInitialSystem && ~isempty(self.Systems)
                sys = self.Systems{1};
                self.Systems{end + 1} = sys;
                return;
            end
            sys = ToyRoadRecoverySystem(matChar, geom, quadrature, dofs, ...
                nodeBoundaries, solStepPar, mesh, stressState, pField, dissFct, ...
                self.Contract.stiffness_matrix);
            self.Systems{end + 1} = sys;
        end

        function [initialResidual, residual, field, coupling, history, failed] = ...
                newtonRaphson(self, assembly, sys, field, fieldOld, couplingIn, ...
                historyOld, activeDof, iRow, jCol, varargin)
            self.NewtonCallCount = self.NewtonCallCount + 1;
            self.Trace(end + 1) = "newton";
            self.assertSame(assembly, self.Contract.assembly_pf_fh, ...
                'Newton assembly handle');
            self.assertContract(sys == self.Systems{1}, 'Newton initial System identity');
            self.assertSame(field, self.Contract.initial_p_field, 'Newton field_vars');
            self.assertSame(fieldOld, self.Contract.initial_p_field_old, ...
                'Newton field_vars_old');
            self.assertSame(couplingIn, self.Contract.zero_raw_driver, ...
                'Newton coupling_vars_in');
            self.assertSame(historyOld, self.Contract.initial_history, ...
                'Newton history_vars_old');
            self.assertSame(activeDof, self.Contract.dofs.active_dof_pf, ...
                'Newton active_dof');
            self.assertSame(iRow, self.Contract.stiffness_matrix.i_row_pf, ...
                'Newton i_row');
            self.assertSame(jCol, self.Contract.stiffness_matrix.j_col_pf, ...
                'Newton j_col');
            expectedOptions = {'max_iter', self.Contract.sol_par.max_iter_pf, ...
                'res_tol', self.Contract.sol_par.tol_p_field, ...
                'line_search', false, 'regularize_pf_only', true};
            self.assertSame(varargin, expectedOptions, 'Newton name-value options');

            initialResidual = self.InitialResidual;
            residual = self.RecoveryResidual;
            field = self.RecoveredField;
            if self.InvalidRecoveredFieldShape
                field = field(1:end - 1);
            end
            coupling = self.CouplingOutput;
            history = self.RecoveredHistory;
            failed = self.ReturnNonConverged;
        end
    end

    methods (Access = private)
        function assertSame(~, actual, expected, label)
            assert(isequaln(actual, expected), 'toyRoad:RecoveryContractMismatch', ...
                'Controlled recovery contract mismatch: %s.', label);
        end

        function assertContract(~, condition, label)
            assert(condition, 'toyRoad:RecoveryContractMismatch', ...
                'Controlled recovery contract mismatch: %s.', label);
        end
    end
end
