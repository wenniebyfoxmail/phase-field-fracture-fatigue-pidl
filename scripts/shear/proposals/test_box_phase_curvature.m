function test_box_phase_curvature()
% PROPOSAL ONLY, never run. Same-batch small-array checks before future PDE.
K=eye(2);b=[.2;2];old=[.8;.3];gamma=2;
opts=struct('max_iter',30,'res_tol',1e-12,'check',@()[],'curvature',@ray_bound);
[a,~,r]=box_phase_curvature(@assemble,@(A,f)A\f,[0;0],(1:2)',opts);
assert(r.ok && abs(a(1)-.6)<1e-12 && a(2)==1);
% Purely linear feasible ray: Q=0, constrained optimum at upper face.
[a,~,r]=box_phase_curvature(@linear,@(A,f)A\f,.5,1,struct('max_iter',5,'res_tol',1e-12,'check',@()[],'curvature',@(x,s)0));
assert(r.ok && a==1);
fprintf('CURVATURE_FIXTURES_PASS: piecewise history and zero-curvature ray\n');
    function c=assemble(x)
        gap=x-old;H=diag(double(gap<0));
        c=struct('u',x,'K',K+gamma*H,'R',K*x-b+gamma*min(gap,0),'energy',.5*x'*K*x-b'*x+.5*gamma*sum(min(gap,0).^2));
    end
    function Q=ray_bound(x,s)
        reach=min(x-old,x+s-old)<0;Q=s'*K*s+gamma*sum(reach.*s.^2);
    end
    function c=linear(x)
        c=struct('u',x,'K',0,'R',-1,'energy',-x);
    end
end
