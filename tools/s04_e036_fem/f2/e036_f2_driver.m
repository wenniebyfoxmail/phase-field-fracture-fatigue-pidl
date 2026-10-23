function result=e036_f2_driver(config_file,config_sha256)
%E036_F2_DRIVER Isolated c1s4 F2 producer; no primary F1 substitution.
% Stage A chain/runtime guards below copied from e036_stage_b_driver.m,
% source SHA256 a494893086548cc707ccd67c69fc225a9f78d906f32459fa541c510b07239098. Only helper inventory/path expands to f2/.
% Preparation does not grant dispatch: explicit F2 authority and source lock required.
checked(config_file,config_sha256);c=jsondecode(fileread(config_file));
required(c,{'run_root','code_root','native_snapshot','overlay_root','build_root', ...
 'build_completion_sha256','manifest_path','manifest_sha256','runtime_bindings','source_checks', ...
 'common_file','common_sha256','mesh_file','mesh_sha256','output_dir','watchdog_id', ...
 'execution_approved','provenance','source_commit','authority_file','authority_sha256', ...
 'stage_a_root','stage_a_evidence_file','stage_a_evidence_sha256','request','predecessor', ...
 'f2','f2_source_lock_file','f2_source_lock_sha256'});
assert(isequal(c.execution_approved,true),'E036F2:Authority','Explicit F2 execution approval required');
assert(c.request.cycle==1 && isequal(c.request.substeps(:)',4) && strcmp(c.request.role,'f2_solver') && ...
 isequal(sort(fieldnames(c.request)),sort({'cycle';'substeps';'role'})) && ...
 ~any(isfield(c,{'pairs','target','targets','initial_fields'})),'E036F2:Scope','Only F2 c1s4 original predictor');
required(c.f2,{'method','limits','primary_F1_replacement'});
assert(strcmp(c.f2.method,'F2-frozen-f-nodal-box-u-d-u') && isequal(c.f2.primary_F1_replacement,false));
assert(isequal(c.f2.limits,struct('max_outer',1500,'u_maxeval',250,'d_maxeval',250,'f_tol',1e-10,'d_inner_tol',4e-8)));
[budget,approval]=e036_stage_b_authority(c);clock=budget.total_timer;root=char(c.run_root);
required(approval,{'f2','f2_source_lock_sha256','root_dispatch_approved'});
assert(isequal(approval.root_dispatch_approved,true) && isequal(approval.f2,c.f2) && ...
 strcmp(approval.f2_source_lock_sha256,c.f2_source_lock_sha256), ...
 'E036F2:Authority','Prepared F2 authority is not dispatch approval or differs from source/method');
assert(budget.max_threads==4 && budget.total_wall_seconds==86400 && budget.step_wall_seconds==43200 && ...
 isempty(budget.global_deadline));
for name={'code_root','native_snapshot','overlay_root','build_root','manifest_path','common_file', ...
 'mesh_file','output_dir','stage_a_evidence_file','f2_source_lock_file'}
 inside(c.(name{1}),root);
end
checked(c.f2_source_lock_file,c.f2_source_lock_sha256);lock=jsondecode(fileread(c.f2_source_lock_file));
assert(strcmp(lock.schema,'e036-f2-source-lock-v1') && strcmp(lock.status,'committed_exact_source') && ...
 strcmp(lock.source_commit,c.provenance.adapter_commit));
for k=1:numel(lock.files)
 p=fullfile(c.code_root,lock.files(k).path);inside(p,c.code_root);checked(p,lock.files(k).sha256);
end
assert(strcmpi(canonical(which('e036_f2_driver')),canonical(fullfile(c.code_root,'tools','s04_e036_fem','f2','e036_f2_driver.m'))));
assert(~isfile(c.output_dir) && ~isfolder(c.output_dir) && isfolder(fileparts(c.output_dir)));
assert(java.io.File(char(c.output_dir)).mkdir());stage='stage_a_evidence';result=[];
try
 evidence=stage_a_pass(c);check();stage='runtime_binding';[resolutions,cfg,options]=bind_runtime(c,approval);check();
 actual=dir(fullfile(c.code_root,'tools','s04_e036_fem','f2','*.m'));
 for k=1:numel(actual)
  [~,name]=fileparts(actual(k).name);p=fullfile(actual(k).folder,actual(k).name);
  assert(strcmpi(canonical(which(name)),canonical(p)),'E036F2:Resolution','Unexpected F2 function resolution');
 end
 reuse=struct('schema','e036-f2-stage-a-reuse-v1','accepted',true,'stage_a_reexecuted',false, ...
  'stage_a_evidence_file',c.stage_a_evidence_file,'stage_a_evidence_sha256',c.stage_a_evidence_sha256, ...
  'runtime_bindings',{resolutions},'config_sha256',config_sha256,'f2_source_lock_sha256',c.f2_source_lock_sha256);
 write_json(fullfile(c.output_dir,'stage_a_reuse_audit.json'),reuse);
 save(fullfile(c.output_dir,'driver_binding.mat'),'c','config_sha256','approval','evidence', ...
  'resolutions','cfg','budget','lock','-v7.3');check();
 stage='native_context';[sys,par,common,binding]=e036_stage_b_context(cfg,options,budget);check();
 eq=str2func('phase_field.mex.fem.assembly.equilibrium.AMOR');
 pf=str2func('phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE');
 stage='predecessor_admission';[pre,admission]=e036_f2_predecessor(sys,eq,pf,common,binding, ...
  c.predecessor,c.request,budget,fullfile(c.output_dir,'predecessor'));check();
 policy=e036_policy('fresh_strict_e011','nodal_box_kkt');
 support=struct('nodes',sys.MESH.node(:,1:2),'cells',sys.MESH.elem(:,1:4), ...
  'Nxi',sys.QUADRATURE.Nxi,'dNdxi',sys.QUADRATURE.dNdxi,'gauss_W',sys.QUADRATURE.gauss_W, ...
  'active_u',sys.DOFS.active_dof(:),'active_d',sys.DOFS.active_dof_pf(:), ...
  'fixed_damage_nodes_zero_based',[4;5;(695:943)'], ...
  'ordered_mesh_sha256_f32_i64','c675e3fd05399cf16cc56884396f46b2af9e6b8e3c5c349e188246692d8bc174');
 authority=struct('execution_approved',true,'approval_id',approval.authority_id, ...
  'producer_hostname',approval.producer_hostname,'run_id',c.watchdog_id,'source_commit',c.source_commit, ...
  'adapter_commit',c.provenance.adapter_commit,'f2_source_lock_sha256',c.f2_source_lock_sha256, ...
  'manifest_sha256',c.manifest_sha256,'native_bindings_verified',true, ...
  'native_eq_name',func2str(eq),'native_pf_name',func2str(pf),'thread_controls_verified',true, ...
  'watchdog_id',c.watchdog_id,'request',c.request,'policy',policy,'limits',c.f2.limits, ...
  'method',c.f2.method,'binding',support,'predecessor_sha256',c.predecessor.sha256);
 stage='f2_candidate';result=e036_f2_run_step(sys,eq,pf,par,pre,c.request,policy,budget,authority, ...
  c.f2.limits,fullfile(c.output_dir,'f2'));check();
 checked(config_file,config_sha256);checked(c.manifest_path,c.manifest_sha256);
 checked(c.f2_source_lock_file,c.f2_source_lock_sha256);checked(c.predecessor.path,c.predecessor.sha256);
 report=struct('status',result.status,'method',c.f2.method,'request',c.request,'history_commits',result.history_commits, ...
  'f2_result_path',fullfile(c.output_dir,'f2','f2_result.mat'), ...
  'f2_result_sha256',e036_sha256_file(fullfile(c.output_dir,'f2','f2_result.mat')), ...
  'admission',admission,'config_sha256',config_sha256,'authority_id',approval.authority_id, ...
  'authority_sha256',c.authority_sha256,'f2_source_lock_sha256',c.f2_source_lock_sha256, ...
  'stage_a_evidence_sha256',c.stage_a_evidence_sha256,'elapsed_seconds',toc(clock),'primary_F1_replacement',false);
 write_json(fullfile(c.output_dir,'stage_b_result.json'),report);check();
catch original
 failure=struct('stage',stage,'identifier',original.identifier,'message',original.message, ...
  'elapsed_seconds',toc(clock),'retry_permitted',false,'method',c.f2.method,'primary_F1_replacement',false);
 try,write_json(fullfile(c.output_dir,'failure.json'),failure);catch,end
 rethrow(original);
end
 function check()
  e036_job_clock(budget,clock,budget.total_wall_seconds);
 end
end

function evidence=stage_a_pass(c)
checked(c.stage_a_evidence_file,c.stage_a_evidence_sha256);evidence=jsondecode(fileread(c.stage_a_evidence_file));
required(evidence,{'schema','prepare','disabled','frozen','supervisors'});
assert(strcmp(evidence.schema,'e036-stage-a-evidence-v1'),'E036B:StageA','Unknown Stage A evidence schema');
a_root=char(c.stage_a_root);
assert(~strcmpi(canonical(a_root),canonical(c.run_root)),'E036B:Isolation', ...
 'Stage B must have a distinct output root from Stage A');
p=read_record(evidence.prepare,a_root);d=read_record(evidence.disabled,a_root);
artifacts=struct('prepare',p,'disabled',d);artifact_refs=struct('prepare',evidence.prepare,'disabled',evidence.disabled);
assert(strcmp(p.status,'prepared_build_and_mock_completed_no_native_call') && ...
 p.mock.cases==28 && strcmp(p.mock.status,'passed') && p.mock.native_solves==0 && ...
 strcmp(d.status,'exact_disabled_identity') && d.native_solves==2 && d.recovery_solves==0, ...
 'E036B:StageA','Actual prepared build/mock and disabled identity must have passed');
assert(numel(evidence.frozen)==4 && isequal(sort([evidence.frozen.cycle]),[1 20 60 83]), ...
 'E036B:StageA','All four distinct frozen states are required');
for k=1:4
 item=evidence.frozen(k);n=read_record(item.native,a_root);r=read_record(item.comparison,a_root);
 assert(n.cycle==item.cycle && n.substep==4 && n.native_solves==0 && ...
  strcmp(r.schema,'e036_frozen_comparison_v1') && strcmp(r.status,'matched') && isequal(r.passed,true) && ...
  r.state_key.cycle==item.cycle && r.state_key.substep==4 && ...
  r.tolerance.atol==1e-10 && r.tolerance.rtol==1e-8 && strcmp(r.input_sha256,n.sha256), ...
  'E036B:StageA','A real native frozen export/comparison is missing or failed');
 inside(n.path,a_root);checked(n.path,n.sha256);
 native_role=sprintf('native_c%d',item.cycle);comparison_role=sprintf('comparison_c%d',item.cycle);
 artifacts.(native_role)=n;artifacts.(comparison_role)=r;
 artifact_refs.(native_role)=item.native;artifact_refs.(comparison_role)=item.comparison;
 required(r.native_provenance,{'binary_checks'});
 previous=r.native_provenance.binary_checks;
 for j=1:numel(previous)
  at=find(strcmp({c.runtime_bindings.name},previous(j).name));
  assert(isscalar(at) && strcmp(c.runtime_bindings(at).sha256,previous(j).sha256), ...
   'E036B:StageA','Stage A evaluated a different actual runtime binding');
 end
end
roles={'prepare','disabled','native_c1','native_c20','native_c60','native_c83', ...
 'comparison_c1','comparison_c20','comparison_c60','comparison_c83'};
assert(numel(evidence.supervisors)==numel(roles) && ...
 isequal(sort(string({evidence.supervisors.role})),sort(string(roles))), ...
 'E036B:StageA','Every required Stage A job needs a supervisor completion');
assert(numel(unique(lower(string({evidence.supervisors.path}))))==numel(roles) && ...
 numel(unique(string({evidence.supervisors.sha256})))==numel(roles) && ...
 numel(unique(string({evidence.supervisors.label})))==numel(roles), ...
 'E036B:StageA','Supervisor paths, hashes and labels must all be distinct');
for k=1:numel(evidence.supervisors)
 s=evidence.supervisors(k);required(s,{'role','label','supervisor_attempt','watchdog_attempt','watchdog_finished'});
 r=read_record(s,a_root);sa=read_record(s.supervisor_attempt,a_root);
 wa=read_record(s.watchdog_attempt,a_root);wf=read_record(s.watchdog_finished,a_root);
 assert(strcmp(r.schema,'e036-stage-a-supervisor-v1') && strcmp(r.label,s.label) && ...
  strcmp(r.stop_reason,'completed') && r.watchdog_exit_code==0 && ...
  isequal(r.watchdog_stopped,true) && isequal(r.global_policy_unchanged,true) && isempty(r.failure), ...
  'E036B:StageA','A Stage A producer job lacks successful supervised completion');
 assert(strcmp(sa.label,s.label) && strcmp(wa.label,s.label) && strcmp(wf.label,s.label) && ...
  strcmp(sa.authority_sha256,r.authority_sha256) && strcmp(wa.authority_sha256,r.authority_sha256) && ...
  strcmp(wf.authority_sha256,r.authority_sha256) && strcmp(sa.watchdog_sha256,r.watchdog_sha256) && ...
  strcmpi(canonical(sa.entry),canonical(wa.entry)) && wf.exit_code==0 && ...
  strcmp(wf.stop_reason,'exited') && isequal(wf.job_object_closed,true) && isempty(wf.wrapper_error), ...
  'E036B:StageA','Supervisor/watchdog attempt and completion identities are disconnected');
 inside(sa.authority_file,a_root);checked(sa.authority_file,r.authority_sha256);
 a=jsondecode(fileread(sa.authority_file));
 assert(strcmp(a.schema,'e036-stage-a-authority-v1') && strcmp(a.stage,'A') && ...
  numel(string(a.allowed_labels))==1 && strcmp(string(a.allowed_labels),s.label) && ...
  strcmp(wa.authority_id,a.authority_id) && strcmp(wf.authority_id,a.authority_id), ...
  'E036B:StageA','Stage A receipts are not from this exact authorized attempt');
 inside(sa.watchdog_file,a_root);checked(sa.watchdog_file,r.watchdog_sha256);
 inside(wa.entry,a_root);checked(wa.entry,wa.entry_sha256);
 product=artifacts.(s.role);product_ref=artifact_refs.(s.role);
 if startsWith(s.role,'comparison_')
  assert(strcmp(wa.kind,'Python'),'E036B:StageA','Comparator role needs its actual Python attempt');
  inside(wa.argv_file,a_root);checked(wa.argv_file,wa.argv_sha256);
  argv=string(jsondecode(fileread(wa.argv_file)));argv=argv(:);
  assert(mod(numel(argv),2)==0,'E036B:StageA','Malformed comparator arguments');
  input=argument(argv,'--input');output=argument(argv,'--output');
  common=argument(argv,'--common-problem');
  assert(strcmpi(canonical(input),canonical(product.input)) && ...
   strcmpi(canonical(fullfile(output,'comparison.json')),canonical(product_ref.path)) && ...
   strcmp(argument(argv,'--input-sha256'),product.input_sha256) && ...
   strcmpi(canonical(common),canonical(product.common_problem)) && ...
   strcmp(argument(argv,'--common-problem-sha256'),product.common_problem_sha256), ...
   'E036B:StageA','Comparator argv does not identify the corresponding input/output');
 else
  required(s,{'config'});config=read_record(s.config,a_root);
  assert(strcmp(wa.kind,'Matlab') && strcmp(product.config_sha256,s.config.sha256) && ...
   strcmp(product.authority_sha256,r.authority_sha256) && strcmp(config.watchdog_id,s.label) && ...
   strcmp(config.authority_sha256,r.authority_sha256), ...
   'E036B:StageA','MATLAB result/config/authority does not match this attempt');
  entry_text=lower(strrep(fileread(wa.entry),'\','/'));
  assert(contains(entry_text,lower(strrep(char(s.config.path),'\','/'))) && ...
   contains(entry_text,s.config.sha256),'E036B:StageA','Bound entry does not invoke this exact config');
  name='native_driver_result.json';
  if strcmp(s.role,'prepare'),name='prepare_result.json';
  elseif strcmp(s.role,'disabled')
   assert(strcmp(product.driver_mode,'disabled'),'E036B:StageA','Wrong native role');
  else
   assert(strcmp(product.driver_mode,strrep(s.role,'native_','frozen_')),'E036B:StageA','Wrong frozen role');
  end
  assert(strcmpi(canonical(fullfile(config.output_dir,name)),canonical(product_ref.path)), ...
   'E036B:StageA','Result path differs from the corresponding config output');
 end
end
end

function value=argument(argv,flag)
at=find(strcmp(argv(1:2:end),flag));
assert(isscalar(at),'E036B:StageA','Missing/duplicate comparator argument');value=char(argv(2*at));
end

function [resolutions,cfg,options]=bind_runtime(c,approval)
checked(c.manifest_path,c.manifest_sha256);m=jsondecode(fileread(c.manifest_path));required(m,{'files'});
paths=strings(numel(m.files),1);
for k=1:numel(m.files)
 p=fullfile(c.run_root,m.files(k).path);inside(p,c.run_root);checked(p,m.files(k).sha256);
 paths(k)=lower(string(canonical(p)));
end
assert(numel(unique(paths))==numel(paths),'E036B:Manifest','Duplicate manifest path');
helpers=fullfile(c.code_root,'tools','s04_e036_fem');files=[dir(fullfile(helpers,'*.m'));dir(fullfile(helpers,'f2','*.m'))];
for k=1:numel(files)
 assert(ismember(lower(string(canonical(fullfile(files(k).folder,files(k).name)))),paths), ...
  'E036B:Manifest','All actual MATLAB helpers must be manifest-bound');
end
checked(fullfile(c.build_root,'completion.json'),c.build_completion_sha256);
done=jsondecode(fileread(fullfile(c.build_root,'completion.json')));
assert(strcmp(done.status,'built_not_scientifically_verified'),'E036B:Build','Fresh pair build did not complete');
receipt=fullfile(c.build_root,'build_receipt.json');checked(receipt,done.receipt_sha256);built=jsondecode(fileread(receipt));
% Reuse the original build receipt unchanged; byte-identical relocation only.
% The receipt's original paths remain provenance and are never re-written.
for k=1:numel(built.source_records)
 r=built.source_records(k);required(r,{'relative_path','sha256'});
 source=fullfile(c.native_snapshot,'Sources','+phase_field','+mex',r.relative_path);
 staged=fullfile(c.build_root,'source',r.relative_path);
 inside(source,c.native_snapshot);inside(staged,c.build_root);
 checked(source,r.sha256);checked(staged,r.sha256);
end
runtime=c.runtime_bindings;at=find(strcmp({runtime.name},'cholmod2'));
assert(isscalar(at) && strcmpi(canonical(runtime(at).path), ...
 canonical('C:\SuiteSparse\SuiteSparse-dev\CHOLMOD\MATLAB\cholmod2.mexw64')) && ...
 strcmp(runtime(at).sha256,'86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329'), ...
 'E036B:Binding','Reviewed CHOLMOD binding is required');
checked(runtime(at).path,runtime(at).sha256);addpath(fileparts(runtime(at).path),'-begin');
addpath(fullfile(c.native_snapshot,'Scripts','fatigue_fracture'),'-begin');
addpath(genpath(fullfile(c.native_snapshot,'Dependencies')),'-begin');
addpath(fullfile(c.native_snapshot,'Sources'),'-begin');addpath(fullfile(c.overlay_root,'Sources'),'-begin');
addpath(fullfile(c.build_root,'Sources'),'-begin');addpath(helpers,'-begin');addpath(fullfile(helpers,'f2'),'-begin');rehash;
names={'AMOR','AT1_PENALTY_FATIGUE'};
qualified={'phase_field.mex.fem.assembly.equilibrium.AMOR','phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE'};
for k=1:2
 b=find(strcmp({built.binaries.name},names{k}));at=find(strcmp({runtime.name},qualified{k}));
 assert(isscalar(b) && isscalar(at),'E036B:Binding','Missing unique fresh kernel');
 assert(strcmpi(canonical(runtime(at).path),canonical(relocated(built.binaries(b).path,built.build_root,c.build_root))) && ...
  strcmp(runtime(at).sha256,built.binaries(b).sha256),'E036B:Binding','Installed MEX fallback is forbidden');
end
resolutions=cell(numel(runtime),1);
for k=1:numel(runtime)
 r=runtime(k);actual=which(r.name);assert(strcmpi(canonical(actual),canonical(r.path)), ...
  'E036B:Binding','Actual function resolution differs');checked(actual,r.sha256);
 if endsWith(lower(r.path),'.m')
  assert(ismember(lower(string(canonical(r.path))),paths),'E036B:Binding','Runtime source is not bound');
 end
 resolutions{k}=struct('name',r.name,'path',actual,'sha256',r.sha256,'which_all',{which(r.name,'-all')});
end
for name={'e036_final_candidate','e036_native_candidate','e036_policy'}
 assert(strcmp(e036_sha256_file(which(['phase_field.audit.' name{1}])), ...
  e036_sha256_file(fullfile(helpers,[name{1} '.m']))),'E036B:Binding','Overlay audit helper differs');
end
assert(~isempty(regexp(c.source_commit,'^[a-f0-9]{40}$','once')),'E036B:Binding','Native source commit required');
cfg=struct('requested_n_step',8,'loading','cyclic','discretization','loading', ...
 'u_max',.12,'R',0,'max_iter_displacement',250,'max_iter_phase',250,'max_iter_staggered',1500);
options=struct('execution_approved',true,'producer_hostname',approval.producer_hostname, ...
 'source_root',c.native_snapshot,'mesh_file',c.mesh_file,'mesh_sha256',c.mesh_sha256, ...
 'common_file',c.common_file,'common_sha256',c.common_sha256,'source_checks',c.source_checks, ...
 'binary_checks',runtime,'thread_controls_verified',true,'provenance',c.provenance);
end
function target=relocated(original,old_root,new_root)
old=canonical(old_root);p=canonical(original);
assert(startsWith(lower(p),[lower(old) filesep]),'E036B:Build','Binary outside original build root');
target=fullfile(new_root,p(numel(old)+2:end));inside(target,new_root);
end
function r=read_record(s,root)
required(s,{'path','sha256'});inside(s.path,root);checked(s.path,s.sha256);r=jsondecode(fileread(s.path));
end
function required(s,names)
assert(isstruct(s) && isscalar(s) && all(isfield(s,names)),'E036B:Schema','Required fields missing');
end
function checked(path,sha)
assert(strcmp(e036_sha256_file(path),sha),'E036B:InputHash','Bound input changed');
end
function inside(p,root)
assert(startsWith(lower(canonical(p)),[lower(canonical(root)) filesep]),'E036B:Path','Task-root path required');
end
function p=canonical(p)
p=char(java.io.File(char(p)).getCanonicalPath());
end
function write_json(path,value)
assert(~isfile(path),'E036B:Output','Never replace a result');
[fid,message]=fopen(path,'w','n','UTF-8');assert(fid>=0,'E036B:Output','%s',message);
closer=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,'PrettyPrint',true));
[message,number]=ferror(fid);assert(number==0,'E036B:Output','%s',message);
end
