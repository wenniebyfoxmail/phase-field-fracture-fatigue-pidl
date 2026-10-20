"""Read-only recovery inspection. Never unlock, resume or recommit automatically."""
import argparse
import json
from pathlib import Path

from hybrid_transaction import StateStore


def inspect(root):
    root=Path(root);rows=[]
    for path in sorted(root.glob('*/latest.npz')):
        row=dict(phase=path.parent.name,crash_lock_present=path.with_name(path.name+'.lock').exists(),
                 action='inspect durable state/certificate; do not blindly retry or remove lock')
        steps=[];errors=[]
        events=path.parent/'events.jsonl'
        try:
            if events.exists():
                for number,line in enumerate(events.read_text().splitlines(),1):
                    try:
                        event=json.loads(line)
                        if not isinstance(event,dict):raise ValueError('event is not an object')
                        if 'step' in event:steps.append(int(event['step']))
                    except (ValueError,TypeError) as exc:
                        errors.append(dict(line=number,error=str(exc),kind='malformed_or_truncated_journal'))
                        break  # only valid prefix is evidence; never skip to later "completion"
        except OSError as exc:errors.append(dict(kind='journal_read_error',error=str(exc)))
        row.update(last_journal_step=max(steps,default=0),journal_errors=errors)
        try:
            state,meta=StateStore(path).load()
            row.update(version=state.version,load_index=state.load_index,state_id=state.fingerprint(),
                       snapshot_present=(path.parent/f'states/state{state.version:04d}.npz').exists(),
                       reconciliation_needed=bool(errors) or state.version!=max(steps,default=0))
        except Exception as exc:
            row.update(inspection_error=str(exc),reconciliation_needed=True)
        trace=path.parent/'work_trace.jsonl';active={};trace_errors=[]
        if trace.exists():
            try:
                for n,line in enumerate(trace.read_text().splitlines(),1):
                    try:
                        event=json.loads(line);key=(event['step'],event['block_id'])
                        if event['event']=='start':active[key]=event
                        elif event['event']=='end':active.pop(key,None)
                    except (ValueError,KeyError,TypeError) as exc:
                        trace_errors.append(dict(line=n,error=str(exc)));break
            except OSError as exc:trace_errors.append(dict(error=str(exc)))
        row.update(unfinished_work_blocks=list(active.values()),work_trace_errors=trace_errors,
                   work_evidence_incomplete=bool(active or trace_errors))
        iteration_file=path.parent/'iterations.jsonl';last_iteration=None;iteration_errors=[]
        if iteration_file.exists():
            try:
                for n,line in enumerate(iteration_file.read_text().splitlines(),1):
                    try:
                        item=json.loads(line)
                        if not isinstance(item,dict) or 'outer' not in item or 'step' not in item:raise ValueError('invalid iteration record')
                        last_iteration=item
                    except (ValueError,TypeError) as exc:iteration_errors.append(dict(line=n,error=str(exc)));break
            except OSError as exc:iteration_errors.append(dict(error=str(exc)))
        row.update(last_outer_iteration=last_iteration,iteration_evidence_errors=iteration_errors)
        rows.append(row)
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True)
    print(json.dumps(inspect(p.parse_args().archive),indent=2))
