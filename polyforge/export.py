"""Export a built creature for any engine: glb/gltf, fbx, usd/usdz/usdc, obj, blend."""
import os

import bpy

FORMATS = ("glb", "gltf", "fbx", "usd", "usdc", "usdz", "obj", "blend")


def _select(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        if o is not None:
            o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def export(result, path, fmt=None):
    fmt = (fmt or os.path.splitext(path)[1].lstrip(".")).lower()
    if fmt not in FORMATS:
        raise ValueError("unknown export format %s (use one of %s)" % (fmt, ", ".join(FORMATS)))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    objs = [result["armature"], result["skin"], result["parts"]]
    _select([o for o in objs if o is not None])
    if fmt in ("glb", "gltf"):
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB" if fmt == "glb" else "GLTF_SEPARATE",
                                  use_selection=True, export_yup=True, export_apply=False, export_skins=True,
                                  export_animations=True, export_animation_mode="NLA_TRACKS",
                                  export_materials="EXPORT", export_extras=False)
    elif fmt == "fbx":
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, add_leaf_bones=False, bake_anim=True,
                                 bake_anim_use_nla_strips=True, bake_anim_use_all_actions=False,
                                 axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE")
    elif fmt in ("usd", "usdc", "usdz"):
        bpy.ops.wm.usd_export(filepath=path, selected_objects_only=True, export_animation=True)
    elif fmt == "obj":
        bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True, export_animation=False, forward_axis="NEGATIVE_Z", up_axis="Y")
    elif fmt == "blend":
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    return path
