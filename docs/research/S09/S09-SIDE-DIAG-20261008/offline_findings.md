# Offline preliminary checks, 2026-10-08

Purpose: identify cheap discriminators before retraining. Same16 seen windows, locked data; no model fitting. New diagnostics are exploratory and not independently reviewed yet.

Persistence baseline: predicted d_next=d_current. Ratio=sum area-weighted absolute prediction errors / sum area-weighted true increments; baseline exactly1.

Constrained secant baseline: d_next=clip(d_current+(d_current-d_previous), d_current,1). Same admissible history, no fitted coefficients. Aggregate ratio1.1339815653; aggregate predicted growth0.9755391168 times reference. Getting total growth roughly right does not get spatial increments right. This comparator also fails0.8; no threshold rescue.

Training targets: damage increment scale3.208220005e-5. Maximum normalized target24367.943. For each window, sort cells by descending true increment; cells within the first1% cumulative area carry mean98.5026% of growth; first3% carry99.9888%. These are equal-window means of cumulative growth fractions, not independent trajectories. Threshold-active area mean3.0603% at delta>1e-7.

Inference: inspect scale and sparse-support supervision before blaming data quantity. None proves the training failure's unique cause. Single-window, scale, support, learning-rate, budget and width checks are prepared but NOT EXECUTED, pending independent review.
