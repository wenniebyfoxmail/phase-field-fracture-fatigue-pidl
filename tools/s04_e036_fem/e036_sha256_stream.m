function digest=e036_sha256_stream(read_next,expected_bytes)
%E036_SHA256_STREAM Hash a bounded byte stream; production reader is FileChannel.
% read_next writes into the supplied Java ByteBuffer and returns the byte count,
% or -1 at EOF. Exceptions propagate, including those after a successful partial
% read. This small core permits deterministic I/O-failure tests without a test
% override or alternate reader in e036_sha256_file's public interface.
assert(isa(read_next,'function_handle') && isscalar(expected_bytes) && ...
 isfinite(expected_bytes) && expected_bytes>=0 && expected_bytes<=flintmax && ...
 expected_bytes==fix(expected_bytes),'E036:HashStream','Invalid stream contract');
hasher=java.security.MessageDigest.getInstance('SHA-256');
buffer=java.nio.ByteBuffer.allocate(1024*1024);total=0;
while true
 buffer.clear();
 count=double(read_next(buffer)); % A genuine read exception never becomes EOF.
 assert(isscalar(count) && isfinite(count) && count==fix(count) && count>=-1, ...
  'E036:HashRead','Invalid read count');
 if count==-1
  assert(double(buffer.position())==0,'E036:HashRead','EOF returned with unread bytes');
  break;
 end
 assert(count>0 && count==double(buffer.position()), ...
  'E036:HashRead','Read made no progress or returned an inconsistent byte count');
 total=total+count;
 assert(total<=expected_bytes,'E036:HashChanged','Stream grew while hashing');
 buffer.flip();hasher.update(buffer);
 assert(double(buffer.remaining())==0,'E036:HashRead','Digest did not consume the complete block');
end
assert(total==expected_bytes,'E036:HashChanged','Stream ended before its recorded size');
bytes=typecast(hasher.digest(),'uint8');
digest=lower(reshape(dec2hex(bytes,2).',1,[]));
assert(numel(digest)==64,'E036:HashDigest','Unexpected SHA-256 result');
end
