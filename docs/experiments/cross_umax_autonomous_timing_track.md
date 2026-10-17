# Cross-Umax autonomous timing track

**Owner:** Mac-PIDL  
**Status:** closed negative Gate C  
**Claim class:** narrow trajectory-sufficiency diagnostic

## Mechanism question

Can a transition learned only from two Umax trajectories, initialized once
with the held-out exact FEM c20 state, autonomously produce the held-out
first-detect time and event field without later teacher forcing?

## Claim boundary

The benchmark contains only three neighbouring amplitudes with identical
geometry, material, initial crack, boundary-condition family, and loading
shape. Success cannot establish general autonomous fatigue-life prediction.
The initial c20 state is an FEM oracle and is not deployable input.

## Closed gate

Primary: equal-trajectory pre-event mean-increment rolling from c20 to a fixed
c160 censoring horizon. Secondary: linear-Umax mean-increment rolling.
Persistence is the negative control. Event detection reproduces the original
node rule through a frozen element-to-node arithmetic mean. Timing and event
field gates must pass independently on all three held-out trajectories.

Local assets:

`local_archive/after_strict_setting_alignment/fem/cross_umax_autonomous_rolling_c20_20260818/`

## Next action

The locked autonomous gate failed. From true c20, the primary equal-trajectory
mean predicted first detect at c69/c76/c98 against FEM c122/c83/c59, so its
timing errors were -53/-7/+39 cycles and complete passes were 0/3. The
secondary linear-Umax mean predicted c124/c76/c63 (+2/-7/+4), but failed every
complete fold because U0.12/U0.13 missed the timing gate and all three missed
the event-field gate (p99 IoU 0.146/0.658/0.669).

Do not promote either stationary transition. A genuinely state-conditioned
nonlinear successor requires a new preregistration and must not tune on these
three held-out outcomes.
