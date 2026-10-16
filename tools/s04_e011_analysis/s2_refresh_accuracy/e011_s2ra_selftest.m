function result=e011_s2ra_selftest()
% Source-native cached timing versus same-direction fresh timing, algebra only.
names={};lo=struct('u_tol',1e-6,'d_tol',4e-4,'joint_tol',4e-4,'outer_u_tol',4e-4,'max_u',30,'max_d',30,'max_outer',2);hi=lo;hi.u_tol=1e-8;hi.d_tol=4e-6;hi.joint_tol=4e-6;hi.outer_u_tol=1e-8;
[v0,p0]=e011_s2ra_stop(0,0,1e-3,lo,0,1);[v1,p1]=e011_s2ra_stop(0,0,1e-3,lo,1,1);assert(v0==0 && p0 && v1>1 && ~p1);names{end+1}='refresh_routing';
[~,p0]=e011_s2ra_stop(0,6e-5,6e-5,lo,0,1);[~,p1]=e011_s2ra_stop(0,6e-5,6e-5,hi,0,1);assert(p0 && ~p1);names{end+1}='accuracy_thresholds';
[v0,~]=e011_s2ra_stop(2e-8,0,0,hi,1,1);assert(v0==2);names{end+1}='strict_u_outer';
[~,p0]=e011_s2ra_stop(0,0,0,lo,0,0);[~,p1]=e011_s2ra_stop(0,0,0,lo,1,0);assert(~p0 && ~p1);names{end+1}='common_initial_ineligible';
sys=e011_s2ra_fixture_system();
for refresh=0:1
 o=e011_s2ra_mechanical(sys,@(varargin)fixture(1,varargin{:}),0,0,1,8,1e-8,refresh);
 assert(o.policy_pass && abs(o.u-.3)<1e-12 && o.calls==2);names{end+1}=sprintf('linear_R%d',refresh); %#ok<AGROW>
 o=e011_s2ra_mechanical(sys,@(varargin)fixture(2,varargin{:}),.5,0,1,8,.1,refresh);
 assert(o.policy_pass && abs(o.raw-o.evaluated_u^2)<1e-12 && o.calls==3);
 if refresh,assert(abs(o.u-1.025)<1e-12 && o.u==o.evaluated_u);else,assert(abs(o.u-1.0003048780487805)<1e-12 && o.u~=o.evaluated_u);end
 names{end+1}=sprintf('nonlinear_timing_R%d',refresh); %#ok<AGROW>
 o=e011_s2ra_mechanical(sys,@(varargin)fixture(3,varargin{:}),0,0,1,8,1,refresh);assert(o.policy_pass && o.calls==2 && o.u==1);names{end+1}=sprintf('strict_equality_R%d',refresh); %#ok<AGROW>
 o=e011_s2ra_coupled(@zeroeq,@zerophase,@zero_u,0,0,0,1,1,1,lo,@noop,refresh);
 assert(o.policy_pass && o.completed_outer==1 && o.counts.u==4 && o.counts.d==3);names{end+1}=sprintf('mandatory_complete_block_R%d',refresh); %#ok<AGROW>
 o=e011_s2ra_mechanical(sys,@badfixture,0,0,1,8,1e-8,refresh);assert(~o.policy_pass && strlength(e011_s2i_fatal(o))>0);names{end+1}=sprintf('nonfinite_through_catch_R%d',refresh); %#ok<AGROW>
end
result=struct('status','passed','cases',numel(names),'names',{names},'native_field_solves',0);
 function o=zero_u(u,d,b,t,R)
  o=e011_s2ra_mechanical(sys,@(varargin)fixture(0,varargin{:}),u,d,1,b,t,R);
 end
end
function [kv,r,raw,h]=fixture(kind,varargin)
x=varargin{7};if kind==2,kv=2*x;r=x*x-1;elseif kind==3,kv=1;r=x-1;elseif kind==1,kv=1;r=x-.3;else,kv=1;r=x;end
raw=x*x;h=zeros(1,1,4);h(:,:,4)=1;
end
function [K,r,raw]=zeroeq(u,~)
K=sparse(1);r=u;raw=u*u;
end
function [K,r,h]=zerophase(d,~)
K=sparse(1);r=d;h=zeros(1,1,4);h(:,:,4)=1;
end
function noop(varargin)
end
function [kv,r,raw,h]=badfixture(varargin)
kv=1;r=NaN;raw=0;h=zeros(1,1,4);h(:,:,4)=1;
end
