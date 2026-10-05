# Limited read-only follow-up

Retrieved Stage0b solve_fatigue_fracture.m shows UV Newton atlines64–77, damage Newton115–128, nodal lower/upper bound enforcement132–135, stag.post_iter_update141–148, and export/historycommit afteracceptance149–196. Therefore metadata res_displ is returned from the UV Newton call before the final damage update; it is not automatically the final accepted-pair residual.

Resolved by S04-E011. The hash-matched original `stag.post_iter_update` reassembles equilibrium with final damage/current UV and accepts on raw free-UV L2 plus phase residual at `4e-4`. The stored metadata equilibrium scalar is from the preceding UV Newton call and is not the accepted-pair norm. See `../S04-E011/source_audit.md` and `../S04-E011/metrics.csv`.
