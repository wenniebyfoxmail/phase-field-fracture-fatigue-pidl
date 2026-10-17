from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.synthetic_fracture_cv.render_analytic_sequence import (
    CASES,
    HEIGHT,
    SLIT_Y,
    START_X,
    TEXTURE_SEEDS,
    TIP_X,
    WIDTH,
    generate_fixture,
    inverse_affine_coordinates,
    make_reference_texture,
    render_case,
)


def _case(name: str) -> dict:
    return next(case for case in CASES if case["case"] == name)


def _independent_support(opening: float) -> np.ndarray:
    # Independent row/column loop: does not use the renderer's rasteriser.
    support = np.zeros((HEIGHT, WIDTH), dtype=np.float64)
    for row in range(HEIGHT):
        pixel_low = float(row)
        pixel_high = float(row + 1)
        slit_low = SLIT_Y - opening / 2.0
        slit_high = SLIT_Y + opening / 2.0
        vertical_overlap = max(0.0, min(pixel_high, slit_high) - max(pixel_low, slit_low))
        for col in range(WIDTH):
            horizontal_overlap = max(0.0, min(float(col + 1), TIP_X) - max(float(col), START_X))
            support[row, col] = vertical_overlap * horizontal_overlap
    return support


def test_zero_displacement_is_exact_in_valid_interior() -> None:
    texture = make_reference_texture(TEXTURE_SEEDS[0])
    rendered, support = render_case(texture, _case("zero"))
    assert np.array_equal(rendered, texture)
    assert not support.any()


def test_integer_translation_is_exact_and_creates_no_crack() -> None:
    texture = make_reference_texture(TEXTURE_SEEDS[0])
    rendered, support = render_case(texture, _case("translation"))
    # Forward offset (x=+3,y=-2): output[y,x] samples source[y+2,x-3].
    assert np.array_equal(rendered[0:125, 3:127], texture[2:127, 0:124])
    assert not support.any()


def test_affine_inverse_map_matches_independent_closed_form() -> None:
    case = _case("affine_strain")
    matrix = np.asarray(case["matrix"], dtype=np.float64)
    offset = np.asarray(case["offset"], dtype=np.float64)
    sx, sy = inverse_affine_coordinates(matrix, offset)
    determinant = matrix[0, 0] * matrix[1, 1] - matrix[0, 1] * matrix[1, 0]
    yy, xx = np.indices((HEIGHT, WIDTH), dtype=np.float64)
    qx, qy = xx - offset[0], yy - offset[1]
    expected_x = (matrix[1, 1] * qx - matrix[0, 1] * qy) / determinant
    expected_y = (-matrix[1, 0] * qx + matrix[0, 0] * qy) / determinant
    assert float(np.max(np.abs(sx - expected_x))) < 1e-9
    assert float(np.max(np.abs(sy - expected_y))) < 1e-9
    _, support = render_case(make_reference_texture(TEXTURE_SEEDS[0]), case)
    assert not support.any()


def test_resolved_support_matches_independent_analytic_reference() -> None:
    texture = make_reference_texture(TEXTURE_SEEDS[0])
    for name, opening in (("opening_2px", 2.0), ("opening_4px", 4.0)):
        _, support = render_case(texture, _case(name))
        expected = _independent_support(opening)
        assert np.array_equal(support, expected)
        rows, cols = np.nonzero(support > 0)
        assert abs((cols.max() + 1) - TIP_X) <= 1
        assert abs((cols.max() + 1 - cols.min()) - (TIP_X - START_X)) <= 1
        assert abs(len(np.unique(rows)) - opening) <= 1


def test_closed_and_subpixel_status_are_not_resolved_labels() -> None:
    assert _case("closed_slit")["status"] == "closed"
    assert _case("opening_0p25px")["status"] == "ambiguous"
    texture = make_reference_texture(TEXTURE_SEEDS[0])
    closed_image, closed_support = render_case(texture, _case("closed_slit"))
    ambiguous_image, ambiguous_support = render_case(texture, _case("opening_0p25px"))
    assert np.array_equal(closed_image, texture)
    assert not closed_support.any()
    assert 0.0 < float(ambiguous_support.max()) < 1.0
    assert not np.array_equal(ambiguous_image, texture)


def test_far_border_has_no_geometry_correlated_pixels_or_support() -> None:
    for seed in TEXTURE_SEEDS:
        texture = make_reference_texture(seed)
        zero_image, _ = render_case(texture, _case("zero"))
        for name in ("opening_2px", "opening_4px", "opening_0p25px"):
            image, support = render_case(texture, _case(name))
            assert np.array_equal(image[0, :], zero_image[0, :])
            assert np.array_equal(image[-1, :], zero_image[-1, :])
            assert np.array_equal(image[:, 0], zero_image[:, 0])
            assert np.array_equal(image[:, -1], zero_image[:, -1])
            assert not support[0, :].any()
            assert not support[-1, :].any()
            assert not support[:, 0].any()
            assert not support[:, -1].any()


def test_generation_is_byte_deterministic_and_metadata_is_pixel_inert(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    records_1 = generate_fixture(first)
    records_2 = generate_fixture(second)
    assert len(records_1) == len(CASES) * len(TEXTURE_SEEDS) == 14
    for one, two in zip(records_1, records_2):
        bytes_1 = (first / one["image_path"]).read_bytes()
        bytes_2 = (second / two["image_path"]).read_bytes()
        assert bytes_1 == bytes_2
        assert hashlib.sha256(bytes_1).hexdigest() == one["image_sha256"]
    for seed in TEXTURE_SEEDS:
        texture = make_reference_texture(seed)
        for case in CASES:
            baseline_image, baseline_support = render_case(
                texture, case, inert_metadata={"event_first_detect": None, "audit": "baseline"}
            )
            changed_case = dict(case)
            changed_case["case"] = "deliberately_changed_audit_name"
            changed_case["status"] = "deliberately_changed_audit_status"
            changed_case["event_first_detect"] = 999
            changed_case["provenance"] = "deliberately_changed_audit_provenance"
            changed_image, changed_support = render_case(
                texture,
                changed_case,
                inert_metadata={"event_first_detect": 999, "audit": "changed"},
            )
            assert np.array_equal(changed_image, baseline_image)
            assert np.array_equal(changed_support, baseline_support)
