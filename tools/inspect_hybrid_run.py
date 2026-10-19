"""Read-only recovery inspection. Never unlock, resume or recommit automatically."""
import argparse
import json
from pathlib import Path

from hybrid_transaction import StateStore


def inspect(root):
    root=Path(root);rows=[]
    for path in sorted(root.glob('*/latest.npz')):
        state,meta=StateStore(path).load()
        events=path.parent/'events.jsonl'
        steps=[]
        if events.exists():
            for line in events.read_text().splitlines():
                row=json.loads(line)
                if 'step' in row:steps.append(row['step'])
        rows.append(dict(phase=path.parent.name,version=state.version,load_index=state.load_index,
                         state_id=state.fingerprint(),last_journal_step=max(steps,default=0),
                         crash_lock_present=path.with_name(path.name+'.lock').exists(),
                         snapshot_present=(path.parent/f'states/state{state.version:04d}.npz').exists(),
                         reconciliation_needed=state.version!=max(steps,default=0),
                         action='inspect durable state/certificate; do not blindly retry or remove lock'))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True)
    print(json.dumps(inspect(p.parse_args().archive),indent=2))
