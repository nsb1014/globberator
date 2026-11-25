"""Shared display material and rigged GLB export for character families."""
import bpy


def clay_material():
    clay = bpy.data.materials.new("Matte clay")
    clay.diffuse_color = (0.40, 0.40, 0.40, 1)
    clay.use_nodes = True
    shader = clay.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = clay.diffuse_color
    shader.inputs["Roughness"].default_value = 0.87
    return clay


def export_character(rig, skin, output):
    output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True);skin.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(output.resolve()),export_format="GLB",use_selection=True,
        export_animations=True,export_animation_mode="ACTIONS",export_anim_single_armature=True,
        export_rest_position_armature=True,export_yup=True,export_texcoords=False,export_cameras=False,
        export_lights=False)
