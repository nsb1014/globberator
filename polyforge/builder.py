"""Recipe -> Blender creature.

Produces, in a collection:
  <name>_rig    armature (rest pose = neutral stance), recipe + rig data as custom props
  <name>_skin   ONE fused sculpted surface: body sweep, limbs and every skin-slot part
                region (bulges, brows, cheeks, lids, paws, hands...) voxel-remeshed together,
                smoothed and decimated, with vertex-painted patterns
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
FIXED = {"white": "#f3efe6", "black": "#141414", "dark": "#2c2220", "horn": "#dccb9f", "claw": "#2e2724", "teeth": "#f1e9cf", "eye": "#e6c13a"}


def hex_rgb(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]


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


def part_sole(part, params, basis=None):
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
        return Vector((0, -0.1, 0))
    lo = min(p.y for p in pts)
    low = [p for p in pts if p.y < lo + 0.012]
    c = sum(low, Vector((0, 0, 0))) / len(low)
    return Vector((c.x, lo, c.z))


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
    def __init__(self, src, quality="final"):
        self.recipe, self.warnings = R.normalize(src)
        self.quality = quality
        self.names, self.parents, self.rest, self.tails = [], [], [], []
        self.limbs, self.parts_rig = [], []
        self.skin_prims = []        # [(verts, faces)] recipe coords
        self.details = []           # [(slot, verts, faces, bone)]
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
            if family and family.cap == "foot":
                role = "leg"
                sole = part_sole(family, l["params"], rotation) * scale - (joints[-1] - hip)
            elif family and family.cap in ("hand", "grasp"):
                role = "arm"
            elif family and family.cap == "flap":
                role = "wing"
            if part is not None:
                if part.cap == "foot":
                    role, sole = "leg", part_sole(part, l["tip_params"]) * scale
                elif part.cap in ("hand", "grasp"):
                    role = "arm"
            if l["motion"] == "tail":
                role = "tail"
            length = sum((joints[k] - joints[k - 1]).length for k in range(1, len(joints)))
            # Off the midline, or on it with a shape that bends sideways: build a
            # reflected twin so the creature stays symmetric (a sideways leg on the
            # midline would otherwise be a single lopsided limb). Authored geometry is kept.
            bends = any(abs(j.x - hip.x) > 1e-4 for j in joints[1:])
            lateral = abs(abs(l["theta"]) - 90.0) > 1e-4 or (bends and not family)
            base = {"uid": l["uid"], "name": l["uid"], "u": l["u"], "v": s["v"], "joints": joints, "radii": radii,
                    "tip": l["tip"], "tip_params": l["tip_params"], "role": role, "has_foot": role == "leg",
                    "scale": scale, "sole_local": sole, "length": length, "mirrored": False,
                    "side": 1.0 if lateral else 0.0}
            if family:
                base.update(family=family.id, params=l["params"], rot=l["rot"])
            self.limbs.append(base)
            if lateral:          # off the midline -> reflected twin (automatic)
                m = dict(base)
                m["joints"] = [Vector((-j.x, j.y, j.z)) for j in joints]
                m["name"] = l["uid"] + "_m"
                m["mirrored"] = True
                m["side"] = -base["side"]
                m["sole_local"] = Vector((-sole.x, sole.y, sole.z))
                self.limbs.append(m)
        for l in self.limbs:
            l["sole"] = l["joints"][-1] + l["sole_local"]

    def ground_level(self, sp):
        lowest = self.body_bottom(sp)
        foot_low = min([l["sole"].y for l in self.limbs if l["has_foot"]] or [float("inf")])
        for l in self.limbs:
            if l["role"] not in ("arm", "tail", "wing"):
                lowest = min(lowest, l["sole"].y)
        ground = foot_low if foot_low < float("inf") else lowest
        ground = self.recipe.get("ground_y", ground)
        for l in self.limbs:
            if l["role"] in ("arm", "tail", "wing"):
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
        J, rad = l["joints"], l["radii"]
        d0 = (J[1] - J[0]).normalized()
        pts, rr = [J[0] - d0 * rad[0] * 0.7], [rad[0] * 0.85]
        for k in range(len(J) - 1):
            bulge = 1.18 if k < len(J) - 2 else 1.08
            pts += [J[k], J[k].lerp(J[k + 1], 0.45)]
            rr += [rad[k], (rad[k] + rad[k + 1]) * 0.5 * bulge]
        pts.append(J[-1])
        rr.append(rad[-1])
        pc = kit.Piece()
        pc.loft(pts, rr, sides=24, density=4)
        self.skin_prims.append(pc.cage())

    def research_limb_prim(self, limb):
        part = catalog.get(limb["family"])
        rotation = Euler([math.radians(a) for a in limb["rot"]], "ZXY").to_matrix()
        basis = rotation @ Matrix.Diagonal((limb["scale"],) * 3)
        if limb["mirrored"]:
            basis = MIRROR.to_3x3() @ basis
        matrix = xform(basis, limb["joints"][0])
        params = limb["params"]
        if part.id == "pincer_limb" and limb["mirrored"] and params["asymmetry"]:
            params = {**params, "_mirrored": True}
        ctx, regions = finish.part_regions(part, params, assembly=True)
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
                if slot == "skin":
                    self.skin_prims.append((verts, faces))
                    continue
                bind = hinged.get(name)
                if bind is None:
                    if part.id == "tail_segmented" and slot == "accent":
                        bind = shell_weights(verts, faces, joints, bones)
                    else:
                        bind = limb_weights(verts, joints, bones)
                self.details.append((slot, verts, faces, bind))
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
        ctx, regions = finish.part_regions(part, params, assembly=True)
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
                if slot == "skin":
                    self.skin_prims.append((verts, faces))
                    if pn != "self":
                        self.warnings.append("%s: skin on a hinged piece is fused rigidly" % part.id)
                else:
                    self.details.append((slot, verts, faces, bone_of.get(pn, pb)))
        F = M.to_3x3().normalized()
        self.parts_rig.append({"uid": uid, "part": part.id, "category": part.category, "cap": part.cap, "bone": pb,
                               "parent": parent_bone, "frame": [list(r) for r in F], "mirrored": mirrored, "jaws": jaws, "u": u})
        return pb, jaws

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
            twin = (not on_limb and abs(abs(p["theta"]) - 90.0) > 1e-3) or (on_limb and (l["side"] != 0.0 or abs(s["p"].x) > 1e-4))
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
                palm = -RIGHT + BACK * .35 if part.orient == "palm_in" and l["side"] else BACK
                if l["mirrored"]:
                    od = Vector((-d.x, d.y, d.z))
                    M = MIRROR @ xform(frame(od, palm), Vector((-end.x, end.y, end.z)))
                else:
                    M = xform(frame(d, palm), end)
            M = M @ Matrix.Scale(l["scale"], 4)
            end_bone = l["bones"][-1]
            ctx, regions = finish.part_regions(part, l["tip_params"], assembly=True)
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
                    if slot == "skin":
                        self.skin_prims.append((verts, faces))
                    else:
                        self.details.append((slot, verts, faces, bone_of.get(pn, end_bone)))
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
            finish.decimate(ob, budget)
        ob.data.shade_smooth()
        return ob

    def assemble(self, collection):
        rc = self.recipe
        name = rc["name"] or "Creature"
        col = collection or bpy.context.scene.collection
        skin = self.fuse(col)
        parts_ob = self.details_object(col, name)
        arm = self.armature(col, name)
        self.paint(skin, parts_ob)
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
        verts, faces, fslot, vbone = [], [], [], []
        for slot, rv, rf, bone in self.details:
            o = len(verts)
            verts += rv
            vbone += bone if isinstance(bone, list) else [((bone, 1.0),)] * len(rv)
            faces += [tuple(i + o for i in f) for f in rf]
            fslot += [slot] * len(rf)
        ob = finish.new_object(name + "_parts", verts, faces, col)
        slots = sorted(set(fslot))
        for s in slots:
            ob.data.materials.append(self.material(s))
        sidx = {s: i for i, s in enumerate(slots)}
        mi = [sidx[s] for s in fslot]
        ob.data.polygons.foreach_set("material_index", mi)
        ob.data.shade_smooth()
        # Corner colours mirror the slot colours so viewport/Workbench "attribute" shading
        # and engines that read vertex colours show the paint.
        cols = [hex_rgb(self.recipe["paint"][s] if s in ("base", "accent", "detail") else FIXED.get(s, "#888888")) for s in slots]
        attr = ob.data.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        flat = []
        for poly in ob.data.polygons:
            c = cols[poly.material_index]
            flat += (c + [1.0]) * poly.loop_total
        attr.data.foreach_set("color", flat)
        groups = {}
        for vi, weights in enumerate(vbone):
            for bone, weight in weights:
                groups.setdefault(bone, {}).setdefault(weight, []).append(vi)
        for bone, weights in groups.items():
            vg = ob.vertex_groups.new(name=self.names[bone])
            for weight, indices in weights.items():
                vg.add(indices, weight, "REPLACE")
        return ob

    def material(self, slot):
        pa = self.recipe["paint"]
        key = "PF_%s_%s" % (slot, (pa.get(slot) if slot in ("base", "accent", "detail") else FIXED.get(slot, "#888888")).lstrip("#"))
        m = bpy.data.materials.get(key)
        if m is None:
            m = bpy.data.materials.new(key)
            col = hex_rgb(pa[slot] if slot in pa else FIXED.get(slot, "#888888"))
            m.diffuse_color = (*col, 1.0)
            m.roughness = 0.85
            m.use_nodes = True
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            bsdf.inputs["Base Color"].default_value = (*col, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.85
        return m

    def skin_material(self):
        old = bpy.data.materials.get("PF_skin")
        if old is not None and old.users == 0:
            bpy.data.materials.remove(old)      # reuse the name instead of PF_skin.001, .002, ...
        m = bpy.data.materials.new("PF_skin")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        bsdf.inputs["Roughness"].default_value = 0.85
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
        m.diffuse_color = (*hex_rgb(self.recipe["paint"]["base"]), 1.0)
        return m

    # ------------------------------------------------- projections (numpy)
    def _project(self, P):
        """Vectorized body + limb projection for recipe-space points P (N x 3).
        Returns dict with body u, theta, v, surface distance; nearest limb index,
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
        out = {"u": np.array([S[i]["u"] for i in k]), "theta": np.degrees(th[n, k]), "v": np.array([S[i]["v"] for i in k]), "body_d": body_d,
               "limb": np.full(len(P), -1), "seg": np.zeros(len(P), int), "t": np.zeros(len(P)), "limb_d": np.full(len(P), np.inf), "lt": np.zeros(len(P))}
        for li, l in enumerate(self.limbs):
            J = [list(j) for j in l["joints"]]
            ext = l["joints"][-1] + (l["joints"][-1] - l["joints"][-2]).normalized() * max(l["radii"][-1] * 2.5, 0.05)
            J.append(list(ext))
            radii = list(l["radii"]) + [l["radii"][-1]]
            acc = 0.0
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
                seg_len = math.sqrt(L2)
                out["lt"] = np.where(better, (acc + t * seg_len) / max(l["length"], 1e-3), out["lt"])
                acc += seg_len
        return out

    def paint(self, skin, parts_ob):
        pa = self.recipe["paint"]
        me = skin.data
        me.materials.append(self.skin_material())
        P = np.array([[v.co.x, v.co.z, -v.co.y] for v in me.vertices])
        pr = self._project(P)
        base, acc, det = (np.array(hex_rgb(pa[k])) for k in ("base", "accent", "detail"))
        sc = pa["pattern_scale"]
        on_limb = pr["limb_d"] < pr["body_d"] - 0.01
        u, th = pr["u"], np.radians(pr["theta"])
        s = np.sin(th)
        col = np.tile(base, (len(P), 1))
        mask = np.zeros(len(P), bool)
        pat = pa["pattern"]
        lt = pr["lt"]

        def h2(a, b):
            x = (a * 92821 + b * 68917 + 17) * 374761393 + 668265263
            x = (x ^ (x >> 13)) * 1274126177
            return ((x & 0xFFFF) / 65535.0)
        if pat == "stripes":
            mask = np.where(on_limb, (lt * 3 * sc) % 1.0 < 0.35, (s > -0.3) & ((u * 9 * sc) % 1.0 < 0.38) & (u > 0.08) & (u < 0.92))
        elif pat in ("spots", "patches"):
            cu = np.floor(u * (14 if pat == "spots" else 5) * sc).astype(np.int64)
            ct = np.floor((pr["theta"] + 180) / (36 if pat == "spots" else 72)).astype(np.int64)
            thr = 0.72 if pat == "spots" else 0.55
            mask = (h2(cu, ct) > thr) & ((s > -0.4) | (pat == "patches"))
            mask &= ~on_limb | (h2(np.floor(lt * 6 * sc).astype(np.int64), pr["limb"].astype(np.int64)) > 0.7)
        col[mask] = acc
        if pat == "gradient":
            f = np.clip((s + 1) * 0.5, 0, 1)[:, None]
            col = np.where(on_limb[:, None], base + (acc - base) * np.clip(lt, 0, 1)[:, None], acc + (base - acc) * f)
        if pa["belly"]:
            col[(~on_limb) & (s < -0.5)] = det
        attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        rgba = np.hstack([col, np.ones((len(P), 1))]).astype(np.float32)
        attr.data.foreach_set("color", rgba.ravel())

    def skin_weights(self, skin):
        me = skin.data
        P = np.array([[v.co.x, v.co.z, -v.co.y] for v in me.vertices])
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
        total = sum(weights.values())
        total = np.where(total > 1e-8, total, 1.0)
        for b, arr in weights.items():
            arr = arr / total
            nz = np.nonzero(arr > 1e-3)[0]
            if not len(nz):
                continue
            vg = skin.vertex_groups.get(self.names[b]) or skin.vertex_groups.new(name=self.names[b])
            for val in np.unique(np.round(arr[nz], 3)):
                ids = nz[np.round(arr[nz], 3) == val].tolist()
                vg.add(ids, float(val), "REPLACE")

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
    return Builder(src, quality).build(collection)
