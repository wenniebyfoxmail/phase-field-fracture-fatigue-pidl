function digest=e036_sha256_file(path)
%E036_SHA256_FILE Stream a local file through MATLAB's JVM; no writes.
% New explicit dependency for E036 readback/publication. Prepared, not executed.
assert(usejava('jvm'),'E036:JVM','SHA-256 verification requires the MATLAB JVM');
assert(isfile(path),'E036:HashFile','A regular existing file is required');
[fid,message]=fopen(path,'rb');assert(fid>=0,'E036:HashOpen','%s',message);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
hasher=java.security.MessageDigest.getInstance('SHA-256');
while true
 block=fread(fid,1024*1024,'*uint8');
 if isempty(block),break;end
 hasher.update(typecast(block(:),'int8'));
end
[message,number]=ferror(fid);assert(number==0,'E036:HashRead','%s',message);
bytes=typecast(hasher.digest(),'uint8');
digest=lower(reshape(dec2hex(bytes,2).',1,[]));
assert(numel(digest)==64,'E036:HashDigest','Unexpected SHA-256 result');
end
