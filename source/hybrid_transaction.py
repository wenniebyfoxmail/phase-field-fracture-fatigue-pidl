"""Single-file accepted-state CAS transactions. No implicit retries.

Local POSIX filesystem required for rename + directory fsync. If an error
occurs AFTER replacement, the commit outcome is uncertain: block further
work and reconcile the durable state. Never pretend the old version survived.
"""
from dataclasses import fields
import json
import os
from pathlib import Path
import tempfile
from time import perf_counter

import numpy as np

from hybrid_history import AcceptedState


class CommitUncertain(RuntimeError):
    pass


class StateStore:
    def __init__(self, path):
        self.path = Path(path)
        self.last_io_seconds = None

    def load(self):
        with np.load(self.path, allow_pickle=False) as data:
            meta = json.loads(str(data["metadata"].item()))
            state = AcceptedState(**{k: data[k] for k in
                                     ("displacement", "damage", "accumulated", "driver", "fatigue", "opaque")},
                                  **meta["identity"])
        if state.fingerprint() != meta["state_id"]:
            raise RuntimeError("stored state digest mismatch")
        return state, meta

    def _write(self, state, metadata):
        # The caller holds the exclusive lock. No state is held in a mutable
        # controller: success returns the persisted state; failure returns none.
        temp = None
        replaced = False
        started = perf_counter()
        try:
            fd, temp = tempfile.mkstemp(prefix=self.path.name + ".trial-", dir=self.path.parent)
            identity = {f.name: getattr(state, f.name) for f in fields(state)
                        if not isinstance(getattr(state, f.name), np.ndarray)}
            meta = dict(metadata, identity=identity, state_id=state.fingerprint())
            with os.fdopen(fd, "wb") as handle:
                np.savez(handle, **{f.name: getattr(state, f.name) for f in fields(state)
                                    if isinstance(getattr(state, f.name), np.ndarray)},
                         metadata=np.array(json.dumps(meta, sort_keys=True, allow_nan=False)))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
            replaced = True
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            return state
        except Exception as exc:
            if replaced:
                raise CommitUncertain("replacement occurred; reconcile stored version before any continuation") from exc
            raise
        finally:
            # Caller must charge this measured IO duration in its external run
            # ledger; putting final fsync timing inside the same file recurses.
            self.last_io_seconds = perf_counter() - started
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)

    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_name(self.path.name + ".lock")
        # Atomic mkdir is supported on declared local filesystems. A crash can
        # leave a lock: manual reconciliation required, never auto-remove it.
        lock.mkdir()
        return lock

    def initialize(self, state):
        lock = self._lock()
        try:
            if self.path.exists():
                raise FileExistsError(self.path)
            return self._write(state, {"kind": "declared_initial_state"})
        finally:
            lock.rmdir()

    def commit(self, proposal):
        lock = self._lock()
        try:
            old, _ = self.load()
            new, cert = proposal.state, proposal.certificate
            if (proposal.previous_id != old.fingerprint()
                    or cert.get("previous_id") != old.fingerprint()
                    or cert.get("state_id") != new.fingerprint()
                    or cert.get("passed") is not True
                    or new.version != old.version + 1 or new.load_index != old.load_index + 1
                    or new.mesh_id != old.mesh_id or new.physics_id != old.physics_id
                    or new.damage.shape != old.damage.shape
                    or np.any(new.damage < old.damage)
                    or np.any(new.accumulated < old.accumulated)
                    or not np.array_equal(new.opaque, old.opaque)):
                raise RuntimeError("stale, unaudited or inconsistent commit proposal")
            return self._write(new, dict(kind="accepted", certificate=cert, work=proposal.work))
        finally:
            lock.rmdir()
