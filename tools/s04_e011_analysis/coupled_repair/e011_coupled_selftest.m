function result=e011_coupled_selftest()
%E011_COUPLED_SELFTEST Algebra only: same-state closure, budgets, failures.
limits=struct('admission_u',0,'admission_d',0,'max_u',100,'max_d',100, ...
 'max_outer',20,'u_tol',1e-8,'d_tol',4e-6,'joint_tol',4e-6);
eq=@(u,d)deal(speye(1),u-(.2+.2*d),u);
pf=@(d,raw)deal(speye(1),d-.2*raw,zeros(1,1,4));
x=e011_coupled_solve(eq,pf,.5,.1,0,1,1,1,limits,@no_checkpoint);
assert(x.joint_pass && x.final.u_l2<=1e-8 && x.final.sum_l2<=4e-6);
assert(x.first_u.u_l2<=1e-8 && x.first_u.d_feasible_l2>x.initial.d_feasible_l2);
assert(x.completed_outer<=20 && x.counts.u<=100 && x.counts.d<=100);
% Global budget must preserve initial complete point, not perform extra calls.
budget=limits;budget.max_u=2;budget.max_d=2;
y=e011_coupled_solve(eq,pf,.5,.1,0,1,1,1,budget,@no_checkpoint);
assert(~y.joint_pass && y.stop=="assembly_budget" && y.completed_outer==0);
assert(y.final.u==.5 && y.final.d==.1 && y.counts.u<=2 && y.counts.d<=2);
% Explicit threshold sliver: phase alone passes, strict joint remains a miss.
eqgap=@(u,d)deal(speye(1),5e-9,0); %#ok<INUSD>
pfgap=@(d,raw)deal(speye(1),3.999e-6,zeros(1,1,4)); %#ok<INUSD>
z=e011_coupled_solve(eqgap,pfgap,0,.5,0,1,1,1,limits,@no_checkpoint);
assert(~z.joint_pass && z.stop=="exact_stagnation" && z.completed_outer==1);
% Phase fails after u succeeds; half block cannot replace the complete point.
f=e011_coupled_solve(eq,@bad_phase,.5,.1,0,1,1,1,limits,@no_checkpoint);
assert(~f.joint_pass && f.stop=="damage_inner_miss" && f.completed_outer==0);
assert(f.final.u==.5 && f.final.d==.1 && ~isempty(f.last_attempt));
% Mechanical prescribed DOF and fresh-return identity.
A=[2 -1;-1 2];b=[1;2];em=@(u)deal(sparse(A),A*u-b,u);
u=e011_displacement_solve(em,[.3;0],2,10,1e-12);
assert(u.stop=="fresh_tolerance" && u.u(1)==.3 && abs(u.u(2)-1.15)<1e-12);
assert(norm((A*u.u-b)-u.r)<1e-12 && isequal(u.u,u.raw));
% Failed mechanical trial retains last evaluated returned point.
bad=e011_displacement_solve(@bad_mechanical,.5,1,10,1e-8);
assert(bad.stop=="numerical_failure" && bad.u==.5 && bad.last_attempted_u<.3);
result=struct('status','passed','cases',6,'native_field_solves',0);
end
function no_checkpoint(varargin) %#ok<INUSD>
end
function [K,r,h]=bad_phase(d,raw)
K=speye(1);r=d-.2*raw;h=zeros(1,1,4);if raw<.3,r=NaN;end
end
function [K,r,raw]=bad_mechanical(u)
K=speye(1);r=u-.2;raw=u;if u<.3,r=NaN;end
end
