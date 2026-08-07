# LTPP GeoForecast background knowledge

Status: living background note; not an experiment result or preregistration.

Last literature check: 2026-08-07.

## Purpose and evidence boundary

This note separates several tasks that are often all called “crack prediction”
and records the literature context for the LTPP GeoForecast tracks. Reported
scores are not directly comparable across papers when the target, split,
annotation width, tolerance, or physical section differs. A random observation
split is not evidence of transfer to a completely unseen pavement section.

## What the field currently predicts

| level | target | common methods | current maturity |
|---|---|---|---|
| crack recognition | crack location in a current image | CNN, U-Net, YOLO, Mask R-CNN, SegFormer | mature in-domain; cross-domain generalization remains difficult |
| aggregate crack regression | crack area, length, count, or percentage at an observation | linear regression, RF, GPR, ANN, GBM/XGBoost | the most common LTPP task |
| initiation or state deterioration | time to first crack or transition among condition states | survival analysis, Markov and hazard models | useful for network-level maintenance planning |
| mechanistic-empirical forecast | future aggregate distress under traffic, climate, material, and structural inputs | mechanics, fatigue damage, empirical transfer functions | operational in pavement design but locally calibrated |
| spatial crack evolution | future initiation location, continuation tip, branch, or crack map | random walk, phase field, FEM, spatiotemporal neural networks | mainly simulation/laboratory work; weak real-road validation |

The central evidence gap is not whether a model can fit observed crack amount.
It is whether a source-time model can predict the next state on a completely
unseen real pavement section, beat persistence, and preserve spatial geometry.

## Aggregate LTPP crack prediction

The typical published workflow is:

```text
structure + pavement age + climate + traffic + optional FWD
                              |
                    RF / ANN / GPR / GBM
                              |
          observed crack length, area, count, or percentage
```

Examples include:

- An FWD-ANN study used 311 observations from 19 LTPP sections. Six inputs
  included HMA thickness, air voids, asphalt content, cumulative ESAL,
  temperature, and an FWD-derived area ratio. It predicted fatigue-cracking
  area and reported overall R2 = 0.90 under a 70/15/15 observation split. The
  paper did not hold out complete sections, so this does not establish transfer
  to a new road. Source: [Applied Sciences 15(7), 3799](https://www.mdpi.com/2076-3417/15/7/3799).
- A flexible-pavement transverse-cracking study used 942 observations from 234
  LTPP sections and compared regression trees, SVM, ensemble trees, GPR, and
  ANN. Exponential GPR reported R2 = 0.70 and RMSE = 17.50 for transverse crack
  count under ordinary cross-validation. Source:
  [Discover Civil Engineering](https://link.springer.com/article/10.1007/s44290-024-00128-1).
- A CRCP longitudinal-cracking study used 395 observations from 33 sections,
  20 structural, climate, traffic, and performance predictors, and PSO-tuned
  GBM. It reported R2 = 0.984 and RMSE = 2.661. The paper explicitly randomly
  divided observations into five folds rather than grouping by physical
  section. Source: [Journal of Engineering and Applied Science](https://link.springer.com/article/10.1186/s44147-025-00623-x).
- A 2026 CRCP transverse-cracking study used the same 395-observation,
  33-section scale and reported R2 = 0.99 under random five-fold validation.
  Its target was transverse crack count, not crack placement. Source:
  [Urban Lifeline](https://link.springer.com/article/10.1007/s44285-025-00061-4).

These high R2 values do not answer the LTPP GeoForecast primary question:

> On a completely held-out section, can source-available information improve
> the next-survey prediction over persistence?

## Initiation, deterioration state, and mechanistic-empirical models

Survival analysis predicts time to first crack or threshold crossing while
retaining right-censored sections that have not cracked by the final valid
observation. One LTPP SPS-5 study evaluated initiation of fatigue, wheel-path
and non-wheel-path longitudinal, and transverse cracking using a Weibull
survival model and pavement, traffic, climate, mixture, and rehabilitation
factors. Source: [ASCE crack-initiation study](https://ascelibrary.org/doi/10.1061/%28ASCE%29CF.1943-5509.0000409).

Markov and hazard models instead discretize condition into states such as no,
light, medium, and severe cracking, then estimate transition probabilities.
Dynamic Markov variants condition those probabilities on the current state and
other observations. Source: [dynamic Markov crack model](https://ascelibrary.org/doi/10.1061/%28ASCE%290733-947X%282005%29131%3A11%28861%29).

AASHTOWare Pavement ME follows a mechanistic-empirical chain:

```text
axle loading + climate + materials + structure
                     |
       stress, strain, and thermal response
                     |
           cumulative fatigue damage
                     |
          empirical transfer function
                     |
       aggregate fatigue or thermal cracking
```

FHWA documentation describes calculation of allowable fatigue cycles from HMA
modulus and tensile strain, Miner-type damage accumulation over traffic and
environmental combinations, and conversion to percent cracked area. Source:
[FHWA mechanistic-empirical analysis](https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/11045/004.cfm).
Local calibration remains essential; FHWA reports frequent underprediction of
fatigue cracking and global-fit difficulty for longitudinal cracking. Source:
[FHWA calibration review](https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/ltpp/17104/003.cfm).

## Spatial crack evolution remains an open real-road problem

Published spatial approaches include a multinomial random-walk model whose
direction probabilities were estimated by tracing 100 real concrete-surface
crack images. It simulates plausible crack paths but does not blind-predict the
next registered map of the same road. Source:
[Scientific Reports 12, 14157](https://www.nature.com/articles/s41598-022-18060-8).

Other deep spatiotemporal crack-path models use theoretical or numerical image
sequences rather than long-term registered road surveys. Regional forecasting
has also combined laser-derived cracking indices with random forests and future
traffic/climate scenarios, but the output remains an aggregate spatial index,
not individual crack geometry. Source:
[Computer-Aided Civil and Infrastructure Engineering](https://onlinelibrary.wiley.com/doi/10.1111/mice.13489).

No reviewed study found in this search simultaneously demonstrated all of:

- repeated registered surveys of the same real pavement;
- complete held-out-section validation;
- source-time-only inputs;
- future crack location, continuation, and initiation output; and
- stable improvement over persistence.

This is a search conclusion, not proof that no such study exists.

## Crack recognition literature

### Task definitions

| task | output | representative methods | suitability here |
|---|---|---|---|
| image or patch classification | crack present/absent or crack family | CNN, ViT | screening only |
| object detection | class plus bounding box | YOLO, Faster/Cascade R-CNN | useful for coarse localization; insufficient for length and topology |
| semantic or instance segmentation | crack pixels or masks | U-Net, DeepCrack, DeepLab, SegFormer, SAM adaptation | required before centerline and growth measurement |

DeepCrack established an end-to-end pixel-segmentation route that fuses
hierarchical, multiscale CNN features under deep supervision. Sources:
[IEEE Transactions on Image Processing](https://doi.org/10.1109/TIP.2018.2878966)
and [Neurocomputing](https://doi.org/10.1016/j.neucom.2019.01.036).

A 2023 lightweight encoder-decoder reported F1 values of 94.94%, 82.95%,
95.74%, and 92.51% on CamCrack789, Crack500, CFD, and DeepCrack237 and 25 FPS
on a mobile robot. These are in-dataset results whose metrics and annotation
conventions are not interchangeable. Source:
[Computer-Aided Civil and Infrastructure Engineering](https://doi.org/10.1111/mice.13103).

### Real multi-region detection is harder

RDD2022 contains 47,420 images from six countries and more than 55,000 road
damage instances, with longitudinal, transverse, alligator cracks and potholes
captured using heterogeneous mobile platforms. Source:
[RDD2022 data paper](https://doi.org/10.1002/gdj3.260).

In the CRDDC 2022 hidden-test challenge, the leading YOLO plus
Faster/Cascade-R-CNN ensemble achieved about 0.76 F1 for the combined six-country
bounding-box task. This is materially below many single-dataset segmentation
scores and still does not provide pixel-accurate centerlines. Source:
[CRDDC 2022](https://arxiv.org/abs/2211.11362).

### Generalization and annotation efficiency

Current research addresses domain shift and annotation cost through domain
adaptation, semi-supervision, weak supervision, self-supervised pretraining,
and foundation-model adaptation.

- Cross-consistency semi-supervised segmentation uses agreement between
  perturbed decoder predictions to exploit unlabelled images; the paper reports
  competitive results using 60% of the precise labels. Source:
  [Road Materials and Pavement Design](https://doi.org/10.1080/14680629.2023.2266853).
- A weakly supervised U-Net accepts rough crack/noncrack annotations and
  reported stronger cross-dataset robustness than its fully supervised U-Net
  counterpart. Source: [Intelligent Transportation Infrastructure](https://academic.oup.com/iti/article/doi/10.1093/iti/liac013/6798398).
- The 2025 Segment Any Crack preprint fine-tunes normalization parameters in
  SAM. It reports 61.22% F1 and 44.13% IoU on OmniCrack30k and average 67.20%
  zero-shot F1 across three new datasets. This is promising but not evidence
  that generic SAM automatically solves thin-crack segmentation, and it remains
  a preprint in this evidence record. Source:
  [arXiv:2504.14138](https://arxiv.org/abs/2504.14138).

### Historical images as a spatial prior

A particularly relevant PLOS ONE study used GPS coarse localization, ORB image
matching, homography-based pixel registration, mapping of historical crack
pixels, and region growing to detect newly grown cracks. It used 113 paired
images from two Wuhan roads collected six months apart and reported 88.9%
growth-detection F-measure. Source:
[PLOS ONE 15(8), e0235171](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0235171).

This supports using historical geometry as a spatial prior, but the small
two-road study assumes growth is near existing cracks and may miss independent
new initiation.

## Crack detection and monitoring algorithm families

“Crack monitoring” is not one algorithmic task. It is a chain of distinct
problems:

```text
current-map recognition
        |
crack geometry extraction
        |
registration of repeated observations
        |
new / extended / branched / widened change detection
        |
future deterioration or crack-growth forecasting
```

Confusing these stages leads to overclaiming. A detector that finds crack
pixels in one image is not automatically a temporal monitoring method, and a
temporal change detector is not a future-geometry forecaster.

### Current-image recognition

| algorithm family | representative methods | output | relevance to the LTPP carrier |
|---|---|---|---|
| classical image processing | adaptive thresholding, Canny, morphology, Frangi or other line filters | candidate crack pixels | interpretable and useful as a baseline, but regular grids, boundaries, arrows, and text can be false positives |
| CNN semantic segmentation | U-Net, DeepCrack, DeepLab, SegFormer | per-pixel crack mask | a reasonable baseline, but vulnerable to map style, template, scan quality, and section shift |
| object detection | YOLO, Faster R-CNN | boxes or coarse regions | useful for screening, but insufficient for length, direction, endpoints, or connectivity |
| instance segmentation | Mask R-CNN, Mask2Former | separate crack instances | can separate multiple cracks, but requires reliable instance-level labels |

DeepCrack is a representative multiscale CNN segmentation method that fuses
hierarchical features for low-contrast and discontinuous cracks. Its reported
benchmark performance is evidence for the architecture on pavement-image
datasets, not evidence of transfer to scanned hand-drawn LTPP maps. Source:
[DeepCrack](https://doi.org/10.1109/TIP.2018.2878966).

For the LTPP carrier, the key failure mode is not simply insufficient network
capacity. The map contains many non-crack line-like structures: printed grid
and frame lines, lane or reference boundaries, handwritten text and numbers,
arrows, dimensions, WIM or patch boxes, hatching, and scan artefacts. A larger
generic detector may learn these structures more confidently without learning
the crack concept.

### Crack geometry and topology extraction

Recognition should be followed by explicit geometry extraction. The relevant
outputs are crack centerline, length, orientation, width where measurable,
endpoints, junctions, branches, and crack-family membership.

Important algorithm families include:

- **Tensor voting:** connects fragmented candidates using local orientation and
  continuity;
- **graph and minimum-spanning-tree methods:** convert candidate pixels or
  segments into a graph, then prune implausible connections;
- **skeletonization:** converts a mask to a centerline and exposes endpoints,
  junctions, and branches;
- **active contour or minimal-path methods:** follow an image-supported path
  from a seed while enforcing smoothness and continuity; and
- **topology-aware neural losses:** constrain the predicted mask to preserve
  thin structures and connectivity.

[CrackTree](https://www.sciencedirect.com/science/article/pii/S0167865511003795)
is a classic example combining local intensity information, tensor voting, a
graph representation, minimum-spanning-tree construction, and edge pruning.
Its important contribution is to use crack continuity and geometry rather than
only independent pixel decisions.

For the current recognition track, a single crack mask should be upgraded to a
multi-output representation:

```text
crack mask
+ centerline
+ endpoint / junction maps
+ non-crack structure classes
```

The non-crack classes should include at least grid/frame, boundary, text,
arrow/dimension, patch/WIM, and uncertain. A topology-aware loss such as
[clDice](https://openaccess.thecvf.com/content/CVPR2021/papers/Shit_clDice_-_A_Novel_Topology-Preserving_Loss_Function_for_Tubular_Structure_CVPR_2021_paper.pdf)
is relevant because it explicitly rewards centerline overlap and connectivity;
IoU alone can give a reasonable score while breaking a long crack into many
pieces.

### Cross-date monitoring and change detection

Temporal monitoring requires registration before change interpretation:

```text
date A map
    |
spatial registration
    |
date B map
    |
crack-mask or crack-graph matching
    |
new / retained / extended / branched / widened / uncertain
```

Registration families include SIFT, ORB, or AKAZE keypoints; BRIEF or FREAK
descriptors; RANSAC with affine or homography models; thin-plate splines for
non-rigid correction; GPS or mileage for coarse localization; and learned
feature matching or unsupervised registration. A recent pavement-image study
found AKAZE plus BRIEF to be the strongest of the tested feature pipelines and
registered 96 of 100 image pairs, illustrating that registration is a separate
qualification gate rather than an invisible preprocessing detail. Source:
[feature-based pavement registration](https://doi.org/10.1111/mice.13407).

After registration, possible change algorithms include pixel differencing,
historical-crack projection with region growing, segmentation difference,
centerline displacement, graph edit distance, and direction-aware crack-graph
matching. A PLOS ONE study combined GPS localization, ORB matching,
homography-based mapping, and region growing on 113 paired images from two
roads over six months, reporting 88.9% growth-detection F-measure on its own
dataset. This is a useful method hypothesis, not a general transfer result.
Source:
[historical crack data and multiscale localization](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0235171).

An emerging route represents each observation as a crack graph and matches
nodes and edges to classify extension and branching. Recent work has explored
heuristic tree search for this graph matching problem, but the approach still
depends critically on a valid spatial registration and reliable upstream
centerline extraction. Source:
[graph-based pavement crack change detection](https://www.sciencedirect.com/science/article/pii/S0926580525001505).

### Three-dimensional crack measurement

When the objective is physical crack width, depth, or 3-D position rather than
map recognition, relevant methods include binocular vision, RGB-D, structured
light, laser-line triangulation, mobile laser scanning, UAV multi-view
reconstruction, and 3-D GPR. A typical binocular pipeline is:

```text
crack segmentation
    |
left-right feature matching
    |
stereo triangulation
    |
length / width / orientation measurement
```

For example, binocular crack-width studies combine DeepLabV3+-style
segmentation with feature matching and stereo geometry. Source:
[binocular crack-width measurement](https://www.mdpi.com/2076-3417/13/5/2752).
Mobile laser-scanning methods instead construct a georeferenced feature image
and use tensor voting to extract low-contrast or discontinuous cracks. Source:
[iterative tensor voting for mobile laser scanning](https://uwaterloo.ca/geospatial-intelligence/sites/default/files/uploads/files/iterative_tensor_voting_for_pavement_crack_extraction_using_mobile_laser_scanning_data.pdf).

These methods cannot directly replace LTPP map recognition because they
require calibrated imagery, depth, or point-cloud data that the current
carrier does not provide.

### Physical sensor monitoring

For active structural monitoring rather than surface-map interpretation, two
important families are:

- **Acoustic emission (AE):** denoise or decompose the signal, estimate arrival
  times, then use TDOA and a wave-speed model to localize crack events. Sensor
  layout and wave-speed assumptions strongly affect localization error. Source:
  [improved AE source localization](https://doi.org/10.1016/j.apacoust.2024.110093).
- **Distributed fiber-optic sensing (DFOS):** detect spatially distributed
  strain anomalies and infer crack appearance, location, and opening-related
  changes. Machine-learning-based interpretation has been demonstrated for
  automatic crack localization and quantification. Source:
  [DFOS crack monitoring](https://doi.org/10.1002/suco.202300100).

AE and DFOS are valuable for structural-health monitoring, but they are not
substitutes for recognizing crack strokes in the current LTPP distress-map
carrier.

### Candidate route for the current LTPP track

The most defensible next algorithmic route is a document-aware, multi-task,
topology-aware recognizer rather than a simple switch to YOLO, SAM, or a larger
generic U-Net:

```text
hand-drawn form parser
        |
grid / frame / boundary / text / arrow / patch masks
        |
multi-task crack segmentation
  + crack mask
  + centerline
  + endpoint / junction
  + non-crack structure masks
        |
skeletonization and crack graph extraction
        |
length, orientation, connectivity, and crack-family metrics
```

The minimum decisive comparison should keep the frozen section-level LOSO
split and compare the existing baseline against this structured route. It
should report not only pixel precision, recall, F1, and IoU, but also
centerline distance, endpoint recall, branch/connectivity error, geometry
length error, and false positives by confounder class. Temporal change
monitoring should remain a later stage, conditional on an independently
qualified spatial-registration carrier.

## Implications for the LTPP distress-map carrier

The LTPP assets are scanned, hand-drawn distress maps rather than ordinary
vehicle-camera pavement photographs. They contain printed grids, frame and lane
boundaries, arrows, handwritten text and numbers, WIM or patch boxes, coloured
and black strokes, and surveyor/date style variation. A generic road-photo
YOLO, DeepCrack, or SAM model may classify grid lines, handwriting, and road
boundaries as cracks.

The appropriate candidate pipeline is therefore document-graphics parsing plus
crack segmentation:

```text
raw distress map
      |
separate grid, text, dimensions, boundaries, symbols, and patch regions
      |
segment crack strokes
      |
skeletonize and extract connected components
      |
measure length, orientation, branches, and endpoints
      |
register repeated maps
      |
classify retained, extended, initiated, and apparently disappeared geometry
```

The original 06-1253 pilot contained nine independently annotated maps. The
current canonical asset has expanded beyond that pilot: the frozen adjudicated
package contains 37 states, 249 total geometries, and 232 crack geometries. The
adjudicated package, not a raw AI overlay, is the only authorized gold label.

Recommended recognition principles are:

- treat raw AI output as a candidate or pseudo-label, never ground truth;
- keep a human-corrected adjudicated reference and preserve uncertainty;
- compare deterministic document-processing, a light segmentation model, and
  a foundation-model-assisted annotation route under the same frozen split;
- split by complete physical section or complete map, never random crops from
  the same map across train and test;
- evaluate centerline placement, length, endpoints, connectivity, and
  confounder-specific false positives in addition to pixel F1/IoU; and
- retain human adjudication because missing a thin new crack can be more
  consequential than a two-pixel boundary discrepancy.

## Relation to current project results

The existing six-section scalar benchmark is stricter than ordinary random
cross-validation. Its negative enriched-input result does not mean all crack
prediction is impossible. It means that, in the frozen six-section,
30-transition sensitivity protocol, traffic, structure, and FWD did not show
stable incremental value beyond the registered source geometry and climate.

The current spatial-registration track independently concluded that the
existing carrier is not qualified for confirmatory two-dimensional
position/tip forecasting. Crack recognition may improve label-production
efficiency, but it cannot by itself repair an unqualified cross-date coordinate
carrier or authorize a future-geometry claim.
