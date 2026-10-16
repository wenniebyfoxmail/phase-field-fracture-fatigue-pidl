function result=e011_commit_selftest(work_dir)
%E011_COMMIT_SELFTEST Tiny algebra-only acceptance/transaction guards.
h=zeros(1,1,4);h(:,:,4)=1;
s=struct('u',zeros(2,1),'d',0,'lower',0,'raw',0,'history',h,'version',0);
c=struct('u',zeros(2,1),'d',.2,'raw',.1);
ht=h;ht(:,:,2)=.064;ht(:,:,3)=.064;
p=struct('u',c.u,'d',c.d,'raw',c.raw,'lower',s.lower,'history',h, ...
 'finite',true,'bounds',true,'fixed_bc',true,'joint_pass',true,'criterion',.5, ...
 'native_accepted',true,'history234',ht(:,:,2:4));
t=struct('cycle',1,'substep',1,'arm','repaired');calls=0;
[n,e]=e011_commit_once(s,c,p,t,'repaired',@phase);assert(n.version==1 && e.commits==1 && calls==1);
assert(isequal(s.history,h) && s.version==0 && n.lower==c.d);
reject(@()e011_commit_once(n,c,p,t,'repaired',@phase),'E011:CommitOrder');assert(calls==1);
q=p;q.joint_pass=false;q.criterion=2;
reject(@()e011_commit_once(s,c,q,t,'repaired',@phase),'E011:CommitBeforeJoint');assert(calls==1);
q=p;q.history(:,:,2)=1;
reject(@()e011_commit_once(s,c,q,t,'repaired',@phase),'E011:CommitPreimage');assert(calls==1);
to=t;to.arm='original';q=p;q.joint_pass=false;q.criterion=2;
[n,e]=e011_commit_once(s,c,q,to,'original',@phase);assert(n.version==1 && ~e.precommit_joint_pass && calls==2);
q=p;q.native_accepted=false;
reject(@()e011_commit_once(s,c,q,to,'original',@phase),'E011:NativeAcceptance');assert(calls==2);
reject(@()e011_commit_once(s,c,p,t,'repaired',@broken),'E011:InjectedCommit');assert(s.version==0 && isequal(s.history,h));
% Repeated read-only trial evaluations do not mutate the predecessor/version.
phase(c.d,c.d,c.raw,s.history);phase(c.d,c.d,c.raw,s.history);
assert(s.version==0 && isequal(s.history,h));
assert(~isfolder(work_dir));mkdir(work_dir);cleanup=onCleanup(@()rmdir(work_dir,'s')); %#ok<NASGU>
packet=struct('proposed',n,'event',e);path=fullfile(work_dir,'commit.mat');
e011_persist_once(path,packet);loaded=load(path);assert(isequal(loaded,packet));
reject(@()e011_persist_once(path,packet),'E011:DuplicateReceipt');
accepted=s;failed=false;
try
 e011_persist_once(fullfile(work_dir,'missing_parent','commit.mat'),packet);accepted=n;
catch
 failed=true;
end
assert(failed && isequal(accepted,s));
result=struct('status','passed','cases',10,'file_io_cases',2,'native_field_solves',0);
 function value=phase(d,lower,raw,old)
  calls=calls+1;assert(d==lower && raw==.1 && isequal(old,h));value=ht;
 end
 function value=broken(varargin) %#ok<INUSD,STOUT>
  error('E011:InjectedCommit','Injected before any accepted-state assignment');
 end
end
function reject(f,expected)
try
 f();
catch ex
 assert(strcmp(ex.identifier,expected));return;
end
error('E011:GuardMissing','Expected guard did not fire');
end
