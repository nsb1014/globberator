"""Closed, rigid volumes assembled around the recipe's existing joint pivots."""

import math

from mathutils import Euler, Vector

from . import catalog, finish, kit
from .builder import Builder, frame


def segment(start, end, root_radius, tip_radius, sides=28, cap_rings=6):
    """A tapered solid with rounded ends concentric with both joint pivots."""
    axis = (end - start).normalized()
    basis = frame(axis, Vector((0, 0, 1)))
    cross_x = basis.col[0].copy()
    cross_y = -basis.col[2].copy()
    length = (end - start).length
    rings = []
    for i in range(1, cap_rings):
        theta = math.pi * i / (2 * cap_rings)
        rings.append((-root_radius * math.cos(theta), root_radius * math.sin(theta)))
    for i in range(9):
        t = i / 8
        eased = t * t * (3 - 2 * t)
        rings.append((t * length, kit.lerp(root_radius, tip_radius, eased)))
    for i in range(1, cap_rings):
        theta = math.pi * i / (2 * cap_rings)
        rings.append((length + tip_radius * math.sin(theta), tip_radius * math.cos(theta)))

    directions = [cross_x * math.cos(math.tau * i / sides) + cross_y * math.sin(math.tau * i / sides)
                  for i in range(sides)]
    vertices = [start + axis * height + direction * radius
                for height, radius in rings for direction in directions]
    faces = []
    for row in range(len(rings) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((row * sides + i, row * sides + j, (row + 1) * sides + j, (row + 1) * sides + i))
    poles = len(vertices)
    vertices.extend((start - axis * root_radius, end + axis * tip_radius))
    last = (len(rings) - 1) * sides
    for i in range(sides):
        j = (i + 1) % sides
        faces.extend(((poles, j, i), (poles + 1, last + i, last + j)))
    return vertices, faces


class SolidBuilder(Builder):
    rigid_surfaces = True

    def resolve_limbs(self, spine):
        super().resolve_limbs(spine)
        for limb in self.limbs:
            # Keep any authored hip inset, while all solid hips and hinges use
            # the same construction and require no secondary deformation bones.
            if "ball_radius" in limb:
                limb["root_radius"] = limb.pop("ball_radius")

    def spine_bone_at(self, v):
        return self.spine_bones[self.hub]

    def limb_prim(self, limb):
        family = catalog.get(limb.get("family"))
        if family and (limb["role"] not in ("leg", "tail")
                       or catalog.metadata(family).get("chain_skinning") == "smooth"):
            super().limb_prim(limb)
            return
        joints = limb["joints"]
        lengths = [(b - a).length for a, b in zip(joints, joints[1:])]
        spans = [lengths[0], *(min(a, b) for a, b in zip(lengths, lengths[1:])), lengths[-1]]
        radii = [min(authored, .48 * local) for authored, local in zip(limb["radii"], spans)]
        radii[0] = min(limb.get("root_radius", 1.13 * limb["radii"][0]), .73 * lengths[0])
        for i, (a, b) in enumerate(zip(joints, joints[1:])):
            vertices, faces = segment(a, b, radii[i], .91 * radii[i + 1])
            self.details.append((vertices, faces, limb["bones"][i]))
        self.family_foot(limb, radii[-1])

    def family_foot(self, limb, radius):
        if limb.get("family") and limb["role"] == "leg" and not limb["tip"]:
            if limb["family"] == "leg_plantigrade" and limb["params"].get("bare_foot", 1):
                self.plantigrade_tip(limb)
                return
            size = limb["scale"]
            ankle = limb["joints"][-1]
            sole = limb["sole_local"]
            height = max(-sole.y, .04 * size)
            foot = kit.Piece()
            foot.oval(ankle + Vector((sole.x, sole.y + height * .58, sole.z)),
                      (1.18 * radius, height * .58, max(1.48 * radius, abs(sole.z) + radius)))
            self.details.append((*foot.cage(), limb["bones"][-1]))

    def plantigrade_tip(self, limb):
        from .parts import Ctx
        from .parts.research_legs import plantigrade_foot

        sculpt = Ctx([])
        sculpt.setup(voxel=.0021, detail=2.35, smooth=.38)
        plantigrade_foot(sculpt, Vector())
        foot = sculpt.current
        vertices, faces = finish.finish_region(foot, foot.cur, *foot.cage(), ([], []))
        basis = Euler([math.radians(a) for a in limb["rot"]], "ZXY").to_matrix()
        size = limb["scale"] * limb["params"].get("size", 1)
        if limb["mirrored"]:
            faces = [tuple(reversed(face)) for face in faces]
        ankle = limb["joints"][-1]
        points = []
        for vertex in vertices:
            offset = basis @ (vertex * size)
            if limb["mirrored"]:
                offset.x = -offset.x
            points.append(ankle + offset)
        self.details.append((points, faces, limb["bones"][-1]))

    def fuse(self, collection):
        (vertices, faces), = self.skin_prims
        ob = finish.new_object(self.recipe["name"] + "_skin", vertices, faces, collection)
        ob.data.shade_smooth()
        ob.data.materials.append(finish.clay_material())
        return ob

    def skin_weights(self, skin):
        owner = skin.vertex_groups.new(name=self.names[self.spine_bones[self.hub]])
        owner.add(list(range(len(skin.data.vertices))), 1, "REPLACE")
