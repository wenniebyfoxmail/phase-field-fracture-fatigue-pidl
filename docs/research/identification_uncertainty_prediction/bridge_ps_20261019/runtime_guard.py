"""Fail-closed worker lifetime guard. Stdlib only; never loads scientific data."""
from pathlib import Path
import argparse,atexit,gc,json,os,runpy,sys,threading,time,warnings,traceback


def durable_write(path, payload, *, append=False, _open=os.open, _write=os.write,
                  _fsync=os.fsync, _close=os.close, _encode=json.dumps,
                  _append=os.O_APPEND, _trunc=os.O_TRUNC,
                  _base=os.O_WRONLY|os.O_CREAT):
 data=(_encode(payload,sort_keys=True)+'\n').encode('utf-8')
 fd=_open(path,_base|(_append if append else _trunc),0o600)
 try:
  while data:
   n=_write(fd,data)
   if n<=0:raise OSError('short runtime evidence write')
   data=data[n:]
  _fsync(fd)
 finally:_close(fd)


def install(root,*,on_fatal=None,event_name='runtime_fatal.jsonl'):
 """Fatal hooks retain low-level functions through Python shutdown."""
 logs=Path(root)/'logs';event=str(logs/event_name);seal=str(logs/'runtime_exit.json')
 returned=[False];pid=os.getpid()
 def fatal(kind,exc_type,message,tb=None, _event=event,_pid=pid,_emit=durable_write,
           _exit=os._exit,_write=os.write,_clock=time.time,_str=str,
           _replace=os.replace,_lock=threading.Lock(),_format=traceback.format_tb,_on_fatal=on_fatal):
  if not _lock.acquire(blocking=False):
   try:_write(2,b'RUNTIME_FATAL_REENTRANT\n')
   finally:_exit(86)
  # Publish the complete, fsynced event atomically before the parent may stop us.
  record={'kind':kind,'pid':_pid,'exception_type':'unavailable','message':'fatal exception'}
  try:
   try:description=_str(message)
   except BaseException:description='unprintable exception'
   try:trace=_format(tb) if tb is not None else []
   except BaseException:trace=[]
   record={'kind':kind,'pid':_pid,'time_unix':_clock(),
           'exception_type':getattr(exc_type,'__name__','unknown'),
           'message':description,'traceback':trace}
   _emit(_event+'.partial',record)
   _replace(_event+'.partial',_event)
  except BaseException:
   try:_write(2,b'RUNTIME_FATAL_EVIDENCE_WRITE_FAILED\n')
   except BaseException:pass
  finally:
   try:
    if _on_fatal is not None:_on_fatal(record)
   except BaseException:
    try:_write(2,b'RUNTIME_FATAL_REJECTION_WRITE_FAILED\n')
    except BaseException:pass
   finally:_exit(86)
 def unraisable(args,_fatal=fatal):
  _fatal('unraisable',args.exc_type,args.exc_value,args.exc_traceback)
 def thread_exception(args,_fatal=fatal):
  _fatal('thread_exception',args.exc_type,args.exc_value,args.exc_traceback)
 sys.unraisablehook=unraisable
 threading.excepthook=thread_exception
 warnings.simplefilter('error')
 def finish(_returned=returned,_gc=gc.collect,_emit=durable_write,_seal=seal,
            _pid=pid,_clock=time.time,_fatal=fatal):
  if not _returned[0]:return
  try:
   _gc()
   _emit(_seal,{'status':'RETURNED_AND_EXIT_CALLBACKS_COMPLETE','pid':_pid,'time_unix':_clock()})
  except BaseException as exc:_fatal('exit_guard',type(exc),'exit callback/clean evidence failure')
 # Registered before target: later target callbacks execute before this seal.
 # This seal is provisional: controller still waits for process exit and checks stderr/events.
 atexit.register(finish)
 return returned


def child_failure(root,pid,returncode,*,require_clean=False):
 """Controller checks both durable events and all stderr, including shutdown fallback."""
 if require_clean and returncode is None:return 'worker_not_exited'
 logs=Path(root)/'logs';event=logs/'runtime_fatal.jsonl';stderr=logs/'worker.stderr'
 if event.exists():return 'runtime_fatal_event'
 if not stderr.is_file():return 'worker_stderr_missing'
 if stderr.stat().st_size:return 'worker_stderr_nonempty'
 if returncode is not None and returncode!=0:return 'worker_failed'
 if require_clean:
  try:seal=json.loads((logs/'runtime_exit.json').read_text())
  except (OSError,ValueError):return 'runtime_clean_exit_evidence_missing'
  if seal.get('status')!='RETURNED_AND_EXIT_CALLBACKS_COMPLETE' or seal.get('pid')!=pid:return 'runtime_clean_exit_identity'
 return None


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--target',required=True,type=Path);p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args(argv)
 flag=install(a.root);args=a.arguments
 if args[:1]==['--']:args=args[1:]
 sys.argv=[str(a.target)]+args
 namespace=runpy.run_path(str(a.target),run_name='__main__')
 del namespace
 gc.collect()
 flag[0]=True


if __name__=='__main__':main()
