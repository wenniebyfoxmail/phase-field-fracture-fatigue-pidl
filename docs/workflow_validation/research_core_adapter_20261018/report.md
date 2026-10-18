# Research core + domain adapter: behavioural test

Date: 2026-10-18 (Europe/London). All case values are invented fixtures.
Scope: skill behaviour and composition, not scientific or numerical validation.

## Versions and method

Tested `research-decision-core` alone for A/C and core + road + physics/PIDL
references for B. The implementation commit containing this report identifies
the tested sources. Inputs are [cases.md](cases.md) and
[local_history.md](local_history.md).

An independent fresh-context sub-agent (`core_adapter_forward_test`) received
the skill paths, the three tasks and the fixture history, without expected
answers or the author's proposed fixes. It was restricted to read-only local
use. No producer run, real scientific payload, network, or vault mutation was
permitted. The parent compared its returned plans with the evidence and scope.

## Observed results

| Case | Required capability | Observed behaviour | Assessment |
|---|---|---|---|
| A: campus electricity exploration | Core usable outside fracture; reuse; permissive early progress | Continued existing baseline/calendar route; calculated mean MAE 11.900 -> 11.767 (about 1.1%); preserved one regression; selected a two-CPU-minute paired residual diagnostic | Works in this case |
| B: synthetic fracture | Adapter adds state/support/trajectory requirements | Reused existing graph route; identified disjoint supports (IoU 0), candidate MAE .50 vs zero comparator .25; retained unknown state/reference status; rejected cell-mean substitution for native equilibrium and random-window transfer inference | Works in this case |
| C: formal solver comparison | Retain the prospective criterion while preserving component progress | Mean runtime ratio .97 misses .95; memory -30% retained separately; rejected retrospective .98 threshold; selected profiling before a prospective repair | Works in this case |

The tables show that the same decision process leads to different executable
next actions depending on evidence stage and domain. They support usability in
these three fixtures, not reliability across every field or future task.

## Returned decision ladders (condensed)

**A:** D1 reuse complete -> **D2 active**, paired development residuals by
building/day type, two CPU minutes -> D3 one targeted follow-up if a recurring
condition explains gains/regressions; otherwise redirect to the identified data
or evaluation bottleneck. Test buildings stay sealed. Error units and temporal
semantics must be supplied before a formal claim.

**B:** D1 overlap/reuse complete -> **D2 active**, offline state/reference
eligibility table from manifests -> D3 aligned damage/error panels if identity
is established, otherwise specify missing native export -> D4 prospective
complete-trajectory evaluation only after qualification. Matching totals are
arithmetic evidence; unresolved state timing blocks physical attribution.

**C:** D1 existing protocol/result located -> **D2 active**, preserve negative
runtime verdict and inspect existing timing profiles -> D3 one prospectively
specified repair if a controllable bottleneck is supported.

Returned B visual explanation:

- See: equal totals hide growth in different cells; candidate MAE is twice the
  zero baseline's in the supplied arrays.
- Therefore: resolve state alignment and spatial support before more training.
- Does not show: a physical mechanism failure without matched states and
  a qualified reference.

## Composition and installation checks

- Three skill frontmatter validations passed: core, road and PIDL.
- Twelve relative links across entrypoints/shared guide resolved; no broken
  template or reference route was found.
- Global core, road, PIDL and figure entries resolve to this task worktree.
- Shared acceptance, decision steps and result communication have one owner
  in the core. The road adapter retains project review, GPU-resource rules,
  IDs, storage paths and domain-reference routing.
- The evaluator returned one combined ladder per case and no second review
  stage. Generic cases did not import fracture claim classes or GPU thresholds.

The evaluator noted one execution-context distinction: the fixture prohibited
writes while the normal workflow can produce figures and milestones. It used
inline tables and specified a figure instead of claiming to have rendered or
stored it. This was appropriate to the test's restriction.

A focused follow-up checked the clarified standalone-core paragraph. The
independent evaluator confirmed that A/C still use the core alone when their
domain semantics are supplied, while B still needs the road/physics references;
no action or routing changed.

## Deployment boundary

Global entrypoints are installed. Existing worktrees that explicitly use older
project-local skill snapshots retain those snapshots until integrated; running
agents may also retain already-loaded instructions. In another project, invoke
`$research-decision-core`, or reference its installed path from that project's
instructions when adopting it. This change does not rewrite every project.
