from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis.toy_road_t3_mechanism_20260819.evidence import verify_compact_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify compact T3 evidence.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_compact_evidence(args.root), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
