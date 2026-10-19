# E027 source qualification, 2026-10-19

D1continued E023–E026 records, existing dataset notes/audits, old SAM2 development selection, local model store and prior reading; no repeated whole-project audit. Bounded primary-source lookup: GitHub(qinnzou/DeepCrack, yhlleo/DeepCrack/DeepSegmentor, cuilimeng/CrackForest-dataset), official release linked checkpoint, existing full Zou PDF. No social/public-data requests or external messages.

|Source|Verified information|Decision|
|---|---|---|
|E023/E003 readout|class/box supervision, polygon envelopes, no qualified crack-pixel representation|closed negative preserved|
|E024/E025/E026 fromscratch controls|failed region baseline; translation weak pairing but Dice0|do not repeat head/translation tuning|
|Liu DeepCrack / local DeepSegmentor|different paper/repo; local dataset audit still unresolved third-party original-image rights|do not promote to this source|
|CrackSAM|local adapters exist, depends on large SAM base and mixed datasets; no exact compatibility/provenance package inspected here|not chosen; no extra download/inference|
|Zou IEEE TIP DeepCrack|official CrackTree260-trained release, final fused native map, strict compatible74finite tensors/30905011params|one new candidate, actual capability not yet qualified|
|CFD12|official non-commercial research statement; original12already exposed IDs, released binary Boundaries|development boundary-reference controls only, not independent heldout/physical area|

Primary-source locators: https://github.com/qinnzou/DeepCrack/tree/f3988031dd2adc3d19b32d1c48a2bf90d12871ac README Training/Pretrained Models/CrackTree260; codes/model/deepcrack.py DeepCrack.forward return0; codes/data/dataset.py _preprocess_img BGR/255; codes/test.py test sigmoid(fused). Checkpointer.load multi_gpu flag only adds module prefix for DataParallel, not a different model. Our state loader uses raw74keys with strict single model, no unsafe deserialization fallback.

Official release https://drive.google.com/file/d/1OO3OAzR4yxYh_UBR9Nu7hV3XayfKVyO-/view, acquired123636774bytes, SHA945239375c2b3de45abccc2dbdc374e3259b55d16298b298fb9e0cd13be5ad63. Exact fine-tuning history not independently reconstructed; FT1 filename/author source report is not a complete training-identity manifest. No unpublished access or weights substitution. Upstream code has no identified general redistribution licence; use as pinned private research input, do not publish code/data/weights in our branch.

CFD https://github.com/cuilimeng/CrackForest-dataset/tree/ed57c2d96754e6c7d105805cd29aeeb3a799f267 README section2 explicitly restricts to non-commercial research. No raw dataset redistribution. Selection reuses old SAM2 run_cross_dataset/selection.json exactly, not chosen from new outcomes. Initial Segmentation==2 assumption failed forIDs115/102/097 before inference; reference corrected prospectively to released Boundaries pixels, not inferred width/filled mask. Full12kept. Prepared12reference positive pixels743/1077/1131/1187/1245/1335/1424/1549/1761/1953/2532/7069. Native source dimensions320x480 match. Raw-preparation abort8decodes+fixed final12=20, futureproducer source/MAT decodes0.

Full existing Zou2019PDF15pages verified title/authors/issue1498–1512 and sectionIV-A(p6) training/source distinction; copied byte-identically to Obsidian original paper shelf. The paper's reported cross-dataset F-score is not our reproduced result. Source/weights scalar audit is completed, real pretrained source capability, PaveTrack qualification and downstream net benefit remain unmeasured. Detailed human-facing synthesis is Deep Research - PaveTrack 裂缝空间信息来源.md; one source/decision record, not multiple research governance ledgers.
