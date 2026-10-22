function result=e036_sha256_selftest(out_dir)
%E036_SHA256_SELFTEST Tiny file/hash fixtures and injected read failures; no FEM.
assert(~isfolder(out_dir) && ~isfile(out_dir) && isfolder(fileparts(out_dir)), ...
 'E036A:Output','Hash selftest needs a new scratch/evidence directory');mkdir(out_dir);
events={};
check_file('empty',uint8([]),'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
check_file('abc',uint8('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
check_file('binary_0_255',uint8(0:255),'40aff2e9d2d8922e47afd4648e6967497158785fbd1da870e7110266bf944880');
check_file('million_a',repmat(uint8('a'),1000000,1),'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0');
chunk=1024*1024;
for n=[chunk-1 chunk chunk+1 2*chunk+17]
 payload=uint8(mod((0:n-1)',251));
 check_file(sprintf('boundary_%d',n),payload,one_shot(payload));
end
must_reject(@()e036_sha256_file(fullfile(out_dir,'absent.bin')),'E036:HashFile');record('missing_file');
must_reject(@()e036_sha256_file(out_dir),'E036:HashFile');record('directory');
mode='partial_ok';calls=0;
assert(strcmp(e036_sha256_stream(@read_fixture,3),one_shot(uint8('abc'))));record('short_reads_until_eof');
mode='partial_error';calls=0;
must_reject(@()e036_sha256_stream(@read_fixture,3),'E036Test:InjectedRead');record('partial_read_then_exception');
mode='zero';calls=0;
must_reject(@()e036_sha256_stream(@read_fixture,3),'E036:HashRead');record('zero_progress');
mode='short_eof';calls=0;
must_reject(@()e036_sha256_stream(@read_fixture,3),'E036:HashChanged');record('truncated_stream');
mode='growth';calls=0;
must_reject(@()e036_sha256_stream(@read_fixture,2),'E036:HashChanged');record('grown_stream');
result=struct('status','passed','cases',numel(events),'events',{events}, ...
 'native_calls',0,'native_solves',0,'training_updates',0, ...
 'scope','file vectors and simulated I/O faults; not an immutable-snapshot or native-solver proof');
save(fullfile(out_dir,'hash_selftest_result.mat'),'result');
 function check_file(label,payload,expected)
  path=fullfile(out_dir,[label '.bin']);[fid,message]=fopen(path,'wb');assert(fid>=0,'%s',message);
  closer=onCleanup(@()close_if_open(fid));
  written=fwrite(fid,payload,'uint8');assert(written==numel(payload));
  [message,number]=ferror(fid);assert(number==0,'%s',message);
  assert(fclose(fid)==0);clear closer;
  assert(strcmp(e036_sha256_file(path),expected),'E036Test:Hash','Wrong digest: %s',label);record(label);
 end
 function count=read_fixture(buffer)
  calls=calls+1;
  if strcmp(mode,'zero'),count=0;return;end
  if strcmp(mode,'partial_error') && calls==2,error('E036Test:InjectedRead','Read failed after first byte');end
  if strcmp(mode,'growth') && calls==1
   buffer.put(typecast(uint8('abc'),'int8'));count=3;return;
  end
  if strcmp(mode,'short_eof') && calls==2,count=-1;return;end
  if calls<=3
   buffer.put(int8(double('a')+calls-1));count=1;
  else
   count=-1;
  end
 end
 function record(label)
  events{end+1}=label;
 end
end
function digest=one_shot(payload)
% Independent one-shot payload input checks streaming boundaries/order.
hasher=java.security.MessageDigest.getInstance('SHA-256');
hasher.update(typecast(payload(:),'int8'));
digest=lower(reshape(dec2hex(typecast(hasher.digest(),'uint8'),2).',1,[]));
end
function must_reject(callback,identifier)
try
 callback();
catch ex
 assert(strcmp(ex.identifier,identifier),'E036Test:WrongRejection','Expected %s, got %s',identifier,ex.identifier);return;
end
error('E036Test:MissingRejection','Expected %s',identifier);
end
function close_if_open(fid)
% Explicit successful fclose above must not cause an invalid-id cleanup call.
if any(fopen('all')==fid),fclose(fid);end
end
