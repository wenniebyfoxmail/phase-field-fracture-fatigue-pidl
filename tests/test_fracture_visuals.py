from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from fracture_visuals.paper_style import method_style as packaged_method_style
from paper_style import method_style as legacy_method_style


def test_paper_style_legacy_import_reexports_the_packaged_implementation() -> None:
    assert legacy_method_style is packaged_method_style


def test_method_style_preserves_canonical_bw_and_crowded_plot_rules() -> None:
    sparse = packaged_method_style("FEM", bw_safe=True, n_methods=3)
    crowded = packaged_method_style("FEM", bw_safe=True, n_methods=5)

    assert sparse == {
        "color": "#1B1919",
        "label": "FEM",
        "linestyle": "-",
        "marker": "o",
    }
    assert crowded == {"color": "#1B1919", "label": "FEM"}
