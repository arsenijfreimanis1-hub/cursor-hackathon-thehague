#!/usr/bin/env python3
"""
BMW E46 2.8L (M52TU) drift exhaust — parametric 3D model generator.

Layout: 6-2-1 collectors → dual primaries → X-pipe crossover → valved
straight-through mufflers → angled dual tips.

Tuned for a deep, menacing tone: 3" (76.2 mm) main piping, X-pipe scavenging,
resonator-delete mid section, perforated straight-through mufflers with
butterfly bypass valves (open = drift mode).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

# ---------------------------------------------------------------------------
# Parameters — BMW E46 328i / 2.8L M52TU drift exhaust
# ---------------------------------------------------------------------------

@dataclass
class ExhaustSpec:
    """All dimensions in millimetres unless noted."""

    # Primary / collector
    runner_od: float = 50.8          # 2.0" header runners
    runner_wall: float = 2.0
    collector_merge_length: float = 120.0
    primary_od: float = 76.2         # 3.0" — deep tone, good flow for 2.8L
    primary_wall: float = 2.5

    # X-pipe
    x_cross_angle_deg: float = 55.0
    x_section_length: float = 280.0

    # Valves (butterfly bypass)
    valve_body_od: float = 95.0
    valve_disc_thickness: float = 6.0
    valve_actuator_od: float = 52.0
    valve_actuator_length: float = 68.0

    # Mufflers — straight-through perforated core (drift)
    muffler_length: float = 320.0
    muffler_od: float = 130.0
    muffler_core_od: float = 76.2

    # Tips — turned-out drift style
    tip_length: float = 140.0
    tip_od: float = 101.6          # 4"
    tip_angle_deg: float = 18.0

    # Layout
    bank_spacing: float = 380.0      # L/R collector centre distance
    runner_spacing: float = 62.0
    flange_od: float = 88.0
    flange_thickness: float = 10.0

    pipe_segments: int = 12
    mesh_sections: int = 24


SPEC = ExhaustSpec()
OUT_DIR = Path(__file__).resolve().parent / "output"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _v(*coords: float) -> np.ndarray:
    return np.array(coords, dtype=float)


def pipe_between(
    start: np.ndarray,
    end: np.ndarray,
    od: float,
    spec: ExhaustSpec,
    color: list[float] | None = None,
) -> trimesh.Trimesh:
    """Hollow-ish pipe represented as solid cylinder (visualisation mesh)."""
    direction = end - start
    length = float(np.linalg.norm(direction))
    if length < 1e-6:
        return trimesh.Trimesh()

    radius = od / 2.0
    cyl = trimesh.creation.cylinder(
        radius=radius,
        height=length,
        sections=spec.mesh_sections,
    )
    # Default cylinder aligned +Z; rotate to direction
    z_axis = _v(0, 0, 1)
    direction_n = direction / length
    rot = trimesh.geometry.align_vectors(z_axis, direction_n)
    cyl.apply_transform(rot)
    cyl.apply_translation((start + end) / 2.0)
    if color:
        cyl.visual.face_colors = color
    return cyl


def pipe_along_path(
    points: list[np.ndarray],
    od: float,
    spec: ExhaustSpec,
    color: list[float] | None = None,
) -> list[trimesh.Trimesh]:
    meshes: list[trimesh.Trimesh] = []
    for i in range(len(points) - 1):
        meshes.append(pipe_between(points[i], points[i + 1], od, spec, color))
    return meshes


def sphere_joint(
    centre: np.ndarray,
    od: float,
    spec: ExhaustSpec,
    color: list[float] | None = None,
) -> trimesh.Trimesh:
    sph = trimesh.creation.icosphere(
        subdivisions=2,
        radius=od / 2.0,
    )
    sph.apply_translation(centre)
    if color:
        sph.visual.face_colors = color
    return sph


def flange_at(
    centre: np.ndarray,
    normal: np.ndarray,
    spec: ExhaustSpec,
    color: list[float] | None = None,
) -> trimesh.Trimesh:
    disc = trimesh.creation.cylinder(
        radius=spec.flange_od / 2.0,
        height=spec.flange_thickness,
        sections=spec.mesh_sections,
    )
    z_axis = _v(0, 0, 1)
    n = normal / np.linalg.norm(normal)
    rot = trimesh.geometry.align_vectors(z_axis, n)
    disc.apply_transform(rot)
    disc.apply_translation(centre)
    if color:
        disc.visual.face_colors = color
    return disc


def butterfly_valve(
    centre: np.ndarray,
    axis: np.ndarray,
    flow_axis: np.ndarray,
    spec: ExhaustSpec,
    open_angle_deg: float = 85.0,
    color_body: list[float] | None = None,
    color_disc: list[float] | None = None,
) -> list[trimesh.Trimesh]:
    """Butterfly valve assembly on pipe centreline."""
    parts: list[trimesh.Trimesh] = []

    body = trimesh.creation.cylinder(
        radius=spec.valve_body_od / 2.0,
        height=spec.valve_body_od * 0.7,
        sections=spec.mesh_sections,
    )
    fa = flow_axis / np.linalg.norm(flow_axis)
    rot = trimesh.geometry.align_vectors(_v(0, 0, 1), fa)
    body.apply_transform(rot)
    body.apply_translation(centre)
    if color_body:
        body.visual.face_colors = color_body
    parts.append(body)

    # Disc — rotated open for drift mode
    disc = trimesh.creation.cylinder(
        radius=spec.primary_od / 2.0 - 1.0,
        height=spec.valve_disc_thickness,
        sections=spec.mesh_sections,
    )
    aa = axis / np.linalg.norm(axis)
    rot_d = trimesh.geometry.align_vectors(_v(0, 0, 1), aa)
    disc.apply_transform(rot_d)
    r_open = Rotation.from_rotvec(np.radians(open_angle_deg) * fa).as_matrix()
    disc.apply_transform(np.eye(4))
    disc.vertices = disc.vertices @ r_open.T
    disc.apply_translation(centre)
    if color_disc:
        disc.visual.face_colors = color_disc
    parts.append(disc)

    # Actuator motor on top
    actuator = trimesh.creation.cylinder(
        radius=spec.valve_actuator_od / 2.0,
        height=spec.valve_actuator_length,
        sections=spec.mesh_sections,
    )
    up = np.cross(fa, aa)
    up = up / np.linalg.norm(up)
    rot_a = trimesh.geometry.align_vectors(_v(0, 0, 1), up)
    actuator.apply_transform(rot_a)
    actuator.apply_translation(centre + up * (spec.valve_body_od / 2.0 + spec.valve_actuator_length / 2.0))
    if color_body:
        actuator.visual.face_colors = color_body
    parts.append(actuator)

    return parts


def straight_through_muffler(
    start: np.ndarray,
    end: np.ndarray,
    spec: ExhaustSpec,
    shell_color: list[float] | None = None,
    core_color: list[float] | None = None,
) -> list[trimesh.Trimesh]:
    direction = end - start
    length = float(np.linalg.norm(direction))
    centre = (start + end) / 2.0
    fa = direction / length
    parts: list[trimesh.Trimesh] = []

    shell = trimesh.creation.cylinder(
        radius=spec.muffler_od / 2.0,
        height=length,
        sections=spec.mesh_sections,
    )
    rot = trimesh.geometry.align_vectors(_v(0, 0, 1), fa)
    shell.apply_transform(rot)
    shell.apply_translation(centre)
    if shell_color:
        shell.visual.face_colors = shell_color
    parts.append(shell)

    core = trimesh.creation.cylinder(
        radius=spec.muffler_core_od / 2.0,
        height=length * 0.92,
        sections=spec.mesh_sections,
    )
    core.apply_transform(rot)
    core.apply_translation(centre)
    if core_color:
        core.visual.face_colors = core_color
    parts.append(core)

    # End caps (visual)
    for cap_centre in (start, end):
        cap = trimesh.creation.cylinder(
            radius=spec.muffler_od / 2.0,
            height=4.0,
            sections=spec.mesh_sections,
        )
        cap.apply_transform(rot)
        cap.apply_translation(cap_centre)
        if shell_color:
            cap.visual.face_colors = shell_color
        parts.append(cap)

    return parts


def exhaust_tip(
    start: np.ndarray,
    direction: np.ndarray,
    side_sign: float,
    spec: ExhaustSpec,
    color: list[float] | None = None,
) -> list[trimesh.Trimesh]:
    """Angled rolled tip — drift style, turned outward."""
    d = direction / np.linalg.norm(direction)
    # Tip bends outward (Y) and slightly down
    out = _v(0, side_sign, 0)
    bend_dir = d * 0.85 + out * 0.35
    bend_dir = bend_dir / np.linalg.norm(bend_dir)
    end = start + bend_dir * spec.tip_length

    pipe = pipe_between(start, end, spec.tip_od, spec, color)
    # Cut-back inner sleeve
    inner = pipe_between(
        start + d * 15,
        end - bend_dir * 8,
        spec.tip_od - 6.0,
        spec,
        [40, 40, 40, 255],
    )
    return [pipe, inner]


# ---------------------------------------------------------------------------
# Exhaust assembly
# ---------------------------------------------------------------------------

# Colour palette (RGBA 0-255)
C_STAINLESS = [192, 198, 204, 255]
C_TI_TIP = [148, 152, 158, 255]
C_VALVE = [72, 76, 82, 255]
C_VALVE_DISC = [210, 175, 55, 255]   # brass disc accent
C_MUFFLER = [110, 112, 118, 255]
C_CORE = [55, 58, 62, 255]
C_FLANGE = [90, 92, 96, 255]


def build_header_runners(bank_y: float, spec: ExhaustSpec) -> list[trimesh.Trimesh]:
    """Three header runners per bank merging toward collector."""
    meshes: list[trimesh.Trimesh] = []
    offsets = [-spec.runner_spacing, 0.0, spec.runner_spacing]
    collector = _v(spec.collector_merge_length, bank_y, 0)

    for i, z_off in enumerate(offsets):
        start = _v(-40.0, bank_y + z_off * 0.3, z_off)
        mid = _v(spec.collector_merge_length * 0.45, bank_y + z_off * 0.15, z_off * 0.4)
        meshes.extend(pipe_along_path([start, mid, collector], spec.runner_od, spec, C_STAINLESS))
        meshes.append(sphere_joint(collector, spec.runner_od * 1.1, spec, C_STAINLESS))

    meshes.append(
        flange_at(
            _v(-45.0, bank_y, 0),
            _v(-1, 0, 0),
            spec,
            C_FLANGE,
        )
    )
    return meshes


def build_primary_to_x(bank_y: float, side: str, spec: ExhaustSpec) -> tuple[list[trimesh.Trimesh], np.ndarray, np.ndarray]:
    """Primary pipe from collector through X-pipe section."""
    meshes: list[trimesh.Trimesh] = []
    sign = 1.0 if side == "left" else -1.0

    collector = _v(spec.collector_merge_length, bank_y, 0)
    x_start = _v(spec.collector_merge_length + 180.0, bank_y, 0)
    x_mid = _v(
        spec.collector_merge_length + 180.0 + spec.x_section_length * 0.5,
        bank_y * 0.35,  # converge toward centre for X
        sign * 25.0,
    )
    x_end = _v(
        spec.collector_merge_length + 180.0 + spec.x_section_length,
        bank_y,
        0,
    )

    path = [collector, x_start, x_mid, x_end]
    meshes.extend(pipe_along_path(path, spec.primary_od, spec, C_STAINLESS))
    for pt in path[1:]:
        meshes.append(sphere_joint(pt, spec.primary_od * 0.55, spec, C_STAINLESS))

    return meshes, x_start, x_end


def build_x_pipe(spec: ExhaustSpec) -> list[trimesh.Trimesh]:
    """X-pipe crossover — the heart of the deep scavenged tone."""
    meshes: list[trimesh.Trimesh] = []
    half = spec.bank_spacing / 2.0
    x0 = spec.collector_merge_length + 180.0 + spec.x_section_length * 0.45

    # Crossing pipes at ~55° — classic deep burble geometry
    angle = math.radians(spec.x_cross_angle_deg)
    length = spec.x_section_length * 0.65

    left_high = _v(x0, half, 20.0)
    right_low = _v(x0 + length * math.cos(angle), -half, -20.0)
    right_high = _v(x0, -half, 20.0)
    left_low = _v(x0 + length * math.cos(angle), half, -20.0)

    meshes.extend(pipe_along_path([left_high, right_low], spec.primary_od, spec, C_STAINLESS))
    meshes.extend(pipe_along_path([right_high, left_low], spec.primary_od, spec, C_STAINLESS))

    # X-centre merge bulb
    centre = _v(x0 + length * math.cos(angle) * 0.5, 0, 0)
    meshes.append(sphere_joint(centre, spec.primary_od * 0.85, spec, C_STAINLESS))

    return meshes


def build_rear_section(bank_y: float, x_end: np.ndarray, side: str, spec: ExhaustSpec) -> list[trimesh.Trimesh]:
    meshes: list[trimesh.Trimesh] = []
    sign = 1.0 if side == "left" else -1.0

    valve_pos = x_end + _v(80.0, 0, 0)
    muffler_start = valve_pos + _v(spec.valve_body_od * 0.5 + 30.0, 0, 0)
    muffler_end = muffler_start + _v(spec.muffler_length, 0, 0)
    tip_start = muffler_end + _v(40.0, 0, 0)

    meshes.extend(pipe_along_path([x_end, valve_pos], spec.primary_od, spec, C_STAINLESS))

    flow = _v(1, 0, 0)
    axis = _v(0, 0, 1)
    meshes.extend(
        butterfly_valve(
            valve_pos,
            axis,
            flow,
            spec,
            open_angle_deg=88.0,  # drift mode — wide open
            color_body=C_VALVE,
            color_disc=C_VALVE_DISC,
        )
    )

    meshes.extend(pipe_along_path([valve_pos, muffler_start], spec.primary_od, spec, C_STAINLESS))
    meshes.extend(straight_through_muffler(muffler_start, muffler_end, spec, C_MUFFLER, C_CORE))
    meshes.extend(exhaust_tip(tip_start, _v(1, 0, 0), sign, spec, C_TI_TIP))

    return meshes


def build_exhaust(spec: ExhaustSpec = SPEC) -> trimesh.Scene:
    scene = trimesh.Scene()
    half = spec.bank_spacing / 2.0

    for bank_y, side in ((half, "left"), (-half, "right")):
        for mesh in build_header_runners(bank_y, spec):
            scene.add_geometry(mesh)

        primary_meshes, _, x_end = build_primary_to_x(bank_y, side, spec)
        for mesh in primary_meshes:
            scene.add_geometry(mesh)

        for mesh in build_rear_section(bank_y, x_end, side, spec):
            scene.add_geometry(mesh)

    for mesh in build_x_pipe(spec):
        scene.add_geometry(mesh)

    return scene


def export_all(scene: trimesh.Scene, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    combined = trimesh.util.concatenate(
        [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
    )

    stl_path = out_dir / "bmw_e46_28l_drift_exhaust.stl"
    obj_path = out_dir / "bmw_e46_28l_drift_exhaust.obj"
    glb_path = out_dir / "bmw_e46_28l_drift_exhaust.glb"

    combined.export(stl_path)
    combined.export(obj_path)
    scene.export(glb_path)

    manifest = {
        "name": "BMW E46 2.8L M52TU Drift Exhaust — Valved X-Pipe",
        "engine": "M52TU 2.8L inline-6",
        "application": "Drift — deep / menacing tone",
        "main_pipe_inches": spec_inches(SPEC.primary_od),
        "runner_inches": spec_inches(SPEC.runner_od),
        "tip_inches": spec_inches(SPEC.tip_od),
        "x_pipe_angle_deg": SPEC.x_cross_angle_deg,
        "valve_mode": "open (drift)",
        "files": {
            "stl": stl_path.name,
            "obj": obj_path.name,
            "glb": glb_path.name,
        },
        "bounds_mm": {
            "x": list(combined.bounds[0]),
            "y": list(combined.bounds[1]),
        },
        "triangle_count": len(combined.faces),
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return manifest


def spec_inches(mm: float) -> float:
    return round(mm / 25.4, 2)


def main() -> None:
    print("Building BMW E46 2.8L drift exhaust model…")
    scene = build_exhaust()
    manifest = export_all(scene, OUT_DIR)
    print(f"Exported to {OUT_DIR}")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
