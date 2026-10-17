function result=e011_s2uj_selftest()
% Actual fresh mechanical helper routing on tiny algebraic fixture, no mesh.
names={};sys=e011_s2ra_fixture_system();
for U=0:1
 for J=0:1
  t=e011_s2uj_limits(U,J);
  assert(t.d_tol==4e-6 && abs(t.u_tol-1e-6*(.01^U))<1e-18);
  assert(abs(t.joint_tol-4e-4*(.01^J))<1e-18);
  if J,assert(t.outer_u_tol==1e-8);else,assert(t.outer_u_tol==4e-4);end
  assert(t.max_outer==20 && t.max_u==248 && t.max_d==248);
  o=e011_s2ra_mechanical(sys,@mechanical,.3-5e-7,0,1,8,t.u_tol,1);
  assert(o.policy_pass && o.u==o.evaluated_u && o.residual_l2<t.u_tol);
  if U,assert(abs(o.u-.3)<1e-12 && o.calls==2);else,assert(o.u==.3-5e-7 && o.calls==1);end
  names{end+1}=sprintf('mechanical_inner_U%dJ%d',U,J); %#ok<AGROW>
  [~,ok]=e011_s2ra_stop(2e-5,1e-6,1e-6,t,1,1);assert(ok==(J==0));
  [~,initial]=e011_s2ra_stop(0,0,0,t,1,0);assert(~initial);
  names{end+1}=sprintf('joint_outer_U%dJ%d',U,J); %#ok<AGROW>
 end
end
result=struct('status','passed','cases',numel(names),'names',{names},'native_field_solves',0);
end
function [kv,r,raw,h]=mechanical(varargin)
u=varargin{7};kv=1;r=u-.3;raw=u*u;h=zeros(1,1,4);h(:,:,4)=1;
end
