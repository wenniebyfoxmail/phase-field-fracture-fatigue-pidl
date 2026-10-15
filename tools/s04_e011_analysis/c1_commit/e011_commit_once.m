function [next,event]=e011_commit_once(previous,candidate,proof,token,mode,commit_phase)
%E011_COMMIT_ONCE Build one atomic proposal; caller persists before accepting it.
% Trial assemblies never enter this function. Native order: new lower=d,
% then history(final d,new lower,final raw,OLD accepted history), exactly once.
assert(ismember(string(mode),["original","repaired"]));
assert(token.cycle==1 && token.substep==previous.version+1 && token.substep<=5, ...
 'E011:CommitOrder','Duplicate or out-of-order commit');
assert(strcmp(token.arm,mode) && previous.version>=0);
assert(isequaln(proof.lower,previous.lower) && isequaln(proof.history,previous.history), ...
 'E011:CommitPreimage','Commit proof uses a different predecessor');
assert(isequaln(candidate.u,proof.u) && isequaln(candidate.d,proof.d) && isequaln(candidate.raw,proof.raw));
assert(proof.finite && proof.bounds && proof.fixed_bc,'E011:CommitAdmissibility','Invalid commit candidate');
if strcmp(mode,'repaired')
 assert(proof.joint_pass && proof.criterion<=1,'E011:CommitBeforeJoint','Joint convergence required');
else
 assert(proof.native_accepted,'E011:NativeAcceptance','Original native convergence required');
end
% Pure value inputs: no accepted state changes if callback/assertion throws.
committed_history=commit_phase(candidate.d,candidate.d,candidate.raw,previous.history);
assert(all(isfinite(committed_history(:,:,2:4)),'all'));
assert(max(abs(committed_history(:,:,2:4)-proof.history234),[],'all')<=1e-10, ...
 'E011:CommitHistory','History mapping differs from precommit trial at identical final fields');
next=struct('u',candidate.u,'d',candidate.d,'lower',candidate.d, ...
 'raw',candidate.raw,'history',committed_history,'version',token.substep);
event=struct('cycle',1,'substep',token.substep,'arm',mode, ...
 'pre_version',previous.version,'post_version',next.version,'commits',1, ...
 'precommit_joint_pass',proof.joint_pass,'precommit_criterion',proof.criterion, ...
 'native_accepted',proof.native_accepted,'history_source','final_fields_and_old_accepted_history', ...
 'lower_timing','new_lower_equals_final_damage','history_reset',false);
end
