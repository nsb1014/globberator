"""Check emitted anatomy meshes and their normal build and animation paths.

blender -b -t 2 --python-exit-code 1 -P tools/tests/anatomy_parts.py
"""

from copy import deepcopy
from itertools import product
from pathlib import Path
import math
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from polyforge import builder, catalog, export, finish, recipe
from polyforge.animator import Animator, write_pose


def region_mesh(vertices, faces, components):
    assert vertices and all(math.isfinite(c) for v in vertices for c in v)
    mesh = bmesh.new()
    try:
        for point in vertices:
            mesh.verts.new(point)
        mesh.verts.ensure_lookup_table()
        for face in faces:
            mesh.faces.new([mesh.verts[i] for i in face])
        assert all(edge.is_manifold and edge.is_contiguous for edge in mesh.edges)
        assert mesh.calc_volume(signed=True) > 0
        remaining, count = set(mesh.verts), 0
        while remaining:
            stack = [remaining.pop()]
            count += 1
            while stack:
                vertex = stack.pop()
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other in remaining:
                        remaining.remove(other)
                        stack.append(other)
        assert count == components, (count, components)
    finally:
        mesh.free()


def projected_gape(regions, section):
    """Cast from below the muzzle to the upper lip and from above to the lower lip."""
    upper, lower = (BVHTree.FromPolygons(v, f) for v, f in regions)
    tip = upper.ray_cast(Vector((0, -1, section)), Vector((0, 1, 0)))[0]
    lower_tip = lower.ray_cast(Vector((0, 1, section)), Vector((0, -1, 0)))[0]
    assert tip is not None and lower_tip is not None
    return tip.y - lower_tip.y


def test_part(part):
    axes = [key for key in part.params if key != "size"]
    extremes = []
    corners = list(product(*(part.params[key][:2] for key in axes)))
    for index, values in enumerate(corners):
        scale = (part.params["size"][0] if index == 0 else
                 part.params["size"][1] if index == len(corners) - 1 else 1)
        extremes.append(dict(zip(axes, values), size=scale))
    for params in [part.defaults(), *extremes]:
        _, regions = finish.part_regions(part, params)
        assert set(regions) == {"self", "jaw"}
        solids = []
        for piece in ("self", "jaw"):
            for slot, vertices, faces in regions[piece]:
                try:
                    region_mesh(vertices, faces, 2 if slot == "detail" else 1)
                except AssertionError as error:
                    raise AssertionError((part.id, params, piece, slot, *error.args)) from error
                if slot != "detail":
                    solids.append(([point / params["size"] for point in vertices], faces))
        axis = 2 if part.id == "head_bovine" else 1
        cutoff = .36 if axis == 2 else .174
        surfaces = [BVHTree.FromPolygons(v, f) for v, f in solids]
        overlaps = surfaces[0].overlap(surfaces[1])
        assert overlaps, (part.id, params, "missing hinge contact")
        for overlap in overlaps:
            for (vertices, faces), index in zip(solids, overlap):
                if min(vertices[v][axis] for v in faces[index]) < cutoff:
                    break
            else:
                raise AssertionError((part.id, params, "distal collision"))
        if axis == 2:
            gape = projected_gape(solids, max(v.z for v in solids[1][0]) - .068)
            assert .002 < gape < .055, (part.id, params, gape)


def authored_fixture(construction="solid"):
    source = recipe.default_recipe()
    source["name"] = "Anatomy hinges"
    source["construction"] = construction
    source["parts"] = [{"uid": "head", "part": "head_bovine", "u": .993, "theta": -90, "offset": -.17}]
    source["limbs"] = [{"uid": "cheliped", "u": .69, "theta": 0, "segments": [[.27, .04, .23], [.02, 0, .22]],
                        "radii": [.078, .060, .042], "tip": "pincer_crescent"}]
    return source


def jaw_samples(rig):
    head = next(part for part in rig["parts"] if part["uid"] == "head")
    yield "roar", .90, head["bone"], head["jaws"][0], Vector((0, -.29, .505)), Vector((0, -1, 0))
    for limb in rig["limbs"]:
        if limb["uid"] != "cheliped":
            continue
        frame = Matrix(limb["tip_frame"])
        clip, phase = ("grasp", .70) if rig.get("construction") == "metaball" else ("roar", .90)
        yield clip, phase, limb["bones"][-1], limb["jaws"][0], frame @ Vector((.027, .29, 0)), frame @ Vector((1, 0, 0))


def check_motion(rig):
    for clip, phase, host, hinge, landmark, opening in jaw_samples(rig):
        animator = Animator(deepcopy(rig))
        assert rig["parents"][hinge["bone"]] == host and animator.play(clip)
        animator.advance_to(phase)
        transforms = animator.deform_matrices()
        child_motion, host_motion = transforms[hinge["bone"]], transforms[host]
        pivot = Vector(rig["rest"][hinge["bone"]])
        assert (child_motion @ pivot - host_motion @ pivot).length < 1e-5
        world_landmark = Vector(rig["rest"][host]) + landmark
        delta = host_motion.inverted() @ (child_motion @ world_landmark) - world_landmark
        assert delta.dot(opening) > .05, (clip, delta[:])


def mesh_for_group(obj, name=None, posed=False):
    drawn = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if posed else obj
    points = [drawn.matrix_world @ vertex.co for vertex in drawn.data.vertices]
    polygons = [tuple(poly.vertices) for poly in drawn.data.polygons]
    if name is not None:
        group = obj.vertex_groups[name].index
        attached = {vertex.index for vertex in obj.data.vertices
                    if any(g.group == group and g.weight == 1 for g in vertex.groups)}
        polygons = [face for face in polygons if all(index in attached for index in face)]
    assert polygons, (obj.name, name)
    return BVHTree.FromPolygons(points, polygons)


def check_solid_attachment(result):
    rig, parts = result["rig"], result["parts"]
    torso = mesh_for_group(result["skin"])
    skull = mesh_for_group(parts, "P_head")
    assert torso.overlap(skull), "Skull lost neck contact"
    for limb in rig["limbs"]:
        forearm, claw = (mesh_for_group(parts, rig["names"][bone]) for bone in limb["bones"][-2:])
        assert forearm.overlap(claw), (limb["name"], "Wrist lost pincer contact")


def check_open_claw_fit(result):
    rig = result["rig"]
    animation = Animator(deepcopy(rig))
    assert animation.play("grasp")
    animation.advance_to(.70)
    write_pose(result["armature"], animation)
    bpy.context.view_layer.update()
    host = mesh_for_group(result["skin"], posed=True)
    for limb in rig["limbs"]:
        jaw = mesh_for_group(result["parts"], rig["names"][limb["jaws"][0]["bone"]], posed=True)
        assert not host.overlap(jaw), (limb["name"], "Open finger collides with host")
    for bone in result["armature"].pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def test_build(construction):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = builder.build(authored_fixture(construction))
    rig, arm, parts = (result[key] for key in ("rig", "armature", "parts"))
    assert not result["report"]["warnings"], result["report"]["warnings"]
    samples = list(jaw_samples(rig))
    assert len(samples) == 3  # one skull jaw and both claw fingers
    check_motion(rig)
    if construction == "solid":
        check_solid_attachment(result)
    else:
        check_open_claw_fit(result)
    for collection, selector in (("parts", lambda item: item["uid"] == "head"),
                                 ("limbs", lambda item: item["uid"] == "cheliped" and item["mirrored"])):
        wrong = deepcopy(rig)
        hinge = next(item for item in wrong[collection] if selector(item))["jaws"][0]
        hinge["axis"] = [-value for value in hinge["axis"]]
        try:
            check_motion(wrong)
        except AssertionError:
            pass
        else:
            raise AssertionError("Reversed jaw opening passed")

    for _, _, host, hinge, _, _ in samples:
        name = rig["names"][hinge["bone"]]
        host_name = rig["names"][host]
        assert arm.data.bones[name].parent.name == host_name
        group = parts.vertex_groups[name].index
        attached = [v for v in parts.data.vertices if any(g.group == group for g in v.groups)]
        assert attached and all(len(v.groups) == 1 and v.groups[0].weight == 1.0 for v in attached)

    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "anatomy.glb")
        export.export(result, path, animated=False)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        assert "FINISHED" in bpy.ops.import_scene.gltf(filepath=path)
        imported = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
        for _, _, host, hinge, _, _ in samples:
            assert imported.data.bones[rig["names"][hinge["bone"]]].parent.name == rig["names"][host]


if __name__ == "__main__":
    for part_id in ("head_bovine", "pincer_crescent"):
        test_part(catalog.get(part_id))
    for construction in ("solid", "metaball"):
        test_build(construction)
    print("Anatomy part geometry, fit, articulation, and GLB reimport passed.")
