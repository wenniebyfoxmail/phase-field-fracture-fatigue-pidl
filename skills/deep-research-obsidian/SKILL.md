---
name: deep-research-obsidian
description: Conduct or archive a research-direction or bottleneck deep research in Obsidian, linking an actionable synthesis to verified paper files, source coverage and manual-download handoffs. Use at topic intake, around brainstorming, after a measured bottleneck, or when importing a ChatGPT Deep Research report; not for every iteration or a single factual lookup.
---

# Deep Research To Obsidian

The deliverable is a reusable research report connected to its source material
and the next decision. Use this with `research-decision-core`; add a domain
adapter when the question needs one. The core/HQ retains the Decision Ladder,
route choice, task authority, and Experiment verdict. The user may request
research, archive an existing report, or resume after manually downloading
papers.

## When To Use It

- **Topic intake:** map the problem, established approaches, evidence/data and
  promising questions before committing to a route.
- **Before brainstorming:** gather a compact factual map so discussion starts
  from known work and feasible options.
- **After brainstorming:** check the shortlisted mechanism, contrary evidence,
  transfer assumptions and simplest comparator.
- **At a measured bottleneck:** identify approaches used in this field and
  structurally similar problems, then design a mechanism-led, decision-scale
  validation rather than automatically proposing another small patch.

Choose the relevant point; there is no required pair of before/after reports.
Reuse an existing report when its question and coverage still fit. A new model
idea or routine failed iteration does not automatically require deep research.
Stop when the live decision can be made, or record the precise missing evidence.

## Start From The Current Decision

Read the existing task/Obsidian note and local source/code inventory. Define
the research question, active D step, intended decision, domain, search scope,
and time/cost limit. Use `orientation` or `bottleneck` as a purpose label, not
as another approval stage. For route adjustment, follow the core's first-
principles design: identify the binding assumption/mechanism and compare a
root-level redesign with local repairs where relevant. Keep the request compact.

For solution-design delegation, honour the user's advanced-model preference
and record the actual model. Give the sub-agent the goal, bottleneck evidence,
baseline, assumptions open to redesign, resource scope and archive destination.
The HQ integrates the result and maintains one report. Do not start a new
user-owned chat or cloud research task without the user's request for one.

## Research And Acquire Materials

Use `research-evidence-workflow` as this operator's internal multi-source
discovery and synthesis tool; choose a mode whose coverage answers the live
question. Reuse its registry rather than creating another source ledger. Use
`paper-reading-obsidian` and `paper-deep-reader` as internal paper-level
operations when needed, plus suitable scholarly search/retrieval tools for
primary papers, official code, datasets and technical reports. These tools
contribute source coverage and evidence; they do not open another governance
route or change an Experiment verdict.

Acquire the papers and files that support the report, rather than downloading
every search hit. Prefer the publisher, author or institutional repository;
record version, DOI/stable identity, URL and access status. Inspect retained
full texts using the relevant reading workflow; substantive findings need a
page, section, figure, equation or equivalent locator. Distinguish what a source
reports from our inference and proposed transfer. Preserve contrary evidence.

For publication files and Obsidian paper notes, use the internal
`paper-reading-obsidian` operation.
Deduplicate by DOI and version; reuse verified existing PDFs and analyses.
Check title/authors/identity, completeness and readability before labelling
material full text. A downloaded webpage or preview is not a complete paper.
Code can be acquired for inspection; acquisition does not mean reproduction.
Keep large datasets and code in the project/case store and link them from the
report. Small relevant supplements or technical files may be archived beside
their related source with explicit names and source URLs.

## Manual Download Handoff

When reasonable official retrieval routes fail, keep the partial synthesis
useful. Give a short queue: title/DOI, exact official page, what is missing and
why it matters. Open the accurate pages in Chrome and keep them for the user
as described in `paper-reading-obsidian`. Ask the user to download to Downloads
and reply when done. Do not invent a local PDF link or repeatedly retry a
blocked source.

On “downloaded”, match candidate files by identity rather than filename/time
alone, check completeness/readability, deduplicate, archive and replace the
pending status and conclusions only after checking the text. Continue other
sources while waiting where useful; do not create a polling automation.

## Archive The Report And Sources

Use the vault's `AGENTS.md` and project configuration. Wennie's current paths
are in [references/wennie_vault.md](references/wennie_vault.md); use other
users' chosen paths rather than carrying these into another project.

Maintain one living report per decision/question. Start with a short plain-
language answer, then the comparison and evidence needed to act. Use
[the report template](assets/report_template.md) where useful. Include:

- the question, purpose, active D step and research date;
- a concise synthesis with source-linked findings and contrary evidence;
- a small comparison of candidate solutions, transfer conditions and cost;
- one recommended route, its discriminating validation and redirect condition;
- for route changes, why the mechanism and evidence scope can resolve the
  main bottleneck rather than merely add another component check;
- a source list distinguishing full text, abstract/preview and pending access;
- actual PDF/analysis links for archived sources, plus code/data pointers;
- search/coverage limits and an exact manual-download queue when needed.

The top summary should usually fit 150–300 Chinese characters. Let the body
carry the necessary reasoning; avoid search logs and copied chat transcripts.
The report may be longer than an ordinary milestone. Updates to the task note
and Roadmap remain two to four short lines and a single link/status.

For a ChatGPT or other external Deep Research report, preserve its original
export when provided and record channel/date/source. Archive a concise local
synthesis and inspect the references used for our decision. An external report
or completion receipt alone does not verify the cited papers or their claims.
Do not switch research channels or change the user's selected model silently.

When a figure/table changes the decision, include it with a source and short
`看见什么 / 说明什么 / 必要时还不能说明什么` interpretation. Label conceptual
or simulated visuals clearly. Research summaries do not imply a new experiment
has been executed.

## Completion

Read back the report and paper links, check unique basename resolution, and
ensure the task note and required Roadmap/index link resolve. The read-only
helper `scripts/check_archive_links.py` checks link existence and ambiguity;
it does not verify paper identity, reading quality or scientific conclusions.

Report separately: synthesis saved, PDFs obtained/verified, pending sources,
and the next decision. A useful provisional report may be archived while some
papers are pending; show its coverage honestly. Do not block the whole topic
on one inaccessible paper or claim full coverage without it.
