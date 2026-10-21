function [u, cache, report] = bounded_mechanical_newton(assemble, linear_solve, u, active, opts)
% Same residual equations. Armijo on Phi=||R_active||^2/2, no stiffness change.
% Full trial plus at most 12 halvings. Rejected trials do not mutate u/cache.
cache=[]; trial_cache=[]; trial_u=[]; p=[]; attempted_cache=[]; attempted_u=[]; evaluating=false;
i=0; j=-1; t=NaN; slope=NaN; linear_residual=NaN; phi0=NaN; ru0=NaN;
report=struct('ok',false,'reason','','message','','evaluations',0,...
    'updates',0,'trials',0,'backtracks',0,'last_residual',NaN);
try
    cache=evaluate(u);
    for i=1:opts.max_iter
        opts.check();
        r=cache.R(active); ru0=norm(r); phi0=0.5*(r'*r);
        report.last_residual=ru0;
        % Current fresh residual is checked before solving or requiring descent.
        if ru0<=opts.res_tol
            report.ok=true; report.reason='converged'; emit('converged'); return;
        end
        trial_cache=[]; trial_u=[]; p=[]; j=-1; t=NaN; slope=NaN; linear_residual=NaN;
        emit('pre');
        Kaa=cache.K(active,active);
        p=linear_solve(Kaa,-r);
        assert(numel(p)==numel(active) && all(isfinite(p)), 'SHEAR:Direction', 'Invalid Newton direction');
        p=p(:); Kp=Kaa*p;
        linear_residual=norm(Kp+r); slope=r'*Kp;
        emit('direction');
        assert(isfinite(slope) && slope<0, 'SHEAR:NonDescent', 'Non-descent residual-merit direction');
        accepted=false;
        for j=0:opts.max_backtracks
            opts.check(); t=opts.beta^j;
            trial_u=u; trial_u(active)=u(active)+t*p;
            trial_cache=[]; report.trials=report.trials+1;
            trial_cache=evaluate(trial_u);
            rt=trial_cache.R(active); phit=0.5*(rt'*rt);
            emit('trial');
            if phit<=phi0+opts.c1*t*slope
                % All accepted fields/force/tangent/driver come from THIS assembly.
                u=trial_u; cache=trial_cache;
                report.updates=report.updates+1;
                report.backtracks=report.backtracks+j;
                report.last_residual=norm(rt);
                emit('accepted'); accepted=true; break;
            end
        end
        if ~accepted
            report.reason='backtracking_exhausted';
            report.message='Full trial plus12halvings exhausted; origin/cache unchanged';
            emit('failure'); return;
        end
    end
    % The final accepted trial has already been reassembled at its actual u.
    if norm(cache.R(active))<=opts.res_tol
        report.ok=true; report.reason='converged'; emit('converged');
    else
        report.reason='newton_limit'; report.message='500 Newton updates exhausted'; emit('failure');
    end
catch failure
    report.reason='exception'; report.message=failure.message;
    report.identifier=failure.identifier;
    % No further assembly, trial or alternate method after a real failure.
    try, emit('failure'); catch trace_failure, report.trace_error=trace_failure.message; end
end
    function c=evaluate(value)
        opts.check();
        assert(all(isfinite(value)), 'SHEAR:Nonfinite', 'Nonfinite trial displacement');
        attempted_u=value; attempted_cache=[]; evaluating=true;
        report.evaluations=report.evaluations+1;
        c=assemble(value); attempted_cache=c;
        assert(isequal(c.u,value), 'SHEAR:Cache', 'Assembly point/cache mismatch');
        assert(all(isfinite(c.R)) && all(isfinite(nonzeros(c.K))) &&...
            all(isfinite(c.force)) && all(isfinite(c.driver(:))) && isfinite(c.energy),...
            'SHEAR:Nonfinite','Nonfinite native assembly');
        opts.check(); evaluating=false;
    end
    function emit(kind)
        tc=trial_cache;tu=trial_u;
        if strcmp(kind,'failure') && evaluating,tc=attempted_cache;tu=attempted_u;end
        event=struct('kind',kind,'iteration',i,'trial',j,'lambda',t,...
            'cache',cache,'trial_cache',tc,'trial_u',tu,...
            'direction',p,'slope',slope,'linear_residual',linear_residual,...
            'pre_residual',ru0,'pre_merit',phi0,'report',report);
        opts.observe(event);
    end
end
