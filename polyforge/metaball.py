"""Construct a continuous soft mesh from Blender's bounded implicit ellipsoids."""

import json
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import catalog, finish, kit
from .builder import Builder, frame
from .solid import SolidBuilder
from .spine import up_of

ISO = .6
STIFFNESS = 2
# This overlap makes the iso-radius nearly constant between equal stations.
# At .6 / 2.0 the radii at a station and halfway to its neighbor differ < .1%.
CROSS_SECTION = .648
AXIAL_OVERLAP = 2.2
PILOT_BUDGET = 20000
COMPLEX_BUDGET = 40000


def field_ellipsoids(stations, caps=False):
    """Create one field element per station (position, tangent, up, width, height)."""
    result = []
    for i, (point, tangent, up, width, height) in enumerate(stations):
        left = stations[max(i - 1, 0)][0]
        right = stations[min(i + 1, len(stations) - 1)][0]
        spacing = ((point - left).length + (right - point).length) / (1 if i in (0, len(stations) - 1) else 2)
        along = max(AXIAL_OVERLAP * spacing, .007)
        if caps and i in (0, len(stations) - 1):
            along = max(along, min(width, height) * 1.55)
        basis = frame(tangent, up)
        result.append((point, basis, (width / CROSS_SECTION, along, height / CROSS_SECTION)))
    return result


def body_field(spine):
    start, stop = spine.ring_samples[1], spine.ring_samples[-2]
    first, last = spine.arc[start], spine.arc[stop]
    radii = sorted((*spine.vw, *spine.vh))
    spacing = max(.018, min(.13, radii[len(radii) // 2] * .42))
    count = max(2, math.ceil((last - first) * spine.length / spacing) + 1)
    stations = []
    for i in range(count):
        s = spine.at(kit.lerp(first, last, i / (count - 1)))
        stations.append((s["p"], s["t"], up_of(s["t"]), s["w"], s["h"]))
    return field_ellipsoids(stations, caps=True)


def limb_field(joints, radii, paired=False):
    stations = []
    directions = [(b - a).normalized() for a, b in zip(joints, joints[1:])]
    for i, (a, b) in enumerate(zip(joints, joints[1:])):
        spacing = max(.017, min(.09, (radii[i] + radii[i + 1]) * .24))
        subdivisions = max(1, math.ceil((b - a).length / spacing))
        for step in range(subdivisions):
            t = step / subdivisions
            direction = directions[i]
            if not step and i:
                direction = (directions[i - 1] + direction).normalized()
                if direction.length < .1:
                    direction = directions[i]
            radius = kit.lerp(radii[i], radii[i + 1], t)
            point = a.lerp(b, t)
            up, width = kit.UP, radius
            if paired and abs(direction.x) < .85:
                # Leave room between two similarly placed legs just outboard of
                # their shared host. Limit medial width while retaining depth.
                gain = kit.smoothstep(.08, .36, t) if i == 0 else 1.0
                width = kit.lerp(radius, min(radius, max(.66 * radius, abs(point.x) * .79)), gain)
                up = kit.RIGHT.cross(direction)
            stations.append((point, direction, up, width, radius))
    stations.append((joints[-1], directions[-1], kit.UP, radii[-1], radii[-1]))
    return field_ellipsoids(stations)


def create_skin(name, field, resolution, collection):
    """Polygonize an isolated field, removing the temporary Blender metaball."""
    data = bpy.data.metaballs.new("GlobberatorField")
    field_object = bpy.data.objects.new("GlobberatorField", data)
    collection.objects.link(field_object)
    data.threshold = ISO
    data.resolution = data.render_resolution = resolution
    try:
        for point, basis, dimensions in field:
            element = data.elements.new(type="ELLIPSOID")
            element.co = kit.to_blender(point)
            element.rotation = Matrix(tuple(kit.to_blender(col) for col in basis.col)).transposed().to_quaternion()
            element.radius = 1
            element.stiffness = STIFFNESS
            element.size_x, element.size_y, element.size_z = dimensions
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        mesh = bpy.data.meshes.new_from_object(field_object.evaluated_get(depsgraph))
    finally:
        bpy.data.objects.remove(field_object, do_unlink=True)
        bpy.data.metaballs.remove(data)
    if not len(mesh.polygons):
        bpy.data.meshes.remove(mesh)
        raise ValueError("Metaball field produced no surface")
    skin = bpy.data.objects.new(name, mesh)
    collection.objects.link(skin)
    return skin


def inspect_topology(mesh):
    """Count closed components and handles in the emitted surface."""
    parents = list(range(len(mesh.vertices)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    incidence = {}
    for poly in mesh.polygons:
        for edge in poly.edge_keys:
            incidence[edge] = incidence.get(edge, 0) + 1
    for edge in mesh.edges:
        a, b = edge.vertices
        parents[root(b)] = root(a)
    components = len({root(index) for index in range(len(parents))})
    chi = len(parents) - len(mesh.edges) + len(mesh.polygons)
    return {"components": components, "handles": max(0, (2 * components - chi) // 2),
            "nonmanifold_edges": sum(incidence.get(edge.key) != 2 for edge in mesh.edges)}


def triangle_count(faces):
    return sum(len(face) - 2 for face in faces)


def simplify(mesh_object, budget):
    triangles = triangle_count(poly.vertices for poly in mesh_object.data.polygons)
    if triangles > budget:
        modifier = mesh_object.modifiers.new("Triangle budget", "DECIMATE")
        modifier.ratio = budget / triangles
        finish.bake(mesh_object)


class MetaballBuilder(SolidBuilder):
    """Use the existing joints and attachments with a new soft-skin surface."""

    deform_surface_chains = True

    def __init__(self, src, quality="final"):
        super().__init__(src, quality)
        self.fields = []
        self.soft_chains = []
        self.body_bvh = None

    def spine_bone_at(self, v):
        return Builder.spine_bone_at(self, v)

    def make_bones(self):
        super().make_bones()
        for limb in self.limbs:
            if limb.get("joint_support") or limb["role"] in ("wing", "fin"):
                continue
            joints, bones = limb["joints"], limb["bones"]
            limb["joint_support"] = [
                self.add_bone(f"{limb['name']}_bend_{i}", bones[i], joints[i], joints[i + 1])
                for i in range(1, len(bones) - 1)
            ]

    def body_prim(self):
        if self.core:
            # Radial core members retain their authored high-curvature cages.
            return Builder.body_prim(self)
        field = body_field(self.spine)
        self.fields.extend(field)
        # Part placement uses the actual body field, independent of nearby limbs.
        body = create_skin("Mount Surface", field, self.spine.length / 150, bpy.context.scene.collection)
        try:
            self.body_bvh = BVHTree.FromPolygons(*finish.read_mesh(body))
        finally:
            finish.remove(body)

    def body_surface(self, sp, u, theta, offset=0.0):
        if self.body_bvh is None or self.core:
            return super().body_surface(sp, u, theta, offset)
        surface = sp.surface(u, theta)
        center = sp.at(u)["p"]
        direction = (surface["p"] - center).normalized()
        if direction.length < .5:
            direction = surface["n"]
        # Cast inward from beyond the skin; a cap station can start outside.
        reach = max(.12, 2.5 * (surface["p"] - center).length)
        point, normal, _, _ = self.body_bvh.ray_cast(center + direction * reach, -direction, reach)
        if point is None:
            point, normal, _, _ = self.body_bvh.find_nearest(surface["p"])
        surface.update(p=point + normal * offset, n=normal)
        return surface

    def limb_prim(self, limb):
        if self.core:
            # Authored radial cores keep their own surface representation and
            # fall through the existing builder for compatible appendages.
            return Builder.limb_prim(self, limb)
        joints, radii = limb["joints"], list(limb["radii"])
        part = catalog.get(limb.get("family"))
        metadata = catalog.metadata(part) if part else {}
        if part and limb["role"] in ("wing", "fin"):
            self.research_limb_prim(limb)
            if metadata.get("regions", {}).get("root") == "metaball":
                # The membrane carries its own skinning beyond the round shoulder.
                midpoint = joints[0].lerp(joints[1], .36)
                root_radii = (radii[0] * 1.12, radii[0] * .59)
                self.fields.extend(limb_field((joints[0], midpoint), root_radii))
                self.soft_chains.append((limb, (joints[0], midpoint), root_radii))
            return
        if part and (limb["role"] not in ("leg", "tail") or metadata["construction"] == "rigid"
                     or metadata.get("chain_skinning") == "smooth"):
            self.research_limb_prim(limb)
            return
        radii[0] = limb.get("root_radius", radii[0])
        paired_support = limb["role"] == "leg" and limb["side"] != 0 and not limb.get("single")
        self.fields.extend(limb_field(joints, radii, paired=paired_support))
        self.soft_chains.append((limb, joints, radii))
        self.family_foot(limb, radii[-1])

    def place_region(self, part, piece, slot, vertices, faces, bone):
        metadata = catalog.metadata(part)
        construction = metadata["regions"].get(slot, "rigid") if "regions" in metadata else metadata["construction"]
        if self.core or construction != "metaball" or piece != "self" or len(vertices) < 4:
            return super().place_region(part, piece, slot, vertices, faces, bone)
        # Soft facial volumes use their measured mesh envelope as a field
        # contributor. Hinges and detail regions keep their authored surfaces.
        points = np.asarray(vertices)
        _, axes = np.linalg.eigh(np.cov(points.T))
        if np.linalg.det(axes) < 0:
            axes[:, 0] *= -1
        coordinates = points @ axes
        lo, hi = coordinates.min(axis=0), coordinates.max(axis=0)
        center = Vector(axes @ ((lo + hi) / 2))
        radii = np.maximum((hi - lo) / 2, .006)
        self.fields.append((center, Matrix(axes.tolist()), radii / CROSS_SECTION))

    def fuse(self, collection):
        if self.core:
            return Builder.fuse(self, collection)
        resolution = max(.003, self.spine.length / (95 if self.quality == "preview" else 175))
        # Long, thin radial or vertical limbs also need bounded polygonization size.
        points = [point for point, _, _ in self.fields]
        extent = max(max(p[i] for p in points) - min(p[i] for p in points) for i in range(3))
        resolution = max(resolution, extent / 190)
        skin = create_skin(self.recipe["name"] + "_skin", self.fields, resolution, collection)
        self.polygonization = inspect_topology(skin.data)
        finish.smooth(skin, .45, 4)
        details = triangle_count(face for _, faces, _ in self.details for face in faces)
        self.triangle_budget = COMPLEX_BUDGET if len(self.limbs) > 4 or details > 10000 else PILOT_BUDGET
        budget = self.triangle_budget - min(details, self.triangle_budget // 2)
        simplify(skin, budget)
        self.detail_budget = self.triangle_budget - triangle_count(p.vertices for p in skin.data.polygons)
        skin.data.name = skin.name
        skin.data.shade_smooth()
        skin.data.materials.append(finish.clay_material())
        return skin

    def details_object(self, collection, name):
        details = super().details_object(collection, name)
        if details is None or self.core:
            return details
        original = details.data.copy()
        topology = inspect_topology(original)
        simplify(details, self.detail_budget)
        reduced = inspect_topology(details.data)
        if (reduced["components"], reduced["handles"]) != (topology["components"], topology["handles"]):
            # Keep the authored surfaces if simplification erases an entire
            # feature or closes a gap, such as the opening of a claw.
            failed = details.data
            details.data = original
            bpy.data.meshes.remove(failed)
            self.warnings.append("detail simplification changed feature topology; retained authored detail")
        else:
            bpy.data.meshes.remove(original)
        return details

    def assemble(self, collection):
        result = super().assemble(collection)
        report = result["report"]
        if self.core:
            report["skin_construction"] = "authored radial core"
        else:
            report["skin_construction"] = "metaball"
            topology = inspect_topology(result["skin"].data)
            report["skin_topology"] = topology
            report["triangle_budget"] = self.triangle_budget
            report["skin_topology_before_simplification"] = self.polygonization
            if topology != {"components": 1, "handles": 0, "nonmanifold_edges": 0}:
                self.warnings.append("metaball skin has disconnected, bridged or open topology: %s" % topology)
            if report["triangles"] > self.triangle_budget:
                self.warnings.append("triangle budget exceeded (%d of %d)" % (report["triangles"], self.triangle_budget))
        result["armature"]["polyforge_report"] = json.dumps(report)
        return result

    def skin_weights(self, skin):
        if self.core:
            return Builder.skin_weights(self, skin)
        points = np.asarray([(v.co.x, v.co.z, -v.co.y) for v in skin.data.vertices])
        # Start with the nearest spine section. Assign local transitions around
        # its pivots instead of interpolating through the full length of a span.
        projection = self._project(points)
        coordinate = projection["v"]
        distance = np.abs(coordinate - self.hub)
        half_width = .24
        inner = np.maximum(np.floor(distance - half_width).astype(int), 0)
        share = self.weight_transition((distance - inner - 1 + half_width) / (2 * half_width))
        sign = np.sign(coordinate - self.hub).astype(int)
        center = (self.hub + sign * inner).clip(0, len(self.spine_bones) - 1)
        towards = (center + sign).clip(0, len(self.spine_bones) - 1)
        weights = {bone: (center == i) * (1 - share) + (towards == i) * share
                   for i, bone in enumerate(self.spine_bones)}
        best = np.full(len(points), np.inf)
        owner = np.full(len(points), -1)
        ownership = []
        for index, (limb, joints, radii) in enumerate(self.soft_chains):
            depth = np.full(len(points), np.inf)
            for a, b, r0, r1 in zip(joints, joints[1:], radii, radii[1:]):
                a, b = np.asarray(a), np.asarray(b)
                span = b - a
                position = points - a
                t = np.clip((position @ span) / (span @ span), 0, 1)
                depth = np.minimum(depth, np.linalg.norm(position - t[:, None] * span, axis=1)
                                   - (r0 + t * (r1 - r0)))
            better = depth < best
            owner[better], best[better] = index, depth[better]
            ownership.append(depth)
        for index, (limb, joints, radii) in enumerate(self.soft_chains):
            select = owner == index
            if not np.any(select):
                continue
            radius = radii[0]
            depth = ownership[index][select]
            strength = self.weight_transition(.5 + (projection["body_d"][select] - depth) / max(.035, radius))
            segment = np.asarray(joints[1] - joints[0])
            length = np.linalg.norm(segment)
            distance = (points[select] - np.asarray(joints[0])) @ (segment / length)
            away_from_root = self.weight_transition(distance / min(.42 * length, .90 * radius))
            on_limb = 1 - self.weight_transition((depth - .12 * radius) / (.40 * radius))
            strength = np.maximum(strength, away_from_root * on_limb)
            for values in weights.values():
                values[select] *= 1 - strength
            if len(joints) != len(limb["joints"]):
                local = {limb["bones"][0]: strength}
            else:
                local = self.local_chain_weights(limb, points[select], strength)
            for bone, values in local.items():
                weights.setdefault(bone, np.zeros(len(points)))[select] += values
        self.bind_weights(skin, weights)

    def local_chain_weights(self, limb, points, strength):
        joints = np.asarray(limb["joints"])
        radii = limb["radii"]
        spans = np.diff(joints, axis=0)
        lengths = np.linalg.norm(spans, axis=1)
        directions = spans / lengths[:, None]
        bones = limb["bones"]
        helpers = limb.get("joint_support", ())
        weights = {}
        remaining = strength
        for i, (bone, axis) in enumerate(zip(bones, directions)):
            width = min(.56 * radii[i + 1], .30 * lengths[i])
            if i + 1 < len(directions):
                width = min(width, .30 * lengths[i + 1])
                bisector = axis + directions[i + 1]
                if np.linalg.norm(bisector) > .05:
                    axis = bisector / np.linalg.norm(bisector)
            advance = self.weight_transition(.5 + ((points - joints[i + 1]) @ axis) / max(.01, 2 * width))
            if i < len(helpers):
                mid = self.weight_transition(2 * advance)
                out = self.weight_transition(2 * advance - 1)
                weights[bone] = remaining * (1 - mid)
                weights[helpers[i]] = remaining * (mid - out)
                remaining = remaining * out
            else:
                weights[bone] = remaining * (1 - advance)
                remaining = remaining * advance
        weights[bones[-1]] = remaining
        return weights

    def bind_weights(self, skin, weights):
        owners = list(weights)
        values = np.stack(list(weights.values()), axis=1)
        best = np.argsort(values, axis=1)[:, -4:]
        keep = np.zeros_like(values)
        rows = np.arange(len(values))[:, None]
        keep[rows, best] = values[rows, best]
        keep /= np.maximum(keep.sum(axis=1, keepdims=True), 1e-8)
        for bone, column in zip(owners, keep.T):
            rounded = np.round(column, 4)
            selected = np.flatnonzero(rounded > 0)
            if not len(selected):
                continue
            group = skin.vertex_groups.new(name=self.names[bone])
            for value in np.unique(rounded[selected]):
                group.add(selected[rounded[selected] == value].tolist(), float(value), "REPLACE")
