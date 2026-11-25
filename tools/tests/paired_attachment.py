"""Blender regression check for mirrored attachments and the bull's recipe.

Run with blender -b --python-exit-code 1 -P tools/tests/paired_attachment.py.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

tools = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(tools))
from attachments import attach_mirrored
from limb_parts import CATALOG

recipe = json.loads((tools.parent/"models/bull.json").read_text())
fore = recipe["attachments"]["shoulders"]
assert set(recipe["attachments"]) == {"shoulders","hips"}
part = CATALOG[fore["part"]]
# Socket-local joints stay fixed when the sculpt changes.
lean_joints,lean = part(fore["profile"],0)
full_joints,full = part(fore["profile"],1)
assert lean_joints == full_joints and max(r[3] for r in full) > max(r[3] for r in lean)

def reflect(v):
    return Vector((-v.x,v.y,v.z))

def close(actual,expected):
    return (actual-expected).length < 1e-5

# An asymmetric surface with its own local transform exposes reversed winding,
# mirroring about the part origin, and double application of the socket offset.
for x in (.5,1.3):
    mesh = bpy.data.meshes.new("Probe")
    mesh.from_pydata([(0,0,0),(.23,.03,0),(.04,.07,.51)],[],[(0,1,2)])
    obj = bpy.data.objects.new("Probe",mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (.12,-.29,.14)
    socket = Matrix.Translation((x,-1.1,2)) @ Matrix.Rotation(math.radians(27),4,'Y')
    expected = [socket @ (v.co+obj.location) for v in mesh.vertices]
    left,right = attach_mirrored([obj],socket)
    for placement,vertices in [(left,expected),(right,list(map(reflect,expected)))]:
        side,mount,items = placement
        emitted = items[0].data.vertices
        assert all(close(v.co,p) for v,p in zip(emitted,vertices,strict=True))
        assert all(close(mount@p, socket@p if side=="L" else reflect(socket@p)) for p in full_joints)
    a,b = left[2][0].data,right[2][0].data
    assert close(b.polygons[0].normal,reflect(a.polygons[0].normal))
    b.flip_normals()
    assert not close(b.polygons[0].normal,reflect(a.polygons[0].normal))
    b.flip_normals()
    b.vertices[0].co.x += .04
    assert close(a.vertices[0].co,expected[0]) and not close(b.vertices[0].co,reflect(expected[0]))

print("PASS: one sided part, two transformed placements, outward winding and independent meshes.")
