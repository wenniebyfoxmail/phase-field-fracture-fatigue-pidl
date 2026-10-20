"""Internal guarded worker. No numerical imports before parent-death/start gate."""
import ctypes,json,os,signal,socket,sys,time
from pathlib import Path


def gate():
    if not sys.platform.startswith('linux'):raise RuntimeError('Linux worker only')
    expected=int(os.environ['E011_SUPERVISOR_PID'])
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0:raise RuntimeError('parent-death guard unavailable')
    if os.getppid()!=expected:raise RuntimeError('supervisor changed before gate')
    fd=int(os.environ['E011_START_FD'])
    if os.read(fd,1)!=b'1':raise RuntimeError('guardian start gate denied')
    os.close(fd)


def main():
    gate()
    from control import allowed_phases,drive,write_json
    from telemetry import Reporter
    from science import Context
    root=Path(os.environ['E011_PACKAGE']);card=json.loads((root/'execution_card.json').read_text())
    science=json.loads((root/'code'/card['science_card']).read_text());archive=Path(card['archive_root'])
    reporter=Reporter(archive/'telemetry.json',[root,archive],science['resource_limits_bytes']);reporter.start()
    ctx=Context(card,science,root,archive,reporter,float(os.environ['E011_STARTED']))
    sock=socket.socket(fileno=int(os.environ['E011_GUARD_FD']));global_sock=socket.socket(fileno=int(os.environ['E011_GLOBAL_GUARD_FD']));scope=os.environ['E011_SCOPE'];names=allowed_phases(scope)
    def notify(row):
        data=json.dumps(row).encode();sock.send(data);global_sock.send(data)
    def save(name,row):
        write_json(archive/(name+'_phase.json'),row)
        if name==names[-1]:
            # Final IO/telemetry/rollback validation is still INSIDE last phase
            # before its done message. After done: only process/socket exit.
            ctx.failure_cleanup();reporter.close()
            status='PREFLIGHT_ONLY_COMPLETE_NOT_SCIENTIFIC_SUCCESS' if scope=='preflight_only' else 'FULL_COMPARISON_COMPLETE'
            write_json(archive/'worker_terminal.json',dict(status=status,scope=scope,run_id=card['run_id'],phase_receipts=list(names),
                closed_before_done=True,accepted_hidden_updates=len(ctx.accepted),science_success_not_inferred=True))
    try:
        drive(scope,ctx.started,{n:getattr(ctx,n) for n in ['preflight','candidate','bounded_witness','readout']},notify,save)
    except BaseException as exc:
        ctx.failure_cleanup()
        try:reporter.close()
        except BaseException:pass
        write_json(archive/'worker_failure.json',dict(type=type(exc).__name__,message=str(exc),retry_allowed=False))
        raise
    finally:sock.close();global_sock.close()


if __name__=='__main__':main()
