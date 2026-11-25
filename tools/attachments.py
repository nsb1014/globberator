"""Place an authored part at a socket and reflect its partner across the host's X=0 plane."""
import bpy
from mathutils import Matrix


def attach_mirrored(objects, socket):
    """Return (side, mount matrix, placed meshes) for geometry and rig binding.

    The canonical meshes are in part space. Preserve their individual transforms
    (for example, a foot under a leg). Bake the reflection before skinning so the
    engine can animate both sides with ordinary, positive-scale bones.
    """
    bpy.context.view_layer.update()
    local = [obj.matrix_world.copy() for obj in objects]
    reflected = Matrix.Diagonal((-1,1,1,1)) @ socket
    twins = []
    for obj in objects:
        twin = obj.copy()
        twin.data = obj.data.copy()
        bpy.context.collection.objects.link(twin)
        twins.append(twin)
    placements = (("L",socket,objects),("R",reflected,twins))
    for _,mount,meshes in placements:
        for obj,part_transform in zip(meshes,local,strict=True):
            if obj.data.users > 1:
                obj.data = obj.data.copy()
            transform = mount @ part_transform
            obj.data.transform(transform)
            if transform.to_3x3().determinant() < 0:
                obj.data.flip_normals()
            obj.matrix_world = Matrix.Identity(4)
    return placements
