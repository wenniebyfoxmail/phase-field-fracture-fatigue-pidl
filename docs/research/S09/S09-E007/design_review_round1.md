# Independent design review — round 1

- Reviewer: ChatGPT through OpenCLI on the authorised Haofan account
- Conversation: <https://chatgpt.com/c/6acc123f-3864-8333-b145-ba7cef22dd6d>
- Submitted revision: `v1-frozen-beta025-u0125-holdout`
- Verdict: **MODIFY_AND_REREVIEW**; unsealing not authorised

The reviewer accepted U0.125 only as a non-blind post-selection holdout,
accepted the frozen data-only checkpoint as the honest comparator, retained the
joint `Q_f<=0.50 AND Q_u<=1.10` criterion, and agreed that E007 is a valid
decision point toward a causal transition PINO. Five blocking ambiguities
required a narrow v2 repair:

1. lock exact trajectory membership and producer stop from immutable metadata;
2. bind preprocessing, normalization, boundary lifting, reconstruction,
   precision, residual assembly, and forbidden information;
3. freeze finite/positive denominator rules and distinguish source invalidity,
   undefined ratios, and model/evaluator failures;
4. order design pass, data lock, fixture-tested implementation, Code Ready,
   permanent unsealing, and one inference;
5. replace discretionary repair language with an exhaustive outcome table.

No candidate, checkpoint, threshold, comparator, holdout trajectory, or primary
question was changed in v2.
