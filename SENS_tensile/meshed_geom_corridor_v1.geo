// meshed_geom_corridor_v1.geo
// α-1 mesh-adaptive Variant A — pre-refined corridor along propagation path
// per design_alpha1_mesh_adaptive_apr27.md
//
// Domain:    [-L, L] × [-L, L]   with  L = 0.5
// Precrack:  x ∈ [-L, 0], y = 0  (NOT modelled as seam — initial α field
//                                  via hist_alpha_init in PIDL pipeline)
// Refined corridor: x ∈ [0, x_max], |y| < y_corridor   with element size h_c
// Background: element size h_f
//
// Sizing rationale:
//   h_c = ℓ₀ / 2 = 0.005   → matches FEM tip refinement (per α-0)
//   h_f = 0.02              → ~4× ℓ₀, same as legacy meshed_geom2.msh
//   y_corridor = 0.04       → 4ℓ₀ (covers the damage band per α-0 PZ_2ℓ₀ ≈ 2ℓ₀)
//   x_max = L = 0.5         → cover full propagation path
//
// Expected element count: ~120k (vs 67k legacy).

SetFactory("Built-in");

// ==== Geometry ====
L          = 0.5;
x_max_corr = 0.5;     // corridor extends to right edge
y_corridor = 0.04;
h_c        = 0.005;
h_f        = 0.02;

// Domain corners (h_f at the far field)
Point(1) = {-L, -L, 0, h_f};
Point(2) = { L, -L, 0, h_f};
Point(3) = { L,  L, 0, h_f};
Point(4) = {-L,  L, 0, h_f};

// Outer rectangle
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// ==== Size field — Box: h_c inside corridor, h_f elsewhere, smooth ramp ====
Field[1] = Box;
Field[1].VIn  = h_c;
Field[1].VOut = h_f;
Field[1].XMin = 0.0;
Field[1].XMax = x_max_corr;
Field[1].YMin = -y_corridor;
Field[1].YMax =  y_corridor;
Field[1].Thickness = 0.04;   // grade region OUTSIDE box (~ corridor width itself)

// ==== Distance field for tip seed (extra refinement at the moving tip path) ====
// Adds local grading around (0,0) → (L,0) line so even within corridor
// elements stay well-shaped near the tip ridge.
Point(10) = {0.0, 0.0, 0, h_c};
Point(11) = {x_max_corr, 0.0, 0, h_c};
Line(10) = {10, 11};
// Note: line 10 is geometric refinement reference; not part of the surface.

Field[2] = Distance;
Field[2].PointsList = {10, 11};
Field[2].CurvesList = {10};
Field[2].Sampling = 80;

Field[3] = Threshold;
Field[3].InField  = 2;
Field[3].SizeMin  = h_c;
Field[3].SizeMax  = h_f;
Field[3].DistMin  = 0.0;
Field[3].DistMax  = 0.10;     // ramp OUTSIDE distance 0.1 from tip line

// Take the minimum of the two fields (whichever asks for finer h)
Field[4] = Min;
Field[4].FieldsList = {1, 3};
Background Field = 4;

// ==== Mesh settings ====
// CharacteristicLengthFactor is the global multiplier (default 1).
// Keep MeshSizeFromPoints = 1 (default) so corner h_f acts as upper bound.
// Background field overrides where it asks for finer h.
Mesh.MeshSizeFromCurvature = 0;
Mesh.MeshSizeExtendFromBoundary = 1;
Mesh.MeshSizeFromPoints = 1;
Mesh.MeshSizeFactor = 1.0;
Mesh.Algorithm = 6;                         // Frontal-Delaunay 2D
Mesh.MshFileVersion = 4.1;                  // match legacy meshed_geom2.msh format
Mesh 2;
Save "meshed_geom_corridor_v1.msh";
