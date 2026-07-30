# PaveTrack source-metadata audit

Primary source: Yang et al., *Scientific Data* 12, 1426 (2025),
https://doi.org/10.1038/s41597-025-05748-5.

The paper confirms that PaveTrack_PD contains 8,928 tracking images at 165
locations. Chinese images were acquired from a mobile vehicle with an
industrial camera. For privacy, nearby GPS observations were clustered at an
approximately 5-20 m scale and the GPS data were then removed from the released
images. The published matching baseline uses GPS clustering followed by
SuperPoint/SuperGlue background matching and local-area matching.

The released local JPEGs inspected by this package contain no EXIF camera, GPS,
focal-length or timezone fields. The paper does not provide a physical
pixel-to-road calibration for PaveTrack_PD. Therefore the SIFT/RANSAC transforms
in this package are an independent image-space diagnostic, not a reproduction
of the paper's full private-coordinate matching pipeline and not a route/model
coordinate registration.
