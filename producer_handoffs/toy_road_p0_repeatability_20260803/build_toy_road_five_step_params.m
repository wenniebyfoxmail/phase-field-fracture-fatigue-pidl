function stepPar = build_toy_road_five_step_params(umax)
%BUILD_TOY_ROAD_FIVE_STEP_PARAMS Build the complete locked Hard5 step object.

if ~(isa(umax,'double') && isreal(umax) && isscalar(umax) && ...
        isfinite(umax) && umax > 0)
    error('toyRoadP0:InvalidFiveStepLoading', ...
        'Hard5 Umax must be a positive finite double scalar.');
end

warningState = warning;
cleanup = onCleanup(@() warning(warningState));
warning('off','all');
evalc(['stepPar = phase_field.fem.solver.step.params(' ...
    '''n_step'',5,''loading'',''cyclic'',''discretization'',''loading'',' ...
    '''uy_final'',umax,''R'',0,''line_search'',false);']);

factors = [0.25 0.50 0.75 1.00 0.00];
stepPar.n_step = 5;
stepPar.loading = 'cyclic';
stepPar.discretization = 'loading';
stepPar.uy_final = umax;
stepPar.R = 0;
stepPar.line_search = false;
stepPar.ux_increment = zeros(1,5);
stepPar.uy_increment = umax*diff([0 factors]);
stepPar.tx_increment = zeros(1,5);
stepPar.ty_increment = zeros(1,5);

increments = {'ux_increment','uy_increment','tx_increment','ty_increment'};
complete = stepPar.n_step == 5 && ~stepPar.line_search && ...
    all(cellfun(@(name) isequal(size(stepPar.(name)),[1 5]),increments)) && ...
    isequal(stepPar.ux_increment,zeros(1,5)) && ...
    isequal(stepPar.tx_increment,zeros(1,5)) && ...
    isequal(stepPar.ty_increment,zeros(1,5)) && ...
    isequal(stepPar.uy_increment,umax*diff([0 factors]));
if ~complete
    error('toyRoadP0:InvalidFiveStepLoading', ...
        'The locked Hard5 step object is incomplete or inconsistent.');
end
end
