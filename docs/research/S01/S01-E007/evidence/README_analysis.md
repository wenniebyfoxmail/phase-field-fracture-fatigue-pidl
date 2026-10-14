# S01-E007-R001 evidence reading guide

Question:can paired original-target harm/gain scores choose safe repairs and
produce actual net detection gain? This evidence covers four **training
qualification** locations353/1459/2028/5982,not the five development or fresh
locations. Shared E003 encoder saw all16 training locations;new correction
coefficients/scalers and decision-head fit excluded these four.

Read qualification/F00_training_qualification.png with qualification_metrics.csv:
all four fixed policies show delta0,retention282/282,and only1/2/4/7 accepted
original-valid pair exposures versus20 required. Empirical same-target harm
1/1,1/2,2/4,5/7 versus.05. The ratios are local descriptive counts,not reliable
population risks. The result is inconclusive_qualification_exposure;no rule was
selected and no deployment refit/development comparison was allowed.

qualification/F02_qualification_montage.png follows the fixed most permissive.1
policy because none qualified,then highest frozen E003 score for admitted new/
lost/FP examples,up to2 locations per role. New/lost counts are0,so only2 FP
panels exist. RedGT,orange original,cyan emitted. Both emitted boxes are unchanged
originals and are metric FPs;the montage does not depict newly harmful corrections.
Source images match the frozen E002 training manifest hashes. This is bounding-box
reference evaluation,not proof of physical crack absence or a temporal claim.

label_counts.csv records exact12-fit/4-qualification labels and joint states;
qualification_summary.json and montage_cases.json preserve scope and selection.
The fixed .1 rule accepted175 of455 proposed repairs,only3 in the operating
prefix,with0new/0lost targets and unchanged282TP/330FP. Sparse effective changes
explain why100% retention is not proof of a useful gain-selection model.

component_path_counts.json is explicitly **posthoc descriptive** and reproduced
by scripts/pavetrack_paired_cv/diagnose_path.py. It counts existing frozen rows and
labels without an extra arm:177 geometry gains,12 score-eligible,4 accepted at.1,
0 accepted gains above baseline threshold. It selects the next corrected-crop
scoring test as an unexecuted hypothesis,not a rescued qualification verdict.

Raw arrays,4heads,paired-bank labels/targets,qualification head/history,4 exact
policy outputs/probabilities,stop decision andlogs:
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S01-E007/runs/S01-E007-R001/evidence/.
ParentE006 arrays/checkpoint identity and all inherited inputs remain in their
owning archives. ZIP333710211bytes/20members/hash and montage hashes are in
retrieval_receipt.json. Original ZIP is immutable;later plot/closure files are
outside it. No actual all16 refit or validation/test file exists.

Render with frozen qualification_analysis via render_qualification.py;the latter
only clarifies "cyan emitted" in the title. See rendering_note.md. Address raw
payloads through a directory/symlink namedS01-E007-R001 to preserve the frozen
CLI's path-basename RunID;no data is changed. Full policy/metric/harm/selection
replay precedes output. F00 and F02 visually checked;numerical table authoritative.

Disposition:retain E003,stop this attempt,keep fresh sealed. Next solution is
scoring repaired crops with unchanged E003 before any further selection-head
training;see result_20261014.md and next_solution_proposal.md. Independent evidence
review pending at this snapshot. Results are local;only the prior approved source
commit05f37c7 has been published to GitHub.
