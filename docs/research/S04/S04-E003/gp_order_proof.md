# Gauss-point ordering proof

Archived solver source cdf4e33710455606421806dfe6ff84ae09378d6b, source zip SHA256 1b60b36b3a1740eea68dd96e472165e0bab33cbd7da43bb8e13e9fa04eeb07ed.

`gauss_quad.m`, order 2: pts=[+0.577350269189626; -0.577350269189626]. `quad_composition.m`, dim 2: outer i, inner j, row=[pts(j),pts(i)]. Thus native order is (++,-+,+-,--). History GP axis is preserved by HDF transpose (2,1,0); no GP sorting occurs.

Runtime explicitly asserts both NumPy and Torch N[gp,node] against these archived locations with absolute tolerance 5e-16, and asserts their per-element/per-GP Jacobians. A negative test swaps GP 0/1 and must fail. No physical coefficient permutation is introduced. This closes the sole blocker in the first Code Ready review of 0984815; it does not assert whole-field numerical agreement before execution.
