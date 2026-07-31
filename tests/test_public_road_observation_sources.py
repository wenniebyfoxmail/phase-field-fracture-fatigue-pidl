from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "SENS_tensile" / "audit_public_road_observation_sources.py"
SPEC = importlib.util.spec_from_file_location("public_road_sources", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_erd_header_parser_extracts_profile_contract() -> None:
    payload = b"""ERDFILEV2.00
      3,   6295,     -1,      1,      5,       0.0250,     -1,
TITLE   LTPP SPS Section 06B410SF: Run 1
UNITSNAMmm      mm      mm
XUNITS  m
DATE    11/Apr/1997

END
 0.0 0.0 0.0
"""
    result = MODULE.parse_erd_header(payload)
    assert result["sample_count"] == 6295
    assert result["sample_spacing"] == 0.025
    assert result["survey_date"] == "11/Apr/1997"
    assert result["x_units"] == "m"


def test_source_roles_keep_metrology_visual_and_mechanics_separate() -> None:
    assert "metrology" in MODULE.classify_source_role("idics_2d")[0]
    assert "visual" in MODULE.classify_source_role("pavetrack")[0]
    assert "mechanical" in MODULE.classify_source_role("mnroad")[0]
    assert "not crack-tip" in MODULE.classify_source_role("ltpp_06B410")[1]


def test_channel_table_preserves_latent_to_sensor_firewall() -> None:
    ltpp = {"profile_dates": ["19970411"], "distress_dates": ["20000628"]}
    mnroad = {"traffic_date_start": "1994-07-15", "traffic_date_end": "2013-09-21"}
    idics = {"max_registration_absolute_error_px": 0.02}
    _, channels, _ = MODULE.build_tables(ltpp, mnroad, idics)
    latent = next(row for row in channels if row["channel"] == "FEM latent fields")
    assert latent["ltpp"] == "not_observed"
    assert latent["mnroad"] == "not_observed"
    assert latent["current_use"] == "never label as sensor data"
