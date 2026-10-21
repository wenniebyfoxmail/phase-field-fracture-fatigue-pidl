function receipt=e036_build_native_pair(snapshot_root,build_root,compiler_xml)
%E036_BUILD_NATIVE_PAIR Fresh Windows Fortran build; never invokes a MEX.
% snapshot_root contains Sources/+phase_field/+mex. build_root MUST NOT exist
% and must be outside snapshot_root. compiler_xml is an explicitly selected
% Intel Fortran MEX configuration: every mex call uses -f; no mex -setup.
% Launch MATLAB from the already authorised oneAPI/MSVC environment. This
% helper neither changes global compiler configuration nor loads the outputs.
% Native scientific acceptance remains a separate, bounded producer action.
assert(ispc && strcmp(mexext,'mexw64'),'E036:BuildPlatform','Windows x64 required');
snapshot_root=canonical(snapshot_root);build_root=canonical(build_root);
compiler_xml=canonical(compiler_xml);
assert(isfolder(snapshot_root) && isfile(compiler_xml),'E036:BuildInput','Missing source root or compiler XML');
assert(~isfolder(build_root) && ~isfile(build_root),'E036:BuildExists','Refusing to reuse a build directory');
assert(~strcmpi(snapshot_root,build_root) && ~startsWith(lower(build_root),[lower(snapshot_root) filesep]), ...
 'E036:BuildInsideSource','Build directory must be outside the source snapshot');
assert(isfolder(fileparts(build_root)),'E036:BuildParent','Build parent must already exist');
assert(java.io.File(build_root).mkdir(),'E036:BuildCreate','Cannot exclusively create build directory');
receipt=struct('schema','e036-native-pair-build-v1','status','incomplete', ...
 'snapshot_root',snapshot_root,'build_root',build_root,'matlab_version',version, ...
 'matlab_release',version('-release'),'computer',computer,'mex_extension',mexext, ...
 'started_utc',utc_now(),'scientific_calls',0,'source_records',{{}},'commands',{{}});
write_json(fullfile(build_root,'incomplete.json'),receipt);
original_dir=pwd;restore_dir=onCleanup(@()cd(original_dir)); %#ok<NASGU>
try
 srcroot=fullfile(snapshot_root,'Sources','+phase_field','+mex');
 staged=fullfile(build_root,'source');objects=fullfile(build_root,'objects');
 logs=fullfile(build_root,'logs');package=fullfile(build_root,'Sources');
 mkdir(staged);mkdir(objects);mkdir(logs);mkdir(package);
 % Actual USE dependencies put scalar_utils before types (unlike the older
 % MIEHE convenience script). All copied inputs are text; no old obj/mod.
 modules={'Modules/scalar_utils.f90','Modules/types.f90', ...
  'Modules/array_utils.f90','Modules/matrix_utils.f90', ...
  'Modules/system_factors.f90','Modules/mex_utils.f90', ...
  'Modules/fem/assembly/equilibrium/amor.f90', ...
  'Modules/fem/assembly/pf/at1_penalty_fatigue.f90'};
 gateways={'+fem/+assembly/+equilibrium/AMOR.f90', ...
  '+fem/+assembly/+pf/AT1_PENALTY_FATIGUE.f90'};
 names={'AMOR','AT1_PENALTY_FATIGUE'};
 relpaths=[modules gateways];
 for i=1:numel(relpaths)
  from=fullfile(srcroot,relpaths{i});to=fullfile(staged,relpaths{i});
  assert(isfile(from),'E036:BuildSource','Missing source: %s',from);
  mkdir(fileparts(to));copyfile(from,to);
  r=struct('relative_path',relpaths{i},'source_path',from,'staged_path',to, ...
   'sha256',e036_sha256_file(from));
  assert(strcmp(r.sha256,e036_sha256_file(to)),'E036:BuildCopy','Source copy differs');
  receipt.source_records{end+1}=r;
 end
 % Validate the complete USE/include closure of this pair before compiling.
 % A changed snapshot requiring another module fails rather than finding an
 % installed .mod through the compiler environment.
 provided={};module_names=cell(size(modules));
 for i=1:numel(modules)
  source=fileread(fullfile(staged,modules{i}));
  check_dependencies(source,provided);
  token=regexp(source,'(?im)^\s*module\s+([a-z][a-z0-9_]*)\s*(?:!.*)?$','tokens');
  assert(numel(token)==1,'E036:BuildModule','Expected exactly one module in %s',modules{i});
  module_names{i}=lower(token{1}{1});provided{end+1}=module_names{i}; %#ok<AGROW>
 end
 for i=1:numel(gateways),check_dependencies(fileread(fullfile(staged,gateways{i})),provided);end
 receipt.compiler=struct('explicit_xml',compiler_xml,'xml_sha256',e036_sha256_file(compiler_xml), ...
  'selection_mode','per-call mex -f; global selection is context only', ...
  'selected_fortran_context',compiler_context());
 copyfile(compiler_xml,fullfile(build_root,'compiler_config.xml'));
 assert(strcmp(receipt.compiler.xml_sha256,e036_sha256_file(fullfile(build_root,'compiler_config.xml'))), ...
  'E036:BuildConfigCopy','Archived compiler configuration differs');
 % Use the original explicitly selected XML, since it may resolve resources
 % relative to its installation location; verify its hash again at the end.
 receipt.environment=struct();
 env_names={'ONEAPI_ROOT','IFORT_COMPILER24','IFORT_COMPILER25','IFX_COMPILER24', ...
  'IFX_COMPILER25','VSINSTALLDIR','VSCMD_VER','WindowsSdkDir','INCLUDE','LIB','PATH'};
 for i=1:numel(env_names),receipt.environment.(env_names{i})=getenv(env_names{i});end
 receipt.helper=struct('path',[mfilename('fullpath') '.m'], ...
  'sha256',e036_sha256_file([mfilename('fullpath') '.m']));
 receipt.hash_helper=struct('path',which('e036_sha256_file'), ...
  'sha256',e036_sha256_file(which('e036_sha256_file')));
 receipt.matlab_dependencies=matlab_dependencies();
 % The gateways use legacy mxGetPr/fintrf interfaces. Pin the separate-complex
 % API explicitly. Keep /free from both original build scripts; no arch-native
 % optimisation or global flags are added. mex -v captures resolved options.
 common={'-v','-f',compiler_xml,'-R2017b',['-I' objects], ...
  'COMPFLAGS=$COMPFLAGS /free'};
 receipt.mex_common_arguments=common;
 write_json(fullfile(build_root,'build_inputs.json'),receipt);
 object_paths=cell(size(modules));
 cd(objects);
 for i=1:numel(modules)
  [~,stem]=fileparts(modules{i});object_paths{i}=fullfile(objects,[stem '.obj']);
  args=[common {'-c',fullfile(staged,modules{i}),'-outdir',objects}];
  receipt.commands{end+1}=run_mex(args,logs,numel(receipt.commands)+1,objects);
  assert(isfile(object_paths{i}),'E036:BuildObject','Compiler did not produce %s',object_paths{i});
  assert(isfile(fullfile(objects,[module_names{i} '.mod'])),'E036:BuildMod','Expected fresh module interface missing');
 end
 % In Windows, AMOR.obj and amor.obj are the same filename. Compile each
 % gateway in its own NEW link cwd, never the module object directory.
 receipt.binaries={};
 for i=1:numel(gateways)
  linkdir=fullfile(build_root,['link_' names{i}]);mkdir(linkdir);cd(linkdir);
  outdir=fullfile(package,'+phase_field','+mex',fileparts(gateways{i}));mkdir(outdir);
  args=[common {fullfile(staged,gateways{i})} object_paths ...
   {'-lmwlapack','-lmwblas','-output',names{i},'-outdir',outdir}];
  receipt.commands{end+1}=run_mex(args,logs,numel(receipt.commands)+1,linkdir);
  binary=fullfile(outdir,[names{i} '.' mexext]);
  assert(isfile(binary),'E036:BuildBinary','Expected output missing: %s',binary);
  receipt.binaries{end+1}=struct('name',names{i},'path',binary,'sha256',e036_sha256_file(binary));
 end
 for i=1:numel(receipt.source_records)
  r=receipt.source_records{i};
  assert(strcmp(r.sha256,e036_sha256_file(r.source_path)) && strcmp(r.sha256,e036_sha256_file(r.staged_path)), ...
   'E036:BuildSourceChanged','Source changed during compilation: %s',r.source_path);
 end
 assert(strcmp(receipt.compiler.xml_sha256,e036_sha256_file(compiler_xml)), ...
  'E036:BuildConfigChanged','Compiler configuration changed during compilation');
 receipt.fresh_objects=artifact_records(objects,'*.obj');
 receipt.fresh_module_interfaces=artifact_records(objects,'*.mod');
 receipt.package_root=package;receipt.status='built_not_scientifically_verified';receipt.finished_utc=utc_now();
 write_json(fullfile(build_root,'build_receipt.json'),receipt);
 % Last file is the completion marker. Partial builds retain incomplete.json
 % and have no completion marker. No automatic rebuild/retry is performed.
 completion=struct('schema',receipt.schema,'status',receipt.status, ...
  'receipt_sha256',e036_sha256_file(fullfile(build_root,'build_receipt.json')), ...
  'binaries',{receipt.binaries},'scientific_calls',0);
 write_json(fullfile(build_root,'completion.json'),completion);
catch failure
 receipt.status='failed';receipt.finished_utc=utc_now();
 receipt.error=struct('identifier',failure.identifier,'message',failure.message, ...
  'report',getReport(failure,'extended','hyperlinks','off'));
 write_json(fullfile(build_root,'failure.json'),receipt);
 rethrow(failure);
end
end

function check_dependencies(source,provided)
uses=regexp(source,'(?im)^\s*use\s*(?:,\s*(?:non_intrinsic|intrinsic)\s*)?(?:::\s*)?([a-z][a-z0-9_]*)','tokens');
for j=1:numel(uses)
 name=lower(uses{j}{1});
 assert(ismember(name,provided),'E036:BuildDependency','Unbuilt module dependency: %s',name);
end
includes=regexp(source,'(?im)^\s*(?:#\s*)?include\s*["'']([^"'']+)["'']','tokens');
for j=1:numel(includes)
 assert(strcmpi(includes{j}{1},'fintrf.h'),'E036:BuildInclude','Unrecorded include: %s',includes{j}{1});
end
end

function command=run_mex(args,logs,index,working_directory)
command=struct('index',index,'working_directory',working_directory,'arguments',{args}, ...
 'started_utc',utc_now());
stem=sprintf('%02d',index);write_json(fullfile(logs,[stem '_command.json']),command);
failure=[];
% Catch inside evalc so verbose compiler/linker output survives mex errors.
output=evalc('try; mex(args{:}); catch cause; failure=cause; end');
logpath=fullfile(logs,[stem '_mex.log']);write_text(logpath,output);
command.log_path=logpath;command.log_sha256=e036_sha256_file(logpath);command.finished_utc=utc_now();
if ~isempty(failure),rethrow(failure);end
end

function result=compiler_context()
% Read-only; an explicit -f configuration works even with no global selection.
try
 selected=mex.getCompilerConfigurations('Fortran','Selected');
 result=evalc('disp(selected)');
catch failure
 result=['Selected-configuration inventory unavailable: ' failure.message];
end
end

function records=matlab_dependencies()
paths={fullfile(matlabroot,'extern','include','fintrf.h'), ...
 fullfile(matlabroot,'extern','lib','win64','microsoft','libmwlapack.lib'), ...
 fullfile(matlabroot,'extern','lib','win64','microsoft','libmwblas.lib'), ...
 fullfile(matlabroot,'bin','win64','libmwlapack.dll'), ...
 fullfile(matlabroot,'bin','win64','libmwblas.dll')};
records=cell(size(paths));
for j=1:numel(paths)
 assert(isfile(paths{j}),'E036:BuildMatlabDependency','Missing expected MATLAB build dependency: %s',paths{j});
 records{j}=struct('path',paths{j},'sha256',e036_sha256_file(paths{j}));
end
end

function records=artifact_records(folder,pattern)
items=dir(fullfile(folder,pattern));records=cell(1,numel(items));
for j=1:numel(items)
 p=fullfile(items(j).folder,items(j).name);
 records{j}=struct('path',p,'bytes',items(j).bytes,'sha256',e036_sha256_file(p));
end
end

function result=canonical(value)
result=char(java.io.File(char(value)).getCanonicalPath());
end

function value=utc_now()
value=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ss.SSS''Z'''));
end

function write_json(path,value)
write_text(path,[jsonencode(value,'PrettyPrint',true) newline]);
end

function write_text(path,value)
assert(~isfile(path),'E036:BuildRecordExists','Refusing to overwrite %s',path);
[fid,message]=fopen(path,'w','n','UTF-8');assert(fid>=0,'E036:BuildRecord','%s',message);
closer=onCleanup(@()fclose(fid)); %#ok<NASGU>
count=fprintf(fid,'%s',value);assert(count>=0,'E036:BuildRecord','Could not write %s',path);
[message,number]=ferror(fid);assert(number==0,'E036:BuildRecord','%s',message);
end
