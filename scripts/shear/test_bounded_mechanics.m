function test_bounded_mechanics()
% Small arrays only. No FEM input, MEX assembly, optimizer or training.
events={};calls=0;opts=struct('max_iter',500,'max_backtracks',12,...
    'beta',0.5,'c1',1e-4,'res_tol',1e-6,'check',@()0,'observe',@collect);
[u,c,r]=bounded_mechanical_newton(@linear,@(K,b)K\b,[0;9],1,opts);
assert(r.ok && abs(u(1)-1)<1e-12 && u(2)==9 && c.driver==u(1));
assert(r.evaluations==2 && r.updates==1);
[~,~,r]=bounded_mechanical_newton(@linear,@never_solve,[1;9],1,opts);
assert(r.ok && r.updates==0 && r.evaluations==1);
[~,~,r]=bounded_mechanical_newton(@linear,@(K,b)-K\b,[0;9],1,opts);
assert(~r.ok && strcmp(r.identifier,'SHEAR:NonDescent') && r.evaluations==1);
[u,c,r]=bounded_mechanical_newton(@wrong_tangent,@(K,b)K\b,0,1,opts);
assert(~r.ok && strcmp(r.reason,'backtracking_exhausted') && u==0 && c.R==-1 && r.evaluations==14);
[u,c,r]=bounded_mechanical_newton(@nonlinear,@(K,b)K\b,0.1,1,opts);
assert(r.ok && abs(u-1)<1e-6 && r.backtracks>0 && c.driver==u^2);
for k=1:numel(events)
 e=events{k};if strcmp(e.kind,'accepted'),assert(isequal(e.cache.u,e.trial_u));end
end
calls=0;[u,c,r]=bounded_mechanical_newton(@throw_trial,@(K,b)K\b,0,1,opts);
assert(~r.ok && strcmp(r.identifier,'FIXTURE:Assembly') && calls==2 && u==0 && c.R==-1);
o=opts;o.check=@budget_fail;
[~,~,r]=bounded_mechanical_newton(@linear,@never_solve,[0;9],1,o);
assert(~r.ok && strcmp(r.identifier,'FIXTURE:Budget') && r.evaluations==0);
calls=0;[u,c,r]=bounded_mechanical_newton(@nonfinite_trial,@(K,b)K\b,0,1,opts);
assert(~r.ok && strcmp(r.identifier,'SHEAR:Nonfinite') && calls==2 && u==0 && c.R==-1);
[~,~,r]=bounded_mechanical_newton(@huge_merit,@never_solve,0,1,opts);
assert(~r.ok && contains(r.message,'Nonfinite residual merit') && r.evaluations==1);
calls=0;[u,c,r]=bounded_mechanical_newton(@huge_trial,@(K,b)K\b,0,1,opts);
assert(~r.ok && contains(r.message,'Nonfinite trial merit') && calls==2 && u==0 && c.R==-1 && r.trials==1);
fprintf('BOUNDED_NEWTON_FIXTURES_PASS count=10; no FEM/model/training executed.\n');
    function collect(e),events{end+1}=e;end
    function c=linear(u),K=diag([2,1]);c=pack(u,K,[2*u(1)-2;u(2)-9],u(1));end
    function c=wrong_tangent(u),c=pack(u,-1,u-1,u);end
    function c=nonlinear(u),c=pack(u,3*u^2,u^3-1,u^2);end
    function c=throw_trial(u)
        calls=calls+1;if calls>1,error('FIXTURE:Assembly','Real assembly failure');end
        c=pack(u,1,u-1,u);
    end
    function c=nonfinite_trial(u)
        calls=calls+1;c=pack(u,1,u-1,u);if calls>1,c.R=NaN;c.force=NaN;end
    end
    function c=huge_merit(u),c=pack(u,1,1e200,0);end
    function c=huge_trial(u)
        calls=calls+1;c=pack(u,1,u-1,0);if calls>1,c.R=1e200;c.force=1e200;end
    end
    function p=never_solve(~,~),error('FIXTURE:UnexpectedSolve','Should not solve');p=[];end %#ok<UNRCH>
    function budget_fail(),error('FIXTURE:Budget','Step budget fixture');end
end
function c=pack(u,K,R,driver)
c=struct('u',u,'K',K,'R',R,'force',R,'driver',driver,'energy',0.5*(u'*K*u));
end
