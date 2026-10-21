function result=e036_stage_a_selftest(out_dir)
%E036_STAGE_A_SELFTEST Small mock transactions/readback/hash, no native solve.
% Source preparation only until the producer explicitly executes this entry.
assert(~isfolder(out_dir) && ~isfile(out_dir) && isfolder(fileparts(out_dir)), ...
 'E036A:Output','Selftest needs a new scratch/evidence directory');mkdir(out_dir);
base=e036_selftest();cases=base.cases;events={};
known=fullfile(out_dir,'sha256_abc.bin');fid=fopen(known,'wb');assert(fid>=0);
fwrite(fid,uint8([97 98 99]),'uint8');fclose(fid);
assert(strcmp(e036_sha256_file(known),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'));
record('sha256_known_abc');
old_history=zeros(1,1,4);old_history(:,:,4)=1;
old=struct('lower',[0;0],'history',old_history,'version',0);
state=struct('u',[0;0],'d',[.25;0],'upper',[1;1],'fixed_u_values',0,'fixed_d_values',0);
free=struct('u',1,'d',1,'fixed_u',2,'fixed_d',2);
policy=e036_policy('fresh_original_tolerances','nodal_box_kkt');
[audit,proposal]=e036_final_candidate(@eq,@pf,state,old,free,policy,1);
assert(audit.joint_pass && proposal.version==1 && isequaln(old.history,old_history));
packet=struct('e036_status','validated_proposal_before_native_assignment', ...
 'e036_audit',audit,'e036_proposal',proposal,'e036_old',old);
checkpoint=struct('displ',proposal.u,'p_field',proposal.d,'p_field_old',proposal.lower, ...
 'history_vars_old',proposal.history,'SOL_CYCL_VAR',struct('n_cycle',1),'i_step_completed',1);
key=struct('cycle',1,'substep',1,'n_step',5);
[pfile,cfile]=write_case('accepted',packet,checkpoint);
[readback,loaded]=e036_verify_persisted(pfile,cfile,key);
accepted=old;commits=0;
assert(isequaln(accepted,old));
accepted=struct('lower',loaded.p_field_old,'history',loaded.history_vars_old,'version',readback.version);
commits=commits+1;
assert(commits==1 && accepted.version==1 && isequal(accepted.history,proposal.history));
record('accepted_saved_readback_then_one_assignment');
before=accepted;badstate=state;badstate.d(1)=1.01;
[rejection,rejected_proposal]=e036_final_candidate(@eq,@pf,badstate,old,free,policy,1);
assert(~rejection.joint_pass && ~rejection.feasible && isempty(rejected_proposal));
assert(isequaln(accepted,before) && commits==1 && isequaln(old.history,old_history));
save(fullfile(out_dir,'rejected_candidate.mat'),'old','badstate','rejection','rejected_proposal','before','accepted','commits');
record('rejected_candidate_zero_assignments');
bad=rmfield(checkpoint,'i_step_completed');[pp,cc]=write_case('cycle_end',packet,bad);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:CheckpointSchema');record('cycle_end_missing_step_metadata');
bad=checkpoint;bad.SOL_CYCL_VAR.n_cycle=20;[pp,cc]=write_case('wrong_cycle',packet,bad);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:CheckpointKey');record('wrong_cycle');
bad=checkpoint;bad.history_vars_old(:,:,2)=bad.history_vars_old(:,:,2)+.1;
[pp,cc]=write_case('wrong_history',packet,bad);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:PersistedMismatch');record('wrong_checkpoint_history');
must_reject(@()e036_verify_persisted(pfile,fullfile(out_dir,'missing_checkpoint.mat'),key),'E036:MissingFile');
record('proposal_only');
bad=packet;bad.e036_proposal.version=2;[pp,cc]=write_case('wrong_version',bad,checkpoint);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:Version');record('wrong_version');
bad=packet;bad.e036_audit.policy.joint_tol=1;[pp,cc]=write_case('loosened_policy',bad,checkpoint);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:Policy');record('self_consistent_receipt_with_unapproved_policy');
bad=packet;badc=checkpoint;
bad.e036_proposal.history(:,:,2)=bad.e036_proposal.history(:,:,2)+.1;
bad.e036_proposal.history(:,:,4)=min(1,(1./(bad.e036_proposal.history(:,:,2)+.5)).^2);
bad.e036_audit.history234_solve=bad.e036_proposal.history(:,:,2:4);
bad.e036_audit.f_solve=bad.e036_proposal.history(:,:,4);
bad.e036_audit.f_commit=bad.e036_proposal.history(:,:,4);
badc.history_vars_old=bad.e036_proposal.history;
[pp,cc]=write_case('wrong_update_algebra',bad,badc);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:HistoryMapping');record('coherent_receipt_but_wrong_old_to_new_update');
bad=packet;bad.e036_audit.joint_pass=false;[pp,cc]=write_case('not_accepted',bad,checkpoint);
must_reject(@()e036_verify_persisted(pp,cc,key),'E036:NotAccepted');record('rejected_receipt_cannot_resume');
result=struct('status','passed','cases',cases,'base_cases',base.cases, ...
 'additional_cases',{events},'native_solves',0,'training_updates',0, ...
 'mock_accepted_assignments',1,'mock_rejected_assignments',0, ...
 'scope','software fixtures only; no native numerical or physical proof');
save(fullfile(out_dir,'selftest_result.mat'),'result');
 function [r,raw]=eq(~,~)
  r=[0;0];raw=.4;
 end
 function [r,h]=pf(d,~,raw,history)
  assert(isequal(history,old_history));r=[0;0];h=history;
  h(:,:,1)=raw;h(:,:,3)=(1-d(1))^2*raw;
  h(:,:,2)=history(:,:,2)+max(h(:,:,3)-history(:,:,3),0);
  h(:,:,4)=min(1,(1./(h(:,:,2)+.5)).^2);
 end
 function [pp,cc]=write_case(label,p,c)
  pp=fullfile(out_dir,[label '_proposal.mat']);cc=fullfile(out_dir,[label '_checkpoint.mat']);
  assert(~isfile(pp) && ~isfile(cc));save(pp,'-struct','p','-v7.3');save(cc,'-struct','c','-v7.3');
 end
 function record(label)
  cases=cases+1;events{end+1}=label;
 end
end
function must_reject(callback,identifier)
try
 callback();
catch ex
 assert(strcmp(ex.identifier,identifier),'E036A:WrongRejection','Expected %s, got %s',identifier,ex.identifier);return;
end
error('E036A:MissingRejection','Expected %s',identifier);
end
