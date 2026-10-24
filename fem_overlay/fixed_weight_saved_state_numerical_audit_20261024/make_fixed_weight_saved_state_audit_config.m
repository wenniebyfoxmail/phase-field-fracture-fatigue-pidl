function cfg = make_fixed_weight_saved_state_audit_config(source_root, audit_root, python_launcher_path)
%MAKE_FIXED_WEIGHT_SAVED_STATE_AUDIT_CONFIG Create a deliberately inert config.
%
% The returned config cannot run until a reviewer changes cfg.execute to true.
% source_root must be a clean checkout at 862992a60edc7f59335365beacb5c71fc8592a7a.

arguments
    source_root (1,1) string
    audit_root (1,1) string
    python_launcher_path (1,1) string
end

package_root = fileparts(mfilename('fullpath'));
manifest_path = fullfile(package_root, 'PACKAGE_SHA256SUMS.txt');
if ~isfile(manifest_path)
    error('fixed_weight:numerical_audit:PackageManifest', ...
        'The reviewed package manifest is missing: %s', manifest_path);
end
python_launcher = bindPythonLauncher(python_launcher_path);
cfg = struct( ...
    'execute', false, ...
    'source_root', source_root, ...
    'audit_root', audit_root, ...
    'python_launcher_path', python_launcher.path, ...
    'python_launcher_sha256', python_launcher.sha256, ...
    'package_root', package_root, ...
    'package_manifest_sha256', sha256File(manifest_path), ...
    'preflight_script', fullfile(package_root, 'preflight_fixed_weight_saved_state_archives.py'), ...
    'archive_roots', {{ ...
        'C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0115_stage0b', ...
        'C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0125_stage0b' ...
    }} ...
    );
end


function launcher = bindPythonLauncher(configured_path)
if ~isExplicitWindowsAbsolutePath(configured_path)
    error('fixed_weight:numerical_audit:PythonLauncherPath', ...
        ['python_launcher_path must be an explicit absolute Windows path to ', ...
         'the reviewed Python launcher; PATH lookup is not permitted.']);
end
actual = canonicalPath(configured_path);
if ~isfile(actual)
    error('fixed_weight:numerical_audit:PythonLauncherPath', ...
        'The configured Python launcher does not exist: %s.', actual);
end
launcher = struct('path', actual, 'sha256', sha256File(actual));
end


function value = canonicalPath(path)
value = string(char(java.io.File(char(path)).getCanonicalPath()));
end


function yes = isExplicitWindowsAbsolutePath(path)
path = string(path);
yes = isscalar(path) && strlength(path) > 3 && ...
    ~contains(path, '"') && ~isempty(regexp(char(path), '^[A-Za-z]:[\\/]', 'once'));
end


function digest = sha256File(path)
md = java.security.MessageDigest.getInstance('SHA-256');
fid = fopen(path, 'rb');
if fid < 0
    error('fixed_weight:numerical_audit:FileOpen', 'Cannot hash file: %s', path);
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
while true
    bytes = fread(fid, 1024 * 1024, '*uint8');
    if isempty(bytes)
        break;
    end
    md.update(bytes);
end
raw = typecast(md.digest(), 'uint8');
digest = lower(string(reshape(dec2hex(raw, 2).', 1, [])));
end
