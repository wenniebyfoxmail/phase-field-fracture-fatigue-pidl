# FYR presentation process revision, 2026-10-17

Local presentation/notes revision only. User wants the revised Chapter 4 logic expressed in the PPT despite leaving the report unchanged, and requires explicit FEM baseline and PIDL calculation workflows. Original assessment deck and report are preserved. No new experiments, remote operations or Overleaf modifications.

Source deck: /Users/wenxiaofang/Downloads/Winnie_First_Year_Assessment.pptx. Narrative sources: the existing three-stage bilingual notes and the two designated Chapter 4 local review packages from 2026-10-15. Numerical conclusions remain those of the paired S04-E011 study. F1 in the latest message is interpreted as FEM and this assumption was stated to the user.

Keep the source 1280x720 canvas, Arial typography, Cambridge colours/footer/logo and suitable source images. Editable computation diagrams precede results. Native tables keep event rules and numerical comparisons editable. Preserve maintenance and supervised results as three backup pages. Core three-stage sequence follows the existing notes: controlled model; limited observations; road adaptation/measurement validation.

Files are authored through @oai/artifact-tool in a private build directory, never python-pptx. Finalizer checks the immutable candidate and writes a new version. All final slides are imported and re-rendered, with native diagrams/tables and bilingual notes verified. PDF learning notes pair each slide with a short English narration and Chinese text.

Run the source scripts from a private build folder linked to the bundled node_modules. RUNTIME_NODE, RUNTIME_NODE_MODULES and RUNTIME_BIN_DIR are the bundled paths recorded in build_deck.mjs. Update the final filename and receipt filename for every new version; the finalizer does not overwrite them. Use the Presentations/PDF skill operation markers once before each new user-requested authoring operation, not for rendering or read-only inspection.
