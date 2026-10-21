"""Persistence-only examples; no network optimization or FEM solve.

These tests are authored but deliberately not executed in the preparation task.
"""
import json
from collections import OrderedDict
from pathlib import Path
import sys

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
import cyclic_persistence as persistence
from cyclic_persistence import (
    PersistenceVerificationError, persist_verified_step, load_verified_step,
)


def _payload():
    field = torch.tensor([0.1, 0.2], dtype=torch.float64)
    return {
        "network_state": OrderedDict(weight=field.clone()),
        "common_problem": {"mesh_digest": "synthetic", "quadrature": "Q4/GP4"},
        "old_state": {"history": torch.zeros(2, dtype=torch.float64),
                      "active_driver": torch.zeros(2, dtype=torch.float64)},
        "fields": {"u": field.clone(), "v": field.clone(), "d": field.clone()},
        "history": field.clone(), "f_solve": torch.ones_like(field),
        "f_commit": torch.ones_like(field),
        "state_key": {"trajectory": "synthetic", "cycle": 1, "substep": 1,
                      "load": 0.25, "timing": "accepted_post_history"},
        "provenance": {"source": "small artificial arrays", "parent": None},
        "acceptance_records": [{"accepted": True, "joint_score": 0.0}],
        "metadata": {"window": "P1", "attempt": 1},
    }


def _replay(payload):
    assert type(payload["network_state"]) is dict
    assert payload["fields"]["d"].device.type == "cpu"
    return {"accepted": True, "joint_score": 0.0, "fresh": True}


def test_saved_payload_is_reloaded_and_replayed_before_completion(tmp_path):
    source = _payload()
    step = tmp_path / "step"
    seen = []
    def replay(loaded):
        assert not (step / "completion.json").exists()
        assert loaded["fields"]["d"] is not source["fields"]["d"]
        seen.append(loaded)
        return _replay(loaded)
    loaded = persist_verified_step(step, source, replay)
    assert loaded is seen[0]
    source["fields"]["d"].zero_()
    assert torch.equal(loaded["fields"]["d"], torch.tensor([0.1, 0.2], dtype=torch.float64))
    receipt = json.loads((step / "completion.json").read_text())
    assert receipt["state_key"] == source["state_key"]
    assert receipt["metadata"]["common_problem"] == source["common_problem"]
    assert receipt["replay"]["fresh"] is True
    assert len(receipt["bundle_sha256"]) == 64
    restored = load_verified_step(step, _replay)
    assert torch.equal(restored["history"], loaded["history"])


@pytest.mark.parametrize("existing_file", ["historical.txt", "incomplete.json"])
def test_existing_directory_cannot_be_reused_or_overwritten(tmp_path, existing_file):
    step = tmp_path / "step"
    step.mkdir()
    marker = step / existing_file
    marker.write_text("preserve")
    with pytest.raises(FileExistsError):
        persist_verified_step(step, _payload(), _replay)
    assert marker.read_text() == "preserve"
    assert sorted(path.name for path in step.iterdir()) == [existing_file]


@pytest.mark.parametrize("result", [True, {"accepted": 1}, {"accepted": False}, {},
                                    {"accepted": True, "metric": float("nan")}])
def test_rejected_or_invalid_replay_never_publishes_completion(tmp_path, result):
    step = tmp_path / "step"
    with pytest.raises(PersistenceVerificationError):
        persist_verified_step(step, _payload(), lambda loaded: result)
    assert not (step / "completion.json").exists()
    assert (step / "incomplete.json").exists()
    with pytest.raises(PersistenceVerificationError):
        load_verified_step(step, _replay)


def test_callback_exception_and_mutation_cannot_publish_completion(tmp_path):
    def raises(loaded):
        raise RuntimeError("reassembly failed")
    def mutates(loaded):
        loaded["history"].zero_()
        return {"accepted": True}
    for name, replay in (("exception", raises), ("mutation", mutates)):
        with pytest.raises(PersistenceVerificationError):
            persist_verified_step(tmp_path / name, _payload(), replay)
        assert not (tmp_path / name / "completion.json").exists()


@pytest.mark.parametrize("change", [
    lambda item: item.update(f_solve=item["f_solve"].float()),
    lambda item: item.update(f_solve=item["f_solve"].reshape(1, 2)),
    lambda item: item["fields"].pop("v"),
    lambda item: item["state_key"].update(cycle=True),
    lambda item: item["fields"]["d"].add_(1.0),
])
def test_readback_strictly_checks_types_keys_shapes_dtypes_and_values(tmp_path, monkeypatch, change):
    original_load = persistence.torch.load
    def changed_load(*args, **kwargs):
        assert kwargs["weights_only"] is True
        result = original_load(*args, **kwargs)
        change(result)
        return result
    monkeypatch.setattr(persistence.torch, "load", changed_load)
    with pytest.raises(PersistenceVerificationError):
        persist_verified_step(tmp_path / "step", _payload(), _replay)
    assert not (tmp_path / "step" / "completion.json").exists()


@pytest.mark.parametrize("bad_value", [object(), Path("not-json"), float("inf")])
def test_unsupported_metadata_is_refused_before_torch_save(tmp_path, monkeypatch, bad_value):
    source = _payload()
    source["provenance"]["unsupported"] = bad_value
    def forbidden_save(*args, **kwargs):
        pytest.fail("invalid metadata must not be pickled")
    monkeypatch.setattr(persistence.torch, "save", forbidden_save)
    with pytest.raises(PersistenceVerificationError):
        persist_verified_step(tmp_path / "step", source, _replay)
    assert not (tmp_path / "step" / "bundle.pt").exists()


def test_bundle_corruption_and_metadata_mismatch_block_loading(tmp_path):
    corrupt = tmp_path / "corrupt"
    persist_verified_step(corrupt, _payload(), _replay)
    with (corrupt / "bundle.pt").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(PersistenceVerificationError, match="checksum"):
        load_verified_step(corrupt, _replay)
    mismatch = tmp_path / "metadata"
    persist_verified_step(mismatch, _payload(), _replay)
    path = mismatch / "completion.json"
    receipt = json.loads(path.read_text())
    receipt["state_key"]["cycle"] = 99
    path.write_text(json.dumps(receipt))
    with pytest.raises(PersistenceVerificationError, match="state_key"):
        load_verified_step(mismatch, _replay)


def test_prior_receipt_does_not_override_current_failed_replay(tmp_path):
    step = tmp_path / "step"
    persist_verified_step(step, _payload(), _replay)
    before = (step / "completion.json").read_bytes()
    with pytest.raises(PersistenceVerificationError, match="replay"):
        load_verified_step(step, lambda loaded: {"accepted": False, "joint_score": 10.0})
    assert (step / "completion.json").read_bytes() == before


def test_explicit_incomplete_marker_overrides_completion(tmp_path):
    step = tmp_path / "step"
    persist_verified_step(step, _payload(), _replay)
    (step / "incomplete.json").write_text('{"complete": false}')
    with pytest.raises(PersistenceVerificationError, match="incomplete"):
        load_verified_step(step, _replay)


def test_bundle_modified_by_replay_is_incomplete(tmp_path):
    step = tmp_path / "step"
    def changes_file(loaded):
        with (step / "bundle.pt").open("ab") as stream:
            stream.write(b"changed during replay")
        return {"accepted": True}
    with pytest.raises(PersistenceVerificationError, match="changed during"):
        persist_verified_step(step, _payload(), changes_file)
    assert not (step / "completion.json").exists()


def test_write_failure_leaves_no_completion_and_no_usable_state(tmp_path, monkeypatch):
    def failed_save(*args, **kwargs):
        raise OSError("simulated write failure")
    monkeypatch.setattr(persistence.torch, "save", failed_save)
    step = tmp_path / "step"
    with pytest.raises(PersistenceVerificationError, match="incomplete"):
        persist_verified_step(step, _payload(), _replay)
    assert not (step / "completion.json").exists()
    with pytest.raises(PersistenceVerificationError):
        load_verified_step(step, _replay)
