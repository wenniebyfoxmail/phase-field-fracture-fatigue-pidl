from pathlib import Path

import numpy as np
import pytest

from scripts.validate_rrapinn_g4_exact_fem import (
    ValidationError,
    _point_in_candidates,
    parse_sha256s,
)


def test_parse_sha256s_accepts_crlf_and_rejects_duplicates(tmp_path: Path) -> None:
    digest_a = "a" * 64
    digest_b = "b" * 64
    sums = tmp_path / "SHA256SUMS"
    sums.write_bytes(
        f"{digest_a}  a.bin\r\n{digest_b}  sub/b.bin\r\n".encode("ascii")
    )
    assert parse_sha256s(sums) == {"a.bin": digest_a, "sub/b.bin": digest_b}
    sums.write_text(f"{digest_a}  a.bin\n{digest_b}  a.bin\n")
    with pytest.raises(ValidationError, match="duplicate"):
        parse_sha256s(sums)


def test_point_in_candidates_uses_frozen_tolerance() -> None:
    triangles = np.array(
        [
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
            [[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        ]
    )
    np.testing.assert_array_equal(
        _point_in_candidates(np.array([0.25, 0.25]), triangles), [True, False]
    )
    np.testing.assert_array_equal(
        _point_in_candidates(np.array([0.75, 0.75]), triangles), [False, True]
    )
    np.testing.assert_array_equal(
        _point_in_candidates(np.array([2.0, 2.0]), triangles), [False, False]
    )
