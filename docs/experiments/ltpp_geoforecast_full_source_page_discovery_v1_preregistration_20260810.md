# LTPP full-source map-page discovery v1 — preregistration

## Status

`FULL_SOURCE_PAGE_DISCOVERY_ONLY__NO_PANEL_SELECTION_OR_REGISTRATION`

The gridness diagnostic established that fixed PDF page 4 is not a common map
page: 1991 page 4 is a survey-summary form.  This one-shot diagnostic renders
every page of every frozen source PDF before any later model is allowed to look
for a map panel.

## Fixed method

Render every PDF page at 100 dpi.  On each render apply the already frozen
nonsemantic gridness response: Otsu ink threshold, 11-pixel horizontal and
vertical closings, their intersection, and a 121×121 mean.  Record the fraction
of pixels whose response is at least `0.030`, and rank all pages within each
date descending by that coverage, breaking ties by lower page number.  Render a
contact sheet showing every page and its fixed coverage value.

The ranking is an inventory, not a map-page acceptance or selection rule.  It
does not choose a page for later processing, crop anything, extract controls,
use handwritten/distress semantics, compare dates, or fit a transform.

## Stop rule

Run once after synthetic tests.  Report every PDF page for every date, including
any rendering failure.  The next panel model, if any, must cite this inventory
and freeze its own page-choice rule before running.
