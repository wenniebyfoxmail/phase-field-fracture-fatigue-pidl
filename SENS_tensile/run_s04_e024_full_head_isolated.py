"""Execution-only recovery controller: cache c20, one fresh c60/c83 process."""
import argparse,csv,datetime,hashlib,json,shutil,socket,subprocess,sys,time
from pathlib import Path
from s04_e024_full_head_recovery import remaining_seconds


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(a):
    source=Path(__file__).resolve().parents[1]
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==a.expected_commit
    assert subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True)==''
    initial=a.project/'local_archive/experiments/S04-E024/full_head_attainable_v1'
    original=read(initial/'execution_exit.json');assert original['exit_code']==1
    prior=float(original['elapsed_seconds']);start=time.perf_counter()
    assert not (a.out/'results').exists()
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'execution_command.json').write_text(json.dumps(dict(source_commit=a.expected_commit,host=socket.gethostname(),
        command=sys.argv,start_utc=now(),prior_failed_elapsed=prior,controller_sha256=sha(Path(__file__)),cpu_threads=2,training=False),indent=2)+'\n')
    worker_records=[]
    try:
        for state in ('c20s4','c60s4','c83s4'):
            remaining=remaining_seconds(time.perf_counter()-start,prior)
            case=a.out/'states'/state;case.mkdir(parents=True,exist_ok=False)
            cmd=[sys.executable,str(source/'SENS_tensile/diagnose_s04_e023_full_head.py'),'--project',str(a.project),
                 '--out',str(case/'results'),'--expected-commit',a.expected_commit,'--state',state]
            record=dict(state=state,command=cmd,start_utc=now(),timeout_seconds=remaining)
            (case/'command.json').write_text(json.dumps(record,indent=2)+'\n')
            with (case/'stdout.log').open('w') as stdout,(case/'stderr.log').open('w') as stderr:
                result=subprocess.run(cmd,cwd=source,stdout=stdout,stderr=stderr,timeout=remaining)
            record.update(end_utc=now(),exit_code=result.returncode)
            (case/'exit.json').write_text(json.dumps(record,indent=2)+'\n')
            if result.returncode:raise RuntimeError(state+' worker failed; no continuation')
            worker_records.append(read(case/'results/receipt.json'))
            remaining_seconds(time.perf_counter()-start,prior)
            print(state,'completed',flush=True)
        assert sum(r['offline_full_head_solves'] for r in worker_records)==2
        assert sum(r['recovered_completed_solves'] for r in worker_records)==1
        assert all(r['source_commit']==a.expected_commit for r in worker_records)
        assert all(all(r[k]==0 for k in ('neural_optimizer_steps','original_checkpoint_writes','history_fatigue_damage_updates','remote_actions')) for r in worker_records)
        target=a.out/'results';target.mkdir()
        copies={};audits=[];assets=[];traces={}
        for name in ('uv_metrics.csv','physical_metrics.csv','guard_values.csv','line_search.csv'):
            rows=[];fields=None
            for state in ('c20s4','c60s4','c83s4'):
                path=a.out/'states'/state/'results'/name
                with path.open() as file:
                    reader=csv.DictReader(file)
                    if fields is None:fields=reader.fieldnames
                    assert fields==reader.fieldnames
                    rows.extend(list(reader))
            with (target/name).open('w') as file:
                writer=csv.DictWriter(file,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
        for state,r in zip(('c20s4','c60s4','c83s4'),worker_records):
            case=a.out/'states'/state/'results';src=case/f'{state}_full_head.npz';dest=target/src.name
            shutil.copyfile(src,dest);assert sha(dest)==sha(src)
            copies[str(dest)]=dict(source=str(src),sha256=sha(src))
            audits.extend(read(case/'numerics.json'));assets.extend(r['assets']);traces.update(read(case/'solver_trace.json'))
        (target/'numerics.json').write_text(json.dumps(audits,indent=2)+'\n')
        (target/'solver_trace.json').write_text(json.dumps(traces,indent=2)+'\n')
        elapsed=time.perf_counter()-start;remaining_seconds(elapsed,prior)
        receipt=dict(source_commit=a.expected_commit,states=['c20s4','c60s4','c83s4'],assets=assets,
            scientific_solve_sources={r['state']:r['scientific_solve_source'] for r in audits},
            scientific_helper_sha256=sha(source/'SENS_tensile/s04_e024_full_head.py'),
            wall_seconds=prior+elapsed,recovery_controller_wall_seconds=elapsed,prior_failed_elapsed_seconds=prior,
            peak_rss_bytes=max(r['peak_rss_bytes'] for r in worker_records),parameter_radius_fraction=.02,
            accepted_external_fields=sum(r['accepted_external_fields'] for r in worker_records),
            unique_full_head_solves=3,new_solves_in_recovery=2,replayed_completed_c20_solves=1,
            neural_optimizer_steps=0,original_checkpoint_writes=0,history_fatigue_damage_updates=0,remote_actions=0,
            worker_receipts=[str(a.out/'states'/s/'results/receipt.json') for s in ('c20s4','c60s4','c83s4')],
            scope='complete fixed-head convex proxy and actual witnesses; c20 reused from preserved incomplete attempt')
        (target/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        (a.out/'aggregate_copy_manifest.json').write_text(json.dumps(copies,indent=2)+'\n')
        (a.out/'execution_exit.json').write_text(json.dumps(dict(exit_code=0,end_utc=now(),combined_elapsed_seconds=prior+time.perf_counter()-start),indent=2)+'\n')
        print('three states aggregated; three unique solves total',flush=True)
    except Exception as error:
        (a.out/'execution_exit.json').write_text(json.dumps(dict(exit_code=1,end_utc=now(),error=str(error),
            combined_elapsed_seconds=prior+time.perf_counter()-start),indent=2)+'\n')
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expected-commit',required=True);run(p.parse_args())
