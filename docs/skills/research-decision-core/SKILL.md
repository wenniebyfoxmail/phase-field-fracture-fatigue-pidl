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
An in-scope method repair needs no extra scope approval; a materially different
question outside existing authority is a proposed fork/redirect for the user
to choose. Do not quietly lower the target or relabel a negative result.

Keep acquisition separate from scientific progress. If access is blocking,
state which decision it enables and the condition for returning to it or taking
an in-scope alternative; continue useful unblocked work or park that dependency.
A request sent, file obtained or waiting status is not an answered research
question. Keep the HQ's next scientific decision visible.

## Design Route Changes From First Principles（第一性原理）

每次分析研究路线调整，必须从第一性原理出发：回到目标、机制、关键假设与实测瓶颈，设计足以改变路线判断的突破性验证，而不是默认继续最小验证。

At a material route choice, return to the goal rather than the last failed
patch. State the governing mechanism or information-generating process,
necessary constraints, measured bottleneck and competing explanations. Use
equations when useful, or an explicit causal/information argument; do not add
ceremonial derivations to routine fixes.

Design a hypothesis-led solution that can remove the binding limitation,
including a coherent redesign of representation, objective or workflow when
needed. Do not restrict every proposal to one parameter or one component.
An integrated candidate can test one central hypothesis against a strong
simple baseline; add only ablations that distinguish a live alternative.
Name the actual intervention, why it should change the limiting mechanism,
and its predicted signature against the alternatives. A generic “stronger
model” or “more cases” does not specify that causal design.

Choose validation at the scale needed to change the research decision:
representative states, cases, horizons and outputs that can expose the actual
failure mode and reveal a useful new capability or meaningful gap reduction.
Explain what different outcomes would establish and which route each selects.
A breakthrough-oriented design seeks consequential evidence, not a guaranteed
breakthrough, a prestigious label or merely more compute.

Do not default to the smallest possible test or require a toy -> micro-test ->
pilot staircase. Use a small preliminary check only for a specific unresolved
feasibility or implementation blocker; skip or combine it when existing
evidence already resolves that blocker. Otherwise proceed directly to a
decision-scale comparison within the applicable data, budget and authority.
Minimise unnecessary work, not the question or the experiment's resolving power.

When a proposed next micro-test would only reconfirm a known sign, improve an
incidental component, or leave the main route equally uncertain, consolidate
the relevant checks into a stronger comparison or redesign the route. Preserve
small gains, but do not let their accumulation substitute for progress on the
central goal. A larger test is not automatically more decisive either.

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

## Choose The Evidence Stage

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

Approve the task once: goal, allowed code/data, producer, total budget,
stop/retry limits and result, in the existing card. Conditional execution
approval covers implementation -> fixed benchmark -> deployment ->
automatic admission -> execution. The agent completes that chain without
asking again for each step. An explicitly plan-only task still permits no run.

- **Agent:** in-scope repairs, fixed benchmark, environment/resources,
  actual versions, Run IDs, paths, hashes and card instantiation. Verify these
  against the approved envelope/reviewed template. Check compatibility rather
  than imposing exact pins on every auxiliary library. Isolated dependency
  repairs stay within scope; model/data execution is not a metadata check.
- **Reviewer (only when requested):** the user's stated question; carry forward
  unchanged findings. Metadata-only fields need consistency checks, not another
  Code Ready review or human approval.
- **User:** one consolidated decision only for a scope/data/producer/expenditure
  or budget expansion, shared-system changes requiring permission, or a scientific
  retry outside the approved limits.

For new cards, set a short zero-start recheck cap within the total budget before
trying. GPU busy means not ready, not scientific failure. Unknown launch state
requires process/receipt checks before another spawn. Preserve explicit user
connection/attempt and scientific stop limits, not agent-invented approval gates.

Migrate active cards prospectively: replace administrative per-step approvals,
state remaining authority, and preserve signed snapshots, consumed attempts and
scientific protocols. This governance update itself starts no new experiment
and reopens no stopped scientific run.

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
select the binding mechanism, a coherent intervention and evidence strong
enough to choose between the alternatives. Reuse existing analysis; do not
insert another diagnostic merely because it is cheaper or easier. Check whether
cumulative work is reducing the central gap, not just producing completed
subtasks. Park if no action is currently available; stop if the route is invalid,
its ceiling inadequate, or budget spent.

When useful, follow [the repair guide](references/solution_oriented_outcomes.md).
For a requested solution-search sub-agent, give the goal, bottleneck evidence,
baseline, assumptions open to redesign, and budget; use `research-evidence-workflow` for
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
