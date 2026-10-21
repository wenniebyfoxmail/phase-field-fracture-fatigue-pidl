function result=e036_stage_a_native_driver(config_file,config_sha256,mode)
%E036_STAGE_A_NATIVE_DRIVER One serial Stage A native job, explicit boundaries.
% modes: disabled (one absent/false pair) or frozen_c1/c20/c60/c83 (assembly).
% Requires prior prepare result, fresh-pair build receipt and reviewed bindings.
% Each invocation is a NEW process/output. No recovery, retry or Stage B mode.
assert(strcmp(e036_sha256_file(config_file),config_sha256),'E036A:DriverConfig','Config changed');
c=jsondecode(fileread(config_file));
required={'run_root','code_root','native_snapshot','overlay_root','overlay_solver_sha256', ...
 'build_root','build_completion_sha256','prepare_result_path','prepare_result_sha256', ...
 'manifest_path','manifest_sha256','runtime_bindings','source_checks','common_file','common_sha256', ...
 'mesh_file','mesh_sha256','pairs','output_dir','watchdog_id','execution_approved','provenance'};
assert(all(isfield(c,required)),'E036A:DriverConfig','Incomplete native driver config');
root='C:\Users\xw436\jobs\E036_A_20261021_2142';
assert(ispc && strcmpi(getenv('COMPUTERNAME'),'CITPC12') && ...
 strcmpi(canonical(c.run_root),canonical(root)) && isequal(c.execution_approved,true), ...
 'E036A:Authority','Original task/producer and explicit approval required');
assert(ismember(string(mode),["disabled","frozen_c1","frozen_c20","frozen_c60","frozen_c83"]), ...
 'E036A:Scope','Unsupported Stage A operation');
deadline=datetime('2026-10-22T00:42:35Z','InputFormat','yyyy-MM-dd''T''HH:mm:ss''Z''','TimeZone','UTC');
remaining=seconds(deadline-datetime('now','TimeZone','UTC'))-60;
assert(remaining>0,'E036A:WallLimit','Original Stage A cleanup reserve reached');
budget=struct('total_timer',tic,'total_wall_seconds',min(10800,remaining), ...
 'max_threads',1,'watchdog_id',c.watchdog_id);
job_clock=tic;cap=600;if strcmp(mode,'disabled'),cap=min(3600,remaining);end
check_time(budget,job_clock,cap,deadline);
for name={'code_root','native_snapshot','overlay_root','build_root','output_dir','manifest_path', ...
 'common_file','mesh_file','prepare_result_path'}
 assert(startsWith(lower(canonical(c.(name{1}))),[lower(canonical(root)) filesep]), ...
  'E036A:DriverPath','Task paths must be under the approved root');
end
assert(strcmp(e036_sha256_file(c.manifest_path),c.manifest_sha256),'E036A:Manifest','Manifest changed');
m=jsondecode(fileread(c.manifest_path));assert(isfield(m,'files') && isstruct(m.files),'E036A:Manifest','Expected files array');
bound_paths=strings(numel(m.files),1);
for k=1:numel(m.files)
 f=m.files(k);p=canonical(fullfile(root,f.path));
 assert(startsWith(lower(p),[lower(canonical(root)) filesep]) && ...
  strcmp(e036_sha256_file(p),f.sha256),'E036A:Manifest','Bound input changed or escaped task root');
 bound_paths(k)=lower(string(p));
end
assert(numel(unique(bound_paths))==numel(bound_paths),'E036A:Manifest','Duplicate manifest path');
assert(strcmp(e036_sha256_file(c.prepare_result_path),c.prepare_result_sha256),'E036A:Prepare','Preparation receipt changed');
prepared=jsondecode(fileread(c.prepare_result_path));
assert(strcmp(prepared.status,'prepared_build_and_mock_completed_no_native_call') && ...
 prepared.mock.cases==28 && strcmp(prepared.mock.status,'passed'), ...
 'E036A:Prepare','Required mock/build preparation did not complete');
completion_path=fullfile(c.build_root,'completion.json');
assert(strcmp(e036_sha256_file(completion_path),c.build_completion_sha256),'E036A:Build','Build completion changed');
completion=jsondecode(fileread(completion_path));receipt_path=fullfile(c.build_root,'build_receipt.json');
assert(strcmp(completion.status,'built_not_scientifically_verified') && ...
 strcmp(e036_sha256_file(receipt_path),completion.receipt_sha256),'E036A:Build','Incomplete or altered fresh build');
built=jsondecode(fileread(receipt_path));
assert(strcmpi(canonical(built.snapshot_root),canonical(c.native_snapshot)) && ...
 strcmpi(canonical(built.build_root),canonical(c.build_root)), ...
 'E036A:Build','Fresh build belongs to another source/task');
for k=1:numel(built.source_records)
 r=built.source_records(k);assert(strcmp(e036_sha256_file(r.source_path),r.sha256) && ...
  strcmp(e036_sha256_file(r.staged_path),r.sha256),'E036A:Build','Built source drift');
end
helpers=fullfile(c.code_root,'tools','s04_e036_fem');
runtime=c.runtime_bindings;
cholmod_at=find(strcmp({runtime.name},'cholmod2'));
assert(isscalar(cholmod_at) && ...
 strcmpi(canonical(runtime(cholmod_at).path),canonical('C:\SuiteSparse\SuiteSparse-dev\CHOLMOD\MATLAB\cholmod2.mexw64')) && ...
 strcmp(runtime(cholmod_at).sha256,'86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329'), ...
 'E036A:Binding','Require the explicitly bound existing CHOLMOD binary');
assert(strcmp(e036_sha256_file(runtime(cholmod_at).path),runtime(cholmod_at).sha256), ...
 'E036A:Binding','Bound CHOLMOD binary changed');
addpath(fileparts(runtime(cholmod_at).path),'-begin');
addpath(fullfile(c.native_snapshot,'Scripts','fatigue_fracture'),'-begin');
addpath(genpath(fullfile(c.native_snapshot,'Dependencies')),'-begin');
addpath(fullfile(c.native_snapshot,'Sources'),'-begin');
addpath(fullfile(c.overlay_root,'Sources'),'-begin');
addpath(fullfile(c.build_root,'Sources'),'-begin');addpath(helpers,'-begin');rehash;
% Verify newly compiled package wins actual MATLAB resolution. Existing
% initial/processing/CHOLMOD bindings are independently explicit below.
pair_names={'AMOR','AT1_PENALTY_FATIGUE'};
qualified={'phase_field.mex.fem.assembly.equilibrium.AMOR','phase_field.mex.fem.assembly.pf.AT1_PENALTY_FATIGUE'};
for k=1:2
 index=find(strcmp({built.binaries.name},pair_names{k}));assert(isscalar(index),'E036A:Build','Missing built kernel');
 b=built.binaries(index);assert(strcmp(e036_sha256_file(b.path),b.sha256),'E036A:Build','Built binary changed');
 at=find(strcmp({runtime.name},qualified{k}));assert(isscalar(at),'E036A:Binding','Runtime manifest lacks one kernel');
 assert(strcmpi(runtime(at).path,b.path) && strcmp(runtime(at).sha256,b.sha256), ...
  'E036A:Binding','Runtime manifest must bind fresh build, never an installed fallback');
end
resolutions=cell(numel(runtime),1);
for k=1:numel(runtime)
 r=runtime(k);actual=which(r.name);
 assert(strcmpi(canonical(actual),canonical(r.path)) && strcmp(e036_sha256_file(actual),r.sha256), ...
  'E036A:Binding','Actual runtime binding differs: %s',r.name);
 resolutions{k}=struct('name',r.name,'actual',actual,'sha256',r.sha256,'which_all',{which(r.name,'-all')});
 if endsWith(lower(r.path),'.m')
  assert(ismember(lower(string(canonical(r.path))),bound_paths),'E036A:Binding','Task MATLAB source is not manifest-bound');
 end
end
for name={'e036_final_candidate','e036_native_candidate','e036_policy'}
 local=fullfile(helpers,[name{1} '.m']);actual=which(['phase_field.audit.' name{1}]);
 assert(strcmp(e036_sha256_file(actual),e036_sha256_file(local)), ...
  'E036A:Binding','Namespaced audit helper differs from reviewed helper');
end
assert(~isfolder(c.output_dir) && ~isfile(c.output_dir) && isfolder(fileparts(c.output_dir)), ...
 'E036A:Output','Native job output must be fresh');
assert(java.io.File(char(c.output_dir)).mkdir(),'E036A:Output','Could not create native job output');
cfg=struct('requested_n_step',8,'loading','cyclic','discretization','loading', ...
 'u_max',.12,'R',0,'max_iter_displacement',250,'max_iter_phase',250,'max_iter_staggered',1500);
options=struct('execution_approved',true,'producer_hostname','CITPC12', ...
 'source_root',c.native_snapshot,'mesh_file',c.mesh_file,'mesh_sha256',c.mesh_sha256, ...
 'common_file',c.common_file,'common_sha256',c.common_sha256,'source_checks',c.source_checks, ...
 'binary_checks',runtime,'thread_controls_verified',true,'provenance',c.provenance);
stage='context';
try
 save(fullfile(c.output_dir,'driver_binding.mat'),'c','config_sha256','mode','resolutions','cfg','budget','-v7.3');
 [sys,par,common,binding]=e036_stage_a_context(cfg,options,budget);
 check_time(budget,job_clock,cap,deadline);
 save(fullfile(c.output_dir,'context_binding.mat'),'binding','-v7.3');
 if strcmp(mode,'disabled')
  assert(binding.u0_admitted,'E036A:U0Admission','U0 is unavailable; no replacement recovery');
  budget.arm_deadline_dir=fullfile(root,'logs',[char(c.watchdog_id) '_arms']);
  stage='disabled_pair';result=e036_stage_a_disabled_pair(sys,par,common,binding, ...
   fullfile(c.overlay_root,'Scripts','fatigue_fracture','solve_fatigue_fracture.m'), ...
   c.overlay_solver_sha256,budget,fullfile(c.output_dir,'controls'));
 else
  cycle=str2double(extractAfter(string(mode),'frozen_c'));
  at=find([c.pairs.cycle]==cycle);assert(isscalar(at),'E036A:Pair','Expected one explicit frozen pair');
  stage='frozen_export';result=e036_stage_a_export_frozen(sys,binding,c.pairs(at),budget, ...
   fullfile(c.output_dir,sprintf('native_c%04d_s04.mat',cycle)));
 end
 check_time(budget,job_clock,cap,deadline);
 result.driver_mode=mode;result.driver_seconds=toc(job_clock);result.config_sha256=config_sha256;
 save(fullfile(c.output_dir,'native_driver_result.mat'),'result','-v7.3');
 write_json(fullfile(c.output_dir,'native_driver_result.json'),result);
 check_time(budget,job_clock,cap,deadline);
catch original
 failure=struct('stage',stage,'identifier',original.identifier,'message',original.message, ...
  'mode',mode,'elapsed_seconds',toc(job_clock),'retry_permitted',false);
 try,write_json(fullfile(c.output_dir,'failure.json'),failure);catch,end
 rethrow(original);
end
end
function check_time(budget,clock,cap,deadline)
e036_stage_a_clock(budget,clock,cap);
assert(datetime('now','TimeZone','UTC')<deadline-seconds(60),'E036A:WallLimit','Original deadline cleanup reserve reached');
end
function p=canonical(p)
p=char(java.io.File(char(p)).getCanonicalPath());
end
function write_json(path,value)
assert(~isfile(path),'E036A:Output','Never replace a driver receipt');
[fid,message]=fopen(path,'w','n','UTF-8');assert(fid>=0,'E036A:Output','%s',message);
closer=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,'PrettyPrint',true));
[message,number]=ferror(fid);assert(number==0,'E036A:Output','%s',message);
end
