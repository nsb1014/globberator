"""Preview pose-generated limb surfaces and inspect torso depth through motion.

Run from the checkout root with Blender:
    blender -b --python-exit-code 1 -P tools/tests/preview_swept_joint.py -- \
        examples/minotaur.json arm out/swept-minotaur

Pass --motion walk or --motion run for side views of a gait cycle. For the
minotaur, --torso-stations 0 1 3 measures the pelvis, waist and upper chest.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from scipy.sparse import csr_matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_articulated_fixture import ArticulatedBuilder

from polyforge import builder, finish, kit, recipe, render
from polyforge.animator import Animator, write_pose


class SweptBuilder(ArticulatedBuilder):
    def __init__(self, source, selection):
        super().__init__(source, selection)
        self.soft_tips = []

    def resolve_limbs(self, spine):
        super().resolve_limbs(spine)
        sides = {limb["uid"]: limb["theta"] for limb in self.recipe["limbs"]}
        for limb in self.limbs:
            if limb["uid"] == self.selection and "root_normal" not in limb:
                normal = self.body_surface(spine, limb["u"], sides[limb["uid"]])["n"].copy()
                if limb["mirrored"]:
                    normal.x = -normal.x
                limb["root_normal"] = normal

    def limb_prim(self, limb):
        if limb["uid"] != self.selection:
            super().limb_prim(limb)

    def place_tips(self):
        limbs = self.limbs
        try:
            for limb in limbs:
                self.limbs = [limb]
                start = len(self.skin_prims)
                builder.Builder.place_tips(self)
                if limb["uid"] == self.selection:
                    bone = limb["bones"][-1]
                    for vertices, faces in self.skin_prims[start:]:
                        self.soft_tips.append((bone, vertices, faces))
                    del self.skin_prims[start:]
        finally:
            self.limbs = limbs


def swept_limb(anim, limb):
    """Fit one rounded tube through the solved joints, then cap both ends."""
    joints = [anim.G[bone].o for bone in limb["bones"]]
    radii = limb["radii"]
    root = joints[0]
    parent = anim.G[limb["parent_bone"]]
    outward = (parent.b @ Vector(limb["root_normal"])).normalized()
    first = joints[1] - root
    start_radius = radii[0]
    points = [root - outward * start_radius * 1.52, root - outward * start_radius * .62]
    sizes = [.71 * start_radius, 1.04 * start_radius]
    root_exit = root + first.normalized() * min(1.2 * start_radius, .40 * first.length)
    for t in (.18, .38, .60, .82, 1.0):
        points.append((root - outward * start_radius * .62) * (1 - t) ** 2
                      + root * (2 * t * (1 - t)) + root_exit * t ** 2)
        sizes.append(start_radius * (1.04 - .04 * t))

    for i in range(1, len(joints) - 1):
        before, pivot, after = joints[i - 1:i + 2]
        radius = radii[i]
        incoming, outgoing = before - pivot, after - pivot
        a_span = min(2.05 * radius, .42 * incoming.length)
        b_span = min(2.05 * radius, .42 * outgoing.length)
        a = pivot + incoming.normalized() * a_span
        b = pivot + outgoing.normalized() * b_span
        before_radius = radius + (radii[i - 1] - radius) * a_span / incoming.length
        after_radius = radius + (radii[i + 1] - radius) * b_span / outgoing.length
        # A quadratic fillet through the hinge keeps the tube tangent to
        # both spans. Its centerline is evaluated on the posed skeleton.
        for t in (0.0, .16, .32, .50, .68, .84, 1.0):
            points.append(a * (1 - t) ** 2 + pivot * (2 * t * (1 - t)) + b * t ** 2)
            sizes.append(before_radius * (1 - t) ** 2
                         + radius * (2 * t * (1 - t)) + after_radius * t ** 2)

    end = joints[-1]
    last = (end - joints[-2]).normalized()
    radius = radii[-1]
    remaining = (end - points[-1]).dot(last)
    near_wrist = max(remaining, 0.0)
    for fraction, blend in ((.40, .48), (.73, .82)):
        points.append(end - last * (near_wrist * (1 - fraction)))
        sizes.append(sizes[-1] * (1 - blend) + radius * blend)
    points.extend([end, end + last * radius * .18])
    sizes.extend([radius * .89, radius * .63])
    piece = kit.Piece()
    piece.loft(points, sizes, sides=34, density=4)
    return piece.cage()


def frozen_mesh(source):
    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.data
    posed = (evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
    verts = [Vector((point.x, point.z, -point.y)) for point in posed]
    faces = [tuple(p.vertices) for p in mesh.polygons]
    return verts, faces


def posed_tips(anim, tips):
    for bone, vertices, faces in tips:
        pose, origin = anim.G[bone], anim.rest[bone]
        yield [pose @ (vertex - origin) for vertex in vertices], faces


def fair_attachments(mesh, attachments):
    """Soften the intersection at each root without smoothing the entire torso."""
    points = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", points)
    points = points.reshape(-1, 3)
    mask = np.zeros(len(points), dtype=np.float32)
    for pivot, radius in attachments:
        distance = np.linalg.norm(points - np.asarray(kit.to_blender(pivot)), axis=1)
        weight = np.clip((2.55 - distance / radius) / 1.3, 0, 1)
        mask = np.maximum(mask, weight ** 2 * (3 - 2 * weight))
    active = np.flatnonzero(mask)
    if not len(active):
        return
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    forward, backward = edges.reshape(-1, 2).T
    src = np.concatenate((forward, backward))
    dst = np.concatenate((backward, forward))
    active_index = np.full(len(points), -1, dtype=np.int32)
    active_index[active] = np.arange(len(active))
    keep = active_index[src] >= 0
    rows = active_index[src[keep]]
    counts = np.bincount(rows, minlength=len(active))
    weights = (1.0 / counts[rows]).astype(np.float32)
    neighbors = csr_matrix((weights, (rows, dst[keep])), shape=(len(active), len(points)))
    rate = .75 * mask[active, None]
    for _ in range(240):
        points[active] += rate * (neighbors @ points - points[active])
    mesh.vertices.foreach_set("co", points.ravel())
    mesh.update()


def combine(body, limbs, voxel, attachments):
    vertices, faces = body
    for points, polygons in limbs:
        start = len(vertices)
        vertices.extend(points)
        faces.extend(tuple(start + i for i in polygon) for polygon in polygons)
    surface = finish.new_object("Swept body", vertices, faces)
    finish.remesh(surface, voxel)
    finish.smooth(surface, .72, 8)
    fair_attachments(surface.data, attachments)
    surface.data.shade_smooth()
    surface.data.materials.append(finish.clay_material())
    return surface


def sagittal_depths(body, anim, stations):
    """Measure the central sagittal section of the evaluated body in bone-local axes."""
    surface = BVHTree.FromPolygons(*body)
    distances = {}
    for label, bone in stations.items():
        pose = anim.G[bone]
        axis = pose.b @ Vector((0, 0, 1))
        span = anim.rig["body_len"]
        front = surface.ray_cast(pose.o + axis * span, -axis, 2 * span)
        back = surface.ray_cast(pose.o - axis * span, axis, 2 * span)
        if front[0] is None or back[0] is None:
            raise RuntimeError(f"missing sagittal intersection at {label}")
        distances[label] = round((front[0] - back[0]).length, 5)
    return distances


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("limb", help="generic skin limb UID")
    parser.add_argument("out", type=Path)
    parser.add_argument("--frames", type=int, default=15)
    parser.add_argument("--motion", choices=("wave", "walk", "run"), default="wave")
    parser.add_argument("--yaw", type=float, help="override the full-body camera angle in degrees")
    parser.add_argument("--torso-stations", nargs=3, type=int, metavar=("PELVIS", "WAIST", "CHEST"),
                        help="spine station indices to audit in the evaluated mesh")
    parser.add_argument("--audit-only", action="store_true", help="measure body depth without rendering")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.frames < 3:
        parser.error("--frames must be at least 3")
    if args.audit_only and args.torso_stations is None:
        parser.error("--audit-only requires --torso-stations")
    args.out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build = SweptBuilder(recipe.load(args.recipe), args.limb)
    result = build.build()
    arm, skin, parts = result["armature"], result["skin"], result["parts"]
    limbs = [limb for limb in result["rig"]["limbs"] if limb["uid"] == args.limb]
    anim = Animator(result["rig"])
    anim.play("idle")
    anim.advance_to(6.0)
    anim.play(args.motion)
    duration = 2.6 if args.motion == "wave" else anim.cycle_length()
    stations = {}
    if args.torso_stations is not None:
        spine = result["rig"]["spine"]
        if any(index < 0 or index >= len(spine) for index in args.torso_stations):
            parser.error("--torso-stations indices must refer to recipe spine stations")
        stations = dict(zip(("pelvis", "waist", "chest"), (spine[i] for i in args.torso_stations)))
    measurements = []
    if not args.audit_only:
        cam = render.setup("workbench", 392)
    voxel = max(.0032, result["report"]["height"] / (590 if build.soft_tips else 300))
    for index in range(args.frames):
        phase = index / (args.frames - 1)
        anim.advance_to(6.0 + duration * phase)
        write_pose(arm, anim)
        bpy.context.view_layer.update()
        body = frozen_mesh(skin)
        if stations:
            measurements.append({"phase": phase, "depth": sagittal_depths(body, anim, stations)})
        if args.audit_only:
            continue
        details = None
        if parts is not None:
            details = finish.new_object("Pose details", *frozen_mesh(parts))
            details.data.shade_smooth()
            details.data.materials.append(finish.clay_material())
            parts.hide_render = True
        surfaces = [swept_limb(anim, limb) for limb in limbs]
        surfaces.extend(posed_tips(anim, build.soft_tips))
        attachments = [(anim.G[limb["bones"][0]].o, limb["radii"][0]) for limb in limbs]
        surface = combine(body, surfaces, voxel, attachments)
        skin.hide_render = True
        if index == 0:
            lo, hi = render.bounds([obj for obj in (surface, details) if obj is not None])
            lo.x -= .13
            hi.x += .28
            yaw = args.yaw if args.yaw is not None else (40 if args.motion == "wave" else 90)
            render.frame(cam, lo, hi, yaw, 11, 1.05)
        render.render(str(args.out / f"{args.motion}-{index:02}.png"), transparent=True)
        if index == (args.frames - 1) // 2 and args.motion == "wave":
            saved_position, saved_rotation = cam.location.copy(), cam.rotation_euler.copy()
            pivot = kit.to_blender(anim.G[limbs[0]["bones"][0]].o)
            extent = Vector((.40, .36, .36))
            render.frame(cam, pivot - extent, pivot + extent, 36, 12, .96)
            render.render(str(args.out / "raised-shoulder.png"), transparent=True)
            render.frame(cam, pivot - extent, pivot + extent, 0, 4, .96)
            render.render(str(args.out / "raised-shoulder-front.png"), transparent=True)
            render.frame(cam, pivot - extent, pivot + extent, 90, 4, .96)
            render.render(str(args.out / "raised-shoulder-side.png"), transparent=True)
            wrist = kit.to_blender(anim.G[limbs[0]["bones"][-1]].o)
            extent = Vector((.24, .24, .24))
            render.frame(cam, wrist - extent, wrist + extent, -24, 19, .98)
            render.render(str(args.out / "raised-wrist.png"), transparent=True)
            cam.location, cam.rotation_euler = saved_position, saved_rotation
        finish.remove(surface)
        if details is not None:
            finish.remove(details)
    if measurements:
        (args.out / f"{args.motion}-torso-depth.json").write_text(
            json.dumps(measurements, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
