"""Mount a socket-local part in the host's rest frame (Blender X is lateral)."""
import bpy
from mathutils import Matrix

CENTER_EPSILON = 1e-5
REFLECTION = Matrix.Diagonal((-1, 1, 1, 1))


def attach_part(objects, socket, author_origin=(0, 0, 0)):
    """Return (side, authored-to-host matrix, meshes) for every placement.

    A socket on the midline produces one part, even if its geometry bends away.
    A lateral socket produces a reflected partner. Source geometry can be
    socket-local or use an explicit anchor in an existing sculpt's coordinates.
    """
    x = socket.translation.x
    mount = socket @ Matrix.Translation(author_origin).inverted()
    placements = [("C", mount, objects)]
    if abs(x) > CENTER_EPSILON:
        twins = []
        for obj in objects:
            twin = obj.copy()
            twin.data = obj.data.copy()
            bpy.context.collection.objects.link(twin)
            twins.append(twin)
        side, other = ("L", "R") if x > 0 else ("R", "L")
        placements = [(side, mount, objects), (other, REFLECTION @ mount, twins)]

    bpy.context.view_layer.update()
    local = [obj.matrix_world.copy() for obj in objects]
    for _, transform, meshes in placements:
        for obj, part_transform in zip(meshes, local, strict=True):
            if obj.data.users > 1:
                obj.data = obj.data.copy()
            baked = transform @ part_transform
            obj.data.transform(baked)
            if baked.to_3x3().determinant() < 0:
                obj.data.flip_normals()
            obj.matrix_world = Matrix.Identity(4)
    return placements


def attach_mirrored(objects, socket):
    """Legacy entry point for socket-local geometry."""
    return attach_part(objects, socket)
