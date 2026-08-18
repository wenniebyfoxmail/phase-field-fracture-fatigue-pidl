from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_three_arm_packet_is_frozen_and_not_authorized():
    validator = load("g3_validator", ROOT / "scripts" / "validate_rrapinn_g3_packet.py")
    payload = json.loads((ROOT / "docs" / "experiments" / "rrapinn_g3_smoke_packet.json").read_text())
    assert validator.validate(payload)["status"] == "pass_schema_only"


def test_runner_tri_state_is_fail_closed():
    runner = load("g3_runner", ROOT / "SENS_tensile" / "run_fem_mesh_probe_driver_umax.py")
    parser = runner._build_parser()
    absent = parser.parse_args(["0.12", "--mechanical-risk-mode", "absent"])
    off = parser.parse_args(["0.12", "--mechanical-risk-mode", "off"])
    on = parser.parse_args([
        "0.12", "--mechanical-risk-mode", "on",
        "--mechanical-risk-lambda", "0.000549728557462236",
    ])
    assert runner._mechanical_risk_config(absent) is None
    assert runner._mechanical_risk_config(off) == {"enable": False}
    assert runner._mechanical_risk_config(on)["enable"] is True
    bad = parser.parse_args(["0.12", "--mechanical-risk-mode", "on"])
    with pytest.raises(ValueError, match="finite positive"):
        runner._mechanical_risk_config(bad)


def test_launcher_rejects_tampered_frozen_receipt():
    launcher = load("g3_launcher", ROOT / "scripts" / "run_rrapinn_g3_arm.py")
    raw = (ROOT / "docs" / "experiments" / "rrapinn_g3_smoke_packet.json").read_bytes()
    template = json.loads(raw)
    head = "a" * 40
    packet = launcher._replace(template, head)
    packet["template_sha256"] = hashlib.sha256(raw).hexdigest()
    packet["launch_receipt_frozen"] = True
    packet["training_authorized"] = False
    launcher.validate_frozen_receipt(ROOT, packet, head)
    packet["command_common"][4] = "999"
    with pytest.raises(RuntimeError, match="exactly reconstruct"):
        launcher.validate_frozen_receipt(ROOT, packet, head)
