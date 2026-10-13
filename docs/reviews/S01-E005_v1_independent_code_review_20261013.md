# S01-E005 v1 independent review

Read-only reviewer e003_independent_review, gpt-5.6-sol / Medium.
PASS at exact clean commit `ddb8fa834e7759ab890f9c219081d5487ec2cc05`.
Manifest SHA256 `68dd8cc4a86d0c448d8d29c3cb7a0e50c87545431746b0c55f6ee2cdf50a972e`;
29/29 source hashes, inherited E002/E003 identities and partition disjointness
verified. 76 targeted tests and compilation passed. Full feature/model/
validation/authorization chain, objective replay, NMS identity and download
firewall have no blocking code/protocol/analysis findings.

Training-only geometry replay (no pixels, model extraction, fit, producer contact
or fresh access) found 11,852 matches, 1,143 of 1,149 represented GTs, 6
unrepresented GTs, 2,147 clamped targets, equal-GT weights summing to1.0.
Target-balanced full containment: p=.5 0.3725728386; p=1 0.5889477290;
p=2 0.8004249897. v1's frozen .90 screen therefore deterministically stops
before CNN extraction, fitting, validation or fresh access. This is an input
contract finding, not a development negative for a fitted bbox head.

Decision: preserve v1; widen/reconstruct context under a reviewed amendment
using train-only information, keep comparator and fresh locations frozen.
