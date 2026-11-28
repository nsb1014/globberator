"""Recipe -> Blender creature.

Produces, in a collection:
  <name>_rig    armature (rest pose = neutral stance), recipe + rig data as custom props
  <name>_skin   ONE fused sculpted surface: body sweep, limbs and every skin-slot part
                region (bulges, brows, cheeks, lids, paws, hands...) voxel-remeshed together,
                smoothed and decimated, with a neutral clay surface
  <name>_parts  finished detail regions (eyes, horns, hooves, teeth, fins...), rigid-skinned

All internal math uses recipe coordinates (+Y up, +Z forward). kit.to_blender
converts at object creation; the armature lives in Blender coordinates.
"""
import json
import math

import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

from . import catalog, finish, kit, placement
from . import recipe as R
from .spine import Spine, up_of, RIGHT, BACK

UP = Vector((0, 1, 0))
MIRROR = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
C3 = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))   # recipe -> Blender rotation
C4 = C3.to_4x4()


def frame(y_dir, z_hint):
    """Orthonormal basis (columns x, y, z) with y along y_dir, z close to z_hint."""
    y = y_dir.normalized()
    z = z_hint - y * z_hint.dot(y)
    if z.length < 0.2:
        z = UP - y * UP.dot(y)
        if z.length < 0.2:
            z = RIGHT - y * RIGHT.dot(y)
    z.normalize()
    x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()


def xform(basis3, origin):
    m = basis3.to_4x4()
    m.translation = origin
    return m


def part_ground_contacts(part, params, basis=None):
    ctx = part.build(params)
    if any(pc.finish_for(slot) in finish.SCULPT_LEVELS
           for pc in ctx.pieces.values() for slot in pc.slots()):
        _, regions = finish.part_regions(part, params, assembly=True)
        pts = [v for piece in regions.values() for _, verts, _ in piece for v in verts]
    else:
        pts = [p for pc in ctx.pieces.values() for p in pc.cage()[0]]
    if basis is not None:
        pts = [basis @ p for p in pts]
    if not pts:
        return Vector((0, -0.1, 0)), Vector((0, -0.1, 0))
    lo = min(p.y for p in pts)
    low = [p for p in pts if p.y < lo + 0.012]
    c = sum(low, Vector((0, 0, 0))) / len(low)
    toe = max(p.z for p in pts if p.y <= lo + 1e-6)
    return Vector((c.x, lo, c.z)), Vector((c.x, lo, toe))


def part_sole(part, params, basis=None):
    return part_ground_contacts(part, params, basis)[0]


def limb_weights(vertices, joints, bones):
    """Blend a detailed region over the adjacent joints of its own chain."""
    vertices = np.asarray(vertices, dtype=float)
    a = np.asarray(joints[:-1], dtype=float)
    directions = np.asarray(joints[1:], dtype=float) - a
    offset = vertices[:, None] - a
    progress = np.clip(np.einsum("nsc,sc->ns", offset, directions)
                       / np.einsum("sc,sc->s", directions, directions), 0, 1)
    delta = offset - progress[..., None] * directions
    segment = np.einsum("nsc,nsc->ns", delta, delta).argmin(axis=1)
    t = progress[np.arange(len(vertices)), segment]
    pair = t + segment
    result = []
    for k in pair:
        left = int(k)
        right = min(left + 1, len(bones) - 1)
        f = k - left
        right_weight = f * f * (3 - 2 * f)
        row = ((bones[left], 1 - right_weight), (bones[right], right_weight))
        result.append(tuple((bone, weight) for bone, weight in row if weight > 1e-6))
    return result


def shell_weights(vertices, faces, joints, bones):
    """Each hard tail segment follows one hinge instead of bending across it."""
    neighbors = [set() for _ in vertices]
    for face in faces:
        for a, b in zip(face, (*face[1:], face[0])):
            neighbors[a].add(b)
            neighbors[b].add(a)
    centers = [a.lerp(b, .5) for a, b in zip(joints, joints[1:])]
    weights = [None] * len(vertices)
    for seed in range(len(vertices)):
        if weights[seed] is not None:
            continue
        component, queue = {seed}, [seed]
        while queue:
            added = neighbors[queue.pop()] - component
            component.update(added)
            queue.extend(added)
        center = sum((vertices[i] for i in component), Vector((0, 0, 0))) / len(component)
        joint = min(range(len(centers)), key=lambda i: (centers[i] - center).length_squared)
        for i in component:
            weights[i] = ((bones[joint], 1.0),)
    return weights


class Builder:
    rigid_surfaces = False
    deform_surface_chains = False

    def __init__(self, src, quality="final"):
        self.recipe, self.warnings = R.normalize(src)
        self.quality = quality
        self.names, self.parents, self.rest, self.tails = [], [], [], []
        self.limbs, self.parts_rig = [], []
        self.skin_prims = []        # [(verts, faces)] recipe coords
        self.details = []           # [(verts, faces, bone)]
        self.core = next((p for p in self.recipe["parts"] if catalog.get(p["part"]).attach == "core"), None)
        self.core_geometry = None
        if self.core:
            part = catalog.get(self.core["part"])
            _, regions = finish.part_regions(part, self.core["params"])
            self.core_geometry = next((v, f) for slot, v, f in regions["self"] if slot == "skin")
            self.core_bvh = BVHTree.FromPolygons(*self.core_geometry)

    def core_origin(self, sp):
        return sp.at(0.5)["p"] + Vector((0, self.core["offset"], 0))

    def body_surface(self, sp, u, theta, offset=0.0):
        surface = sp.surface(u, theta, offset if not self.core else 0.0)
        if self.core:
            origin, scale = self.core_origin(sp), self.core["scale"]
            point, normal, _, _ = self.core_bvh.find_nearest((surface["p"] - origin) / scale)
            surface.update(p=origin + point * scale + normal * offset, n=normal)
        return surface

    def body_bottom(self, sp):
        if not self.core:
            return sp.bottom_y()
        return self.core_origin(sp).y + min(v.y for v in self.core_geometry[0]) * self.core["scale"]

    def fringe_mount(self, instance):
        from .parts.research_feeding import TENTACLE_FRINGE_RADIUS

        radius = max(math.hypot(v.x, v.z) for v in self.core_geometry[0])
        steps = 120
        rim = []
        for i in range(steps):
            angle = math.tau * i / steps
            query = Vector((radius * math.cos(angle), 0, radius * math.sin(angle)))
            point, _, _, _ = self.core_bvh.find_nearest(query)
            rim.append((math.hypot(point.x, point.z), point.y))
        radius_model = TENTACLE_FRINGE_RADIUS * instance["params"]["size"]
        origin, core_scale = self.core_origin(self.spine), self.core["scale"]

        def mount(vertex):
            angle = math.atan2(vertex.z, vertex.x)
            step = angle * steps / math.tau
            i = math.floor(step)
            a, b = rim[i % steps], rim[(i + 1) % steps]
            t = step - i
            r = core_scale * kit.lerp(a[0], b[0], t)
            r += (math.hypot(vertex.x, vertex.z) - radius_model) * instance["scale"]
            y = core_scale * kit.lerp(a[1], b[1], t) + vertex.y * instance["scale"] + instance["offset"]
            return origin + Vector((r * math.cos(angle), y, r * math.sin(angle)))
        return origin, mount

    # ---------------------------------------------------------- resolve
    def resolve_limbs(self, sp):
        for l in self.recipe["limbs"]:
            s = self.body_surface(sp, l["u"], l["theta"])
            scale = l["scale"]
            rotation = Euler([math.radians(a) for a in l["rot"]], "ZXY").to_matrix()
            radii = [radius * scale for radius in l["radii"]]
            hip = s["p"] - s["n"] * radii[0] * 0.5
            joints = [hip]
            for sg in l["segments"]:
                joints.append(joints[-1] + (rotation @ Vector(sg)) * scale)
            part = catalog.get(l["tip"]) if l["tip"] else None
            family = catalog.get(l.get("family"))
            if part and part.orient == "palm_in" and not family:
                # The wrist blends into the forearm's terminal loft. Keep a
                # bulky authored forearm from forming a cuff around the palm.
                wrist_radius = .035 * l["tip_params"]["size"] * scale
                radii[-1] = min(radii[-1], wrist_radius)
            role, sole = "appendage", Vector((0, -radii[-1], 0))
            toe = None
            if family and family.cap == "foot":
                role = "leg"
                sole = part_sole(family, l["params"], rotation) * scale - (joints[-1] - hip)
            elif family and family.cap in ("hand", "grasp"):
                role = "arm"
            elif family and family.cap == "flap":
                role = "wing"
            elif family and family.cap == "paddle":
                role = "fin"
            if part is not None:
                if part.cap == "foot":
                    sole, tip_toe = part_ground_contacts(part, l["tip_params"])
                    role, sole = "leg", sole * scale
                    if part.id == "foot_hoof" and len(joints) == 4 and self.recipe.get("gait") == "humanoid":
                        toe = tip_toe * scale
                elif part.cap in ("hand", "grasp"):
                    role = "arm"
            if l["motion"] in ("tail", "fin", "wing"):
                role = l["motion"]
            # Off the midline, or on it with a shape that bends sideways: build a
            # reflected twin so the creature stays symmetric (a sideways leg on the
            # midline would otherwise be a single lopsided limb). Authored geometry is kept.
            bends = any(abs(j.x - hip.x) > 1e-4 for j in joints[1:])
            lateral = abs(abs(l["theta"]) - 90.0) > 1e-4 or (bends and not family)
            paired_hip = role == "leg" and lateral and self.recipe.get("gait") == "humanoid"
            ball_hip = paired_hip and l.get("ball_hip")
            if ball_hip:
                # Seat the ball and its pivot together without moving the
                # authored downstream joints in the rest pose.
                joints[0] = Vector((hip.x * (1 - l.get("ball_hip_inset", 0.0)), hip.y, hip.z))
            length = sum((joints[k] - joints[k - 1]).length for k in range(1, len(joints)))
            base = {"uid": l["uid"], "name": l["uid"], "u": l["u"], "v": s["v"], "joints": joints, "radii": radii,
                    "tip": l["tip"], "tip_params": l["tip_params"], "role": role, "has_foot": role == "leg",
                    "scale": scale, "sole_local": sole, "length": length, "mirrored": False,
                    "side": 1.0 if lateral else 0.0}
            if part and part.id in ("foot_webbed", "foot_webbed_long"):
                base["motion_cap"] = "paddle"
            if "bend_limits" in l:
                base["bend_limits"] = l["bend_limits"]
            if self.recipe.get("construction") == "metaball":
                if part:
                    base["tip_cap"] = part.cap
                if family:
                    base["family_cap"] = family.cap
            if toe is not None:
                base["toe_local"] = toe
            if family:
                base.update(family=family.id, params=l["params"], rot=l["rot"])
            if l.get("root_blend"):
                base["root_blend"] = l["root_blend"]
            if paired_hip:
                if ball_hip:
                    base["ball_radius"] = min(1.26 * radii[0], .76 * (joints[1] - joints[0]).length)
                elif l.get("glute_shape"):
                    base["glute_shape"] = l["glute_shape"]
            if l.get("root_blend") or self.recipe.get("gait") == "humanoid":
                base["root_normal"] = s["n"]
            self.limbs.append(base)
            if l.get("mirror") is False:
                base["side"] = 1.0 if hip.x > 1e-5 else -1.0 if hip.x < -1e-5 else 0.0
                base["single"] = True
            elif lateral:        # off the midline -> reflected twin (automatic)
                m = dict(base)
                m["joints"] = [Vector((-j.x, j.y, j.z)) for j in joints]
                m["name"] = l["uid"] + "_m"
                m["mirrored"] = True
                m["side"] = -base["side"]
                m["sole_local"] = Vector((-sole.x, sole.y, sole.z))
                if toe is not None:
                    m["toe_local"] = Vector((-toe.x, toe.y, toe.z))
                if "root_normal" in m:
                    m["root_normal"] = MIRROR.to_3x3() @ m["root_normal"]
                self.limbs.append(m)
        for l in self.limbs:
            l["sole"] = l["joints"][-1] + l["sole_local"]

    def ground_level(self, sp):
        lowest = self.body_bottom(sp)
        foot_low = min([l["sole"].y for l in self.limbs if l["has_foot"]] or [float("inf")])
        for l in self.limbs:
            if l["role"] not in ("arm", "tail", "wing", "fin"):
                lowest = min(lowest, l["sole"].y)
        ground = foot_low if foot_low < float("inf") else lowest
        ground = self.recipe.get("ground_y", ground)
        for l in self.limbs:
            if l["role"] in ("arm", "tail", "wing", "fin"):
                continue
            gap = l["sole"].y - ground
            if l["has_foot"]:
                hip, end = l["joints"][0], l["joints"][-1]
                drop = hip.y - (ground - l["sole_local"].y)
                horiz = math.hypot(end.x - hip.x, end.z - hip.z)
                reach = math.hypot(drop, horiz)
                if gap <= max(0.06, 0.12 * l["length"]) or drop <= 0 or reach <= l["length"]:
                    l["role"] = "leg"
                else:
                    self.warnings.append("limb %s has a foot but cannot reach the ground (short by %.2f)" % (l["name"], reach - l["length"]))
                    l["role"] = "appendage"
            else:
                l["role"] = "leg" if gap <= max(0.06, 0.12 * l["length"]) else "appendage"
        return ground

    # ------------------------------------------------------------ bones
    def add_bone(self, name, parent, pos, tail):
        nm, k = name, 2
        while nm in self.names:
            nm = "%s_%d" % (name, k)
            k += 1
        self.names.append(nm)
        self.parents.append(parent)
        self.rest.append(pos.copy())
        self.tails.append(tail.copy())
        return len(self.names) - 1

    def spine_bone_at(self, v):
        return self.spine_bones[min(max(int(round(v)), 0), len(self.spine_bones) - 1)]

    def make_bones(self):
        sp = self.spine
        n = len(sp.vpos)
        self.add_bone("root", -1, Vector((0, 0, 0)), Vector((0, 0, 0.2)))
        legs = [l["v"] for l in self.limbs if l["role"] == "leg"]
        self.hub = min(max(int(round(sum(legs) / len(legs))), 0), n - 1) if legs else n // 2
        self.spine_bones = [0] * n

        def tail_toward(i, j):
            d = sp.vpos[j] - sp.vpos[i] if j != i else sp.at(1.0 if i == n - 1 else 0.0)["t"] * 0.2
            return sp.vpos[i] + (d if d.length > 1e-4 else Vector((0, 0, 0.1)))
        h = self.hub
        self.spine_bones[h] = self.add_bone("spine_%d" % h, 0, sp.vpos[h], tail_toward(h, min(h + 1, n - 1)))
        for i in range(h + 1, n):
            self.spine_bones[i] = self.add_bone("spine_%d" % i, self.spine_bones[i - 1], sp.vpos[i],
                                                tail_toward(i, i + 1) if i < n - 1 else sp.vpos[i] + sp.at(1.0)["t"] * sp.vw[i])
        for i in range(h - 1, -1, -1):
            self.spine_bones[i] = self.add_bone("spine_%d" % i, self.spine_bones[i + 1], sp.vpos[i],
                                                tail_toward(i, i - 1) if i > 0 else sp.vpos[i] - sp.at(0.0)["t"] * sp.vw[i])
        for l in self.limbs:
            l["parent_bone"] = self.spine_bone_at(l["v"])
            bones = []
            J = l["joints"]
            for k in range(len(J)):
                tail = J[k + 1] if k + 1 < len(J) else J[k] + (J[k] - J[k - 1]).normalized() * max(l["radii"][-1] * 1.5, 0.03)
                bones.append(self.add_bone("%s_%d" % (l["name"], k), l["parent_bone"] if k == 0 else bones[k - 1], J[k], tail))
            l["bones"] = bones
            if "ball_radius" in l:
                l["joint_support"] = [
                    self.add_bone(f"{l['name']}_bend_{k}", bones[k], J[k], J[k + 1])
                    for k in range(1, len(bones) - 1)
                ]

    # -------------------------------------------------------- geometry
    def body_prim(self):
        if self.core:
            verts, faces = self.core_geometry
            origin, scale = self.core_origin(self.spine), self.core["scale"]
            self.skin_prims.append(([origin + v * scale for v in verts], faces))
            return
        S = self.spine.samples
        segs = 40
        verts, faces = [], []
        idx = []
        for s in S:
            if s.get("tip"):
                idx.append([len(verts)])
                verts.append(s["p"].copy())
                continue
            up = up_of(s["t"])
            row = []
            for i in range(segs):
                a = 2 * math.pi * i / segs
                row.append(len(verts))
                verts.append(s["p"] + RIGHT * math.cos(a) * s["w"] + up * math.sin(a) * s["h"])
            idx.append(row)
        for k in range(len(idx) - 1):
            a, b = idx[k], idx[k + 1]
            for i in range(segs):
                j = (i + 1) % segs
                if len(a) == 1:
                    faces.append((a[0], b[j], b[i]))
                elif len(b) == 1:
                    faces.append((a[i], a[j], b[0]))
                else:
                    faces.append((a[i], a[j], b[j], b[i]))
        self.skin_prims.append((verts, faces))

    def limb_prim(self, l):
        if l.get("family"):
            self.research_limb_prim(l)
            return
        if "ball_radius" in l:
            self.ball_hip_prim(l)
            return
        J, rad = l["joints"], l["radii"]
        d0 = (J[1] - J[0]).normalized()
        blend = l.get("root_blend", 0.0)
        glute = l.get("glute_shape", 0.0)
        if blend:
            # Extend the same upper-limb loft into its host. Its buried rings
            # approach along the surface normal instead of exposing a round cap.
            r = rad[0]
            inward = l["root_normal"] * r
            pts = [(J[0] - d0 * r * 0.70).lerp(J[0] - inward * 1.15, blend),
                   (J[0] - d0 * r * 0.35).lerp(J[0] - inward * 0.48 - d0 * r * 0.24, blend)]
            rr = [r * (0.85 - 0.15 * blend), r * (0.93 + 0.17 * blend)]
        else:
            pts, rr = [J[0] - d0 * rad[0] * 0.7], [rad[0] * 0.85]
        for k in range(len(J) - 1):
            bulge = 1.18 if k < len(J) - 2 else 1.08
            pts += [J[k], J[k].lerp(J[k + 1], 0.45)]
            root_radius = rad[k] * (1 - .17 * glute) if k == 0 else rad[k]
            rr += [root_radius, (rad[k] + rad[k + 1]) * 0.5 * bulge]
        pts.append(J[-1])
        rr.append(rad[-1])
        pc = kit.Piece()
        pc.loft(pts, rr, sides=32 if glute else 24, density=7 if glute else 4)
        vertices, faces = pc.cage()
        if glute:
            # Form the rear mass on the thigh cage before fusing the limb at
            # its socket. The loft's centerline stays aligned to the leg.
            posterior = (d0 * d0.dot(BACK) - BACK).normalized()
            span = (J[1] - J[0]).length
            offsets = np.asarray(vertices) - np.asarray(J[0])
            t = offsets @ np.asarray(d0) / span
            seat = np.clip((t + .22) / .42, 0.0, 1.0)
            taper = np.clip((.85 - t) / .65, 0.0, 1.0)
            rear = np.clip((offsets @ np.asarray(posterior)) / (.85 * rad[0]), 0.0, 1.0)
            fullness = (.56 * glute * rad[0] * seat ** 2 * (3 - 2 * seat)
                        * taper ** 2 * (3 - 2 * taper) * rear ** 2 * (3 - 2 * rear))
            vertices = [vertex + posterior * float(amount) for vertex, amount in zip(vertices, fullness)]
        self.skin_prims.append((vertices, faces))

    def ball_hip_prim(self, limb):
        """Build the thigh root on a sphere concentric with the hip pivot."""
        joints, radii = limb["joints"], limb["radii"]
        radius = limb["ball_radius"]
        axis = (joints[1] - joints[0]).normalized()
        sections = (-.998, -.97, -.88, -.70, -.46, -.20, 0.0, .24, .48)
        points = [joints[0] + axis * (radius * t) for t in sections]
        widths = [radius * math.sqrt(1 - t * t) for t in sections]
        points.append(joints[1])
        widths.append(radii[1])
        for i in range(1, len(joints) - 1):
            points.extend((joints[i].lerp(joints[i + 1], .5), joints[i + 1]))
            widths.extend(((radii[i] + radii[i + 1]) * .52, radii[i + 1]))
        piece = kit.Piece()
        piece.loft(points, widths, sides=40, density=5)
        limb["ball_meshes"] = [piece.cage()]

    def finish_ball_leg(self, limb):
        vertices, faces = [], []
        for points, polygons in limb.pop("ball_meshes"):
            start = len(vertices)
            vertices.extend(points)
            faces.extend(tuple(start + i for i in polygon) for polygon in polygons)
        if self.quality != "preview":
            obj = finish.new_object("Leg sculpt", vertices, faces)
            finish.remesh(obj, max(.002, min(.008, limb["length"] / 275)))
            finish.smooth(obj, .6, 8)
            finish.decimate(obj, 7000)
            vertices, faces = finish.read_mesh(obj)
            finish.remove(obj)
        points = np.asarray(vertices)
        weights = self.chain_weights(limb, points, np.ones(len(points)))
        rows = [tuple((bone, value) for bone, column in weights.items()
                      if (value := round(float(column[i]), 3)) > 0)
                for i in range(len(points))]
        self.details.append((vertices, faces, rows))

    def research_limb_prim(self, limb):
        part = catalog.get(limb["family"])
        smooth_chain = catalog.metadata(part).get("chain_skinning") == "smooth"
        rotation = Euler([math.radians(a) for a in limb["rot"]], "ZXY").to_matrix()
        basis = rotation @ Matrix.Diagonal((limb["scale"],) * 3)
        if limb["mirrored"]:
            basis = MIRROR.to_3x3() @ basis
        matrix = xform(basis, limb["joints"][0])
        params = limb["params"]
        if part.id == "pincer_limb" and limb["mirrored"] and params["asymmetry"]:
            params = {**params, "_mirrored": True}
        ctx, regions = finish.part_regions(part, params, assembly=not self.rigid_surfaces)
        flip = limb["mirrored"]
        joints, bones = limb["joints"], limb["bones"]
        jaws = []
        hinged = {}
        for bone in part.bones:
            pivot = matrix @ ctx.pivots[bone["name"]]
            k = min(range(len(joints)), key=lambda i: (joints[i] - pivot).length_squared)
            index = self.add_bone(limb["name"] + "_" + bone["name"], bones[k], pivot, pivot + basis @ Vector((0, .05, 0)))
            hinged[bone["name"]] = index
            jaws.append({"bone": index, "axis": list(bone["axis"]), "angle": bone["angle"]})
        for name, piece in regions.items():
            for slot, verts, faces in piece:
                verts = [matrix @ v for v in verts]
                if not verts:
                    continue
                faces = [tuple(reversed(f)) for f in faces] if flip else faces
                if slot == "skin" and not self.rigid_surfaces:
                    self.skin_prims.append((verts, faces))
                    continue
                bind = hinged.get(name)
                if bind is None:
                    if ((self.rigid_surfaces and not smooth_chain
                         and not (self.deform_surface_chains and limb["role"] in ("wing", "fin")))
                            or (part.id == "tail_segmented" and slot == "accent")):
                        bind = shell_weights(verts, faces, joints, bones)
                    else:
                        bind = limb_weights(verts, joints, bones)
                self.details.append((verts, faces, bind))
        limb["jaws"] = jaws
        limb["tip_frame"] = [list(row) for row in basis.normalized()]

    def limb_surface(self, l, u, theta, offset):
        J, rad = l["joints"], l["radii"]
        target, acc, k, t = u * l["length"], 0.0, 0, 0.0
        for i in range(len(J) - 1):
            sl = (J[i + 1] - J[i]).length
            if acc + sl >= target or i == len(J) - 2:
                k, t = i, min(max((target - acc) / max(sl, 1e-4), 0.0), 1.0)
                break
            acc += sl
        a, b = J[k], J[k + 1]
        d = (b - a).normalized()
        e90 = UP - d * UP.dot(d)
        if e90.length < 0.2:
            e90 = BACK - d * BACK.dot(d)
        e90.normalize()
        e0 = e90.cross(d).normalized()
        n = (e0 * math.cos(math.radians(theta)) + e90 * math.sin(math.radians(theta))).normalized()
        r = rad[k] + (rad[k + 1] - rad[k]) * t
        return {"p": a.lerp(b, t) + n * (r + offset), "n": n, "t": d, "up": e90, "bone": l["bones"][k]}

    def place(self, part, params, M, parent_bone, name, mirrored, uid, u, mount=None):
        """Instance one part copy: skin regions -> fused skin, others -> details, bones -> rig."""
        ctx, regions = finish.part_regions(part, params, assembly=not self.rigid_surfaces)
        world = mount if mount is not None else M.__matmul__
        pb = self.add_bone("P_" + name, parent_bone, M.translation, M @ Vector((0, 0.06, 0)))
        bone_of = {"self": pb}
        jaws = []
        for b in part.bones:
            piv = M @ ctx.pivots.get(b["name"], Vector(b["pivot"]))
            jb = self.add_bone("P_%s_%s" % (name, b["name"]), pb, piv, piv + (M.to_3x3() @ Vector((0, 0.05, 0))))
            bone_of[b["name"]] = jb
            jaws.append({"bone": jb, "axis": list(b["axis"]), "angle": b["angle"]})
        flip = M.to_3x3().determinant() < 0
        for pn, piece in regions.items():
            for slot, rv, rf in piece:
                verts = [world(v) for v in rv]
                faces = [tuple(reversed(f)) for f in rf] if flip else rf
                self.place_region(part, pn, slot, verts, faces, bone_of.get(pn, pb))
        F = M.to_3x3().normalized()
        self.parts_rig.append({"uid": uid, "part": part.id, "category": part.category, "cap": part.cap, "bone": pb,
                               "parent": parent_bone, "frame": [list(r) for r in F], "mirrored": mirrored, "jaws": jaws, "u": u})
        return pb, jaws

    def place_region(self, part, piece, slot, vertices, faces, bone):
        if slot == "skin" and not self.rigid_surfaces:
            self.skin_prims.append((vertices, faces))
            if piece != "self":
                self.warnings.append("%s: skin on a hinged piece is fused rigidly" % part.id)
        else:
            self.details.append((vertices, faces, bone))

    def place_parts(self):
        sp = self.spine
        limb_of = {(l["uid"], l["mirrored"]): l for l in self.limbs}
        muzzles = {p["uid"] for p in self.recipe["parts"] if p["part"] == "muzzle"}
        nose_mounts = {}
        mounted_noses = []

        def muzzle_mount(instance, matrix, bone, mirrored):
            from .parts.research_feeding import muzzle_nose_scale, muzzle_nose_socket

            params = instance["params"]
            anchor, size = muzzle_nose_socket(params), muzzle_nose_scale(params)
            nose_mounts.setdefault(instance["uid"], []).append((matrix, anchor, size, bone, mirrored, instance["u"]))
            self.parts_rig[-1]["nose_socket"] = list(matrix @ anchor)
            self.parts_rig[-1]["nose_snap_radius"] = .095 * instance["scale"] * instance["params"]["size"]

        for p in self.recipe["parts"]:
            part = catalog.get(p["part"])
            if part.attach == "core":
                continue
            if part.id == "nose_pad" and p["on"] in muzzles:
                mounted_noses.append(p)
                continue
            if self.core and self.core["part"] == "bell_radial" and part.id == "tentacle_fringe" and p["on"] == "body":
                origin, mount = self.fringe_mount(p)
                matrix = xform(Matrix.Identity(3), origin)
                self.place(part, p["params"], matrix, self.spine_bones[self.hub], p["uid"], False, p["uid"], p["u"], mount)
                continue
            on_limb = p["on"] != "body"
            if on_limb:
                l = limb_of[(p["on"], False)]
                s = self.limb_surface(l, p["u"], p["theta"], p["offset"])
                parent = s["bone"]
            else:
                s = self.body_surface(sp, p["u"], p["theta"], p["offset"])
                parent = self.spine_bone_at(s["v"])
            if part.orient == "native":
                basis = Matrix.Identity(3)
            elif part.orient == "forward":
                vertical = UP - s["n"] * UP.dot(s["n"])
                if vertical.length < 0.15:
                    vertical = -s["t"] if s["n"].y > 0 else s["t"]
                basis = frame(vertical, s["n"])
            elif part.orient == "face":
                zh = UP - s["n"] * UP.dot(s["n"])
                basis = frame(s["n"], UP if zh.length > 0.25 else s["t"])
            else:
                basis = frame(s["n"], s["t"])
            rot = Euler([math.radians(a) for a in p["rot"]], "ZXY").to_matrix()
            M = xform(basis @ rot @ Matrix.Diagonal((p["scale"],) * 3), s["p"])
            bone, _ = self.place(part, p["params"], M, parent, p["uid"], False, p["uid"], p["u"])
            if part.id == "muzzle":
                muzzle_mount(p, M, bone, False)
            twin = p.get("mirror") is not False and (
                (not on_limb and abs(abs(p["theta"]) - 90.0) > 1e-3)
                or (on_limb and not l.get("single") and (l["side"] != 0.0 or abs(s["p"].x) > 1e-4))
            )
            if twin:
                if on_limb:
                    ml = limb_of.get((p["on"], True), l)
                    mparent = self.limb_surface(ml, p["u"], p["theta"], p["offset"])["bone"]
                else:
                    mparent = self.spine_bone_at(sp.surface(p["u"], 180.0 - p["theta"])["v"])
                mirrored_matrix = MIRROR @ M
                bone, _ = self.place(part, p["params"], mirrored_matrix, mparent, p["uid"] + "_m", True, p["uid"], p["u"])
                if part.id == "muzzle":
                    muzzle_mount(p, mirrored_matrix, bone, True)

        for nose in mounted_noses:
            part = catalog.get("nose_pad")
            rot = Euler([math.radians(a) for a in nose["rot"]], "ZXY").to_matrix()
            for matrix, anchor, size, bone, mirrored, u in nose_mounts[nose["on"]]:
                basis = rot @ Matrix.Diagonal((nose["scale"] * size,) * 3)
                mount = matrix @ xform(basis, anchor + BACK * nose["offset"])
                name = nose["uid"] + ("_m" if mirrored else "")
                self.place(part, nose["params"], mount, bone, name, mirrored, nose["uid"], u)

    def place_tips(self):
        for l in self.limbs:
            if not l["tip"]:
                l.setdefault("jaws", [])
                l.setdefault("tip_frame", [list(r) for r in Matrix.Identity(3)])
                continue
            part = catalog.get(l["tip"])
            J = l["joints"]
            end = J[-1]
            if part.cap == "foot" or part.orient == "native":
                M = xform(Matrix.Identity(3), end)
                if l["mirrored"]:
                    M = xform(Matrix.Diagonal((-1, 1, 1)), end)
            else:
                d = (J[-1] - J[-2]).normalized()
                # Authored tips use the +X-side limb. Reflect its whole frame
                # so the other hand also faces its thigh and keeps chirality.
                if part.orient == "plantar":
                    palm = -UP
                else:
                    palm = -RIGHT + BACK * .35 if part.orient == "palm_in" and l["side"] else BACK
                if l["mirrored"]:
                    od = Vector((-d.x, d.y, d.z))
                    M = MIRROR @ xform(frame(od, palm), Vector((-end.x, end.y, end.z)))
                else:
                    M = xform(frame(d, palm), end)
            M = M @ Matrix.Scale(l["scale"], 4)
            end_bone = l["bones"][-1]
            ctx, regions = finish.part_regions(part, l["tip_params"], assembly=not self.rigid_surfaces)
            flip = M.to_3x3().determinant() < 0
            jaws, bone_of = [], {"self": end_bone}
            for b in part.bones:
                piv = M @ ctx.pivots.get(b["name"], Vector(b["pivot"]))
                jb = self.add_bone("%s_%s" % (l["name"], b["name"]), end_bone, piv, piv + M.to_3x3() @ Vector((0, 0.05, 0)))
                bone_of[b["name"]] = jb
                jaws.append({"bone": jb, "axis": list(b["axis"]), "angle": b["angle"]})
            for pn, piece in regions.items():
                for slot, rv, rf in piece:
                    verts = [M @ v for v in rv]
                    faces = [tuple(reversed(f)) for f in rf] if flip else rf
                    if slot == "skin" and not self.rigid_surfaces:
                        if "ball_meshes" in l:
                            l["ball_meshes"].append((verts, faces))
                        else:
                            self.skin_prims.append((verts, faces))
                    else:
                        self.details.append((verts, faces, bone_of.get(pn, end_bone)))
            l.setdefault("jaws", []).extend(jaws)
            l["tip_frame"] = [list(r) for r in M.to_3x3().normalized()]

    # ------------------------------------------------------------ build
    def build(self, collection=None):
        rc = self.recipe
        sp0 = Spine(rc["spine"])
        self.resolve_limbs(sp0)
        ground = self.ground_level(sp0)
        shift = Vector((0, -ground, 0))
        self.shift_y = -ground
        for l in self.limbs:
            l["joints"] = [j + shift for j in l["joints"]]
            l["sole"] = l["sole"] + shift
        self.spine = Spine(rc["spine"], shift)
        bottom = self.body_bottom(self.spine)
        if any(l["role"] == "leg" for l in self.limbs) and bottom < -0.02:
            self.warnings.append("body dips %.2f below the ground; lengthen the legs or raise the spine" % -bottom)
        self.make_bones()
        self.body_prim()
        for l in self.limbs:
            self.limb_prim(l)
        self.place_parts()
        self.place_tips()
        for limb in self.limbs:
            if "ball_meshes" in limb:
                self.finish_ball_leg(limb)
        return self.assemble(collection)

    def fuse(self, col):
        verts, faces = [], []
        for v, f in self.skin_prims:
            o = len(verts)
            verts += v
            faces += [tuple(i + o for i in fc) for fc in f]
        ob = finish.new_object(self.recipe["name"] + "_skin", verts, faces, col)
        if self.quality != "preview":
            height = max(v.y for v in verts) - min(v.y for v in verts)
            length = max(v.z for v in verts) - min(v.z for v in verts)
            voxel = min(max(max(height, length) / 260.0, 0.004), 0.025)
            budget = 26000
            hand_sizes = [l["scale"] * l["tip_params"]["size"] for l in self.limbs if l["tip"] == "hand_basic"]
            if hand_sizes:
                # Preserve the gaps and rounded pads of the fingers during
                # body fusion, even when a tall torso sets the base resolution.
                voxel = min(voxel, max(.0038, .0032 * min(hand_sizes)))
                budget = 44000
            detail_voxels = [.0028 * l["scale"] * l["tip_params"]["size"] for l in self.limbs
                             if l["tip"] in ("paw_padded", "foot_grasping")]
            detail_voxels += [.0034 * p["scale"] * p["params"]["size"] for p in self.recipe["parts"]
                              if p["part"] == "muzzle"]
            if detail_voxels:
                # Preserve the toe clefts and muzzle crease at ordinary
                # scales while bounding the voxel count on large creatures.
                width = max(v.x for v in verts) - min(v.x for v in verts)
                voxel = min(voxel, max(.0026, min(detail_voxels), max(width, height, length) / 700))
                budget = max(budget, 48000)
            finish.remesh(ob, voxel)
            finish.smooth(ob, 0.55, 5)
            blended = [limb for limb in self.limbs if limb.get("root_blend") and "ball_radius" not in limb]
            if blended:
                # Relax the ridge where the volumes meet while keeping nearby
                # anatomy and the rest of the limb out of the smoothing pass.
                points = np.empty(len(ob.data.vertices) * 3, dtype=np.float32)
                ob.data.vertices.foreach_get("co", points)
                points = points.reshape(-1, 3)
                weights = np.zeros(len(points), dtype=np.float32)
                for limb in blended:
                    radius = limb["radii"][0]
                    seat = limb["joints"][0] + limb["root_normal"] * (radius * 0.5)
                    center = np.asarray(kit.to_blender(seat))
                    d = np.linalg.norm(points - center, axis=1)
                    t = np.clip((1.65 * radius - d) / radius, 0, 1)
                    weights = np.maximum(weights, t * t * (3 - 2 * t) * limb["root_blend"])
                self.smooth_socket_group(ob, weights, 28)
            glute_legs = [limb for limb in self.limbs if limb.get("glute_shape")]
            if glute_legs:
                points = np.empty(len(ob.data.vertices) * 3, dtype=np.float32)
                ob.data.vertices.foreach_get("co", points)
                points = points.reshape(-1, 3)
                weights = np.zeros(len(points), dtype=np.float32)
                for limb in glute_legs:
                    radius = limb["radii"][0]
                    hip = kit.to_blender(limb["joints"][0])
                    seat = np.array((hip.x, hip.y + .52 * radius, hip.z - .15 * radius))
                    distance = np.linalg.norm(points - seat, axis=1) / radius
                    local = np.clip((1.73 - distance) / .95, 0, 1)
                    weights = np.maximum(weights, local ** 2 * (3 - 2 * local) * limb["glute_shape"])
                self.smooth_socket_group(ob, weights, 102)
            finish.decimate(ob, budget)
            ob.data.validate(clean_customdata=False)
        ob.data.shade_smooth()
        ob.data.materials.append(finish.clay_material())
        return ob

    @staticmethod
    def smooth_socket_group(ob, weights, iterations):
        group = ob.vertex_groups.new(name="Limb root smoothing")
        group_name = group.name
        weights = np.round(weights, 2)
        for weight in np.unique(weights[weights > 0]):
            group.add(np.flatnonzero(weights == weight).tolist(), float(weight), "REPLACE")
        finish.smooth(ob, 0.85, iterations, group_name)
        group = ob.vertex_groups.get(group_name)
        if group is not None:
            ob.vertex_groups.remove(group)

    def assemble(self, collection):
        rc = self.recipe
        name = rc["name"] or "Creature"
        col = collection or bpy.context.scene.collection
        skin = self.fuse(col)
        parts_ob = self.details_object(col, name)
        arm = self.armature(col, name)
        self.skin_weights(skin)
        for ob in (skin, parts_ob):
            if ob is None:
                continue
            ob.parent = arm
            mod = ob.modifiers.new("Armature", "ARMATURE")
            mod.object = arm
        legs = [l for l in self.limbs if l["role"] == "leg"]
        sv = [v.co for v in skin.data.vertices]
        rig = {
            "rest": [list(v) for v in self.rest], "parents": self.parents, "names": self.names,
            "spine": self.spine_bones, "hub": self.hub, "parts": self.parts_rig,
            "limbs": [{k: ([list(j) for j in v] if k == "joints" else (list(v) if isinstance(v, Vector) else v))
                       for k, v in l.items()} for l in self.limbs],
            "leg_len": sum(l["length"] for l in legs) / len(legs) if legs else 0.0,
            "body_len": self.spine.length, "body_h": self.spine.vh[self.hub], "hub_height": self.spine.vpos[self.hub].y,
            "body_w": max(self.spine.vw), "shift_y": self.shift_y,
        }
        if rc.get("gait") == "humanoid":
            rig["gait"] = "humanoid"
        if "locomotion" in rc:
            rig["locomotion"] = rc["locomotion"]
        if rc.get("construction") == "metaball":
            rig["construction"] = "metaball"
        tris = sum(len(p.vertices) - 2 for p in skin.data.polygons) + (sum(len(p.vertices) - 2 for p in parts_ob.data.polygons) if parts_ob else 0)
        report = {"name": name, "library_version": catalog.LIBRARY_VERSION, "warnings": self.warnings, "triangles": tris,
                  "bones": len(self.names), "legs": len(legs), "arms": sum(1 for l in self.limbs if l["role"] == "arm"),
                  "parts": len(self.parts_rig) + int(self.core is not None), "clearance": round(self.body_bottom(self.spine), 3),
                  "height": round(max(v.z for v in sv), 3), "length": round(max(v.y for v in sv) - min(v.y for v in sv), 3)}
        arm["polyforge_recipe"] = json.dumps(rc)
        arm["polyforge_rig"] = json.dumps(rig)
        arm["polyforge_report"] = json.dumps(report)
        return {"armature": arm, "skin": skin, "parts": parts_ob, "rig": rig, "report": report, "recipe": rc}

    def details_object(self, col, name):
        if not self.details:
            return None
        verts, faces, vbone = [], [], []
        for rv, rf, bone in self.details:
            o = len(verts)
            verts += rv
            vbone += bone if isinstance(bone, list) else [((bone, 1.0),)] * len(rv)
            faces += [tuple(i + o for i in f) for f in rf]
        ob = finish.new_object(name + "_parts", verts, faces, col)
        ob.data.shade_smooth()
        ob.data.materials.append(finish.clay_material())
        groups = {}
        for vi, weights in enumerate(vbone):
            for bone, weight in weights:
                groups.setdefault(bone, {}).setdefault(weight, []).append(vi)
        for bone, weights in groups.items():
            vg = ob.vertex_groups.new(name=self.names[bone])
            for weight, indices in weights.items():
                vg.add(indices, weight, "REPLACE")
        return ob

    # ------------------------------------------------- projections (numpy)
    def _project(self, P):
        """Vectorized body + limb projection for recipe-space points P (N x 3).
        Returns dict with body ring index and surface distance; nearest limb index,
        segment, t, surface distance."""
        S = [s for s in self.spine.samples if not s.get("tip")]
        sp = np.array([list(s["p"]) for s in S])
        st = np.array([list(s["t"]) for s in S])
        su = np.array([list(up_of(s["t"])) for s in S])
        sw = np.maximum(np.array([s["w"] for s in S]), 1e-3)
        sh = np.maximum(np.array([s["h"] for s in S]), 1e-3)
        rel = P[:, None, :] - sp[None]                      # N x S x 3
        along = np.einsum("nsk,sk->ns", rel, st)
        lx = rel[..., 0] / sw
        ly = np.einsum("nsk,sk->ns", rel, su) / sh
        th = np.arctan2(ly, lx)
        radial = np.hypot(lx * sw, ly * sh)
        surf = np.hypot(np.cos(th) * sw, np.sin(th) * sh)
        score = np.abs(radial - surf) + np.abs(along) * 2.0
        k = score.argmin(1)
        n = np.arange(len(P))
        body_d = (radial - surf)[n, k]
        out = {"v": np.array([S[i]["v"] for i in k]), "body_d": body_d,
               "limb": np.full(len(P), -1), "seg": np.zeros(len(P), int), "t": np.zeros(len(P)), "limb_d": np.full(len(P), np.inf)}
        for li, l in enumerate(self.limbs):
            J = [list(j) for j in l["joints"]]
            ext = l["joints"][-1] + (l["joints"][-1] - l["joints"][-2]).normalized() * max(l["radii"][-1] * 2.5, 0.05)
            J.append(list(ext))
            radii = list(l["radii"]) + [l["radii"][-1]]
            for s_ in range(len(J) - 1):
                a, b = np.array(J[s_]), np.array(J[s_ + 1])
                ab = b - a
                L2 = max(ab @ ab, 1e-9)
                t = np.clip(((P - a) @ ab) / L2, 0, 1)
                c = a + t[:, None] * ab
                r = radii[s_] + (radii[s_ + 1] - radii[s_]) * t
                d = np.linalg.norm(P - c, axis=1) - r
                better = d < out["limb_d"]
                out["limb_d"] = np.where(better, d, out["limb_d"])
                out["limb"] = np.where(better, li, out["limb"])
                out["seg"] = np.where(better, s_, out["seg"])
                out["t"] = np.where(better, t, out["t"])
        return out

    def skin_weights(self, skin):
        me = skin.data
        P = np.array([[v.co.x, v.co.z, -v.co.y] for v in me.vertices])
        weights = self.humanoid_weights(P) if self.recipe.get("gait") == "humanoid" else self.projected_weights(P)
        total = np.maximum(sum(weights.values()), 1e-8)
        for b, arr in weights.items():
            values = np.round(arr / total, 3)
            nz = np.flatnonzero(values > 0)
            if not len(nz):
                continue
            vg = skin.vertex_groups.get(self.names[b]) or skin.vertex_groups.new(name=self.names[b])
            for value in np.unique(values[nz]):
                vg.add(nz[values[nz] == value].tolist(), float(value), "REPLACE")

    @staticmethod
    def weight_transition(value):
        t = np.clip(value, 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)

    def chain_weights(self, limb, points, remaining):
        joints = np.asarray(limb["joints"])
        radii = limb["radii"]
        directions = np.diff(joints, axis=0)
        directions /= np.linalg.norm(directions, axis=1)[:, None]
        weights = {}
        for i, bone in enumerate(limb["bones"][:-1]):
            axis = directions[i].copy()
            if i + 1 < len(directions):
                bisector = axis + directions[i + 1]
                norm = np.linalg.norm(bisector)
                if norm > 1e-6:
                    axis = bisector / norm
            half_width = 1.6 * radii[i + 1]
            if i + 1 == len(directions) and limb["tip"] == "hand_basic":
                # Seat the wrist in the forearm and let the palm and
                # digits follow one bone beyond the short wrist blend.
                half_width = .025 * limb["scale"] * limb["tip_params"]["size"]
            fraction = self.weight_transition(.5 + ((points - joints[i + 1]) @ axis) / (2.0 * half_width))
            if i == 0 and "ball_radius" in limb:
                radius = limb["ball_radius"]
                distance = np.linalg.norm(points - joints[0], axis=1)
                fraction *= self.weight_transition((distance - 1.035 * radius) / (.15 * radius))
            supports = limb.get("joint_support", ())
            if i < len(supports):
                advance = self.weight_transition(2 * fraction)
                release = self.weight_transition(2 * fraction - 1)
                weights[supports[i]] = remaining * (advance - release)
                weights[bone] = remaining * (1.0 - advance)
                remaining = remaining * release
            else:
                weights[bone] = remaining * (1.0 - fraction)
                remaining = remaining * fraction
        weights[limb["bones"][-1]] = remaining

        return weights

    def humanoid_weights(self, points):
        """Continuous limb envelopes with a separate transition at each joint."""
        transition = self.weight_transition
        fused = [limb for limb in self.limbs if "ball_radius" not in limb]

        heights = [ring.y for ring in self.spine.vpos]
        upright = np.all(np.diff(heights) > 0)
        outside = (np.abs(points[:, 0]) - np.interp(points[:, 1], heights, self.spine.vw)) if upright else None
        envelopes = []
        for limb in fused:
            joints = np.asarray(limb["joints"])
            radii = limb["radii"]
            spans = np.diff(joints, axis=0)
            lengths = np.linalg.norm(spans, axis=1)
            directions = spans / lengths[:, None]
            root_offset = points - joints[0]
            along = root_offset @ directions[0]
            outward = root_offset @ np.asarray(limb["root_normal"])
            if limb["role"] == "arm":
                # A downward arm axis also points along the flank. Favor
                # the shoulder's outward direction so the flank stays put.
                seat = transition((.72 * outward + .28 * along + .22 * radii[0]) / (1.65 * radii[0]))
                if outside is not None:
                    # Keep the torso's influence at the shoulder. A clear
                    # forearm or hand must follow its own chain in full.
                    seat = np.maximum(seat, transition(outside / (1.35 * radii[0])))
            else:
                seat = transition((np.maximum(along, outward) + .50 * radii[0]) / (1.55 * radii[0]))
                if limb.get("glute_shape"):
                    r = radii[0]
                    rear = transition(-root_offset[:, 2] / (.85 * r))
                    drop = -root_offset[:, 1]
                    hip_width = max(abs(joints[0, 0]), .03)
                    own_side = transition((limb["side"] * points[:, 0] - .46 * hip_width) / (.48 * hip_width))
                    below_socket = transition((drop + .92 * r) / (1.13 * r))
                    seat = np.maximum(seat, limb["glute_shape"] * rear * own_side * below_socket)

            # The capsule distance is continuous even where two spans meet.
            extension = max(2.5 * radii[-1], .05)
            outer_radius = radii[-1]
            if limb["tip"] == "hand_basic":
                size = limb["scale"] * limb["tip_params"]["size"]
                extension = .23 * size
                # The wrist radius describes the forearm, not the width of
                # the palm and thumb. Give the hand its own distal envelope.
                outer_radius = .125 * size
            depth = np.full(len(points), np.inf)
            start_radii = radii if limb["tip"] != "hand_basic" else (*radii[:-1], outer_radius)
            for a, direction, length, start_radius, end_radius in zip(
                    joints, np.vstack((directions, directions[-1])),
                    (*lengths, extension), start_radii, (*radii[1:], outer_radius)):
                offset = points - a
                t = np.clip(offset @ direction / length, 0.0, 1.0)
                distance = np.linalg.norm(offset - (t * length)[:, None] * direction, axis=1)
                depth = np.minimum(depth, distance - (start_radius + t * (end_radius - start_radius)))
            margin = max(.025, (.74 if limb["role"] == "arm" else .5) * radii[0])
            if limb.get("glute_shape"):
                # Cover the protruding rear thigh while leaving pelvis and
                # the other leg outside this limb's binding envelope.
                upper_thigh = transition(1 - abs(drop - .42 * r) / (1.5 * r))
                depth -= .95 * r * limb["glute_shape"] * rear * own_side * upper_thigh
            envelopes.append(seat * (1.0 - transition((depth - .55 * margin) / margin)))

        influence = np.sum(envelopes, axis=0) if envelopes else np.zeros(len(points))
        normalizer = np.maximum(1.0, influence)
        weights = {}
        for limb, envelope in zip(fused, envelopes):
            weights.update(self.chain_weights(limb, points, envelope / normalizer))

        # Upright body rings use height, independently of limb proximity.
        n = len(self.spine_bones)
        if upright:
            position = np.interp(points[:, 1], heights, np.arange(n))
        else:
            position = np.clip(self._project(points)["v"], 0, n - 1)
        lower = position.astype(int)
        upper = np.minimum(lower + 1, n - 1)
        taper = transition(position - lower)
        body = 1.0 - influence / normalizer
        for i, bone in enumerate(self.spine_bones):
            weights[bone] = body * ((lower == i) * (1.0 - taper) + (upper == i) * taper)
        return weights

    def projected_weights(self, P):
        pr = self._project(P)
        nsp = len(self.spine_bones)
        v = np.clip(pr["v"], 0, nsp - 1)
        i0 = np.floor(v).astype(int)
        i1 = np.minimum(i0 + 1, nsp - 1)
        f = v - i0
        wsp = 1 - f * f * (3 - 2 * f)
        # Limb membership: smooth transition where limb and body surfaces meet.
        falloff = max(0.03, self.spine.vw[self.hub] * 0.18)
        wl = 1.0 / (1.0 + np.exp(-(pr["body_d"] - pr["limb_d"]) / falloff))
        wl = np.where(pr["limb"] >= 0, wl, 0.0)
        weights = {}

        def add(bone, idx, w):
            arr = weights.setdefault(bone, np.zeros(len(P)))
            np.add.at(arr, idx, w)
        allidx = np.arange(len(P))
        body = 1 - wl
        for k in range(nsp):
            sel = i0 == k
            add(self.spine_bones[k], allidx[sel], (body * wsp)[sel])
            sel = i1 == k
            add(self.spine_bones[k], allidx[sel], (body * (1 - wsp))[sel])
        for li, l in enumerate(self.limbs):
            sel = pr["limb"] == li
            if not sel.any():
                continue
            nb = len(l["bones"])
            seg = np.minimum(pr["seg"][sel], nb - 1)
            t = pr["t"][sel]
            idx = allidx[sel]
            w = wl[sel]
            # Blend across joints: near the start of a segment share with the previous bone.
            prev_share = np.where((seg > 0) & (t < 0.25), 0.5 * (1 - t / 0.25), 0.0)
            next_share = np.where((seg < nb - 1) & (t > 0.75), 0.5 * ((t - 0.75) / 0.25), 0.0)
            own = 1 - prev_share - next_share
            for b in range(nb):
                m = seg == b
                add(l["bones"][b], idx[m], (w * own)[m])
                m2 = (seg == b + 1)
                add(l["bones"][b], idx[m2], (w * prev_share)[m2])
                m3 = (seg == b - 1)
                add(l["bones"][b], idx[m3], (w * next_share)[m3])
        return weights

    def armature(self, col, name):
        data = bpy.data.armatures.new(name + "_rig")
        arm = bpy.data.objects.new(name + "_rig", data)
        col.objects.link(arm)
        view = bpy.context.view_layer
        prev = view.objects.active
        for o in view.objects:
            o.select_set(False)
        view.objects.active = arm
        arm.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        ebs = []
        for i, nm in enumerate(self.names):
            eb = data.edit_bones.new(nm)
            eb.head = kit.to_blender(self.rest[i])
            tail = kit.to_blender(self.tails[i])
            if (tail - eb.head).length < 1e-4:
                tail = eb.head + Vector((0, 0, 0.05))
            eb.tail = tail
            eb.roll = 0.0
            ebs.append(eb)
        for i, p in enumerate(self.parents):
            if p >= 0:
                ebs[i].parent = ebs[p]
        bpy.ops.object.mode_set(mode="OBJECT")
        view.objects.active = prev if prev else arm
        return arm


def build(src, quality="final", collection=None):
    if src.get("construction") == "metaball":
        from .metaball import MetaballBuilder

        return MetaballBuilder(src, quality).build(collection)
    if src.get("construction") == "solid":
        from .solid import SolidBuilder

        return SolidBuilder(src, quality).build(collection)
    return Builder(src, quality).build(collection)
