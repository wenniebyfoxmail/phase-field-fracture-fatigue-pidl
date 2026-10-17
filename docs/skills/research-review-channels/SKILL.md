---
name: research-review-channels
description: Route a road-fracture research review to ChatGPT Chat Pro, an independent Codex reviewer, or ChatGPT Work when a HQ needs design, code, or evidence scrutiny. Use when arranging or interpreting an independent review, not for routine progress or to add a new scientific acceptance gate.
---

# Research Review Channels

Choose a reviewer by the question it can actually answer and the evidence it can access. A review admits or challenges an identified decision; it does not vote on an Experiment's frozen primary criterion. The HQ owns the final adoption decision and the existing `Storyline -> Experiment -> Run -> Evidence` record remains authoritative.

Small development-data explorations use local tests and a labelled result
record, not an independent review on every iteration. Route an independent
review when a candidate enters a formal claim-bearing test or a concrete
technical risk warrants one. GPU-hour budget checks are resource decisions,
not scientific review requests.

## Route one bounded review

| Question | Useful channel | Maximum warranted scope |
|---|---|---|
| Is a frozen research design, information set, comparator, or criterion defensible? | Ordinary ChatGPT Chat with the **Pro model option**, given the actual design packet | Design review of submitted material; not code, execution, or scientific validation |
| Does an exact code/config/data-lock/protocol snapshot satisfy Code Ready? | Independent read-only Codex reviewer with repository access | Code/contract review and checks actually performed |
| Does a large evidence packet need isolated execution, recomputation, or sustained cross-checking? | Cloud ChatGPT Work, after its snapshot and tools are made available | Evidence or code review within the cloud task's verified access |

Codex may also review evidence when it can independently recompute the result. Pro may offer a second scientific-interpretation opinion when useful; do not require multiple channels or majority agreement by default. Work and Codex share usage limits; subagents add their own model/tool usage. Do not present Work as a way to avoid Codex usage, or a Codex review as a Pro review. Check current product limits rather than assuming a fixed per-review price.

## HQ handoff and user choice

Before dispatch, give the user a compact choice: recommended channel and why, alternatives, expected usage category, exact material to be shared, and the conclusion each channel could support. If the user has already chosen a channel and authorized the material, proceed within that scope. Otherwise wait for the choice; do not silently substitute a channel after access, model, quota, or transport failure. Preparing the packet is not permission to transmit it.

Reuse the Experiment or task record for the request. State only the review question, immutable protocol/commit or external snapshot identity, material actually provided, requested checks, and blocked conclusions. A local path by itself is not evidence that Chat or cloud Work received the file. Give a reviewer the frozen material and questions, not the desired verdict. Keep reviewers read-only; after a material change to a reviewed formal package, request focused review of the changed risk and downstream effects. Reuse unchanged findings rather than restarting the whole review.

## Receipt and interpretation

Store one compact review receipt alongside the owning task: channel/surface and reviewer, requested and visibly confirmed model where available, material identity and access verified, review scope, answer location/retrieval status, verdict, and decisive blockers. For Chat Pro, confirm the selected Pro option before submission and the completed response after it; a visible `Pro` label is not proof of an undisclosed backend model. Record `REVIEW_PASS`, `MODIFY_AND_REREVIEW`, or `NOT_REVIEWABLE` with the exact scope. A connection challenge, missing file, or unreadable response is `NOT_REVIEWABLE`, not a failed scientific claim.

Only a reviewer who could inspect the required material may sign that review scope. Review PASS never upgrades a Run launch, a computed scalar, or an Experiment to scientific success. Follow the project gate for validity, the frozen primary criterion, minimum decision visualization, and the scientific verdict. Summarize a chosen route or consequential review result in the project's concise Obsidian decision note when that convention applies; do not mirror every review turn.
