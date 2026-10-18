"""G01 v0.2 CLI-only stop protection. Import has no global hook side effects.

Standard Logger._log/factory and threading.Thread only, not arbitrary native
faults or hostile runtime mutation. A nonzero process exit overrides markers.
"""
import logging
import os
from pathlib import Path
import stat
import threading

VERSION = 'E019-D03-G01-v0.2'
EVENTS = 'runtime_guard_events.log'
LIMITATION = ('standard logging factory and threading.Thread only; no atomic '
              'commit or hard-real-time guarantee; exit status overrides markers')


class CliGuard:
    def __init__(self):
        # Capture before installing hooks. Never re-resolve os._exit in fatal.
        real_exit = os._exit

        def force_exit():
            try:
                real_exit(70)
            finally:
                # Only relevant if a non-production substitute returns/raises.
                raise SystemExit(70)

        self._force_exit = force_exit
        self._expected_exit = force_exit
        self._real_exit = real_exit
        self._write = os.write
        self._ident = threading.get_ident
        self._lock = threading.Lock()
        self._fatal_seen = False
        self._active = False
        self._fd = 2
        self._event_path = None
        self._event_identity = None
        self._phase = 'bootstrap'
        original_factory = logging.LogRecord

        def factory(name, level, *args, **kwargs):
            if type(level) is not int or level >= 30:
                # No old factory, handler lock, formatting or object repr first.
                self.fatal('logging', args[2] if len(args) > 2 else '')
            self.check()
            return original_factory(name, level, *args, **kwargs)

        def thread_hook(args):
            try:
                self._fatal_seen = True
                # Never format the exception object. Native class names let
                # artificial controls distinguish intended from setup errors.
                cls = args.exc_type
                label = cls.__name__ if type(cls) is type else '<exception-class>'
                self.fatal('thread_exception', label)
            finally:
                force_exit()

        self._factory = factory
        self._thread_hook = thread_hook
        try:
            if (threading.current_thread() is not threading.main_thread() or
                    logging.getLogRecordFactory() is not original_factory or
                    threading.excepthook is not threading.__excepthook__):
                self.fatal('unsupported_initial_hooks')
            logging.setLogRecordFactory(factory)
            threading.excepthook = thread_hook
            self._active = True
            self.check()
        except BaseException:
            self.fatal('guard_installation')

    def fatal(self, kind, message=''):
        exit_now = self._expected_exit
        try:
            self._fatal_seen = True  # Before any lock, introspection or I/O.
            if not self._lock.acquire(blocking=False):
                return  # The outer finally still terminates this process.
            payload = b'G01 fatal; diagnostic unavailable\n'
            try:
                text = message[:512] if type(message) is str else '<non-string>'
                label = kind[:64] if type(kind) is str else '<unknown>'
                phase = self._phase[:64] if type(self._phase) is str else '<unknown>'
                payload = ('G01 fatal '+label+' phase='+phase+' thread='+
                           str(self._ident())+' '+text+'\n').encode('utf-8', 'backslashreplace')
            except BaseException:
                pass  # Fixed bytes remain; never invoke arbitrary formatting.
            try:
                self._write(self._fd, payload)  # One attempt, no retry/flush.
            except BaseException:
                pass
        finally:
            exit_now()

    def check(self, phase=None):
        exit_now = self._expected_exit
        try:
            if self._fatal_seen:
                exit_now()  # Do not wait for the fatal writer or its lock.
            if (not self._active or logging.getLogRecordFactory() is not self._factory or
                    threading.excepthook is not self._thread_hook or
                    self._force_exit is not self._expected_exit or os._exit is not self._real_exit):
                self.fatal('guard_identity_lost')
            if phase is not None:
                if type(phase) is not str:
                    self.fatal('invalid_phase')
                self._phase = phase
            if self._event_path is not None:
                info = os.fstat(self._fd)
                path_info = self._event_path.lstat()
                if (not stat.S_ISREG(path_info.st_mode) or
                        (info.st_dev, info.st_ino) != self._event_identity or
                        (path_info.st_dev, path_info.st_ino) != self._event_identity or info.st_size != 0):
                    self.fatal('guard_event_identity_or_content')
            if self._fatal_seen:
                exit_now()
        except BaseException:
            exit_now()

    def bind_events(self, output):
        self.check('bind_events')
        if self._event_path is not None:
            self.fatal('duplicate_event_binding')
        output = Path(output)
        if not output.is_absolute() or not output.is_dir():
            self.fatal('invalid_event_directory')
        for path in (output, *output.parents):
            if path.is_symlink():
                self.fatal('symlink_event_directory')
        target = output / EVENTS
        # Caller has already checked the fresh exact run directory. Exclusive
        # O_NOFOLLOW open never overwrites a prior event or frozen artifact.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self._fd = fd
        self._event_path = target
        info = os.fstat(fd)
        self._event_identity = (info.st_dev, info.st_ino)
        self.check('events_bound')

    def receipt_state(self):
        self.check('guard_receipt')
        if self._event_path is None:
            self.fatal('missing_event_binding')
        return dict(version=VERSION, healthy=True, fatal_seen=False,
                    events_file=EVENTS, external_exit_required=True, limitation=LIMITATION)


def install_cli():
    """Explicit bootstrap only; keep the guard alive until process exit."""
    return CliGuard()
