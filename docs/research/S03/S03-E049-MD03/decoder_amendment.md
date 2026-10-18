# E049 pre-target source-format amendment — 2026-10-18

Two fixed historical TIFFs verified at5496×3670, PIL modeI;16, unsigned16-bit,
PhotometricInterpretation1. Initial JPEG-style PIL `.convert('RGB')` clamps
values>255 rather than converting16-bit intensity units; previews are almost
white and not usable visual evidence. No extraction, prediction or target
acquisition has happened at this point. Preserve R001 initial previews/receipt.

Before ROI selection or target access, use deterministic code-value conversion
`gray8 = (gray16 // 257).astype(uint8)`, then repeat grayscale in3RGB channels.
Range0..65535 maps0..255, no image minimum/maximum, histogram/percentile stretch,
gamma, denoising, spatial resize or error-dependent choice. Same conversion on
all3frames; reject any different source mode/bitdepth instead of adapting.
This replaces the source-reader portion of the original RGB-conversion clause,
not the frozen E045/E037 recognition thresholds/logic or old half-depth values.
16bit export colour processing/gamma and physical intensity calibration remain
unknown. Recognition-domain transfer validity is empirical, not assumed.

R001b rerenders the same two histories with corrected units; no image/window
replacement, measurement retry or parameter sweep. Original source-byte hashes
and fixed triplet remain unchanged. TIFFs have no DateTime/DateTimeOriginal
tags; file numbering cannot be elevated to confirmed acquisition times. D2
therefore remains file-order geometry continuation, not qualified forecasting.
