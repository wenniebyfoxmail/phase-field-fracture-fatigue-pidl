function result=e036_stage_b_driver(config_file,config_sha256)
%E036_STAGE_B_DRIVER One conditional native window; prepared, not executed.
% Requires actual Stage A evidence, explicit Stage B authority and predecessor.
checked(config_file,config_sha256);c=jsondecode(fileread(config_file));
required(c,{'run_root','code_root','native_snapshot','overlay_root','build_root', ...
 'build_completion_sha256','manifest_path','manifest_sha256','runtime_bindings','source_checks', ...
 'common_file','common_sha256','mesh_file','mesh_sha256','output_dir','watchdog_id', ...
 'execution_approved','provenance','source_commit','authority_file','authority_sha256', ...
 'stage_a_root','stage_a_evidence_file','stage_a_evidence_sha256','request','predecessor'});
assert(isequal(c.execution_approved,true),'E036B:Authority','Conditional execution approval required');
required(c.request,{'cycle','substeps','role'});steps=c.request.substeps(:)';
assert(isequal(sort(fieldnames(c.request)),sort({'cycle';'substeps';'role'})) && ...
 ~isfield(c,'pairs') && ~isfield(c,'target') && ~isfield(c,'targets'), ...
 'E036B:Scope','Window config must not carry future targets');
main=strcmp(c.request.role,'main');tight=strcmp(c.request.role,'tightening');oracle=strcmp(c.request.role,'nodal_oracle');
assert((main && ((ismember(c.request.cycle,[1 83]) && isequal(steps,1:5)) || ...
 (ismember(c.request.cycle,[20 60]) && isequal(steps,4)))) || ...
 ((tight || oracle) && ismember(c.request.cycle,[1 83]) && isscalar(steps) && ismember(steps,[2 4])), ...
 'E036B:Scope','Only the declared windows/endpoints and same-predecessor tightening are supported');
assert(~(tight || oracle) || strcmp(c.predecessor.kind,'verified_window_step'), ...
 'E036B:Tightening','Tightening must use the main-window verified immediately preceding checkpoint');
assert(oracle==isfield(c,'initial_fields'),'E036B:OracleScope','Initial candidate is exclusive to the oracle');
[budget,approval]=e036_stage_b_authority(c);root=char(c.run_root);clock=budget.total_timer;
for name={'code_root','native_snapshot','overlay_root','build_root','manifest_path','common_file', ...
 'mesh_file','output_dir','stage_a_evidence_file'}
 inside(c.(name{1}),root);
end
for name={'path','origin_file','proposal_file','completion_file','main_window_result_file'}
 if isfield(c.predecessor,name{1}),inside(c.predecessor.(name{1}),root);end
end
assert(~isfile(c.output_dir) && ~isfolder(c.output_dir) && isfolder(fileparts(c.output_dir)), ...
 'E036B:Output','New output directory required');
assert(java.io.File(char(c.output_dir)).mkdir(),'E036B:Output','Could not create output directory');
stage='stage_a_evidence';result=[];
try
 evidence=stage_a_pass(c);check();
 stage='runtime_binding';[resolutions,cfg,options]=bind_runtime(c,approval);check();
 helpers=fullfile(c.code_root,'tools','s04_e036_fem');adapter_bindings=struct;
 for helper={'e036_final_candidate','e036_native_candidate','e036_policy'}
  name=helper{1};adapter_bindings.(name)=struct('qualified_name',['phase_field.audit.' name], ...
   'source_path',fullfile(helpers,[name '.m']),'resolved_path',which(['phase_field.audit.' name]), ...
   'sha256',e036_sha256_file(fullfile(helpers,[name '.m'])));
 end
 reuse=struct('schema','e036-stage-a-reuse-audit-v1','accepted',true,'tasks_verified',10, ...
  'stage_a_reexecuted',false,'stage_a_evidence_file',c.stage_a_evidence_file, ...
  'stage_a_evidence_sha256',c.stage_a_evidence_sha256,'stage_a_evidence',evidence, ...
  'runtime_bindings',{resolutions},'adapter_bindings',adapter_bindings, ...
  'build_receipt_path',fullfile(c.build_root,'build_receipt.json'), ...
  'build_receipt_sha256',e036_sha256_file(fullfile(c.build_root,'build_receipt.json')), ...
  'audit_source_path',[mfilename('fullpath') '.m'],'audit_source_sha256',e036_sha256_file([mfilename('fullpath') '.m']), ...
  'config_sha256',config_sha256,'manifest_sha256',c.manifest_sha256, ...
  'scope','Preserved Stage A evidence and current byte-identical native bindings; no Stage B result inferred');
 write_json(fullfile(c.output_dir,'stage_a_reuse_audit.json'),reuse);check();
 save(fullfile(c.output_dir,'driver_binding.mat'),'c','config_sha256','approval','evidence', ...
  'resolutions','cfg','budget','-v7.3');
 stage='native_context';[sys,par,common,binding]=e036_stage_b_context(cfg,options,budget);check();
 eq=str2func('phase_field.mex.fem.assembly.equilibrium.AMOR');
 pf=str2func('phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE');
 stage='predecessor_admission';
 [pre,admission]=e036_stage_b_predecessor(sys,eq,pf,common,binding,c.predecessor, ...
  c.request,budget,fullfile(c.output_dir,'predecessor'));check();
 if tight
  par.solver.tol_displ=1e-8;par.solver.tol_p_field=4e-6;par.stag.tol=4e-6;
  policy=e036_policy('fresh_strict_e011','nodal_box_kkt');
 else
  policy=e036_policy('fresh_original_tolerances','nodal_box_kkt');
 end
 support=struct('nodes',sys.MESH.node(:,1:2),'cells',sys.MESH.elem(:,1:4), ...
  'Nxi',sys.QUADRATURE.Nxi,'dNdxi',sys.QUADRATURE.dNdxi,'gauss_W',sys.QUADRATURE.gauss_W, ...
  'active_u',sys.DOFS.active_dof(:),'active_d',sys.DOFS.active_dof_pf(:), ...
  'fixed_damage_nodes_zero_based',[4;5;(695:943)'], ...
  'ordered_mesh_sha256_f32_i64','c675e3fd05399cf16cc56884396f46b2af9e6b8e3c5c349e188246692d8bc174');
 b=rmfield(budget,{'total_timer','watchdog_id','authority_file','authority_sha256','authority_id','global_deadline'});
 authority=struct('execution_approved',true,'approval_id',approval.authority_id, ...
  'producer_hostname',approval.producer_hostname,'run_id',c.watchdog_id,'source_commit',c.source_commit, ...
  'manifest_sha256',c.manifest_sha256,'native_bindings_verified',true, ...
  'native_eq_name',func2str(eq),'native_pf_name',func2str(pf),'thread_controls_verified',true, ...
  'watchdog_id',c.watchdog_id,'request',c.request,'solver',par.solver,'stag',par.stag, ...
  'policy',policy,'budget',b,'binding',support,'predecessor_sha256',c.predecessor.sha256);
 initial=[];
 if oracle
  required(c.initial_fields,{'path','sha256','source_snapshot_path','source_snapshot_sha256','source_completion_path','source_completion_sha256'});
  inside(c.initial_fields.path,root);inside(c.initial_fields.source_snapshot_path,root);
  checked(c.initial_fields.path,c.initial_fields.sha256);
  checked(c.initial_fields.source_snapshot_path,c.initial_fields.source_snapshot_sha256);
  inside(c.initial_fields.source_completion_path,root);
  checked(c.initial_fields.source_completion_path,c.initial_fields.source_completion_sha256);
  endpoint=jsondecode(fileread(c.initial_fields.source_completion_path));
  assert(isequal(endpoint.readback_verified,true) && isequal(endpoint.endpoint_complete,true) && ...
   strcmp(endpoint.fields_sha256,c.initial_fields.source_snapshot_sha256), ...
   'E036B:OracleEndpoint','Complete read-back L+ endpoint receipt required');
  q=load(c.initial_fields.path,'initial_fields');required(q,{'initial_fields'});initial=q.initial_fields;
  authority.initial_fields_sha256=c.initial_fields.sha256;
  authority.initial_source_snapshot_sha256=c.initial_fields.source_snapshot_sha256;
  authority.initial_source_completion_sha256=c.initial_fields.source_completion_sha256;
 end
 stage='native_window';result=e036_run_window(sys,eq,pf,par,pre,c.request,policy,budget,authority, ...
  fullfile(c.output_dir,'window'),initial);check();
 checked(config_file,config_sha256);checked(c.manifest_path,c.manifest_sha256);
 checked(c.stage_a_evidence_file,c.stage_a_evidence_sha256);
 checked(c.predecessor.path,c.predecessor.sha256);
 report=struct('status',result.status,'request',c.request,'history_commits',result.history_commits, ...
  'window_result_path',fullfile(c.output_dir,'window','window_result.mat'), ...
  'window_result_sha256',e036_sha256_file(fullfile(c.output_dir,'window','window_result.mat')), ...
  'admission',admission,'config_sha256',config_sha256,'authority_id',approval.authority_id, ...
  'authority_sha256',c.authority_sha256,'stage_a_evidence_sha256',c.stage_a_evidence_sha256, ...
  'elapsed_seconds',toc(clock));
 write_json(fullfile(c.output_dir,'stage_b_result.json'),report);check();
catch original
 failure=struct('stage',stage,'identifier',original.identifier,'message',original.message, ...
  'elapsed_seconds',toc(clock),'retry_permitted',false);
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
helpers=fullfile(c.code_root,'tools','s04_e036_fem');files=dir(fullfile(helpers,'*.m'));
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
addpath(fullfile(c.build_root,'Sources'),'-begin');addpath(helpers,'-begin');rehash;
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
