# S09-E016 implementation review round 2

Reviewer: ChatGPT Pro, Haofan account  
Reviewed commit: `a2efcec3443153b9406f0abfc856422179606229`  
Design baseline: `68e47e543630efea45c67690e8842baed219500c`  
Verdict: `E016_IMPLEMENTATION_REVISE`

The focused rereview independently replayed the round-1 counterexamples. It
closed R1, R2, R3, R4, and R6. Within R5, it confirmed that missing or mutated
NPZ members, ordinary CSV/JSON value mutations, missing Markdown, and frozen
source-hash drift are now rejected before a successful receipt.

One R5 residual remained. The CSV and JSON validators compared parsed Python
objects. `csv.DictReader` therefore discarded earlier values when a scientific
column name was duplicated, `json.loads` discarded earlier duplicate keys, and
Python equality allowed a JSON integer `1` to compare equal to boolean `true`.
Those files could contain conflicting evidence while still matching the parsed
expected object.

## Narrow repair for the next rereview

- Reconstruct the deterministic UTF-8 CSV bytes from the authoritative
  in-memory rows and require exact byte equality before semantic checks.
- Reconstruct the deterministic JSON text with the same serializer used for
  writing and require exact text equality before semantic checks.
- Retain the semantic CSV and JSON checks as a second layer.
- Add executable regressions for duplicate conflicting CSV columns and
  duplicate conflicting JSON keys. Exact text comparison also distinguishes
  JSON booleans from integers.

Focused validation after the repair: 41 E014/E015/E016 tests passed; focused
Ruff, `py_compile`, and `git diff --check` passed. No experiment arrays were
read and no model forward, training, gradient, optimizer, FEM, or holdout
action occurred.
