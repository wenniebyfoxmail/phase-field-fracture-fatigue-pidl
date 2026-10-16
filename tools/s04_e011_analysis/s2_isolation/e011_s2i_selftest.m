function result=e011_s2i_selftest()
%E011_S2I_SELFTEST Fresh return, raw stop, clip timing and finite linear cases.
for k=1:4
 target=.2*k;out=e011_unbounded_fresh(@(x)linear(x,target),0,0,1,1,5,1e-12);
 assert(strcmp(out.stop,'fresh_tolerance') && abs(out.d-target)<1e-12 && out.raw_l2_before_clip<1e-12);
end
out=e011_unbounded_fresh(@(x)linear(x,-.2),0,0,1,1,5,1e-12);
assert(out.d==0 && abs(out.unclipped+.2)<1e-12 && out.raw_l2_before_clip<1e-12);
out=e011_unbounded_fresh(@(x)linear(x,.5),0,0,1,1,1,1e-12);
assert(strcmp(out.stop,'budget') && out.d==0 && out.calls==1);
out=e011_unbounded_fresh(@nonlinear,.5,0,2,1,20,1e-10);
assert(abs(out.d-1)<1e-9 && out.raw_l2_before_clip<=1e-10);
lim=struct('joint_tol',4e-4,'u_tol',1e-6);
assert(e011_s2i_stop(1e-7,0,.01,lim,0,true)>1);
assert(e011_s2i_stop(1e-7,0,.01,lim,1,true)<1);
assert(e011_s2i_stop(2e-6,0,0,lim,1,true)<1 && e011_s2i_stop(2e-6,0,0,lim,1,false)>1);
assert(strlength(e011_s2i_fatal(struct('last_attempt',struct('d_out',struct('failure',"E011:Nonfinite: rejected trial")))))>0);
assert(strlength(e011_s2i_fatal(struct('last_attempt',struct('u_out',struct('failure',"E011:UBudget: cap")))))==0);
assert(strlength(e011_s2i_fatal(struct('failure',"E011:PredictorMismatch: identity")))>0);
assert(strlength(e011_s2i_fatal(struct('failure',"")))==0);
bad=e011_displacement_solve(@badmechanical,0,1,3,1e-8);assert(strlength(e011_s2i_fatal(struct('last_attempt',struct('u_out',bad))))>0);
bad=e011_damage_solve(@badphase,0,0,1,1,"constrained",3,1e-8);assert(strlength(e011_s2i_fatal(struct('last_attempt',struct('d_out',bad))))>0);
result=struct('status','passed','cases',16,'native_field_solves',0);
end
function [K,r,h]=linear(x,target)
K=sparse(1);r=x-target;h=zeros(1,1,4);h(:,:,4)=1;
end

function [K,r,h]=nonlinear(x)
K=sparse(2*x);r=x*x-1;h=zeros(1,1,4);h(:,:,4)=1;
end

function [K,r,raw]=badmechanical(~)
K=sparse(1);r=NaN;raw=0;
end
function [K,r,h]=badphase(~)
K=sparse(1);r=NaN;h=ones(1,1,4);
end
