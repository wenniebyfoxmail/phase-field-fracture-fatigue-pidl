"""One bounded Linux validation driver, under independent pidfd guardian."""
import argparse,json,os,resource,sys,time
from pathlib import Path
from validate_hybrid_linux import verify_contract,cpu_environment


def main(a):
    card=verify_contract(a)
    outer=Path(card['validation_contract']['outer_control_root'])
    if outer.exists() or a.root.exists():raise FileExistsError('validation already reserved; inspect, never retry')
    outer.mkdir();started=time.perf_counter();cpu_environment(outer)
    # Numerical imports occur only after the CPU/BLAS/CUDA environment is set.
    from run_hybrid_producer import run_owned_worker
    from hybrid_producer_common import write_json
    usage={};error=None;cpu0=resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        command=[sys.executable,'-u',str(a.code/'tools/validate_hybrid_linux.py'),'--outer-worker']
        for key in ('root','code','card','inputs','package'):command+=['--'+key,str(getattr(a,key).resolve())]
        spec=dict(id='actual_linux_validation',kind='admission',gpu=False,wall_seconds=1800)
        run_owned_worker(command,a.code,dict(os.environ,HYBRID_SUPERVISOR_PID=str(os.getpid())),outer/'driver.log',spec,card,outer,outer,
                         dict(start_monotonic=started,gpu_seconds=0.),usage=usage)
        evidence=json.loads((a.root/'admission.json').read_text())
        if evidence.get('passed') is not True:raise RuntimeError('actual validation evidence not passed')
    except BaseException as exc:error=str(exc);raise
    finally:
        cpu=resource.getrusage(resource.RUSAGE_CHILDREN);own=resource.getrusage(resource.RUSAGE_SELF)
        report=dict(passed=error is None,error=error,wall_seconds=time.perf_counter()-started,
                    cpu_seconds_children=cpu.ru_utime+cpu.ru_stime-cpu0.ru_utime-cpu0.ru_stime,
                    cpu_seconds_self=own.ru_utime+own.ru_stime,allocated_core_hours_upper=16*(time.perf_counter()-started)/3600,
                    usage=usage,child_admission=str(a.root/'admission.json'),gpu_seconds=0.,diagnostic_substeps_max=5)
        write_json(outer/'validation_total.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','code','card','inputs','package'):p.add_argument('--'+key,type=Path,required=True)
    main(p.parse_args())
