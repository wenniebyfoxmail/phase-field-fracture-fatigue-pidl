# S02-E004 R003-A packet review

Date: 2026-10-09

Review type: independent, read-only

Verdict: `PASS` for Round A annotation

## Binding

- Reviewed commit: `a58971aa4d36d70d33c0e0ced54278b7e6010086`
- Reviewed committed runner SHA-256:
  `d3e1f56821a36f32da5edfc9469a64669a7a0d059ad5bdcd9fe6711a978100f4`
- Selection SHA-256:
  `d02d75cb7f3206ab3da2e5167d363c72f2475fa288d00802c6fab3bdd50ac85b`
- Extraction-receipt SHA-256:
  `03d0837c508021c91683c01223c633fdb3b6a42be23c1af22177b4435d63d910`

## Verified evidence

- Exactly 15 unique source members and released TIFFs: five frozen states each
  for H01-1, H05-1, and V05-1.
- Recomputed processed-row indices, nearest camera-0 TIFF selection, earlier
  tie handling, and directional tolerances all match the sealed selection.
- The three retained 1-MiB ZIP tails match the frozen SHA-256 identities and
  parse to 3686, 3690, and 3668 unique entries. All 15 extraction rows match
  the central-directory name, CRC-32, flags, compression method, sizes, offset,
  source ZIP MD5, cycles, and tail digest.
- All 12 source workbooks retain their frozen receipt identity, size, and CRC.
- Every canonical/released TIFF pair is byte-identical and pixel-identical,
  fully decodes as 4112 x 3008 grayscale, contains no forbidden identifying
  TIFF metadata, and has the normalized timestamp.
- The sealed secret is 32 bytes with mode 0600. Recomputed Round A and
  hypothetical Round B tokens are individually unique and disjoint.
- `annotations.csv` contains exactly 15 one-to-one blank rows. No Round B
  directory and no Round A completion record exist.
- No raw extracted TIFF remains and no source mutation was found.

## Administrative correction

The packet receipt's stale `protocol_revision: v1` can be reconstructed exactly
from the committed runner. The current receipt changes only that value to
`v1.2` and adds a correction record. The current source changes only the same
literal. Selection, images, digests, measurements, protocol criteria, and
scientific evidence are unchanged.

## Boundary

This PASS admits Round A annotation only. Round B remains blocked until the
runner validates all Round A rows, seals their digest and completion time, and
24 hours elapse. Packet validity is not a repeatability result.
