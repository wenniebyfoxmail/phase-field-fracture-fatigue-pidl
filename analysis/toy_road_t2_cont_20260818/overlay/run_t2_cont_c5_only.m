function result = run_t2_cont_c5_only(enterC5S4, solveStage)
% Diagnostic adapter: callers supply sealed entry and raw stage solve handles.
arguments
    enterC5S4 (1,1) function_handle
    solveStage (1,1) function_handle
end
entry = enterC5S4();
localRequire(entry.cycle == 5 && entry.substep == 4, ...
    'T2-CONT entry must be the T2 c5/s4 subproblem.');
accepted = entry.state;
fixedDamageLowerBound = entry.state.d_lb;
fixedHistory = entry.state.history_pre;
lambda = 0;
step = 1/4;
attempt = 0;
rows = struct([]);
while attempt < 24
    attempt = attempt + 1;
    if attempt == 1
        trialLambda = 0;
        trialStep = 0;
    else
        trialLambda = min(1, lambda + step);
        trialStep = trialLambda - lambda;
    end
    gc = 0.010 - 0.002 * trialLambda;
    trial = solveStage(gc, accepted, fixedDamageLowerBound, fixedHistory);
    passed = localPasses(trial);
    rows(attempt).lambda = trialLambda;
    rows(attempt).Gc = gc;
    rows(attempt).step = trialStep;
    rows(attempt).accepted = passed;
    rows(attempt).stagger_count = trial.stagger_count;
    if ~passed
        if attempt == 1
            result = localResult('FAIL_T2_CONT_ANCHOR_NONCONVERGENCE', rows);
            return
        end
        if trialStep <= 1/128
            result = localResult('FAIL_T2_CONT_MIN_STEP_AT_C5_S4', rows);
            return
        end
        step = trialStep / 2;
        continue
    end
    localRequire(isequal(trial.state.d_lb, fixedDamageLowerBound), ...
        'Damage lower bound changed during continuation.');
    localRequire(isequal(trial.state.history_pre, fixedHistory), ...
        'History changed during continuation.');
    accepted = trial.state;
    lambda = trialLambda;
    if lambda == 1
        result = localResult( ...
            'PASS_TARGET_C5_S4_ONLY_NEEDS_SEPARATE_FULL_T2_AUTHORIZATION', rows);
        result.state = accepted;
        return
    end
    if trial.stagger_count <= 250
        step = min(1-lambda, 2*trialStep);
    elseif trial.stagger_count <= 750
        step = min(1-lambda, trialStep);
    else
        step = min(1-lambda, trialStep/2);
    end
    step = max(step, 1/128);
end
result = localResult('FAIL_T2_CONT_ATTEMPT_CAP_AT_C5_S4', rows);
end

function passed = localPasses(trial)
passed = trial.newton_converged && trial.native_stagger_converged && ...
    trial.stagger_count >= 1 && trial.stagger_count <= 1000 && ...
    trial.displacement_residual <= 4e-4 && ...
    trial.projected_phase_kkt <= 4e-4 && ...
    trial.consecutive_damage_inf <= 1e-3 && ...
    trial.primal_feasibility <= 1e-12;
end

function result = localResult(classification, rows)
result = struct('diagnostic_only_nonproduction', true, ...
    'classification', classification, 'attempts', rows, ...
    'trajectory_authorized', false);
end

function localRequire(condition, message)
if ~condition
    error('toyRoadT2Cont:ContractViolation', '%s', message);
end
end
