# Fixture project history

This document is invented local history, not a real project record.

## Campus demand pilot

Previous work compared a previous-week baseline and a calendar-feature model
on three development buildings. The existing implementation is below; it
accepts histories of at least seven days. Its basic repeat-week behaviour was
checked in the pilot. No transformer was built. Baseline results are in case A.

```python
def previous_week(history):
    return history[-7]
```

A prior synthetic simulator performed well on artificial demand curves but
did not support a real-building prediction claim. No future-building test
results have been read. Reuse the baseline and its evaluation routine before
adding architecture complexity.

## Synthetic fracture route

A graph-operator route already covers FEM-state imitation. Its existing
analysis can compare aligned cell damage increments and plot the reference,
prediction, and absolute error on a shared mesh. It can also compare a zero
increment baseline. It does not reconstruct valid nodal displacement from
cell means. The prior random-window split did not separate physical trajectories.
