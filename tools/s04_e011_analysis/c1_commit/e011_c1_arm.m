function result=e011_c1_arm(mode,common,initial_KK,sys,native_eq,native_pf,par,refs,work_dir)
%E011_C1_ARM Independent sequential five-substep arm, one persisted commit/step.
assert(ismember(string(mode),["original","repaired"]) && ~isfolder(work_dir));mkdir(work_dir);
accepted=common;sys.STIFFNESS_MATRIX.KK=initial_KK;rows=[];all_counts=[];
counts=struct('u',0,'d',0);caps=counts;stage="not_started";step=0;out=[];
pre=[];candidate=[];proof=[];proposed=[];event=[];post=[];
try
 for step=1:5
  counts=struct('u',0,'d',0);stage="predictor";pre=accepted;
  out=[];candidate=[];proof=[];proposed=[];event=[];post=[];
  if strcmp(mode,'original'),caps=struct('u',251002,'d',250003);
  else,caps=struct('u',250,'d',250);end
  assert(pre.version==step-1);
  [predicted,res_displ,D_RHS]=phase_field.fem.solver.step.pre_iter_update(step,sys,pre.u,par.step);
  assert(all(D_RHS==0),'This diagnostic is displacement-controlled');
  expected_fixed_u=predicted;step_dir=fullfile(work_dir,sprintf('s%d',step));mkdir(step_dir);
  stage="solve";
  if strcmp(mode,'original')
   out=e011_original_step(sys,@eq_counted,@pf_counted,predicted,pre.d,pre.lower, ...
    pre.history,res_displ,D_RHS,par,step_dir,@read_counts,step);
   candidate=struct('u',out.u,'d',out.d,'raw',out.raw);native_accepted=out.native_accepted;
  else
   limits=struct('admission_u',0,'admission_d',0,'max_u',248,'max_d',247, ...
    'max_outer',20,'u_tol',1e-8,'d_tol',4e-6,'joint_tol',4e-6);
   checkpoint=@(state,trace,calls)save_trial(step_dir,state,trace,calls);
   out=e011_coupled_solve(@matrix_eq,@matrix_pf,predicted,pre.d,pre.lower,ones(size(pre.d)), ...
    sys.DOFS.active_dof,sys.DOFS.active_dof_pf,limits,checkpoint);
   assert(out.counts.u==counts.u && out.counts.d==counts.d,'Controller counter mismatch');
   native_accepted=out.joint_pass;
   if isempty(out.final),error('E011:NoFinal','No completed joint point');end
   candidate=struct('u',out.final.u,'d',out.final.d,'raw',out.final.raw);
  end
  % This audit uses PRE-COMMIT lower/history. Never qualify under new lower.
  stage="precommit_audit";[proof,Kfinal]=audit(candidate,pre,expected_fixed_u);
  proof.native_accepted=native_accepted;
  assert(isequaln(accepted,pre),'Accepted predecessor mutated during trial solves');
  assert(counts.u<=caps.u-1 && counts.d<=caps.d-2,'Commit/postaudit reserve lost');
  save(fullfile(step_dir,'precommit.mat'),'pre','candidate','proof','out','counts','stage','-v7.3');
  if ~native_accepted || (strcmp(mode,'repaired') && ~proof.joint_pass)
   error('E011:StepNotAccepted','No commit or following substep after a solver miss');
  end
  stage="commit_proposal";
  token=struct('cycle',1,'substep',step,'arm',mode);
  [proposed,event]=e011_commit_once(pre,candidate,proof,token,mode,@commit_phase);
  assert(isequaln(accepted,pre),'Accepted state changed before persistence');
  stage="postcommit_readonly_audit";[post,~]=audit(candidate,proposed,expected_fixed_u);
  assert(max(abs(post.history234-proposed.history(:,:,2:4)),[],'all')<=1e-10, ...
   'Committed history is not idempotent at identical final fields');
  reference=struct('required',strcmp(mode,'original'),'pass',true);
  if strcmp(mode,'original')
   z=load(refs(step).target,'request28_snapshot');ref=z.request28_snapshot;
   assert(ref.cycle==1 && ref.substep==step);
   assert(isequal(sys.MESH.node(:,1:2),ref.node_coords) && isequal(sys.MESH.elem(:,1:4),ref.connectivity));
   reference=struct('required',true,'u_maxerr',max(abs(candidate.u-ref.u_node(:))), ...
    'd_maxerr',max(abs(candidate.d-ref.d_node)), ...
    'raw_scaled_maxerr',max(abs(proof.raw-ref.psi_raw_gp)./max(1,abs(ref.psi_raw_gp)),[],'all'), ...
    'history234_scaled_maxerr',max(abs(proposed.history(:,:,2:4)-ref.history_vars_old(:,:,2:4))./max(1,abs(ref.history_vars_old(:,:,2:4))),[],'all'), ...
    'history_H_maxerr',max(abs(proposed.history(:,:,1)-ref.history_vars_old(:,:,1)),[],'all'), ...
    'history_H_finite',all(isfinite(proposed.history(:,:,1)),'all'), ...
    'history_H_nonfinite_count',sum(~isfinite(proposed.history(:,:,1)),'all'), ...
    'reference_H_finite',all(isfinite(ref.history_vars_old(:,:,1)),'all'), ...
    'iterations',out.completed_outer,'expected_iterations',ref.staggered_iterations);
   reference.pass=reference.u_maxerr<=1e-10 && reference.d_maxerr<=1e-10 && ...
    reference.raw_scaled_maxerr<=1e-10 && reference.history234_scaled_maxerr<=1e-10 && ...
    reference.iterations==reference.expected_iterations;
   assert(reference.pass,'E011:BaselineRegression','Original c1 archive regression failed; no repaired arm');
  end
  event.u_calls=counts.u;event.d_calls=counts.d;
  event.uy=sum(par.step.uy_increment(1:step));event.predictor_solves=1;
  stage="persist_once";
  destination=fullfile(step_dir,'accepted_commit.mat');assert(~isfile(destination),'E011:DuplicateReceipt','Never overwrite a commit');
  packet=struct('pre',pre,'candidate',candidate,'proof',proof,'proposed',proposed, ...
   'event',event,'post',post,'reference',reference,'out',out,'counts',counts);
  e011_persist_once(destination,packet);
  % Sole accepted-state assignment, after a complete durable transaction.
  accepted=proposed;sys.STIFFNESS_MATRIX.KK=Kfinal;
  row=struct('step',step,'uy',event.uy,'commits',1,'pre_version',pre.version, ...
   'post_version',accepted.version,'precommit_joint_pass',proof.joint_pass, ...
   'precommit_u_l2',proof.u_l2,'precommit_d_l2',proof.d_feasible_l2, ...
   'precommit_C',proof.criterion,'completed_outer',out.completed_outer, ...
   'u_calls',counts.u,'d_calls',counts.d,'reference_pass',reference.pass);
  if isempty(rows),rows=row;all_counts=counts;else,rows(end+1)=row;all_counts(end+1)=counts;end %#ok<AGROW>
  fprintf('[E011_C1_COMMIT] arm=%s step=%d version=%d C=%.12g\n',mode,step,accepted.version,proof.criterion);
 end
 result=struct('status','completed','arm',mode,'steps',5,'history_commits',accepted.version, ...
  'all_precommit_joint_pass',all([rows.precommit_joint_pass]),'rows',rows, ...
  'total_u_calls',sum([all_counts.u]),'total_d_calls',sum([all_counts.d]),'predictor_solves',5);
 save(fullfile(work_dir,'arm_result.mat'),'result','accepted','-v7.3');
 write_json(fullfile(work_dir,'arm_result.json'),result);
catch ex
 failure=struct('arm',mode,'step',step,'stage',stage,'identifier',ex.identifier, ...
  'message',ex.message,'history_commits',accepted.version,'counts',counts);
 save(fullfile(work_dir,'failure_state.mat'),'failure','accepted','pre','candidate','proof','proposed','event','post','out','-v7.3');
 write_json(fullfile(work_dir,'failure.json'),failure);rethrow(ex);
end
 function value=read_counts()
  value=counts;
 end
 function [kv,r,raw,h]=eq_counted(varargin)
  assert(counts.u<caps.u,'E011:UBudget','Native u cap');counts.u=counts.u+1;
  [kv,r,raw,h]=native_eq(varargin{:});
  assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(raw),'all'));
 end
 function [kv,r,aux,h]=pf_counted(varargin)
  assert(counts.d<caps.d,'E011:DBudget','Native phase cap');counts.d=counts.d+1;
  [kv,r,aux,h]=native_pf(varargin{:});
  assert(all(isfinite(kv)) && all(isfinite(r)) && all(isfinite(h(:,:,2:4)),'all'));
 end
 function [K,r,raw]=matrix_eq(u,d)
  [kv,r,raw,~]=eq_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,u,0.0,d,sys.stress_state.as_number,0.0);
  K=sparse(sys.STIFFNESS_MATRIX.i_row,sys.STIFFNESS_MATRIX.j_col,kv);
 end
 function [K,r,h]=matrix_pf(d,raw)
  [kv,r,~,h]=pf_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d,pre.lower,raw,sys.stress_state.as_number,pre.history);
  K=sparse(sys.STIFFNESS_MATRIX.i_row_pf,sys.STIFFNESS_MATRIX.j_col_pf,kv);
 end
 function h=commit_phase(d,lower,raw,history)
  [~,~,~,h]=pf_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,d,lower,raw,sys.stress_state.as_number,history);
 end
 function [p,K]=audit(c,state,bc)
  [K,ru,raw]=matrix_eq(c.u,c.d);
  [~,rd,~,ht]=pf_counted(sys.MESH,sys.DOFS,sys.GEOM.t,sys.QUADRATURE,sys.MAT_CHAR,sys.CC,c.d,state.lower,raw,sys.stress_state.as_number,state.history);
  assert(max(abs(raw-c.raw)./max(1,abs(raw)),[],'all')<=1e-10,'Candidate raw is stale');
  fu=sys.DOFS.active_dof(:);fd=sys.DOFS.active_dof_pf(:);
  fixed_u=setdiff((1:numel(c.u))',fu);fixed_d=setdiff((1:numel(c.d))',fd);
  q=rd(fd);lo=c.d(fd)<=state.lower(fd)+1e-10;hi=c.d(fd)>=1-1e-10;
  q(lo)=min(q(lo),0);q(hi)=max(q(hi),0);q(lo&hi)=0;
  ur=norm(ru(fu));dr=norm(q);C=max((ur+dr)/4e-6,ur/1e-8);
  finite=all(isfinite(c.u)) && all(isfinite(c.d)) && all(isfinite([ur dr C]));
  bounds=all(c.d>=state.lower-1e-12 & c.d<=1+1e-12);
  fixed_bc=isequal(c.u(fixed_u),bc(fixed_u)) && isequal(c.d(fixed_d),pre.d(fixed_d));
  p=struct('u',c.u,'d',c.d,'raw',raw,'ru',ru,'rd',rd,'history234',ht(:,:,2:4), ...
   'lower',state.lower,'history',state.history,'finite',finite,'bounds',bounds,'fixed_bc',fixed_bc, ...
   'u_l2',ur,'d_feasible_l2',dr,'criterion',C,'joint_pass',finite && bounds && fixed_bc && C<=1, ...
   'native_accepted',false);
 end
end
function save_trial(root,state,trace,calls)
save(fullfile(root,'last_completed_trial.mat'),'state','trace','calls','-v7.3');
end
function write_json(path,value)
fid=fopen(path,'w');assert(fid>=0);cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value));
end
