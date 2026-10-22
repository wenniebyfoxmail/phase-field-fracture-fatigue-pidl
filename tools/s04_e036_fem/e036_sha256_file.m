function digest=e036_sha256_file(path)
%E036_SHA256_FILE Stream a local file through MATLAB's JVM; no writes.
% FileChannel distinguishes normal EOF (-1) from an IOException. In particular,
% do not interpret MATLAB ferror's platform-dependent EOF message as read failure.
% Size/mtime checks detect ordinary drift, not an immutable filesystem snapshot;
% callers must still compare the digest with their bound value and recheck it
% at publication. Same-size concurrent rewrites can evade metadata checks.
assert(usejava('jvm'),'E036:JVM','SHA-256 verification requires the MATLAB JVM');
assert(isfile(path),'E036:HashFile','A regular existing file is required');
file=java.io.File(char(path)).getCanonicalFile();
before_size=double(file.length());before_mtime=double(file.lastModified());
input=java.io.FileInputStream(file);
cleanup=onCleanup(@()input.close()); %#ok<NASGU>
channel=input.getChannel();opened_size=double(channel.size());
assert(opened_size==before_size,'E036:HashChanged','File size changed while opening');
digest=e036_sha256_stream(@(buffer)channel.read(buffer),opened_size);
assert(double(channel.position())==opened_size && double(channel.size())==opened_size, ...
 'E036:HashChanged','Opened file size or position changed while hashing');
input.close(); % A close failure must not publish a digest either.
assert(file.isFile() && double(file.length())==before_size && ...
 double(file.lastModified())==before_mtime,'E036:HashChanged','File metadata changed while hashing');
end
