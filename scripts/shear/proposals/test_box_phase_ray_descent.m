function test_box_phase_ray_descent()
% A convex SPD problem where clipping nearly cancels Newton first-order descent.
% One update only: implementation test, not a full convergence certificate.
a0=[.5;.5];g0=[.01+1e-8;.01];K=[1,1-1e-12;1-1e-12,1];
opts=struct('max_iter',1,'res_tol',1e-12,'check',@()[],'ray_step',@ray);
[~,old,old_report]=box_phase_ray(@assemble,@(A,b)A\b,a0,[1;2],opts);
[result_alpha,new,new_report]=box_phase_ray_descent(@assemble,@(A,b)A\b,a0,[1;2],opts);
assert(old_report.fallbacks==0 && new_report.fallbacks==1);
assert(new.energy<old.energy-1e-6 && all(result_alpha>=0 & result_alpha<=1));
fprintf('DESCENT_FIXTURE_PASS: feasible diagonal gradient beats nearly cancelling clipped Newton direction\n');
    function c=assemble(point)
        x=point-a0;c=struct('u',point,'K',K,'R',g0+K*x,'energy',g0'*x+.5*x'*K*x);
    end
    function [lambda,info]=ray(~,direction,slope)
        q=direction'*K*direction;lambda=min(1,-slope/q);
        info=struct('Qbase',q,'slope1',slope+q,'bisections',0,'bracket_lo',lambda,'bracket_hi',lambda,'analytic_slope0',slope,'slope_mismatch',0);
    end
end
