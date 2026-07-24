from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from build_road_observation_state_bundle_v1 import _auto_root  # noqa: E402


def test_clean_checkout_source_precedes_sibling_worktree(tmp_path: Path) -> None:
    checkout = tmp_path / "integration"
    sibling = tmp_path / "sibling"
    relative = Path("analysis/final_contract.json")
    (checkout / relative).parent.mkdir(parents=True)
    (checkout / relative).write_text("{}", encoding="utf-8")
    (sibling / relative).parent.mkdir(parents=True)
    (sibling / relative).write_text("{}", encoding="utf-8")

    assert _auto_root(None, relative, sibling, checkout_root=checkout) == checkout
    assert _auto_root(sibling, relative, sibling, checkout_root=checkout) == sibling.resolve()
