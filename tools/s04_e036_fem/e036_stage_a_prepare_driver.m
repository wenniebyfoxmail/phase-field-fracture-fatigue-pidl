function result=e036_stage_a_prepare_driver(config_file,config_sha256)
%E036_STAGE_A_PREPARE_DRIVER Checkcode, mock tests, fresh build; no native call.
% Root owns the serial external watchdog. Current authority supplies its
% independent timeout and optional global deadline; no historical fallback.
assert(strcmp(e036_sha256_file(config_file),config_sha256),'E036A:DriverConfig','Driver config changed');
c=jsondecode(fileread(config_file));
required={'run_root','code_root','native_snapshot','build_root','compiler_xml', ...
 'compiler_xml_sha256','output_dir','manifest_path','manifest_sha256','watchdog_id', ...
 'authority_file','authority_sha256'};
assert(all(isfield(c,required)),'E036A:DriverConfig','Incomplete preparation config');
[budget,authority]=e036_stage_a_authority(c,false);root=char(c.run_root);
clock=budget.total_timer;check_time(budget,clock);
for name={'code_root','native_snapshot','build_root','output_dir','manifest_path'}
 p=canonical(c.(name{1}));assert(startsWith(lower(p),[lower(canonical(root)) filesep]), ...
  'E036A:DriverPath','Every task input/output must remain under the approved root');
end
assert(strcmp(e036_sha256_file(c.manifest_path),c.manifest_sha256),'E036A:Manifest','Manifest changed');
m=jsondecode(fileread(c.manifest_path));assert(isfield(m,'files') && isstruct(m.files),'E036A:Manifest','Expected files:[{path,sha256}]');
paths=strings(numel(m.files),1);
for k=1:numel(m.files)
 f=m.files(k);p=canonical(fullfile(root,f.path));
 assert(startsWith(lower(p),[lower(canonical(root)) filesep]),'E036A:Manifest','Manifest path escapes task root');
 assert(strcmp(e036_sha256_file(p),f.sha256),'E036A:Manifest','Bound file differs: %s',f.path);
 paths(k)=lower(string(p));
end
assert(numel(unique(paths))==numel(paths),'E036A:Manifest','Duplicate case-insensitive paths');
helpers=fullfile(c.code_root,'tools','s04_e036_fem');
files=dir(fullfile(helpers,'*.m'));
for k=1:numel(files)
 assert(ismember(lower(string(canonical(fullfile(files(k).folder,files(k).name)))),paths), ...
  'E036A:Manifest','Every actual MATLAB helper must be bound: %s',files(k).name);
end
modules={'Modules/scalar_utils.f90','Modules/types.f90','Modules/array_utils.f90', ...
 'Modules/matrix_utils.f90','Modules/system_factors.f90','Modules/mex_utils.f90', ...
 'Modules/fem/assembly/equilibrium/amor.f90','Modules/fem/assembly/pf/at1_penalty_fatigue.f90', ...
 '+fem/+assembly/+equilibrium/AMOR.f90','+fem/+assembly/+pf/AT1_PENALTY_FATIGUE.f90'};
for k=1:numel(modules)
 p=fullfile(c.native_snapshot,'Sources','+phase_field','+mex',modules{k});
 assert(ismember(lower(string(canonical(p))),paths),'E036A:Manifest','Native build input is not bound: %s',modules{k});
end
assert(strcmp(c.compiler_xml_sha256,'1915687ebc9645d140f3259d3c155d1af708b6f19274dee5f65a6672a04c08b5') && ...
 strcmp(e036_sha256_file(c.compiler_xml),c.compiler_xml_sha256), ...
 'E036A:Compiler','Explicit compiler configuration differs from the reviewed producer binding');
assert(strcmp(e036_sha256_file(fullfile(c.native_snapshot,'Sources','+phase_field','+mex',modules{8})), ...
 'ea7e0bb9def96678115627014f53500c1081a5e892554e1120629a5bfd1702e6'), ...
 'E036A:Kernel','New raw-history kernel is not the audited source');
assert(~isfolder(c.output_dir) && ~isfile(c.output_dir) && isfolder(fileparts(c.output_dir)), ...
 'E036A:Output','Preparation output must be new');
assert(java.io.File(char(c.output_dir)).mkdir(),'E036A:Output','Could not exclusively create preparation output');
addpath(helpers,'-begin');
assert(strcmpi(which('e036_stage_a_prepare_driver'),[mfilename('fullpath') '.m']), ...
 'E036A:DriverPath','Preparation entry was shadowed');
checks=cell(size(files));stage='checkcode';
result=struct('status','incomplete','scope','checkcode/mock/fresh build only', ...
 'native_calls',0,'native_solves',0,'config_sha256',config_sha256, ...
 'manifest_sha256',c.manifest_sha256,'authority',authority,'authority_sha256',c.authority_sha256, ...
 'watchdog_id',c.watchdog_id,'started_utc',utc_now());
try
 for k=1:numel(files)
  p=fullfile(files(k).folder,files(k).name);check_time(budget,clock);
  checks{k}=struct('path',p,'sha256',e036_sha256_file(p),'messages',checkcode(p,'-id'));
 end
 save(fullfile(c.output_dir,'checkcode.mat'),'checks','-v7.3');
 write_json(fullfile(c.output_dir,'checkcode.json'),struct('checks',{checks}, ...
  'scope','all diagnostics retained; message count is not a scientific acceptance criterion'));
 stage='hash_selftest';check_time(budget,clock);
 result.hash_selftest=e036_sha256_selftest(fullfile(c.output_dir,'hash_selftest'));
 assert(strcmp(result.hash_selftest.status,'passed') && result.hash_selftest.cases==15 && ...
  result.hash_selftest.native_calls==0,'E036A:HashSelftest','File hashing fixtures did not complete exactly');
 stage='mock';check_time(budget,clock);
 result.mock=e036_stage_a_selftest(fullfile(c.output_dir,'mock'));
 assert(strcmp(result.mock.status,'passed') && result.mock.cases==28 && result.mock.native_solves==0, ...
  'E036A:Mock','Prepared mock suite did not complete exactly');
 stage='fresh_build';check_time(budget,clock);
 result.build=e036_build_native_pair(c.native_snapshot,c.build_root,c.compiler_xml);
 check_time(budget,clock);
 assert(strcmp(result.build.status,'built_not_scientifically_verified'),'E036A:Build','Fresh build did not complete');
 for k=1:numel(m.files)
  f=m.files(k);assert(strcmp(e036_sha256_file(fullfile(root,f.path)),f.sha256),'E036A:Drift','Bound source changed during preparation');
 end
 assert(strcmp(e036_sha256_file(config_file),config_sha256) && ...
  strcmp(e036_sha256_file(c.manifest_path),c.manifest_sha256),'E036A:Drift','Config/manifest drift');
 check_time(budget,clock);result.status='prepared_build_and_mock_completed_no_native_call';
 result.elapsed_seconds=toc(clock);result.finished_utc=utc_now();
 save(fullfile(c.output_dir,'prepare_result.mat'),'result','-v7.3');
 write_json(fullfile(c.output_dir,'prepare_result.json'),result);check_time(budget,clock);
catch original
 failure=struct('stage',stage,'identifier',original.identifier,'message',original.message, ...
  'elapsed_seconds',toc(clock),'retry_permitted',false);
 try,write_json(fullfile(c.output_dir,'failure.json'),failure);catch,end
 rethrow(original);
end
end
function check_time(budget,clock)
e036_stage_a_clock(budget,clock,budget.total_wall_seconds);
end
function p=canonical(p)
p=char(java.io.File(char(p)).getCanonicalPath());
end
function value=utc_now()
value=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ss.SSS''Z'''));
end
function write_json(path,value)
assert(~isfile(path),'E036A:Output','Never replace a preparation receipt');
[fid,message]=fopen(path,'w','n','UTF-8');assert(fid>=0,'E036A:Output','%s',message);
closer=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'%s\n',jsonencode(value,'PrettyPrint',true));
[message,number]=ferror(fid);assert(number==0,'E036A:Output','%s',message);
end
