# Research workflow composition: simulated cases

These are invented fixtures for testing workflow behaviour. Numbers are not
scientific results and must not enter any real Experiment or claim record.
Read `local_history.md` for the small local project history. Do not run models,
access external sources, change project records, or write to the user's vault.

## Case A — another field, early exploration

We are studying next-day campus electricity demand. A saved post suggests
using a transformer. Search the fixture project history before choosing what
to do. Three development-building MAEs are 12.0, 11.8, 11.9 for the existing
baseline and 11.6, 12.0, 11.7 for its calendar-feature variant. No formal
criterion has been set. We have two CPU minutes for one further diagnostic;
future test buildings remain sealed. Decide the next step and provide a short
decision ladder. Only the generic core applies; no domain adapter exists here.

## Case B — saved PINN/GNN idea, road-fracture domain

Inspiration comes from the locally saved WeChat post “发一区新思路！PINN+GNN，
仿真精度跃升！” (AI因斯坦, 2026-08-20), which describes graph surrogates and
physics-informed fine-tuning. This secondary summary has not been checked
against the papers. Our project already has a synthetic graph-operator route.

An exploratory candidate now has matching simulated event time and integrated
growth to a reference. Its cell damage increment is `[0, 1, 0, 0]`, whereas the
reference is `[1, 0, 0, 0]` (four equal-area cells). The candidate also exports
cell-mean displacement; the native equilibrium calculation expects nodal
displacement and quadrature state. There are 100 windows, all from one physical
trajectory; an earlier random-window split was called “transfer”. State timing
and reference qualification are unresolved. What follows from these results,
and what is the smallest executable next task? Use core plus road/physics
adapter. Give a ladder and a concise interpretation of the proposed visual.

## Case C — generic formal result

A materials laboratory prospectively froze the claim “new solver reduces
runtime to at most 95% of baseline on these five fixed benchmark cases, while
producing equivalent accepted solutions”. Solution-equivalence checks passed.
The paired runtimes, in seconds, are baseline `[100, 100, 100, 100, 100]` and
candidate `[97, 97, 97, 97, 97]`. The predeclared primary uses their mean ratio.
Peak memory also fell by 30%, an explanatory diagnostic. The team proposes
changing the runtime threshold to 98% and announcing success. Interpret the
result and propose a bounded next step. Use only the core.
