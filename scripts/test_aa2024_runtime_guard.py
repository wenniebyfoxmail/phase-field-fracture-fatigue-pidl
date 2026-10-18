"""G01: standard-library artificial child processes only; execution needs approval.

No scientific imports, arrays, reports, plotting or actual QR/SVD. Expected
negative-control exit70 is not permission to ignore an unexpected parent error.
"""
import time
START = time.monotonic()

import argparse
import ast
import hashlib
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import warnings
import json

IMPORT_STATE = (logging.getLogRecordFactory(), threading.excepthook)
import aa2024_runtime_guard as runtime
IMPORT_UNCHANGED = IMPORT_STATE == (logging.getLogRecordFactory(), threading.excepthook)

warnings.simplefilter('error')
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS')
NAMES = ('aa2024_q_recheck.py', 'aa2024_q_verify.py', 'test_aa2024_q_recheck.py',
         'aa2024_dyadic_reference.py', 'test_aa2024_underflow.py',
         'aa2024_runtime_guard.py', 'test_aa2024_runtime_guard.py')
BASELINE = '5e7553887f70c840e02a830f2e5ab8f7553d6869'
CASES = ('normal_main', 'normal_thread', 'import_only', 'main_warning', 'main_error',
         'background_warning', 'background_error', 'thread_exception', 'thread_systemexit',
         'thread_pythonwarning', 'swallowed_logging', 'late_failure', 'write_failure',
         'short_write', 'hostile_message', 'old_raise_handler', 'locked_handler',
         'factory_lost', 'hook_lost', 'inactive_guard', 'exit_rebound',
         'blocked_evidence', 'simultaneous', 'early_import_warning',
         'unsupported_factory', 'unsupported_hook')


class NoScientificImports:
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split('.')[0]
        if root in ('numpy', 'scipy', 'matplotlib', 'torch', 'aa2024_q_recheck',
                    'aa2024_q_verify', 'aa2024_dyadic_reference',
                    'test_aa2024_underflow', 'test_aa2024_q_recheck'):
            raise AssertionError('G01 forbids scientific/producer imports: '+root)


sys.meta_path.insert(0, NoScientificImports())


def demand(ok, message):
    if not ok:
        raise AssertionError(message)


def left():
    remaining = 60-(time.monotonic()-START)
    if remaining <= 0:
        raise TimeoutError('G01 entire artificial package soft60s; no retry')
    return remaining


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True,
                                   timeout=min(5., left())).strip()


def identity(repo, source):
    head = git(repo, 'rev-parse', 'HEAD')
    demand(not git(repo, 'status', '--porcelain'), 'clean source required')
    git(repo, 'merge-base', '--is-ancestor', source, head)
    demand(all(p.startswith('docs/') for p in
               git(repo, 'diff', '--name-only', source, head).splitlines()), 'docs-only successors')
    hashes = {n: hashlib.sha256((repo/'scripts'/n).read_bytes()).hexdigest() for n in NAMES}
    left()
    return head, hashes


def child(case, root):
    demand(case in CASES and root.is_absolute() and root.is_dir(), 'owned artificial case')
    if case == 'import_only':
        demand(IMPORT_UNCHANGED, 'first helper import isolation')
        (root/'passed').write_text('import only')
        return
    if case == 'unsupported_factory':
        logging.setLogRecordFactory(lambda *a, **k: logging.LogRecord(*a, **k))
    if case == 'unsupported_hook':
        threading.excepthook = lambda args: None
    if case in ('old_raise_handler', 'locked_handler'):
        class OldHandler(logging.Handler):
            def emit(self, record):
                (root/'handler_entered').write_text('unexpected')
                raise RuntimeError('old raise-only handler')
        handler = OldHandler()
        logging.getLogger().addHandler(handler)
        if case == 'locked_handler':
            ready = threading.Event()

            def hold():
                handler.acquire()
                ready.set()
                threading.Event().wait(10)
            threading.Thread(target=hold).start()
            demand(ready.wait(1), 'handler lock setup')
    guard = runtime.install_cli()
    if case == 'early_import_warning':
        logging.warning('artificial dependency-import warning')
    guard.bind_events(root)
    if case == 'normal_main':
        logging.getLogger().addHandler(logging.NullHandler())
        logging.getLogger().setLevel(logging.INFO)
        logging.info('ordinary information')
    elif case == 'normal_thread':
        worker = threading.Thread(target=lambda: None)
        worker.start(); worker.join(1)
        demand(not worker.is_alive(), 'normal worker finished')
    elif case in ('main_warning', 'old_raise_handler', 'locked_handler'):
        logging.warning('artificial expected warning')
    elif case == 'main_error':
        logging.error('artificial expected error')
    elif case in ('background_warning', 'background_error'):
        level = logging.WARNING if case == 'background_warning' else logging.ERROR
        worker = threading.Thread(target=lambda: logging.log(level, 'artificial thread log'))
        worker.start(); worker.join(1)
    elif case in ('thread_exception', 'thread_systemexit', 'thread_pythonwarning'):
        def fail():
            if case == 'thread_pythonwarning':
                warnings.warn('artificial thread warning', UserWarning)
            if case == 'thread_systemexit':
                raise SystemExit(0)
            raise RuntimeError('artificial unhandled worker exception')
        worker = threading.Thread(target=fail)
        worker.start(); worker.join(1)
    elif case == 'swallowed_logging':
        try:
            logging.warning('artificial library catch')
        except Exception:
            (root/'caught').write_text('unexpected recovery')
    elif case == 'late_failure':
        ready = threading.Event()

        def late():
            demand(ready.wait(1), 'late failure rendezvous')
            logging.warning('artificial warning after marker')
        worker = threading.Thread(target=late)
        worker.start()
        (root/'completion').write_text('not sufficient for success')
        ready.set(); worker.join(1)
    elif case == 'write_failure':
        def broken_write(fd, payload):
            raise OSError('artificial evidence failure')
        guard._write = broken_write
        logging.warning('artificial failed evidence')
    elif case == 'short_write':
        guard._write = lambda fd, payload: 0
        logging.warning('artificial short evidence')
    elif case == 'hostile_message':
        class Hostile:
            def __str__(self):
                (root/'formatted').write_text('unexpected formatting')
                raise RuntimeError('must not format')
        logging.warning(Hostile())
    elif case == 'factory_lost':
        logging.setLogRecordFactory(logging.LogRecord)
        guard.check()
    elif case == 'hook_lost':
        threading.excepthook = threading.__excepthook__
        guard.check()
    elif case == 'inactive_guard':
        guard._active = False
        guard.check()
    elif case == 'exit_rebound':
        os._exit = lambda status: None
        guard.check()
    elif case == 'blocked_evidence':
        entered = threading.Event()

        def blocked(fd, payload):
            entered.set()
            threading.Event().wait(10)
            return 0
        guard._write = blocked
        worker = threading.Thread(target=lambda: logging.warning('artificial blocked evidence'))
        worker.start()
        demand(entered.wait(1), 'writer entered after fatal latch')
        guard.check()  # Must exit without waiting for writer/event-file content.
    elif case == 'simultaneous':
        barrier = threading.Barrier(3)

        def race():
            barrier.wait(1)
            logging.warning('artificial concurrent fatal')
        first, second = threading.Thread(target=race), threading.Thread(target=race)
        first.start(); second.start(); barrier.wait(1)
        first.join(1); second.join(1)
    guard.check()
    guard.receipt_state()
    (root/'passed').write_text('normal terminal sentinel')


def source_checks(repo):
    def tree(name, old=False):
        text = git(repo, 'show', BASELINE+':scripts/'+name) if old else (repo/'scripts'/name).read_text()
        return ast.parse(text)
    producer = tree('aa2024_q_recheck.py')
    nodes = {n.name: n for n in producer.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    imports = [n.lineno for n in producer.body if isinstance(n, ast.ImportFrom) and n.module in ('numpy', 'scipy')]
    numpy_import = next(n.lineno for n in producer.body if isinstance(n, ast.Import) and any(a.name == 'numpy' for a in n.names))
    guard_line = next(n.lineno for n in producer.body if isinstance(n, ast.Assign) and
                      any(isinstance(t, ast.Name) and t.id == '_RUNTIME_GUARD' for t in n.targets))
    demand(guard_line < min([numpy_import, *imports]), 'guard before scientific imports')
    demand('guard_point' in ast.dump(nodes['Budget']), 'budget checks guard health')
    demand('guard_point' in ast.dump(nodes['draw']), 'plot stage checks guard health')
    demand('runtime_guard' in ast.dump(nodes['main']), 'receipt declares guard state')
    before, after = tree('aa2024_q_recheck.py', True), producer
    old = {n.name: n for n in before.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    for name in ('require', 'close', 'mm', 'q', 'square', 'Factors', 'mesh_definition',
                 'sampling', 'validate_source', 'construct', 'repair', 'analyze',
                 'artificial', 'selective', 'load_real'):
        demand(ast.dump(old[name]) == ast.dump(nodes[name]), 'unchanged producer numeric/source '+name)
    old_budget, new_budget = old['Budget'], nodes['Budget']
    check = next(n for n in new_budget.body if isinstance(n, ast.FunctionDef) and n.name == 'check')
    inserted = check.body.pop(0)
    demand(ast.dump(inserted) == ast.dump(ast.parse('guard_point()').body[0]), 'only budget insertion')
    demand(ast.dump(old_budget) == ast.dump(new_budget), 'original budget clock/60s unchanged')
    old_verify, new_verify = tree('aa2024_q_verify.py', True), tree('aa2024_q_verify.py')
    funcs = lambda t: {n.name: ast.dump(n) for n in t.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name != 'main'}
    demand(funcs(old_verify) == funcs(new_verify), 'verifier math unchanged')
    for name in ('aa2024_dyadic_reference.py', 'test_aa2024_underflow.py', 'test_aa2024_q_recheck.py'):
        baseline = subprocess.check_output(['git', 'show', BASELINE+':scripts/'+name], cwd=repo,
                                           timeout=min(5., left()))
        demand(baseline == (repo/'scripts'/name).read_bytes(), 'original arithmetic/tests unchanged '+name)
    left()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit')
    parser.add_argument('--child', choices=CASES)
    parser.add_argument('--case-root', type=Path)
    args = parser.parse_args()
    demand(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and
           all(os.environ.get(k) == '1' for k in THREADS), 'single CPU environment')
    if args.child:
        demand(args.case_root is not None, 'artificial case root')
        child(args.child, args.case_root)
        return
    demand(args.source_commit is not None and args.case_root is None, 'parent source identity')
    guard = runtime.install_cli()
    repo = Path(__file__).resolve().parents[1]
    initial = identity(repo, args.source_commit)
    source_checks(repo)
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='e019-g01-artificial-') as temporary:
        base = Path(temporary).resolve()
        for case in CASES:
            guard.check('artificial_child')
            left()
            root = base/case
            root.mkdir()
            command = [sys.executable, '-W', 'error', '-B', str(Path(__file__).resolve()),
                       '--child', case, '--case-root', str(root)]
            # run(timeout) kills and waits only its own child on timeout. No
            # retries or next case after that unexpected failure.
            run = subprocess.run(command, cwd=repo, capture_output=True, text=True,
                                 timeout=min(3., left()))
            expected = 0 if case in ('normal_main', 'normal_thread', 'import_only') else 70
            demand(run.returncode == expected, case+' exit '+str(run.returncode)+' expected '+str(expected)+
                   '\nstdout='+run.stdout+'\nstderr='+run.stderr)
            demand(run.stdout == '' and (run.stderr == '' or
                   all(line.startswith('G01 fatal ') for line in run.stderr.splitlines())), case+' unexpected output')
            demand((root/'passed').exists() == (expected == 0), case+' terminal sentinel')
            demand(not any((root/name).exists() for name in ('handler_entered', 'formatted', 'caught')), case+' recovery/handler/format sentinel')
            demand((root/'completion').exists() == (case == 'late_failure'), case+' late marker')
            event = root/runtime.EVENTS
            if expected == 0 and case != 'import_only':
                demand(event.read_bytes() == b'', case+' clean events')
            if case in ('early_import_warning', 'unsupported_factory', 'unsupported_hook', 'import_only'):
                demand(not event.exists(), case+' must not bind unknown output')
            outcomes.append(dict(case=case, exit_code=run.returncode, expected=expected,
                                 stderr=run.stderr, event_text=event.read_text() if event.exists() else None))
            guard.check()
            left()
    demand(identity(repo, args.source_commit) == initial, 'final source identity')
    demand(not any(n.split('.')[0] in ('numpy', 'scipy', 'matplotlib', 'torch') for n in sys.modules), 'no scientific modules')
    guard.check('parent_stdout')
    elapsed = 60-left()
    print(json.dumps(dict(status='G01_artificial_children_completed_not_resource_or_DIC_acceptance',
                          children=len(outcomes), source_checks=2, outcomes=outcomes,
                          actual_svd=0, actual_qr=0, runtime_head=initial[0],
                          source_commit=args.source_commit, source_sha256=initial[1], elapsed_before_print=elapsed)))
    guard.check()
    left()


if __name__ == '__main__':
    main()
