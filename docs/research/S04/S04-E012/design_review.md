# Design review

The S04-E011 independent evidence review passed and explicitly recommended c82s4/c83s4 fixed-accepted-damage, frozen-fatigue UV-only polish plus a read-only c82s5 control. E006 and E008 already produced the two requested polished arrays under that contract. E012 therefore adopts the cheaper read-only route: independently reassemble and verify those arrays instead of repeating the solves.

Adopted: strict-physics derived-reference label; separate native-fidelity estimand; `rho_u <= 1e-3`; original and polished arrays remain separate; c82s5 is no-solve; full teacher remains `NOT_QUALIFIED`.

Modified: the requested pilot is implemented as a retrospective adoption audit because the exact solves already exist. A new solve is triggered only by a failed identity or metric check.

Rejected: calling the polished arrays qualified FEM teachers; adding the original phase scalar to the polished UV residual; using “either route passes” as a success rule; transferring the original MATLAB bridge to the polished field.
