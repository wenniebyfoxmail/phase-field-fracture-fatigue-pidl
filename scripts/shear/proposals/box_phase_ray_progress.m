function [alpha,c,report]=box_phase_ray_progress(assemble,linear_solve,alpha,free,opts)
% Original native constrained energy/KKT; rank actual acceptable ray energies.
% No iteration/backtrack budget. Stop only on convergence or real numerical failure.
if isfield(opts,'clear_direction'),opts.clear_direction();end
free=free(:);alpha=alpha(:);assert(all(isfinite(alpha)) && all(alpha>=0 & alpha<=1));
report=struct('ok',false,'iterations',0,'kkt',Inf,'raw',NaN,'reason','','backtracks',0,'fallbacks',0);
previous_iterate=[];c=evaluate(alpha);it=0;
while true
    it=it+1;opts.check();[~,report.kkt]=box_kkt_residual(alpha,c.R,free);
    report.raw=norm(c.R(free));report.iterations=it;
    fprintf('BOX_PF iteration=%d kkt=%.9g raw=%.9g min=%.9g max=%.9g\n',it,report.kkt,report.raw,min(alpha),max(alpha));
    if report.kkt<=opts.res_tol,report.ok=true;report.reason='converged_same_assembled_state';return;end
    z=alpha(free)-c.R(free);lower=free(z<=0);upper=free(z>=1);inactive=free(z>0 & z<1);
    bound=[lower;upper];delta=zeros(size(alpha));delta(lower)=-alpha(lower);delta(upper)=1-alpha(upper);
    if ~isempty(inactive)
        delta(inactive)=linear_solve(c.K(inactive,inactive),-c.R(inactive)-c.K(inactive,bound)*delta(bound));
    end
    assert(all(isfinite(delta)),'BOX:Direction','Nonfinite Newton direction');
    nt=alpha;nt(free)=min(1,max(0,alpha(free)+delta(free)));
    D=full(diag(c.K(free,free)));assert(all(isfinite(D) & D>0),'BOX:Diagonal','Invalid exact native diagonal');
    pt=alpha;pt(free)=min(1,max(0,alpha(free)-c.R(free)./D));
    nc=candidate(nt,'projected_newton');pc=candidate(pt,'diagonal_projected_gradient');
    assert(nc.ok || pc.ok,'BOX:NoRepresentableDescent','Neither ray has a representable native-energy Armijo step');
    use_pg=pc.ok && (~nc.ok || pc.cache.energy<nc.cache.energy);
    if use_pg,chosen=pc;report.fallbacks=report.fallbacks+1;else,chosen=nc;end
    en=Inf;ep=Inf;if nc.ok,en=nc.cache.energy;end;if pc.ok,ep=pc.cache.energy;end
    fprintf('BOX_PROGRESS iteration=%d E_origin=%.17g E_newton=%.17g E_pg=%.17g chosen=%s lambda=%.17g\n',it,c.energy,en,ep,chosen.label,chosen.lambda);
    assert(~isequal(chosen.cache.u,alpha),'BOX:Stalled','No representable phase update before KKT');
    assert(isempty(previous_iterate) || ~isequal(chosen.cache.u,previous_iterate),'BOX:Cycle','Exact two-cycle');
    previous_iterate=alpha;alpha=chosen.cache.u;
    % phase_assembly's diagnostic capture must also identify the selected point.
    if use_pg,c=chosen.cache;else,c=evaluate(alpha);end
    report.backtracks=report.backtracks+chosen.backtracks;
    if isfield(opts,'observe_direction')
        witness=struct('chosen',chosen.label,'iteration',it,'lambda0',chosen.lambda,'newton_energy',en,'pg_energy',ep,'timing','selected_native_trial');
        opts.observe_direction(previous_iterate,alpha-previous_iterate,chosen.origin_R,witness);
    end
end
    function result=candidate(target,label)
        s=target-alpha;slope=c.R(free)'*s(free);
        assert(isfinite(slope),'BOX:Nonfinite','Nonfinite ray slope');
        result=struct('ok',false,'cache',[],'label',label,'lambda',NaN,'backtracks',0,'origin_R',c.R);
        if slope>=0,return;end
        [lambda,ray]=opts.ray_step(alpha,s,slope);
        assert(isfinite(lambda) && lambda>0 && lambda<=1);
        bt=0;
        while true
            opts.check();if lambda==1,trial=target;else,trial=alpha+lambda*s;end
            if lambda==0 || isequal(trial,alpha),return;end
            actual_slope=c.R(free)'*(trial(free)-alpha(free));
            assert(isfinite(actual_slope));
            if isfield(opts,'observe_direction')
                witness=struct('chosen',label,'iteration',it,'lambda0',lambda,'slope',slope,'Qbase',ray.Qbase,'timing','pre_candidate_native_trial');
                opts.observe_direction(alpha,s,c.R,witness);
            end
            ct=evaluate(trial);armijo=c.energy+1e-4*actual_slope;
            assert(isfinite(armijo));
            fprintf('BOX_CANDIDATE iteration=%d direction=%s trial=%d lambda=%.17g E=%.17g actual_slope=%.17g\n',it,label,bt,lambda,ct.energy,actual_slope);
            if actual_slope<0 && ct.energy<=armijo
                result.ok=true;result.cache=ct;result.lambda=lambda;result.backtracks=bt;return;
            end
            lambda=lambda*.5;bt=bt+1;
        end
    end
    function value=evaluate(a)
        opts.check();assert(all(isfinite(a)) && all(a>=0 & a<=1),'BOX:Trial','Invalid feasible trial');
        value=assemble(a);
        assert(isequal(value.u,a) && all(isfinite(value.R)) && all(isfinite(nonzeros(value.K))) && isfinite(value.energy),'BOX:Assembly','Invalid native assembly/energy');
    end
end
