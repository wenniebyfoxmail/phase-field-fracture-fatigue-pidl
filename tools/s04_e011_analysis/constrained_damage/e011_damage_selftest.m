function result=e011_damage_selftest()
%E011_DAMAGE_SELFTEST Small deterministic algebra only, before native cases.
A=[2 -1;-1 2];b=[-2;3];lower=[0;0];upper=[1;1];x0=[.4;.5];
f=@(x)deal(sparse(A),A*x-b,zeros(1,1,4));
x=e011_damage_solve(f,x0,lower,upper,[1;2],"constrained",100,1e-10);
assert(x.infeasible_nodes==0 && x.filtered_l2<1e-10 && max(abs(x.d-[0;1]))<1e-9);
% Fresh-only must stop on the returned solution, not on its predecessor.
y=e011_damage_solve(f,x0,lower,upper,[1;2],"fresh_only",10,1e-10);
assert(y.raw_l2<1e-10 && max(abs(A*y.d-b))<1e-10 && y.calls>=2);
assert(y.infeasible_nodes>0); % Low raw R does not imply feasible convergence.
% Fixed DOF and coincident bounds, plus an active node that must be released.
A=speye(3);b=[.3;.7;.8];f=@(d)deal(A,A*d-b,zeros(1,1,4));
z=e011_damage_solve(f,[.2;0;.8],[.2;0;.8],[.2;1;.8],[2;3],"constrained",50,1e-10);
assert(max(abs(z.d-[.2;.7;.8]))<1e-9 && z.filtered_l2<1e-10);
% Budget counts callback evaluations, including unsuccessful trials.
q=e011_damage_solve(f,[.2;0;.8],[.2;0;.8],[.2;1;.8],[2;3],"constrained",2,1e-10);
assert(q.calls<=2 && q.infeasible_nodes==0);
bad=e011_damage_solve(@bad_trial,.2,0,1,1,"constrained",20,1e-10);
assert(bad.stop=="numerical_failure" && bad.d==.2 && bad.last_attempted_d>.5 && bad.last_evaluated_d==.2);
first=e011_damage_solve(@bad_trial,.8,0,1,1,"constrained",20,1e-10);
assert(first.stop=="numerical_failure" && ~first.returned_residual_available && first.d==.8);
result=struct('status','passed','cases',6,'native_field_solves',0);
end

function [K,r,h]=bad_trial(d)
K=speye(1);r=d-.7;h=zeros(1,1,4);if d>.5,r=NaN;end
end
