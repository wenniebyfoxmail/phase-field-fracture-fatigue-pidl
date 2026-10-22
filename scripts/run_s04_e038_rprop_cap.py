"""S04-E038: zero L2, RPROP maximum 1e-3, frozen c1/c40 unloading states."""
from pathlib import Path
import sys
import torch
import run_s04_e035_l2_pairs as base

CAP = 1e-3
base.EXPERIMENT_ID = 'S04-E038'
base.STEPS = (5, 200)
base.ARMS = (('L2_zero_cap1e-3', 0.),)
original_get_optimizer = base.get_optimizer
observations = []


def snapshot(optimizer, record):
    sizes = [optimizer.state[p]['step_size'].detach().reshape(-1)
             for g in optimizer.param_groups for p in g['params']
             if 'step_size' in optimizer.state[p]]
    weights = [p.detach().reshape(-1) for g in optimizer.param_groups
               for p in g['params'] if p.ndim == 2]
    assert len(weights) == 9
    ss, ww = torch.cat(sizes), torch.cat(weights)
    return dict(update=record['updates'], weight_norm=float(ww.norm()),
                weight_abs_max=float(ww.abs().max()), step_max=float(ss.max()),
                step_at_cap_fraction=float((ss >= CAP).float().mean()),
                step_min=float(ss.min()))


def capped_optimizer(params, optimizer_type):
    optimizer = original_get_optimizer(params, optimizer_type)
    assert optimizer_type == 'RPROP'
    for group in optimizer.param_groups:
        assert group['lr'] == 1e-5 and group['etas'] == (.5, 1.2)
        assert group['step_sizes'] == (1e-10, 50)
        group['step_sizes'] = (1e-10, CAP)
    record = dict(step=base.STEPS[len(observations)], updates=0, rows=[])
    observations.append((optimizer, record))

    def observe(opt, _args, _kwargs):
        record['updates'] += 1
        if record['updates'] == 1 or record['updates'] % 50 == 0:
            record['rows'].append(snapshot(opt, record))
    optimizer.register_step_post_hook(observe)
    return optimizer


base.get_optimizer = capped_optimizer

if __name__ == '__main__':
    try:
        base.main()
    finally:
        output = Path(sys.argv[sys.argv.index('--output') + 1])
        if output.is_dir():
            for optimizer, record in observations:
                if record['updates']:
                    record['final'] = snapshot(optimizer, record)
                base.dump(output / f"optimizer_trace_step_{record['step']:03d}.json", record)
            base.dump(output / 'cap_configuration.json', dict(
                max_step=CAP, min_step=1e-10, initial_step=1e-5,
                etas=[.5, 1.2], L2=0., steps=base.STEPS,
                observer='read-only post-step; first/every50/final'))
