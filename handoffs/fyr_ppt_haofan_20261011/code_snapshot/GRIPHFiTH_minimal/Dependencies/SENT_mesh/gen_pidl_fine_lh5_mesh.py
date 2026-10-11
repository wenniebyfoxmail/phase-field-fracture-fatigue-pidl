"""
Generate FEM-1 PIDL-fine SENT mesh for mesh convergence check (2026-05-05).

Goal: same 1×1 mm SENT geometry as PIDL series, but ℓ/h_tip = 5 (h_tip = 0.002 mm)
      vs the coarse Abaqus baseline (h_tip ≈ 0.01 mm, ℓ/h ≈ 1).

Only h_tip differs from Carrara mesh generator — everything else (geometry, slit,
notch coordinates, recombination algorithm) is identical to gen_carrara_quad_mesh.py.
"""
import gmsh

OUT = r"C:/Users/xw436/GRIPHFiTH/Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp"

# PIDL-fine mesh sizes (mm; ℓ=0.01, ℓ/h_tip=5 ⇒ h_tip=0.002)
h_global = 0.05    # bulk
h_zone   = 0.005   # extended crack zone
h_tip    = 0.002   # crack tip propagation corridor (ℓ/5)

gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("SENT_pidl_fine")

# Same SENT geometry as Carrara/Castillon: 1×1 mm, notch slit from x=-0.5 to x=0
P1 = gmsh.model.geo.addPoint(-0.5, -0.5, 0, h_global)
P2 = gmsh.model.geo.addPoint( 0.5, -0.5, 0, h_global)
P3 = gmsh.model.geo.addPoint( 0.5,  0.5, 0, h_global)
P4 = gmsh.model.geo.addPoint(-0.5,  0.5, 0, h_global)
P5 = gmsh.model.geo.addPoint(-0.5,  0.001, 0, h_global)
P6 = gmsh.model.geo.addPoint(-0.5, -0.001, 0, h_global)
P7 = gmsh.model.geo.addPoint( 0.0,  0.0,   0, h_tip)

L1 = gmsh.model.geo.addLine(P1, P2)
L2 = gmsh.model.geo.addLine(P2, P3)
L3 = gmsh.model.geo.addLine(P3, P4)
L4 = gmsh.model.geo.addLine(P4, P5)
L5 = gmsh.model.geo.addLine(P5, P7)
L6 = gmsh.model.geo.addLine(P7, P6)
L7 = gmsh.model.geo.addLine(P6, P1)

CL = gmsh.model.geo.addCurveLoop([L1, L2, L3, L4, L5, L6, L7])
S  = gmsh.model.geo.addPlaneSurface([CL])
gmsh.model.geo.synchronize()

# Tip corridor
F6 = gmsh.model.mesh.field.add("Box")
gmsh.model.mesh.field.setNumber(F6, "VIn",  h_tip)
gmsh.model.mesh.field.setNumber(F6, "VOut", h_global)
gmsh.model.mesh.field.setNumber(F6, "XMin", -0.05)
gmsh.model.mesh.field.setNumber(F6, "XMax",  0.5)
gmsh.model.mesh.field.setNumber(F6, "YMin", -0.015)
gmsh.model.mesh.field.setNumber(F6, "YMax",  0.015)

# Extended zone
F7 = gmsh.model.mesh.field.add("Box")
gmsh.model.mesh.field.setNumber(F7, "VIn",  h_zone)
gmsh.model.mesh.field.setNumber(F7, "VOut", h_global)
gmsh.model.mesh.field.setNumber(F7, "XMin", -0.15)
gmsh.model.mesh.field.setNumber(F7, "XMax",  0.5)
gmsh.model.mesh.field.setNumber(F7, "YMin", -0.1)
gmsh.model.mesh.field.setNumber(F7, "YMax",  0.1)

F8 = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(F8, "FieldsList", [F6, F7])
gmsh.model.mesh.field.setAsBackgroundMesh(F8)

gmsh.option.setNumber("Mesh.RecombineAll", 1)
gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 3)
gmsh.option.setNumber("Mesh.Algorithm", 11)
gmsh.option.setNumber("Mesh.ElementOrder", 1)
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.QuadqsTopologyOptimizationMethods", 100)

gmsh.model.mesh.generate(2)
gmsh.model.mesh.recombine()
gmsh.model.mesh.optimize("Laplace2D", force=True, niter=5)
gmsh.model.mesh.optimize("Relocate2D", force=True, niter=5)

elem_types, elem_tags, _ = gmsh.model.mesh.getElements(2)
total_quads = 0
for et, etags in zip(elem_types, elem_tags):
    name = gmsh.model.mesh.getElementProperties(et)[0]
    print(f"  type={et} ({name}): {len(etags)} elements")
    if et == 3: total_quads = len(etags)
n_nodes = len(gmsh.model.mesh.getNodes()[1].reshape(-1, 3))
print(f"  total: {n_nodes} nodes, {total_quads} quads")

gmsh.write(OUT)
gmsh.finalize()

with open(OUT, 'r') as f: lines = f.readlines()
out, in_node = [], False
for L in lines:
    Ls = L.strip()
    if Ls.startswith('*'):
        in_node = (Ls.upper().startswith('*NODE'))
        out.append(L); continue
    if in_node:
        parts = [p.strip() for p in L.strip().split(',')]
        if len(parts) == 4: out.append(', '.join(parts[:3]) + '\n')
        else: out.append(L)
    else: out.append(L)
with open(OUT, 'w') as f: f.writelines(out)

nodes_set, quad_nodes = set(), set()
mode = None
with open(OUT) as f:
    for L in f:
        Ls = L.strip()
        if Ls.startswith('*'):
            U = Ls.upper()
            if U.startswith('*NODE'): mode='node'
            elif U.startswith('*ELEMENT') and 'CPS4' in U: mode='quad'
            else: mode='other'
            continue
        if not Ls: continue
        parts = [p.strip() for p in Ls.split(',')]
        if mode=='node' and len(parts)>=3: nodes_set.add(int(parts[0]))
        elif mode=='quad' and len(parts)==5:
            for p in parts[1:5]: quad_nodes.add(int(p))
orphans = nodes_set - quad_nodes
print(f"orphan check: {len(orphans)} orphan(s)")
if orphans: print(f"  orphan IDs: {sorted(orphans)[:5]}")
print(f"Wrote {OUT}")
