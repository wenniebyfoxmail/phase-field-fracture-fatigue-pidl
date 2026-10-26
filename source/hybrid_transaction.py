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
from hybrid_state_contract import envelope, verify_envelope, verify_transition


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
            evidence = {k[len('evidence_'):]: data[k] for k in data.files if k.startswith('evidence_')}
        if state.fingerprint() != meta["state_id"]:
            raise RuntimeError("stored state digest mismatch")
        if 'state_contract' in meta:
            verify_envelope(state, meta, evidence)
        elif evidence:
            raise RuntimeError('unbound field evidence')
        return state, meta

    def _write(self, state, metadata, evidence=None):
        # The caller holds the exclusive lock. No state is held in a mutable
        # controller: success returns the persisted state; failure returns none.
        temp = None
        replaced = False
        started = perf_counter()
        try:
            identity = {f.name: getattr(state, f.name) for f in fields(state)
                        if not isinstance(getattr(state, f.name), np.ndarray)}
            meta = dict(metadata, identity=identity, state_id=state.fingerprint())
            evidence = {} if evidence is None else evidence
            if 'state_contract' in meta:
                verify_envelope(state, meta, evidence)
            fd, temp = tempfile.mkstemp(prefix=self.path.name + ".trial-", dir=self.path.parent)
            with os.fdopen(fd, "wb") as handle:
                np.savez(handle, **{f.name: getattr(state, f.name) for f in fields(state)
                                    if isinstance(getattr(state, f.name), np.ndarray)},
                         **{'evidence_' + k: v for k, v in evidence.items()},
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

    def initialize(self, state, *, context=None):
        lock = self._lock()
        try:
            if self.path.exists():
                raise FileExistsError(self.path)
            meta = {"kind": "declared_initial_state"}
            if context is not None:
                meta['state_contract'] = envelope(state, context, None, {})
            return self._write(state, meta)
        finally:
            lock.rmdir()

    def commit(self, proposal):
        lock = self._lock()
        try:
            old, old_meta = self.load()
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
            meta = dict(kind="accepted", certificate=cert, work=proposal.work)
            if proposal.accepted_contract is not None:
                meta['state_contract'] = proposal.accepted_contract
                verify_transition(old, old_meta, new, meta)
                return self._write(new, meta, proposal.field_evidence)
            if 'state_contract' in old_meta:
                raise RuntimeError('cannot drop accepted-state contract during commit')
            return self._write(new, meta)
        finally:
            lock.rmdir()
