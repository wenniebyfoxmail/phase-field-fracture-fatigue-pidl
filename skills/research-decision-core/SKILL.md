---
name: research-decision-core
description: Advance a research goal in any field through first-principles route design, decision-scale validation, local reuse, stage-appropriate criteria and visual interpretation. Use when choosing or executing a research route or interpreting an attempt; not for routine edits, a factual lookup, or prose polishing.
---

# Research Decision Core

Use this cross-domain workflow to turn a research question into the next useful
action. Reuse the project's existing task and evidence records. Domain-specific
data semantics, acceptance tolerances, ethics, resources, and execution authority
come from the user and project rules.

## 只跑固定基准，通过即交付（用户规则，2026-10-22）

- 默认只运行当前任务的一套固定基准测试；开始时在原任务记录里写清命令、
  代表性输入、对照和预期结果。复用已有基准，不临时扩建测试体系。
  基准覆盖当前主功能与已声明的科研比较，不把全套历史测试改名为“基准”。
- 代码更新只跑这套基准，不再自动追加全量回归、历史实验重跑、多轮smoke、
  消融、压力测试或独立审核。基准通过即交付并推进下一步，不继续“找保险”。
- 文档、措辞、路径或元数据小改只做直接一致性检查，不运行科研基准。
- 基准失败就修复并重跑失败项；已通过且未受影响的结果直接复用。没有基准时，
  选择一个代表性端到端用例作为基准，不先搭建一串微型验证。
- 额外测试或独立审核仅在用户明确要求时执行；进入正式实验、改commit或加载
  领域适配器本身都不触发。过去由Agent自加的复审门不算用户要求。
- 运行许可、预算、保护数据及共享机器安全规则不变；基准通过不等于科学结论成立。

For an execution-control benchmark, identify real calls separately from
fault-injected or simulated states. A simulated producer establishes control
behaviour only. If native functions cannot run locally, name that uncovered
boundary without adding remote compute. Preserve an unavailable exit code as
unknown; do not infer it from a wrapper message.

This is the validation default for HQs, executors and adapters. Scientific
evaluation uses the declared comparator and criterion; it is not permission to
rerun old experiments or add validation stages.

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

## Keep The Goal Continuous

The project-designated current owner card or Experiment holds detailed state
and effective authority. HQ stores a short summary and a pointer, not a second
independently editable authority. A direct user update remains authoritative
even before the card is reconciled. Pausing HQ is not undone by editing rules,
task records or running a development benchmark.

Keep a short goal anchor near the top of the existing owner note: original
question -> current question; `continue | fork | redirect` and why; scope-change
authority/source when applicable; previous route's status. Link an existing
decision rather than copying it. Refresh only when scope changes or a handoff
reveals a mismatch, not every turn.

A user-directed change is legitimate: follow it without asking again, preserve
the old route and its results, and explain whether the new work advances that
question or replaces it. When scope materially changes, update the owner note
and its Roadmap/portfolio summary together; correct a misleading chat title where
permitted, or put a prominent current-scope line in the update/handoff.

Easier data or tools do not by themselves authorise replacing the question.
A same-contract technical repair needs no extra scope approval; a materially different
question outside existing authority is a proposed fork/redirect for the user
to choose. Do not quietly lower the target or relabel a negative result.

Keep acquisition separate from scientific progress. If access is blocking,
state which decision it enables and the condition for returning to it or taking
an in-scope alternative; continue useful unblocked work or park that dependency.
A request sent, file obtained or waiting status is not an answered research
question. Keep the HQ's next scientific decision visible.

## Design Route Changes From First Principles（第一性原理）

从当前科学问题和关键证据缺口出发，选择足以改变判断的行动，并说明不同结果将如何影响结论或下一步。涉及机制解释或方法改进时，再明确瓶颈、干预及可区分的结果。复用已有决策记录，不要求每次逐项填写。

Scientific value, feasibility and cost are separate considerations. Do not
automatically prefer the cheapest patch or a larger experiment. Choose the
scale that can resolve the live question within actual authority.

The argument may be a proof and its unresolved assumption, a descriptive
comparison, calibration against an independent reference, source synthesis,
or a mechanism/method intervention. Use the form appropriate to the task;
do not force every research question into an intervention template.

For mechanism or method changes, identify the measured bottleneck, proposed
intervention and observable differences between live explanations. Reuse
diagnostics that already answer the question. A preliminary check is useful
only for a specific unresolved blocker; do not require a toy-to-smoke ladder.
Keep component gains, but ask whether the next action can change the central
conclusion rather than merely make another component run.

## Decision Ladder

Keep a short ladder inside the existing goal, Experiment, or task note.
Usually three to six steps are enough; an atomic task may use one. Use the
fewest steps that expose the actual decisions, with one active `D#`:

| Step | Purpose / uncertainty | Decision-scale action and evidence asset | Advance condition -> next step | Redirect condition -> alternative |
|---|---|---|---|---|
| D1 | Prior work and reuse | Targeted local search | Useful existing route -> continue it | No suitable route -> define the new question |

Every step resolves a consequential uncertainty or selects a research action.
A step may contain a coherent multi-part validation; do not split every
engineering check or ablation into another serial decision or approval.
Implementation, plotting, transfer, and review are tasks within that step unless
they answer
an independent feasibility question. Detail the active step enough to execute;
future steps may stay provisional. Identify the next step or mark the task
finished. After an attempt, attach its result pointer and update the active step.

D steps are navigation, not new ledger objects or acceptance gates. Keep
finished results intact when future steps change. A changed formal question,
data boundary, comparator, or primary criterion needs a prospective amendment
or a new experiment under the project's rules.

## Choose Work Mode Once

Record one mode in the existing owner record before work starts:

- **Daily iteration:** implement or repair within the current route, run the
  fixed task benchmark, and report the engineering or research progress. It is
  not a new scientific claim by default.
- **Scientific validation:** obtain evidence for the current research decision,
  using the exploration or formal-test contract below as appropriate. It does
  not create a review by default.
- **Formal review:** answer a user-requested review question or one explicitly
  required by an approved task contract. A submission-facing use alone does not
  start review. It does not itself require a new run.

These are selectable modes, not automatic stages. A result may recommend a mode
change, but an agent must not upgrade a task because a commit changed, a
benchmark passed, a run finished, or more confidence would be desirable. The
user or an already-authorised task contract selects and records any change.
Formal scientific testing is scientific validation, not formal review.

## Scientific Validation: Choose The Evidence Stage

**Exploration:** state the question, simplest useful comparator, observable,
resource cap, and next decision. Run the fixed task benchmark and preserve an
attributable result. A directional or component gain, working capability, or
diagnostic that selects a repair can justify a bounded follow-up when it has a
credible path to the central goal. Show its
magnitude and available uncertainty. A first prototype need not meet the final
performance target. Do not add independent review unless the user requests it.

**Formal test:** before results, freeze one bounded claim, evaluation units,
evidence and allowed inputs, comparator, one primary criterion, uncertainty
handling, budget/stop rule, and required evidence. Justify the criterion using
baseline variation, reference noise, a meaningful tolerance, or an attainable
ceiling. For qualitative work, specify the equivalent evidence and decision
rule rather than inventing a numerical threshold. Formal status does not add
automatic review. Protected evaluation evidence remains outside exploration.

Use only validity checks whose failure prevents interpretation. Combine primary
conditions only when each is necessary for the same claim. Secondary diagnostics
explain progress and repairs; they do not overturn the primary result. Do not
relabel known exploratory results as prospective confirmation or lower a viewed
criterion to rescue an old result.

## 一次授权，机械检查自动完成 / Bounded Task Authority

Keep one run-enabled task authority in the existing owner card or Experiment:
goal, allowed code/data, producer, total budget, scientific stop condition and
deliverable. It covers implementation, the fixed benchmark, deployment,
admission/waiting, execution and retrieval, plus same-contract technical repair.
A plan-only task permits no scientific execution. The latest direct user
instruction takes precedence; update the owner record when it changes scope.

Wrapper errors, GPU busy and SSH loss do not by themselves change authority
or establish whether a producer started, consumed resources or remains alive.
Check actual process/receipt/output identity first. Unknown state means inspect
and retain the reservation, not spawn again. A fresh Run ID is provenance,
not a new approval and not proof of zero progress.

Same-contract repairs preserve scientific/numerical meaning and remain inside
the original cumulative budget and scientific stop rule. A log-path or exception
propagation repair differs from changing the solver, inputs or convergence
criterion. User-explicit one-start, first-stop and retry restrictions always
prevail, including when the observed failure appears technical. Never reopen a
consumed historical authority through a workflow amendment.

Use one total task budget, not a consent token per process. In the existing
record distinguish resource consumption from elapsed task wall time, whether
waiting is charged, scientific stop time and cleanup deadline when applicable.
Repairs/restarts/continuations accumulate in the same task; record the start
once. Unknown consumption stays unknown, not zero. Apply the agreed accounting
and most restrictive remaining limit. Do not invent a budget table for tasks
that do not need it or silently reinterpret old accounting.

Routine implementation, fixed-benchmark checks, path/version binding and
same-contract recovery belong to the agent. Metadata edits need consistency
checks only. Review is added only when explicitly requested. Ask the user for
a material scope/data/producer/resource expansion, shared-system change,
changed scientific/numerical semantics, or a retry outside explicit limits;
do not seek consent again for unchanged routine steps.

## Turn Results Into The Next Action

At topic intake, around a useful brainstorming decision, or when a measured
bottleneck needs external solutions, use `deep-research-obsidian` to preserve
the synthesis and source papers. Choose the occasion that resolves the live
decision; do not insert a compulsory research round before every attempt.

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
justify a repair. For a route adjustment, use the first-principles design above:
start from the scientific question and evidence gap, and choose an action whose
outcomes can change the conclusion or next step. For mechanism/method work,
identify the bottleneck, intervention and discriminating outcomes. Reuse existing analysis; do not
insert another diagnostic merely because it is cheaper or easier. Check whether
cumulative work is reducing the central gap, not just producing completed
subtasks. Park if no action is currently available; stop if the route is invalid,
its ceiling inadequate, or budget spent.

A result may recommend the next action, but it does not by itself authorise a
new run, retry, data access, budget, or mode change. Start one only when the
existing approved task envelope explicitly covers it or the user authorises it.

When useful, follow [the repair guide](references/solution_oriented_outcomes.md).
For a requested solution-search sub-agent, give the goal, bottleneck evidence,
baseline, assumptions open to redesign, and budget; use `research-evidence-workflow` for
literature work. Seek solutions in this field and analogous problems elsewhere,
then return a short set of mechanisms, sources, transfer conditions, costs,
and discriminating tests. For solution-design delegation, honour the user's
preference for the strongest available reasoning model and highest supported
effort; record the actual choice in the handoff.

## Show And Explain The Evidence

At a clear result or route decision, make one fast decision visual from already
evaluated or retrieved output when it is interpretable. This presents existing
evidence; it must not trigger new computation, training, simulation, data
access, analysis sweeps, or review. A second visual is useful only when it
answers another necessary decision.

For an interpretable computed or measured method result, show the simplest
comparator, relevant variation, units and evidence scope; use a stated
example-selection rule. For CV show predictions on the evaluated images; for
fields show aligned reference, prediction and error with comparable scales; for
forecasting show origin-to-horizon trajectories. A non-numerical result may use
a compact evidence/decision table or diagram where useful. Pure
documentation/configuration work or an uninterpretable output does not require
a figure.

Immediately below the visual, use two or three short lines in the user's language:

- **See:** the visible pattern and comparator.
- **Therefore:** the bounded conclusion or decision it supports.
- **Does not show:** only when a material over-interpretation is likely.

Explain practical meaning rather than repeating metric labels or the caption.
For a fast decision snapshot, use only `research-figure-workflow`'s source-trace,
basic visual-sanity, and See/Therefore rules. Its planning, caption, manuscript,
and handoff sections apply only to claim-bearing or standalone figure work.
Missing visuals are a presentation gap, not a scientific failure; a visually
attractive result cannot override the measured criterion.

## Update People And Records

Before modifying an existing main file, confirm its effective absolute path,
entrypoint and references. Update it in place in its authorised task worktree;
keep a live producer's pinned script/config stable if it may read again.
Report actual paths and whether the result is an in-place update, a versioned
delivery or an un-applied temporary copy. Original data, frozen snapshots and
archived results retain their existing version rules.

Use one result entrypoint to locate evaluated inputs, plotting code, figures
when useful, and interpretation. Link large data and fixed code by stable
path/version instead of duplicating them. Small label/caption edits reuse the
existing plotting entrypoint and check only affected output. Not every result
requires a figure.

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

This fast visual and its two-to-three-line interpretation are the normal result
snapshot. A full figure set, analysis README, sidecar, or archival package is
required only when a frozen protocol explicitly requires it, the user asks, or
an independently reusable figure set is genuinely needed for citation,
submission, or handoff. A claim-bearing result alone does not trigger that
package.

For an exploratory task, a short plan/record suffices:

```text
Purpose / evidence stage:
Goal anchor / existing scope-decision pointer:
D1 reuse decision and source pointers:
Route-change mechanism / hypothesis and alternatives (when applicable):
Decision ladder / active step:
Decision-scale action / comparator / observable / resource cap:
Why this evidence can change the route; preliminary blocker only if unresolved:
Measured result and visual interpretation (or pending):
Conclusion / next step:
```

Reuse existing formal protocols and run receipts for confirmatory work. Loading
this core does not require new IDs, duplicate records, or extra approval stages.

## HQ And Sub-Agent Handoffs

Each HQ passes the current core path, relevant domain adapter, goal anchor,
active D step, mechanism/hypothesis, evidence/code pointers, permitted scope,
budget, decision-scale validation and expected output
and advance/return/redirect condition to its executors. Make clear how the
helper's subquestion serves the current goal. Executors return the result,
its evidence pointer and its impact on that goal and next decision. Carry scope
changes into the portfolio summary, not just the helper's activity report.
Reuse one owner record; do not open a duplicate ladder for every helper.
A workflow refresh does not authorise a new run, retry or data access.
