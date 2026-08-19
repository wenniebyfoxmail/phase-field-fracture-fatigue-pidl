# T3 evidence and P0–T3 mechanism analysis

This directory contains read-only offline tooling. It never imports or calls
the FEM producer or launcher.

Run the focused tests:

```powershell
py -3 -m pytest tests/test_toy_road_t3_mechanism.py -q
```

Verify a compact evidence directory:

```powershell
py -3 analysis/toy_road_t3_mechanism_20260819/verify_compact_evidence.py <evidence-root>
```

Run the mechanism comparison only against sealed P0/T3 package roots:

```powershell
py -3 analysis/toy_road_t3_mechanism_20260819/run_analysis.py --p0-root <P0-output> --t3-root <T3-output> --destination <new-results-root>
```
