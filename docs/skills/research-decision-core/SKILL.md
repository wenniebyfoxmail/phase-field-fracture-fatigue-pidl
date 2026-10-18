---
name: research-decision-core
description: Advance a research goal in any field using local reuse search, decision substeps, stage-appropriate criteria, visual result interpretation, and concise milestone records. Use when choosing or executing a research route or interpreting an attempt; not for routine edits, a factual lookup, or prose polishing.
---

# Research Decision Core

Use this cross-domain workflow to turn a research question into the next useful
action. Reuse the project's existing task and evidence records. Domain-specific
data semantics, acceptance tolerances, ethics, resources, and execution authority
come from the user and project rules.

## Compose With A Domain Adapter

Read this core once, then the adapter relevant to the actual claim. The core
owns the workflow; the adapter adds only domain-specific requirements. Apply
one combined plan and one result record. No extra review is created merely by
loading two skills.

For road-fracture work, use `road-fracture-experiment-gate`; it selects its
observation, inverse, forecast, or physics references. For other fields, use
the project's domain instructions if available. The core can also work alone
when the task supplies the relevant domain semantics; record unresolved domain
requirements before a formal test. An adapter supplies evidence/reference
semantics, necessary validity checks, claim-specific criteria and applicable
review/resource rules. Do not import road-fracture claim classes, producer
names, paths, or GPU thresholds into unrelated projects.

## D1: Find Prior Work And Reusable Assets

Before substantive new work, search relevant local research notes, prior
attempts (including negative results), repository docs, and likely code,
tests, parsers, datasets, and plotting scripts. Use the task's terms and
aliases, follow promising references, and stop once the reuse decision is
clear. Record the search scope and useful pointers in a few lines.

Choose `reuse | continue | fork | redirect | stop`, with one reason. A saved
post, paper summary, or meeting idea is inspiration until its supporting
evidence is checked. State the new question or evidence axis before opening
a new research direction. Do not repeat an unchanged terminal attempt.

At a continuation, reuse the existing D1 record and check only what changed;
do not restart D1 each turn. Routine edits need only a proportionate lookup.

## Decision Ladder

Keep a short ladder inside the existing goal, Experiment, or task note.
Usually three to six steps are enough; an atomic task may use one. Use the
fewest steps that expose the actual decisions, with one active `D#`:

| Step | Purpose / uncertainty | Smallest action and evidence asset | Advance condition -> next step | Redirect condition -> alternative |
|---|---|---|---|---|
| D1 | Prior work and reuse | Targeted local search | Useful existing route -> continue it | No suitable route -> define the new question |

Every step resolves an uncertainty or selects an action. Implementation,
plotting, transfer, and review are tasks within that step unless they answer
an independent feasibility question. Detail the active step enough to execute;
future steps may stay provisional. Identify the next step or mark the task
finished. After an attempt, attach its result pointer and update the active step.

D steps are navigation, not new ledger objects or acceptance gates. Keep
finished results intact when future steps change. A changed formal question,
data boundary, comparator, or primary criterion needs a prospective amendment
or a new experiment under the project's rules.

## Choose The Evidence Stage

**Exploration:** state the question, simplest useful comparator, observable,
resource cap, and next decision. Run relevant local checks and preserve an
attributable result. A directional or component gain, working capability, or
diagnostic that selects a repair can justify a bounded follow-up. Show its
magnitude and available uncertainty. A first prototype need not meet the final
performance target. Independent review is used for a concrete risk or project
requirement, not automatically for every small iteration.

**Formal test:** before results, freeze one bounded claim, evaluation units,
evidence and allowed inputs, comparator, one primary criterion, uncertainty
handling, budget/stop rule, and required evidence. Justify the criterion using
baseline variation, reference noise, a meaningful tolerance, or an attainable
ceiling. For qualitative work, specify the equivalent evidence and decision
rule rather than inventing a numerical threshold. Use the domain's applicable
review requirements. Protected evaluation evidence remains outside exploration.

Use only validity checks whose failure prevents interpretation. Combine primary
conditions only when each is necessary for the same claim. Secondary diagnostics
explain progress and repairs; they do not overturn the primary result. Do not
relabel known exploratory results as prospective confirmation or lower a viewed
criterion to rescue an old result.

## Turn Results Into The Next Action

Report execution status, evidence availability, the bounded conclusion, and the
research action separately. Code running or data transferring establishes only
that capability. For a formal test:

```text
uninterpretable evidence -> inadmissible
valid evidence + primary met -> supports the bounded claim
valid evidence + primary missed -> negative for that claim
insufficient evidence to decide -> inconclusive
```

Preserve measured component progress. Choose `advance | repair | redirect |
park | stop` from the evidence and remaining budget. A negative claim can still
justify a repair. Identify the bottleneck, one controllable change, and the
smallest test that distinguishes it from alternatives. Prefer existing analysis
or a diagnostic before another expensive run. Park if no action is currently
available; stop if the route is invalid, its ceiling inadequate, or budget spent.

When useful, follow [the repair guide](references/solution_oriented_outcomes.md).
For a requested solution-search sub-agent, give the measured bottleneck,
baseline, feasible changes, and budget; use `research-evidence-workflow` for
literature work. Seek solutions in this field and analogous problems elsewhere,
then return a short set of mechanisms, sources, transfer conditions, costs,
and discriminating tests. For solution-design delegation, honour the user's
preference for the strongest available reasoning model and highest supported
effort; record the actual choice in the handoff.

## Show And Explain The Evidence

For computed or measured method results, display at least one decision-facing
visual from the exact evaluated outputs. Show the simplest comparator, relevant
variation, units and evidence scope; use a stated example-selection rule.
For CV show predictions on the evaluated images; for fields show aligned
reference, prediction and error with comparable scales; for forecasting show
origin-to-horizon trajectories. A non-numerical result may use a compact
evidence/decision table or diagram where useful.

Immediately below the visual, use two or three short lines in the user's language:

- **See:** the visible pattern and comparator.
- **Therefore:** the bounded conclusion or decision it supports.
- **Does not show:** only when a material over-interpretation is likely.

Explain practical meaning rather than repeating metric labels or the caption.
Use `research-figure-workflow` for figure production. Missing visuals are a
presentation gap, not a scientific failure; a visually attractive result cannot
override the measured criterion.

## Update People And Records

After substantive progress, answer `目的 / 本轮 / 结论`, normally one sentence
each. Include the active D step where useful. Describe preparation as preparation.
Ordinary discussion and unchanged quiet monitoring need no repeated summary.

At a clear route decision or interpretable attempt result, update the existing
task note and its single Roadmap/index link. When the project uses Obsidian,
write a concise milestone, normally two to four lines: decision/result, evidence
pointer, active D step and next action. Embed the selected rendered figure with
its short interpretation and verify the image/link resolves. Keep raw outputs
in the project's evidence store; use project-specific vault paths. If no vault
is configured, use the existing project note rather than inventing a directory.

For an exploratory task, a short plan/record suffices:

```text
Purpose / evidence stage:
D1 reuse decision and source pointers:
Decision ladder / active step:
Smallest action / comparator / observable / resource cap:
Measured result and visual interpretation (or pending):
Conclusion / next step:
```

Reuse existing formal protocols and run receipts for confirmatory work. Loading
this core does not require new IDs, duplicate records, or extra approval stages.
