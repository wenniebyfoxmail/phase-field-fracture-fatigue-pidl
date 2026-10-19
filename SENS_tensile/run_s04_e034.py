"""Opt-in E034 producer entrypoint. Default/import performs no input/model/GPU IO."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
import numpy as np
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
import s04_e027 as old
import s04_e028 as scored
import s04_e034 as m
from compute_energy import stress
from run_s04_e027 import initializer_compatibility, deadline_signal

LOCK = ROOT/'docs/research/S04/S04-E034/data_lock.json'
UUID = 'GPU-5622bd47-1050-3003-246d-3cabe2b4791b'


def rss_bytes():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system() == 'Darwin' else 1024)


def dump(path, value):
    tmp = path.with_suffix(path.suffix+'.new')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
    return digest.hexdigest()


def finalize(out, grant, receipt, budget, primary_error):
    """Terminal IO cannot turn an interrupted/partial package into completion.

    Return a finalization exception separately, retaining the original failure.
    A nonzero outer exit or watchdog stop always overrides any partial receipt.
    """
    final_error = None
    if primary_error is not None:
        receipt['status'] = 'stopped_no_retry'
        receipt.setdefault('error', f'{type(primary_error).__name__}: {primary_error}')
    archived = Path(grant['archive_root'])/'output'
    def diagnostic(message):
        try:
            print(message, file=sys.stderr, flush=True)
        except BaseException:
            pass  # A broken log sink must not replace the scientific/run error.
    def invalidate_completion():
        for folder in (out, archived):
            try:
                (folder/'completion.json').unlink(missing_ok=True)
            except BaseException as error:
                diagnostic('E034 completion invalid (nonzero exit required): '+repr(error))
    def record_failure(error):
        nonlocal final_error
        if final_error is None: final_error = error
        receipt['status'] = 'stopped_no_retry'
        receipt.setdefault('finalization_errors', []).append(f'{type(error).__name__}: {error}')
        try:
            try:
                dump(out/'receipt.json', receipt)
            except BaseException as write_error:
                # Disk failure can prevent receipts; outer nonzero exit rules.
                diagnostic('E034 FINALIZATION STOP: '+repr(error)+'; receipt write: '+repr(write_error))
            try:
                if archived.exists(): dump(archived/'receipt.json', receipt)
            except BaseException as write_error:
                diagnostic('E034 archived receipt invalid: '+repr(write_error))
        finally:
            invalidate_completion()
    try:
        budget.guard()
        receipt.update(elapsed_seconds=time.monotonic()-budget.started, end_unix=time.time(),
            shared_seconds=budget.shared+(time.monotonic()-budget.phase_started if budget.phase == 'shared' else 0),
            peak_RSS_bytes=rss_bytes())
        if budget.cap is not None:
            receipt.update(peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(), peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated())
        if primary_error is None:
            receipt['status'] = 'completed_pending_HQ_evaluation'
        dump(out/'receipt.json', receipt)
        manifest = []
        for path in sorted(out.rglob('*')):
            if path.is_file() and path.name not in ('manifest.json', 'phase_deadline.json', 'watchdog_done', 'completion.json'):
                manifest.append(dict(path=str(path.relative_to(out)), bytes=path.stat().st_size, sha256=sha256(path)))
        dump(out/'manifest.json', manifest)
        if archived.exists():
            for name in ('receipt.json', 'manifest.json'): shutil.copy2(out/name, archived/name)
        budget.guard()
        if primary_error is None:
            # The marker, matching manifest, no watchdog stop AND outer exit=0
            # together constitute completion. Watchdog stays active through IO.
            dump(out/'completion.json', dict(status='completed_pending_HQ_evaluation', protocol=m.PROTOCOL,
                 manifest_sha256=sha256(out/'manifest.json'), final_unix=time.time()))
            if archived.exists(): shutil.copy2(out/'completion.json', archived/'completion.json')
            budget.guard()
    except BaseException as error:
        record_failure(error)
    finally:
        try:
            budget.close()
        except BaseException as error:
            record_failure(error)
    return final_error


def authorization(lock, grant, out):
    """Fail before resource access or real input loading, including on Mac."""
    if platform.system() == 'Darwin':
        raise PermissionError('Mac is synthetic-fixture/import only')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True) or head != grant.get('approved_commit'):
        raise PermissionError('clean exact approved commit required')
    if lock['protocol'] != m.PROTOCOL or grant.get('protocol') != m.PROTOCOL:
        raise PermissionError('protocol mismatch')
    if grant.get('execution_authorized') is not True or not all(grant.get(k) for k in ('review_reference', 'human_approval_reference')):
        raise PermissionError('new exact execution authorization and review required')
    if (grant.get('gpu_hours_cap'), grant.get('ram_gib_cap'), grant.get('output_gib_cap'), grant.get('total_gpu_hours_cap')) != (.5, 32, 2, 2):
        raise PermissionError('frozen budget mismatch')
    if grant.get('prior_conservative_gpu_hours') != 1.108339654581623:
        raise PermissionError('cumulative accounting mismatch')
    if grant.get('hostname') != platform.node() or grant.get('gpu_uuid') != UUID or grant.get('cuda_visible_devices') != '5' or os.environ.get('CUDA_VISIBLE_DEVICES') != '5':
        raise PermissionError('exact host/GPU5 required')
    runroot = Path(grant['run_root'])
    if runroot.parent != Path('/mnt/data2/drtao/wennie') or out != runroot/'output' or grant.get('output') != str(out):
        raise PermissionError('fresh canonical task output required')
    if grant.get('archive_root') != str(Path('/mnt/data2/drtao/pidl_archives')/runroot.name):
        raise PermissionError('canonical archive root required')
    if Path(grant['archive_root']).exists():
        raise FileExistsError('fresh archive only; no retry')
    for key, suffix in [('TMPDIR', 'tmp'), ('XDG_CACHE_HOME', '.cache'), ('TORCH_EXTENSIONS_DIR', '.jitcache')]:
        if os.environ.get(key) != str(runroot/suffix):
            raise PermissionError('task-owned cache '+key)
    if out.exists():
        raise FileExistsError('fresh output only; no retry')
    gitdir = Path(subprocess.check_output(['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT, text=True).strip())
    common = (ROOT/subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT, text=True).strip()).resolve()
    if gitdir != common or (gitdir/'objects/info/alternates').exists() or any(p.stat().st_nlink > 1 for p in (gitdir/'objects').rglob('*') if p.is_file()):
        raise PermissionError('independent clone: no worktree, alternates or hardlinked objects')
    return head


def device_admission():
    """Called only after exact new grant, never by preparation/fixture checks."""
    query = ['nvidia-smi', '-i', '5', '--query-gpu=uuid,memory.free,utilization.gpu', '--format=csv,noheader,nounits']
    fields = subprocess.check_output(query, text=True, timeout=10).strip().split(',')
    apps = subprocess.check_output(['nvidia-smi', '-i', '5', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], text=True, timeout=10).strip()
    if len(fields) != 3 or fields[0].strip() != UUID or float(fields[1]) < 20480 or float(fields[2]) != 0 or apps:
        raise PermissionError('GPU5 live UUID/20GiB/free/SM0/no-app admission failed')
    disks = subprocess.check_output(['df', '-Pk', '/', '/mnt/data2', '/mnt/data3'], text=True, timeout=10)
    # Query distinct filesystems and forbid unavailable/small data mount.
    data_disk = subprocess.check_output(['df', '-Pk', '/mnt/data2'], text=True, timeout=10).splitlines()[-1].split()
    if data_disk[-1] != '/mnt/data2' or int(data_disk[3])*1024 < 8*1024**3:
        raise OSError('canonical mount needs 8GiB free')
    available = next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    if available < 32*1024**3:
        raise MemoryError('host requires 32GiB available')
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise PermissionError('one visible CUDA GPU required')
    free, total = torch.cuda.mem_get_info()
    if free < 20*1024**3:
        raise MemoryError('initial 20GiB CUDA free required')
    cap = free-1024**3
    torch.cuda.set_per_process_memory_fraction(cap/total, 0)
    return cap, dict(gpu_query=fields, compute_apps=apps, disks=disks, host_available_bytes=available)


class Budget:
    """Nontransferable phase quotas, plus an independent process watchdog."""
    def __init__(self, out, started):
        self.out, self.started, self.shared = out, started, 0.
        self.phase, self.phase_started, self.cap = 'shared', started, None
        self.write_deadline()
        self.watchdog = subprocess.Popen([sys.executable, str(ROOT/'source/s04_e034_watchdog.py'), str(os.getpid()), str(out)])

    def write_deadline(self):
        quota = 480-self.shared if self.phase == 'shared' else 600
        dump(self.out/'phase_deadline.json', dict(pid=os.getpid(), phase=self.phase,
             deadline=min(self.started+1790, self.phase_started+quota)))

    def phase_to(self, name):
        now = time.monotonic()
        if self.phase == 'shared':
            self.shared += now-self.phase_started
        self.phase, self.phase_started = name, now
        self.write_deadline(); self.guard()

    @contextmanager
    def exporting(self):
        """Arm exports consume both their arm wall quota and shared export quota."""
        began = time.monotonic()
        if self.phase != 'shared':
            dump(self.out/'phase_deadline.json', dict(pid=os.getpid(), phase=self.phase+'+shared_export',
                 deadline=min(self.started+1790, self.phase_started+600, began+480-self.shared)))
        try:
            yield
        finally:
            if self.phase != 'shared': self.shared += time.monotonic()-began
            self.write_deadline(); self.guard()

    def guard(self):
        now = time.monotonic()
        if now-self.started >= 1790:
            raise TimeoutError('whole package cap')
        quota = 480-self.shared if self.phase == 'shared' else 600
        if now-self.phase_started >= quota:
            raise TimeoutError('phase cap '+self.phase)
        if self.cap is not None:
            torch.cuda.synchronize()
            if torch.cuda.max_memory_reserved() > self.cap or torch.cuda.mem_get_info()[0] < 1024**3:
                raise MemoryError('GPU cap/1GiB headroom')
        if rss_bytes() > 32*1024**3:
            raise MemoryError('RSS cap')
        if sum(p.stat().st_size for p in self.out.rglob('*') if p.is_file()) > 2*1024**3:
            raise OSError('2GiB output cap')

    def close(self):
        (self.out/'watchdog_done').touch()
        self.watchdog.wait(timeout=3)


def physical_identity(p, q, damage):
    scored.check_physical(p, q)
    if not torch.equal(q[:, 2], damage):
        raise ValueError('external physical damage changed')
    free = torch.zeros(2*len(q), dtype=torch.bool, device=q.device); free[p.free] = True
    delta = torch.cat(((q-p.ref)[:, 0], (q-p.ref)[:, 1]))
    if delta[~free].numel() and float(delta[~free].abs().max().detach()) > 1e-10:
        raise ValueError('prescribed UV boundary violation')


def actual_forward(model, theta, p, damage):
    """Functional actual NN forward; no trial mutates formal model weights."""
    state = dict(model.named_parameters())
    state['output_layer.weight'] = torch.cat((theta[:, :-1], state['output_layer.weight'][2:]), 0)
    state['output_layer.bias'] = torch.cat((theta[:, -1], state['output_layer.bias'][2:]), 0)
    with torch.no_grad():
        raw = torch.func.functional_call(model, state, (p.xy,))
        y = p.xy[:, 1]; bubble = (y+.5)*(.5-y)
        return torch.stack((old.US*bubble*raw[:, 0], old.US*(bubble*raw[:, 1]+y+.5), damage), 1)


def snapshot(p, q, out, label, accounting):
    """Only scheduled points: native fields/strain/stress/forces and local errors."""
    accounting['snapshot_physics_calls'] += 1
    q = q.detach().requires_grad_(True)
    parts = p.parts(*q.unbind(1)); force = p.force(q)
    def gp_data(value):
        gu, gv = (old.q4_gradient(value[:, j], p.conn, p.B) for j in (0, 1))
        strain = (gu[:, :, 0], gv[:, :, 1], .5*(gu[:, :, 1]+gv[:, :, 0]))
        d = old.q4_interpolate(value[:, 2], p.conn, p.N)
        sigma = stress(*strain, d, p.mat, p.pff)
        sub = p.parts(*value.unbind(1))
        gpfields = [old.q4_interpolate(value[:, j], p.conn, p.N) for j in range(3)]+list(sub[3:])
        return torch.stack(gpfields, -1), torch.stack(strain, -1), torch.stack(sigma, -1)
    gp, eps, sigma = gp_data(q)
    rgp, reps, rsigma = gp_data(p.ref)
    xy = torch.einsum('gn,enx->egx', p.N, p.xy[p.conn])
    top = (p.xy[p.conn][:, :, 1] == .5).any(1)[:, None].expand_as(p.w)
    masks = dict(global_domain=torch.ones_like(p.gp_zone), Z=p.gp_zone,
                 left_band=(xy[:, :, 0] <= 0) & (xy[:, :, 1].abs() <= .03), top_layer=top)
    payload = dict(fields=q, signed_nodal_error=q-p.ref, gp_fields=gp, signed_gp_error=gp-rgp,
                   strain=eps, signed_strain_error=eps-reps, stress=sigma, signed_stress_error=sigma-rsigma,
                   force=force)
    payload.update({'mask_'+k: v for k, v in masks.items()})
    np.savez_compressed(out/(label+'.npz'), **{k: v.detach().cpu().numpy() for k, v in payload.items()})
    summary = dict(scores=scored.component_scores(p, q.detach()),
        reactions=[float(force[len(q):][p.xy[:, 1] == y].sum().detach()) for y in (.5, -.5)],
        free_force_norm=float(force[p.free].norm().detach()),
        signed_free_v_sum=float(force[p.free[p.free >= len(q)]].sum().detach()),
        signed_all_v_sum=float(force[len(q):].sum().detach()), regions={})
    summary['reaction_absolute_errors'] = [abs(a-b) for a, b in zip(summary['reactions'], m.REACTION_REF)]
    for name, mask in masks.items():
        w = p.w[mask]
        if not len(w):
            raise ValueError('empty reporting support '+name)
        summary['regions'][name] = dict(gp_field_RMSE=torch.sqrt((w[:, None]*(gp-rgp)[mask].square()).sum(0)/w.sum()).detach().cpu().tolist(),
            strain_RMSE=torch.sqrt((w[:, None]*(eps-reps)[mask].square()).sum(0)/w.sum()).detach().cpu().tolist(),
            stress_RMSE=torch.sqrt((w[:, None]*(sigma-rsigma)[mask].square()).sum(0)/w.sum()).detach().cpu().tolist())
    dump(out/(label+'.json'), summary)
    return summary


def run(lock, grant, out):
    started = time.monotonic()
    head = authorization(lock, grant, out)
    out.mkdir(parents=True)
    budget = Budget(out, started)
    receipt = dict(protocol=m.PROTOCOL, commit=head, host=platform.node(), pid=os.getpid(), command=sys.argv, e033_output=grant['e033_output'],
                   source_dirty=False, retry=False, status='preparing', arms={}, snapshot_physics_calls=0,
                   verification_physics_calls=0, shared_jacobian_points=0, history_commits=0, FEM_solves=0,
                   accepted_head_updates=0, start_unix=time.time())
    primary_error = None
    try:
        dump(out/'data_lock.json', lock); dump(out/'grant.json', grant)
        budget.cap, admission = device_admission(); dump(out/'admission.json', admission)
        receipt.update(gpu_uuid=UUID, cuda_visible_devices='5', cuda_cap_bytes=budget.cap)
        state, compatibility = initializer_compatibility(Path(grant['s0']), {'initializer': lock['s0']})
        dump(out/'compatibility.json', compatibility)
        control, history = Path(grant['control_output']), Path(grant['e033_output'])
        for row in lock['control_payloads'].values():
            old.verify_payload(control, row); budget.guard()
        for row in lock['e033_payloads'].values():
            old.verify_payload(history, row); budget.guard()
        arrays = old.load_reference(Path(grant['data_root']), lock['reference_lock'])
        p = old.Problem(arrays, 'cuda:0'); scored.validate_current_lower(p)
        # Include repeated baseline/verification/export mechanics in accounting,
        # beyond the separately recorded optimizer objective/constraint calls.
        for name in ('parts', 'force'):
            operation = getattr(p, name)
            key = 'native_'+name+'_calls'; receipt[key] = 0
            def counted(*args, operation=operation, key=key, **kwargs):
                receipt[key] += 1
                return operation(*args, **kwargs)
            setattr(p, name, counted)
        frozen = np.load(control/'fields.npz'); theta_np = np.load(control/'head_endpoint.npz')['theta']
        parent_receipt = json.loads((control/'receipt.json').read_text())
        if parent_receipt['commit'] != lock['expected_control_runtime_commit'] or parent_receipt['accepted_head_updates'] != 1:
            raise ValueError('actual accepted E032 parent required')
        historic = np.load(history/'head_geometry.npz'); diagnostic = np.load(history/'diagnostic_geometry.npz')
        if not np.array_equal(historic['theta0'], theta_np) or not np.array_equal(diagnostic['theta0'], theta_np):
            raise ValueError('frozen cone anchor identity')
        geometry = m.Geometry(historic['basis'], diagnostic['full_gradients'])
        if not np.allclose(historic['gradients'], m.RADIUS*np.einsum('ij,kj->ik', diagnostic['full_gradients'], geometry.basis), atol=1e-12, rtol=1e-12):
            raise ValueError('saved8 projected gradient identity')
        model = old.make_model(state, 'cuda:0')
        for param in model.parameters(): param.requires_grad_(False)
        theta0 = torch.as_tensor(theta_np, device=p.xy.device, dtype=torch.float64)
        if theta0.shape != (2, 401) or abs(.02*float(theta0.norm())-m.RADIUS) > 1e-15:
            raise ValueError('frozen head/radius')
        with torch.no_grad():
            features = model.encode(p.xy).detach()
            model.output_layer.weight[:2].copy_(theta0[:, :-1]); model.output_layer.bias[:2].copy_(theta0[:, -1])
        damage = torch.as_tensor(frozen['UVjoint'][:, 2].copy(), device=p.xy.device, dtype=torch.float64)
        identities = (p.previous.clone(), p.f.clone(), p.old_gp.clone())
        before = {k: v.detach().clone() for k, v in model.state_dict().items()}
        q0 = m.parent.fields(theta0, features, p, damage)
        physical_identity(p, q0, damage)
        if not np.array_equal(frozen['reference'], arrays['ref']) or not np.allclose(q0.cpu().numpy(), frozen['UVjoint'], atol=1e-10, rtol=0):
            raise ValueError('full E032 replay')
        if float((actual_forward(model, theta0, p, damage)-q0).abs().max()) > 1e-10:
            raise ValueError('zero actual NN forward mismatch')
        initial = scored.component_scores(p, q0)
        for key, value in lock['expected_zero_scores'].items():
            if not np.isclose(initial[key], value, atol=1e-10, rtol=1e-10):
                raise ValueError('E032 zero score '+key)
        with torch.no_grad(): reference = tuple(v.detach() for v in p.parts(*p.ref.unbind(1)))
        force_norm = initial['free_force']
        zero_leaf = q0.detach().requires_grad_(True)
        zero_values, reactions = m.physical_values(p, zero_leaf, reference, force_norm)
        if max(abs(float(a.detach())-b) for a, b in zip(reactions, m.REACTION_ZERO)) > 1e-10:
            raise ValueError('locked two-sided baseline reaction mismatch')
        baseline = zero_values.detach(); baseline[-2:] = 1.  # Locked E032 reaction-error scales, not rescaled by replay.
        if not bool(torch.isfinite(baseline).all()) or bool((baseline <= 0).any()):
            raise ValueError('positive actual baseline metrics')
        dump(out/'zero_metrics.json', dict(zip(m.METRICS, baseline.cpu().tolist())))
        np.savez_compressed(out/'frozen_features.npz', features=features.cpu().numpy(), theta0=theta_np,
                            physical_damage=damage.cpu().numpy(), basis=geometry.basis, cone=geometry.cone)
        snapshot(p, q0, out, 'Z0', receipt); budget.guard()
        # One actual zero-point Jacobian check per planned coordinate system.
        # Compare chain projection, not finite-difference optimization or a trial correction.
        shared_jacs = {}
        for arm in ('F8', 'F802'):
            matrix = torch.as_tensor(geometry.matrix(arm), device=p.xy.device, dtype=torch.float64)
            r, j, _ = m.values_and_jacobian(p, theta0, features, damage, matrix, np.zeros(len(matrix)), baseline, reference, force_norm)
            m.finite(r, 'zero ratios'); m.finite(j, 'zero Jacobian'); shared_jacs[arm] = j
            receipt['shared_jacobian_points'] += 1; budget.guard()
        if not np.allclose(shared_jacs['F8'], np.einsum('ij,kj->ik', shared_jacs['F802'], geometry.basis), atol=1e-10, rtol=1e-8):
            raise ValueError('actual F8/F802 Jacobian embedding mismatch')
        # Frozen eleven gradients must replay the actual anchor, including higher-order force chain.
        replay_g = shared_jacs['F802'][:11]*baseline[:11].cpu().numpy()[:, None]/m.RADIUS
        if not np.allclose(replay_g, diagnostic['full_gradients'], atol=1e-10, rtol=1e-8):
            raise ValueError('saved original eleven gradients changed')
        np.savez_compressed(out/'zero_jacobians.npz', **shared_jacs)
        endpoints = {}
        for arm in ('F8', 'F802'):
            budget.phase_to(arm)
            armout = out/arm; armout.mkdir()
            matrix = torch.as_tensor(geometry.matrix(arm), device=p.xy.device, dtype=torch.float64)
            verified = {}
            def evaluate(x):
                result = m.values_and_jacobian(p, theta0, features, damage, matrix, x, baseline, reference, force_norm)
                with torch.no_grad():
                    q = m.parent.fields(theta0+m.RADIUS*torch.einsum('i,ij->j', torch.as_tensor(x, device=p.xy.device), matrix).reshape(2, 401), features, p, damage)
                physical_identity(p, q, damage); budget.guard()
                return result
            def verify(x, ratios):
                theta = theta0+m.RADIUS*torch.einsum('i,ij->j', torch.as_tensor(x, device=p.xy.device), matrix).reshape(2, 401)
                q = actual_forward(model, theta, p, damage)
                affine = m.parent.fields(theta, features, p, damage)
                gap = float((q-affine).abs().max())
                physical_identity(p, q, damage)
                if gap > 1e-10: raise ValueError('actual NN/affine finite forward mismatch')
                vals, _ = m.physical_values(p, q.detach().requires_grad_(True), reference, force_norm)
                receipt['verification_physics_calls'] += 1
                actual = (vals/baseline).detach().cpu().numpy()
                dump(armout/'actual_forward.json', dict(gap=gap, ratios=actual.tolist()))
                if not m.meets_target(actual, geometry.constraints(x, arm)[0]):
                    raise ValueError('first target failed actual NN guards; stop, no search continuation')
                verified.update(q=q.detach(), theta=theta.detach(), ratios=actual)
            def observe(row):
                # JSON null preserves nonfinite observations before a mandatory stop.
                def clean(value):
                    if isinstance(value, float) and not np.isfinite(value): return None
                    if isinstance(value, list): return [clean(v) for v in value]
                    if isinstance(value, dict): return {k: clean(v) for k, v in value.items()}
                    return value
                with (armout/'points.jsonl').open('a') as f: f.write(json.dumps(clean(row), allow_nan=False)+'\n')
            def milestone(iteration, x):
                with torch.no_grad():
                    q = m.parent.fields(theta0+m.RADIUS*torch.einsum('i,ij->j', torch.as_tensor(x, device=p.xy.device), matrix).reshape(2, 401), features, p, damage)
                with budget.exporting(): snapshot(p, q, armout, 'major_'+str(iteration), receipt)
                budget.guard()
            cache = m.PointCache(arm, geometry, evaluate, verify, observe, budget.guard)
            try:
                x, result = m.solve_arm(cache, milestone)
            finally:
                dump(armout/'accounting.json', dict(calls=cache.calls, distinct_points=len(cache.rows),
                     elapsed_seconds=time.monotonic()-budget.phase_started))
            with budget.exporting():
                dump(armout/'solver.json', result)
                q = verified['q'] if result['accepted'] else torch.as_tensor(frozen['UVjoint'].copy(), device=p.xy.device)
                theta = verified['theta'] if result['accepted'] else theta0.clone()
                physical_identity(p, q, damage)
                endpoints[arm] = dict(x=x.copy(), q=q.detach().cpu().numpy(), accepted=result['accepted'])
                scores = snapshot(p, q, armout, 'endpoint', receipt)
                scores['global_active_vs_E030_zero'] = scores['scores']['global_active_RMSE']/scored.component_scores(p, torch.as_tensor(frozen['E030_zero'], device=p.xy.device))['global_active_RMSE']
                e031 = scored.component_scores(p, torch.as_tensor(frozen['E031_R'], device=p.xy.device))
                scores['u_RMS_vs_E031'] = {k: scores['scores'][k]/e031[k] for k in ('global_u_RMS_Us', 'zone_u_RMS_Us')}
                dump(armout/'endpoint.json', scores)
                np.savez_compressed(armout/'head_endpoint.npz', theta0=theta_np, theta=theta.cpu().numpy(), coefficient=x)
                endpoint_state = {k: v.clone() for k, v in before.items()}
                endpoint_state['output_layer.weight'][:2] = theta[:, :-1]
                endpoint_state['output_layer.bias'][:2] = theta[:, -1]
                torch.save(dict(model=endpoint_state, physical_damage=damage, theta0=theta0, theta=theta,
                                protocol=m.PROTOCOL, network_damage_is_not_physical_buffer=True), armout/'endpoint.pt')
                receipt['accepted_head_updates'] += int(result['accepted']); receipt['arms'][arm] = result
                dump(out/'receipt.json', receipt); budget.guard()
        budget.phase_to('shared')
        h = endpoints['F802']['x']; z, decomposition = geometry.decompose(h)
        if endpoints['F802']['accepted'] and decomposition['outside_norm'] <= 1e-12 and decomposition['reconstruction_max_abs'] <= 1e-12:
            matrix = torch.as_tensor(geometry.basis, device=p.xy.device)
            r, j, extra = m.values_and_jacobian(p, theta0, features, damage, matrix, z, baseline, reference, force_norm)
            receipt['projected_reproduction_points'] = 1
            m.finite(j, 'projected reproduction Jacobian')
            theta = theta0+m.RADIUS*torch.einsum('i,ij->j', torch.as_tensor(z, device=p.xy.device), matrix).reshape(2, 401)
            q = actual_forward(model, theta, p, damage); physical_identity(p, q, damage)
            if float((q-m.parent.fields(theta, features, p, damage)).abs().max()) > 1e-10:
                raise ValueError('projected actual forward mismatch')
            vals, _ = m.physical_values(p, q.detach().requires_grad_(True), reference, force_norm)
            actual = (vals/baseline).detach().cpu().numpy(); m.finite(actual, 'projected actual values')
            decomposition['projected_actual_target_pass'] = m.meets_target(actual, geometry.constraints(z, 'F8')[0])
            decomposition.update(projected_ratios=actual.tolist(), affine_ratios=r.tolist(), extra=extra)
        else: receipt['projected_reproduction_points'] = 0
        dump(out/'representation.json', decomposition)
        if any(not torch.equal(a, b) for a, b in zip(identities, (p.previous, p.f, p.old_gp))) or any(not torch.equal(v, before[k]) for k, v in model.state_dict().items()):
            raise ValueError('frozen hidden/damage head/history/fatigue changed')
        dump(out/'identity.json', dict(frozen_model_bitwise=True, external_damage_bitwise=True, history_fatigue_bitwise=True))
        render(out, p, endpoints, frozen, receipt); budget.guard()
        receipt['status'] = 'computed_pending_finalization'
        # CPU archive is still inside the shared wall quota and outer watchdog.
        shutil.copytree(out, Path(grant['archive_root'])/'output', ignore=shutil.ignore_patterns('phase_deadline.json', 'watchdog_done'))
        budget.guard()
    except BaseException as error:
        receipt.update(status='stopped_no_retry', error=f'{type(error).__name__}: {error}')
        primary_error = error
    finally:
        final_error = finalize(out, grant, receipt, budget, primary_error)
    if primary_error is not None: raise primary_error
    if final_error is not None: raise final_error


def render(out, p, endpoints, frozen, receipt):
    """FEM-first same-scale field/error maps; native local supports also exported."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    names = ['reference', 'E032', 'H0', 'F8', 'F802']
    h0 = np.load(Path(receipt['e033_output'])/'fields.npz')['endpoint']
    fields = [frozen['reference'], frozen['UVjoint'], h0, endpoints['F8']['q'], endpoints['F802']['q']]
    display = []
    for values in fields:
        q = torch.as_tensor(values, device=p.xy.device)
        with torch.no_grad():
            gp = [old.q4_interpolate(q[:, j], p.conn, p.N) for j in range(3)]+list(p.parts(*q.unbind(1))[3:])
            display.append(np.stack([((v*p.w).sum(1)/p.w.sum(1)).cpu().numpy() for v in gp]))
    polygons = p.xy[p.conn].cpu().numpy()
    baseline = json.loads((out/'Z0.json').read_text())['scores']['global_raw_RMSE']
    takeaway = '; '.join(arm+': raw ratio '+str(json.loads((out/arm/'endpoint.json').read_text())['scores']['global_raw_RMSE']/baseline)+', accepted '+str(endpoints[arm]['accepted']) for arm in ('F8', 'F802'))
    def sidecar(stem, guide):
        (out/(stem+'.md')).write_text('# '+stem+'\n\nQuestion: bounded finite state repair with reaction protection.\n\n'
            'Data provenance: this exact run data_lock.json, receipt.json, manifest.json; native Q4 GP4.\n\n'
            'How to read: '+guide+'\n\nNumerical takeaway: '+takeaway+'. Original target ratio <=0.999.\n\n'
            'Limitation: one exposed state; no physical evolution, teacher qualification or generalization. H0 is archived historical comparator, not a matched causal ablation.\n')
    views = dict(global_domain=None, Z=(0, .5, -.03, .03), left_band=(-.5, 0, -.03, .03), top_layer=(-.5, .5, float(p.xy[p.conn[(p.xy[p.conn][:, :, 1] == .5).any(1)]][:, :, 1].min()), .5))
    for error, base_stem in ((False, 'fields'), (True, 'signed_errors')):
        cols = list(range(1, 5)) if error else list(range(5))
        for view, limits in views.items():
            stem = base_stem+'_'+view
            fig, axes = plt.subplots(5, len(cols), figsize=(3.2*len(cols), 14), squeeze=False, layout='constrained')
            for row, label in enumerate(('u', 'v', 'd', 'raw', 'active')):
                values = [display[k][row]-display[0][row] if error else display[k][row] for k in cols]
                hi = max(float(abs(v).max()) for v in values) or 1e-30
                lo = -hi if error else min(float(v.min()) for v in values)
                if not error: hi = max(float(v.max()) for v in values)
                for ax, k, val in zip(axes[row], cols, values):
                    im = PolyCollection(polygons, array=val, cmap='RdBu_r' if error else 'viridis', edgecolors='none')
                    im.set_clim(lo, hi); ax.add_collection(im); ax.autoscale_view(); ax.set_aspect('equal'); ax.set_title(label+': '+names[k])
                    if limits is not None: ax.set_xlim(limits[:2]); ax.set_ylim(limits[2:])
                fig.colorbar(im, ax=list(axes[row]), shrink=.8)
            fig.suptitle('E034 | exposed c20s4 / horizon0 / seed1 | '+view)
            fig.savefig(out/(stem+'.png'), dpi=130); plt.close(fig)
            sidecar(stem, 'Rows u/v/d/raw/active; columns '+', '.join(names[k] for k in cols)+
                    '. Shared unclipped global row scale across all zooms; native Jacobian-weighted element means. Errors are prediction minus FEM. '+
                    'View '+view+'; exact local GP masks and errors in snapshot JSON/NPZ; top_layer includes all top-adjacent elements.')
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')
    for ax, arm in zip(axes, ('F8', 'F802')):
        rows = [json.loads(line) for line in (out/arm/'points.jsonl').read_text().splitlines() if '"ratios"' in line]
        for j, name in enumerate(m.METRICS): ax.plot([r['index'] for r in rows], [r['ratios'][j] for r in rows], label=name)
        ax.axhline(1, color='gray', linestyle=':'); ax.axhline(.998001, color='black', linestyle='--')
        ax.set(title=arm, xlabel='distinct actual parameter point (not physical time)', ylabel='squared metric / E032 baseline')
        ax.legend(fontsize=6, ncol=2)
    fig.savefig(out/'actual_trace.png', dpi=150); plt.close(fig)
    sidecar('actual_trace', 'Left F8, right F802. Thirteen actual squared metric ratios at every distinct visited point, including rejected trials. Dotted nonincrease=1; dashed raw target=0.998001. Lines are diagnostic evaluation order, not a physical trajectory or accepted updates.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--grant', type=Path); parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if not args.execute:
        print('Preparation only; no inputs/model/GPU read.')
    else:
        if not args.grant or not args.out: parser.error('exact grant and fresh output required')
        signal.signal(signal.SIGTERM, deadline_signal); signal.signal(signal.SIGINT, deadline_signal)
        run(json.loads(LOCK.read_text()), json.loads(args.grant.read_text()), args.out)
