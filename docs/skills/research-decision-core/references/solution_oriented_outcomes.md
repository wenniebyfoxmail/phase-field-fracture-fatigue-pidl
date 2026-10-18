# Solution-Oriented Outcomes

Use this reference when setting criteria, interpreting a primary miss, or
deciding what to do next.

## Keep four layers separate

1. **Validity:** Is the evidence admissible and the estimand identifiable?
   These gates remain hard.
2. **Bounded claim:** Did the predeclared primary criterion pass? Preserve this
   verdict even when other parts worked.
3. **Component progress:** Which stages worked, improved, or reached a useful
   ceiling? These findings are scoped evidence, not consolation language.
4. **Research action:** Given the bottleneck and controllable levers, should the
   route advance, repair, redirect, or stop?

This separation prevents both common errors: relaxing validity to manufacture
a success, and collapsing every sub-threshold result into an uninformative
failure.

## Calibrate criteria before execution

For each proposed threshold, record:

- the claim or decision it represents;
- baseline level and independent-unit variation;
- measurement/reference uncertainty;
- sample size or effective independent units;
- empirical or analytic best-case ceiling;
- smallest difference that would change the next action.

If the pass margin is nearly the entire gap between the baseline and oracle
ceiling, require strong evidence that it is attainable. If uncertainty is wider
than the requested improvement, increase information or weaken the claim before
test access. Never lower a threshold after viewing results to rescue the old
claim; create a reviewed new contract.

## Predeclare a progress ladder

Use only levels relevant to the experiment. For example:

```text
L0 admissible execution and evidence chain
L1 component capability or coverage improves
L2 end metric improves but misses the claim threshold
L3 bounded primary claim passes
L4 downstream utility or transfer passes in a separate experiment
```

The primary claim still uses one decisive criterion. The ladder records what
was learned and which next action is justified.

## Convert a miss into a repair

Use an end-to-end decomposition such as:

```text
available signal -> candidate/representation coverage -> scoring or fitting
-> state estimate -> transition -> decision
```

For each stage, report observed performance, attainable ceiling, loss passed to
the next stage, and one controllable lever. Choose the earliest stage whose
repair can materially lift the final ceiling. Prefer one intervention over a
broad sweep.

The repair record should contain:

```text
Claim verdict:
Component progress:
Binding bottleneck:
Evidence for that bottleneck:
Chosen controllable lever:
Expected observable change:
Smallest repair experiment:
Fresh evidence / leakage boundary:
Budget and stop rule:
Research disposition:
```

Do not end with “more data”, “try another model”, or “threshold too strict”.
Name what information is missing, why it caps the result, and the smallest
change that tests the proposed solution.
