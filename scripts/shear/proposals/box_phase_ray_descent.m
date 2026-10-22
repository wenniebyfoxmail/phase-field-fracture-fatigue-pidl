function [alpha,c,report] = box_phase_ray_descent(assemble,linear_solve,alpha,free,opts)
% Piecewise-quadratic ray initial step; original PDAS/native energy Armijo/KKT.
% Same original native PF energy + box. Projection is INSIDE
% constrained optimization, never a post-solve repair. Exact unscaled KKT.
if isfield(opts,'clear_direction'),opts.clear_direction();end
free=free(:);alpha=alpha(:);assert(all(alpha>=0 & alpha<=1),'BOX:Initial','Infeasible initial field');
report=struct('ok',false,'iterations',0,'kkt',Inf,'raw',NaN,'reason','iteration_limit','backtracks',0,'fallbacks',0);
previous_iterate=[];c=evaluate(alpha);
for it=1:opts.max_iter
    opts.check();[~,report.kkt]=box_kkt_residual(alpha,c.R,free);report.raw=norm(c.R(free));report.iterations=it;
    fprintf('BOX_PF iteration=%d kkt=%.9g raw=%.9g min=%.9g max=%.9g\n',it,report.kkt,report.raw,min(alpha),max(alpha));
    if report.kkt<=opts.res_tol,report.ok=true;report.reason='converged_same_assembled_state';return;end
    z=alpha(free)-c.R(free);lower=free(z<=0);upper=free(z>=1);inactive=free(z>0 & z<1);
    bound=[lower;upper];delta=zeros(size(alpha));delta(lower)=-alpha(lower);delta(upper)=1-alpha(upper);
    if ~isempty(inactive)
        delta(inactive)=linear_solve(c.K(inactive,inactive),-c.R(inactive)-c.K(inactive,bound)*delta(bound));
    end
    assert(all(isfinite(delta)),'BOX:Direction','Nonfinite phase direction');
    target=alpha;target(free)=min(1,max(0,alpha(free)+delta(free)));
    s=target-alpha;slope=c.R(free)'*s(free);
    assert(isfinite(slope),'BOX:Nonfinite','Nonfinite target slope');
    % Compare the CLIPPED Newton target against the same native-diagonal
    % projected-gradient target. A tiny negative cancellation is not enough
    % when a strictly stronger feasible first-order descent is available.
    newton_slope=slope;
    D=full(diag(c.K(free,free)));assert(all(isfinite(D) & D>0),'BOX:Diagonal','Invalid exact native positive diagonal');
    pg_target=alpha;pg_target(free)=min(1,max(0,alpha(free)-c.R(free)./D));
    pg_s=pg_target-alpha;pg_slope=c.R(free)'*pg_s(free);
    assert(isfinite(pg_slope) && pg_slope<=0,'BOX:ProjectedGradient','Invalid diagonal projected-gradient slope');
    chosen='projected_newton';
    if pg_slope<0 && slope>pg_slope
        target=pg_target;s=pg_s;slope=pg_slope;chosen='diagonal_projected_gradient';
        report.fallbacks=report.fallbacks+1;
    end
    fprintf('BOX_DIRECTION newton_slope=%.17g diagonal_pg_slope=%.17g chosen=%s\n',newton_slope,pg_slope,chosen);
    assert(isfinite(slope) && slope<0,'BOX:NonDescent','No feasible descent direction');
    direction_witness=struct('newton_slope',newton_slope,'diagonal_pg_slope',pg_slope,'chosen',chosen,'slope',slope,'iteration',it,'lambda0',NaN,'timing','pre_ray_step');
    if isfield(opts,'observe_direction'),opts.observe_direction(alpha,s,c.R,direction_witness);end
    [lambda0,ray_info]=opts.ray_step(alpha,s,slope);
    assert(isfinite(lambda0) && lambda0>0 && lambda0<=1,'BOX:InitialStep','Invalid exact-ray initial step');
    fprintf('BOX_RAY Qbase=%.17g slope0=%.17g slope1=%.17g initial_lambda=%.17g bisections=%d lo=%.17g hi=%.17g analytic_slope0=%.17g slope_mismatch=%.17g\n',ray_info.Qbase,slope,ray_info.slope1,lambda0,ray_info.bisections,ray_info.bracket_lo,ray_info.bracket_hi,ray_info.analytic_slope0,ray_info.slope_mismatch);
    direction_witness.lambda0=lambda0;direction_witness.timing='pre_native_trial';
    if isfield(opts,'observe_direction'),opts.observe_direction(alpha,s,c.R,direction_witness);end
    accepted=false;
    for bt=0:12
        opts.check();lambda=lambda0*.5^bt;
        if lambda==1,trial=target;else,trial=alpha+lambda*s;end
        ct=evaluate(trial);actual_slope=c.R(free)'*(trial(free)-alpha(free));
        fprintf('BOX_TRIAL iteration=%d trial=%d E=%.17g slope=%.17g\n',it,bt,ct.energy,actual_slope);
        armijo=c.energy+1e-4*actual_slope;
        assert(isfinite(actual_slope) && isfinite(armijo),'BOX:Nonfinite','Nonfinite Armijo arithmetic');
        if actual_slope<0 && ct.energy<=armijo
            assert(~isequal(trial,alpha),'BOX:Stalled','Energy line search stalled before KKT');
            assert(isempty(previous_iterate) || ~isequal(trial,previous_iterate),'BOX:Cycle','Exact two-cycle');
            previous_iterate=alpha;alpha=trial;c=ct;accepted=true;report.backtracks=report.backtracks+bt;break;
        end
    end
    assert(accepted,'BOX:LineSearch','Ray-selected initial step plus12halvings exhausted');
end
% Every accepted trial has already been assembled at its actual returned field.
[~,report.kkt]=box_kkt_residual(alpha,c.R,free);report.raw=norm(c.R(free));
report.ok=report.kkt<=opts.res_tol;if report.ok,report.reason='converged_same_assembled_state';end
    function c=evaluate(a)
        opts.check();assert(all(isfinite(a)) && all(a>=0 & a<=1),'BOX:Trial','Invalid feasible trial');
        c=assemble(a);
        assert(isequal(c.u,a) && all(isfinite(c.R)) && all(isfinite(nonzeros(c.K))) && isfinite(c.energy),'BOX:Assembly','Invalid phase assembly/energy');
        opts.check();
    end
end
