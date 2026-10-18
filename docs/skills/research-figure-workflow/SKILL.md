---
name: research-figure-workflow
description: Use when planning, generating, auditing, or revising research figures for papers, thesis chapters, Overleaf manuscripts, computational mechanics results, PIDL/FEM comparisons, captions, figure panels, or visual evidence packages.
---

# Research Figure Workflow

Use this skill when a figure is part of a research argument, not just a quick
plot. The goal is to make figures that are traceable, visually clean, and honest
about what the data supports.

## Core Rule

Start from the claim, not from the plot type.

Before making or editing a figure, identify:

1. The claim this figure supports.
2. The exact data source: run id, archive, CSV, NPY, log, mesh, notebook, or script.
3. The comparison standard: baseline, FEM reference, ablation, literature value, or
   previous figure.
4. The intended destination: thesis, paper, appendix, supervision note, or quick
   diagnostic.

If the data source is unclear, stop and locate it before polishing visuals.

## Figure Planning

Use this compact plan:

```text
Figure purpose:
Claim:
Panels:
Data source per panel:
Metric definitions:
Known caveats:
Output path:
Caption message:
```

For multi-panel figures, each panel should earn its place. Remove panels that
repeat the same evidence or make a separate claim that belongs in another figure.

Prefer one theme per exported figure. If a draft combines field snapshots,
scalar trajectories, error maps, and schematic elements, split them into
separate files unless the combined layout is needed for a specific manuscript
argument. Separate exports are easier to resize, caption, and adjust in
Overleaf.

## Data Integrity

- Prefer existing plotting scripts and project conventions before writing a new
  plotting pipeline.
- Keep raw data, processed data, and rendered figures conceptually separate.
- Do not smooth, clip, normalize, or rescale fields unless the caption or label
  makes that choice clear.
- For PIDL/FEM comparisons, separate scalar metrics from field-level agreement.
  A matching fracture cycle or integrated quantity does not prove matching local
  mechanism.
- Keep units and nondimensional variables explicit.
- For one-seed, one-load, or one-archive evidence, label the figure or caption
  with the scope.

## Plotting Standards

Prefer Matplotlib for project-native research plots unless the repo already uses
another tool for that figure family.

### Colour And Line Policy

Use colour to clarify evidence, not to decorate the figure.

For mechanism diagrams, conceptual schematics, or graphical abstracts that
need stable semantic colour roles and controlled area balance, pair this skill
with `research-figure-color`. Do not transfer a schematic palette to scalar or
field data; quantitative colour scales and shared limits remain governed here.

Default colour choices:

- Default scalar field: `viridis`
- High-localisation or intensity field: `magma`
- Signed or difference field: `RdBu_r`, zero-centred
- Method-comparison lines: Okabe-Ito palette, muted when possible

Avoid:

- `jet` / rainbow maps
- overly saturated palettes
- per-panel autoscaling in comparison montages

For line plots:

- prefer muted colours
- use thinner but printable lines, usually `1.2-1.8 pt`
- add more whitespace around dense information
- use light grey gridlines only when they help read values
- use line style or markers as redundancy when several methods are compared
- prefer direct labels for 2-4 curves; use a legend when there are more
- reserve saturated colour for one highlighted result, not every curve

For comparable field panels, shared colour limits are usually more important
than the exact palette. Do not make two panels visually comparable if their
colour scales represent different magnitudes.

Use:

- consistent fonts and sizes across panels
- colorbars with units or normalized quantity labels
- fixed color limits when comparing fields across cases
- direct labels or concise legends
- vector output for line plots when possible
- high-resolution PNG or PDF for field montages when raster is more reliable
- both PNG and PDF exports for paper figures whenever practical

Avoid:

- cropped fields without noting the crop
- legends that cover data
- unlabeled cycle numbers, load levels, seeds, or method variants

## Visual QA Checklist

Before considering a figure done, check:

- The figure answers one clear question.
- Every panel has a readable label.
- Axes, colorbars, and legends are legible at manuscript size.
- Compared fields use the same coordinate frame and color scale.
- The plotted quantity matches the claim and caption.
- The output file opens correctly.
- The figure path is recorded for Overleaf or manuscript handoff.

For field figures, inspect the rendered image rather than trusting the script
alone. Look for blank panels, transposed axes, flipped coordinates, bad masks,
overlapping labels, and misleading color limits.

For horizontal field montages, prefer a right-side vertical colourbar when it
keeps axis labels and titles cleaner. Use a bottom colourbar only when the
manuscript layout clearly benefits from it.

## Explain What The Figure Means

When presenting a result figure to the user, place a compact **What this
figure means** block immediately below it, in the user's working language:

- **See:** one visible, case-bound pattern, naming the comparator where there is one.
- **Therefore:** the bounded conclusion or decision that pattern supports.
- **Does not show:** add this line only when a material over-interpretation is likely.

Use two or three short, plain-language lines. Translate metrics and fields into
their practical meaning; do not repeat the caption, table, or provenance. The
interpretation must respect the stated scope and cannot turn a component gain,
curve match, or attractive field map into an unsupported full-method claim.

For common figure types, make the visible evidence explicit: identify where a
CV overlay finds or misses the target; where reference, prediction, and error
fields agree or diverge; or whether curves separate, overlap, or change slope.

## Caption Draft

Write captions as argument support:

1. Name what is plotted.
2. State the setup and comparison.
3. State the key observation.
4. Add the limitation if the figure could be overread.

Good pattern:

```text
<Quantity> for <methods/cases> at <cycle/load>. The panels use a shared colour
scale to show <comparison>. <Main observation>. This comparison is limited to
<scope/caveat>.
```

## Overleaf Handoff

When the user wants the figure in the manuscript, pair this skill with
`overleaf-git-workflow`.

Handoff should include:

- final figure path
- suggested Overleaf destination path
- caption text
- required citation or data caveat
- whether the figure replaces an existing file

Do not push to Overleaf without following the Overleaf sync protocol.

## Delivery Format

For figure work, report:

- what figure was created or revised
- source data used
- output path
- key visual QA result
- caption or manuscript insertion note, when relevant
