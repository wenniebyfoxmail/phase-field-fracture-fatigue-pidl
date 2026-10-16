function result=e011_s2dj_selftest()
% Tiny deterministic tolerance/solver/stop routing; no mesh field solve.
names={};
for P=0:1
 for J=0:1
  t=e011_s2dj_limits(P,J);
  assert(abs(t.d_tol-4e-4*(.01^P))<1e-18 && abs(t.u_tol-1e-6*(.01^J))<1e-18);
  assert(abs(t.joint_tol-4e-4*(.01^J))<1e-18);
  if J,assert(t.outer_u_tol==1e-8);else,assert(t.outer_u_tol==4e-4);end
  assert(t.max_outer==20 && t.max_u==248 && t.max_d==248);
  o=e011_damage_solve(@phase,.3-6e-5,0,1,1,"constrained",8,t.d_tol);
  assert(strlength(o.failure)==0 && o.filtered_l2<=t.d_tol);
  if P,assert(abs(o.d-.3)<1e-12 && o.calls==2);else,assert(o.d==.3-6e-5 && o.calls==1);end
  names{end+1}=sprintf('damage_inner_P%dJ%d',P,J); %#ok<AGROW>
  [~,ok]=e011_s2ra_stop(2e-5,1e-6,1e-6,t,1,1);assert(ok==(J==0));
  [~,initial]=e011_s2ra_stop(0,0,0,t,1,0);assert(~initial);
  names{end+1}=sprintf('joint_policy_P%dJ%d',P,J); %#ok<AGROW>
 end
end
result=struct('status','passed','cases',numel(names),'names',{names},'native_field_solves',0);
end
function [K,r,h]=phase(d)
K=sparse(1);r=d-.3;h=zeros(1,1,4);h(:,:,4)=1;
end
