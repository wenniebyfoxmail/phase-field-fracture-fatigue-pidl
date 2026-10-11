from __future__ import annotations

import sys
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).parents[1] / "tools" / "s04_e011_analysis"
sys.path.insert(0, str(MODULE_DIR))
from analyze_fem_staggered_endpoints import parse_log  # noqa: E402


def test_parser_detects_first_crossing_and_nonmonotonicity(tmp_path: Path) -> None:
    log = tmp_path / "q4.log"
    log.write_text(
        "\n".join(
            (
                "CYCLE Nr.:1 STEP Nr.: 4",
                " STAG ITER Nr.: 1  tot_en=0.01 res_sum=0.0008",
                " STAG ITER Nr.: 2  tot_en=0.02 res_sum=0.0009",
                " STAG ITER Nr.: 3  tot_en=0.03 res_sum=0.0003",
                "CYCLE Nr.:1 STEP Nr.: 5",
            )
        ),
        encoding="utf-16",
    )
    trace, summary = parse_log(log, "q4", 4e-4)
    assert len(trace) == 3
    assert len(summary) == 1
    result = summary[0]
    assert result["topology"] == "q4" and result["cycle"] == 1 and result["step"] == 4
    assert result["iterations"] == result["first_pass_iteration"] == 3
    assert result["final_residual_sum"] == pytest.approx(3e-4)
    assert result["final_over_tol"] == pytest.approx(0.75)
    assert result["minimum_residual_sum"] == pytest.approx(3e-4)
    assert result["maximum_residual_sum"] == pytest.approx(9e-4)
    assert result["increases"] == 1 and result["nonmonotone"]
    assert result["terminal_is_first_pass"]
