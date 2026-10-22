function result=e036_initial_candidate_selftest()
%E036_INITIAL_CANDIDATE_SELFTEST Tiny pure-array checks; no native solver.
key=struct('cycle',1,'substep',2);source=repmat('a',1,64);completed=repmat('b',1,64);prior=repmat('c',1,64);
old=struct('u',zeros(6,1),'d',[0;.2;1],'lower',[0;.2;1],'history',ones(1,4,4));before=old;
initial=struct('u',(1:6)','d',[-.1;.8;2],'state_key',key,'source_snapshot_sha256',source, ...
 'source_completion_sha256',completed,'predecessor_checkpoint_sha256',prior, ...
 'arm','L+','mapping_mode','legacy','complete_endpoint',true);
[state,p]=e036_initial_candidate(initial,old,key,[1;6],[0;.06],3,source,completed,prior);
assert(isequal(state.d,[0;.8;1]) && isequal(state.u,[0;2;3;4;5;.06]));
assert(isequal(p.raw_d,initial.d) && isequal(p.raw_u,initial.u) && ...
 p.d_changed_count==2 && p.u_changed_count==2 && p.d_max_abs_change==1 && ...
 p.history_commits==0 && p.recovery_solves==0 && isequal(old,before));
reject(initial,'source');bad=initial;bad.u(2)=nan;reject(bad,'E036:OracleUnavailable');
bad=initial;bad.history=old.history;reject(bad,'E036:OracleSchema');
bad=initial;bad.complete_endpoint=false;reject(bad,'E036:OracleIdentity');
result=struct('status','passed','cases',5,'native_solves',0,'history_commits',0);
 function reject(candidate,identifier)
  passed=false;
  try
   expected=source;if strcmp(identifier,'source'),expected=repmat('d',1,64);identifier='E036:OracleIdentity';end
   e036_initial_candidate(candidate,old,key,[1;6],[0;.06],3,expected,completed,prior);
  catch ex,passed=strcmp(ex.identifier,identifier);end
  assert(passed,'E036:OracleSelftest','Expected rejection was absent or had the wrong reason');
 end
end
