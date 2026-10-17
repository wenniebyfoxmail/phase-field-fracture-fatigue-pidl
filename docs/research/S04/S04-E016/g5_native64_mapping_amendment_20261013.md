# G5 mapping revision v4 — native64 repair after v3 FAIL

Status: independent review pending. No full field export or D0 executed.

Preserved result: v3 old/native center identity gate failed at 1e-12. Native-minus-old max absolute centroid difference 4.9148775993490545e-8; area difference 2.342048330272739e-8. The old reference stores float64 arrays but centers AND areas exactly reproduce calculations performed on native Q4 nodes first cast to float32. This is verified lineage/precision loss, not a reason to loosen the original identity threshold. Original FAIL is retained.

Single repair: build a NEW mapping asset from sealed native float64 Q4 coordinates/connectivity, deriving native centers and shoelace areas. Reuse old triangle assignment only as candidate indices; independently barycentrically test every new native center, exclude every failure, never nearest fallback. Preflight gives 85113 old-contained vs 85112 native-contained, one changed cell. No new FEM/PINN solve, threshold relaxation, target-selected domain or amplitude expansion.

All paired channels must adopt the new geometry-only domain and native64 areas. Old three PINN P0 arrays may be reused only after exact assignment equality and field-definition compatibility audit; their old center/area metadata cannot become the new canonical geometry. This is a bounded P0 query representation, not conservative overlap integration or physical teacher qualification. Float32 field precision remains separately audited.

Geometry code now requires exact replay of the old float32 lineage and emits a fresh native64 mapping with old failure, differences and changed-mask count in its receipt. Candidate Python SHA 334196924ef89ba59256d591686a54f9c0e41256102a7be298e58f2ae424eb1c; MATLAB unchanged cc846227024b610e2a2522caba30ac4fa14e64107683fbfa56b951ace793a8e7. v3 code review does not automatically cover this material change. Python compile PASS. Fresh geometry output will use geometry_native64_v4 only if independently approved. Prior v3 assertion occurred before output-directory creation; raw inputs remain unchanged.

Remaining G5 requirements unchanged: actual geometry/history/export receipts, precision and effective-load records, old-three compatibility, both-producer pre-event/censor list, paired data lock and deployable PINN-only feature implementation. D0 remains closed until G5 and D0 runner review pass. Only main dialogue executes; method dialogue is read-only reviewer.

Old-three header/metadata check: u011 c1..122, u012 c1..83, u013 c1..59; raw_steps exactly 5c-1. All assignment and historical mask arrays exactly equal the locked reference. Five exported fields are float32 with shape (ncycle,86408). This verifies structural reuse only, not full field compatibility/qualification. No old trajectory re-export or D0 was executed.
