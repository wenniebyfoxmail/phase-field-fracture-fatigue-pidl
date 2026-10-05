#!/usr/bin/env python3
"""Apply the minimal fail-closed GRIPHFiTH patch for S04-E011.

The input must be the exact extracted cdf4e337 source archive.  Every textual
replacement has an exact occurrence count so source drift fails before write.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def replace_exact(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{path}: expected {count} occurrences, found {actual}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()

    abaqus = root / "Sources/+specimen/+external/abaqus_import.m"
    capture = root / "Sources/+phase_field/+audit/capture_peak_state.m"
    postcommit = root / "Sources/+phase_field/+audit/capture_post_commit_state.m"
    simplex_quad = root / "Sources/+phase_field/+fem/+quadrature/simplex_quad.m"
    solver = root / "Scripts/fatigue_fracture/solve_fatigue_fracture.m"
    runner = root / "Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m"
    for path in (abaqus, capture, postcommit, simplex_quad, solver, runner):
        if not path.is_file():
            raise FileNotFoundError(path)

    replace_exact(abaqus, "nel = 4;                    %number of nodes per element",
                  "nel = size(elem,2);         % number of nodes per element (Q4 or T3)")
    replace_exact(abaqus, "elem = round(elem,4);\nnode = round(node,4);\n", "")
    replace_exact(
        capture,
        "if numel(history_size) ~= 3 || history_size(2) ~= 4 || history_size(3) ~= 4\n"
        "            error('phase_field:audit:InvalidHistoryShape', ...\n"
        "                'history_vars_old must have shape [num_elem, 4, 4].');",
        "if numel(history_size) ~= 3 || ~ismember(history_size(2), [3 4]) || history_size(3) ~= 4\n"
        "            error('phase_field:audit:InvalidHistoryShape', ...\n"
        "                'history_vars_old must have shape [num_elem, 3|4, 4].');",
    )

    old_filename = "sprintf('cycle_%04d_peak_native_q4.mat', SOL_CYCL_VAR.n_cycle)"
    new_filename = (
        "sprintf('cycle_%04d_peak_%s.mat', SOL_CYCL_VAR.n_cycle, "
        "char(native_q4_capture.label))"
    )
    replace_exact(solver, old_filename, new_filename, count=2)
    replace_exact(solver, "sys.MESH.elem(:,1:4)",
                  "sys.MESH.elem(:,1:sys.MESH.nel)")
    replace_exact(solver, "phase_field.audit.q4_strain_at_gauss_points(",
                  "phase_field.audit.strain_at_gauss_points(")
    replace_exact(solver, "'connectivity_q4', request28_connectivity,",
                  "'connectivity', request28_connectivity,")

    replace_exact(
        simplex_quad,
        "phase_field.fem.quadrature.2D_simplex(quad_order)",
        "phase_field.fem.quadrature.simplex_2d(quad_order)",
    )
    replace_exact(
        simplex_quad,
        "[gauss_pts, gauss_weights] = phase_field.fem.quadrature.3D_simplex(quad_order);",
        "error('phase_field:quadrature:E011UnsupportedDimension', ...\n"
        "            'S04-E011 supports two-dimensional simplex quadrature only.');",
    )

    tools_dir = Path(__file__).resolve().parent
    (root / "Sources/+phase_field/+fem/+quadrature/simplex_2d.m").write_bytes(
        (tools_dir / "simplex_2d.m").read_bytes()
    )
    (root / "Sources/+phase_field/+audit/strain_at_gauss_points.m").write_bytes(
        (tools_dir / "strain_at_gauss_points.m").read_bytes()
    )
    postcommit.write_bytes((tools_dir / "capture_post_commit_state.m").read_bytes())

    insertion_anchor = "run(fullfile(repo_root, 'Scripts', 'brittle_fracture', 'INPUT_SENS_tensile.m'));\n"
    insertion = insertion_anchor + """
if ~isfield(options, 'mesh_file') || ~isfile(options.mesh_file)
    invalidConfig('options.mesh_file must name an existing Abaqus mesh.');
end
if ~isfield(options, 'topology') || ~ismember(string(options.topology), ["q4" "t3"])
    invalidConfig('options.topology must be q4 or t3.');
end
[MESH, GEOM] = specimen.external.abaqus_import(options.mesh_file, 't', 1.0);
mesh_tol = 1e-12;
NODESET = struct();
NODESET.top_edge = find(abs(MESH.node(:,2) - max(MESH.node(:,2))) <= mesh_tol);
NODESET.bot_edge = find(abs(MESH.node(:,2) - min(MESH.node(:,2))) <= mesh_tol);
NODESET.crack = find(abs(MESH.node(:,2)) <= mesh_tol & MESH.node(:,1) <= mesh_tol);
if isempty(NODESET.top_edge) || isempty(NODESET.bot_edge) || isempty(NODESET.crack)
    invalidConfig('Imported mesh is missing top, bottom, or crack nodes.');
end
NODE_BOUNDARIES = phase_field.fem.bc.set_boundaries( ...
    'fix_X', [NODESET.bot_edge; NODESET.top_edge], ...
    'fix_Y', NODESET.bot_edge, 'disp_Y', NODESET.top_edge, ...
    'non_hom_pf', NODESET.crack);
DOFS = phase_field.init.dofs(MESH, NODE_BOUNDARIES);
if string(options.topology) == "q4"
    if MESH.nel ~= 4
        invalidConfig('Q4 arm requires four-node connectivity.');
    end
    e011_elem_type = phase_field.init.ElementType.QUAD4;
    e011_label = "q4";
else
    if MESH.nel ~= 3
        invalidConfig('T3 arm requires three-node connectivity.');
    end
    e011_elem_type = phase_field.init.ElementType.TRIA3;
    e011_label = "t3";
end
QUADRATURE = phase_field.init.quadrature(MESH.dim, ...
    'elem_type', e011_elem_type, 'order', 2);
"""
    replace_exact(runner, insertion_anchor, insertion)

    replace_exact(
        runner,
        "'staging_dir', fullfile(work_dir, 'native_q4_staging'));",
        "'staging_dir', fullfile(work_dir, 'native_gp_staging'), ...\n"
        "    'label', e011_label);",
    )
    replace_exact(runner, "mkdir(native_q4_capture.staging_dir);",
                  "mkdir(native_q4_capture.staging_dir);")
    replace_exact(
        runner,
        "sprintf('cycle_%04d_peak_native_q4.mat', cfg.requested_cycles(index))",
        "sprintf('cycle_%04d_peak_%s.mat', cfg.requested_cycles(index), char(e011_label))",
    )
    replace_exact(
        runner,
        "metadata.output_identity = cfg.output_identity;",
        "metadata.output_identity = cfg.output_identity;\n"
        "metadata.topology = string(['arity' num2str(sys.MESH.nel)]);\n"
        "metadata.element_arity = sys.MESH.nel;\n"
        "metadata.quadrature_order = sys.QUADRATURE.order;\n"
        "metadata.num_gauss_points = sys.QUADRATURE.num_gauss_pts;",
    )

    launch_src = Path(__file__).with_name("run_s04_e011_fem_arm.m")
    launch_dst = root / "Scripts/fatigue_fracture/run_s04_e011_fem_arm.m"
    launch_dst.write_bytes(launch_src.read_bytes())

    print("S04-E011 FEM patch applied")
    patched_files = (
        abaqus, capture, postcommit, simplex_quad, solver, runner, launch_dst,
        root / "Sources/+phase_field/+fem/+quadrature/simplex_2d.m",
        root / "Sources/+phase_field/+audit/strain_at_gauss_points.m",
    )
    for path in patched_files:
        print(f"{sha256(path)}  {path.relative_to(root)}")


if __name__ == "__main__":
    main()
