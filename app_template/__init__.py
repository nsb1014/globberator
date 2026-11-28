"""Globberator application template: starts Blender as the creature builder.

Installed to <blender user scripts>/startup/bl_app_templates_user/Globberator by
tools/install.py, then launched with:  blender --app-template Globberator
"""
import bpy
from bpy.app.handlers import persistent


def _configure():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.show_region_ui = True
                    sh = space.shading
                    sh.type = "SOLID"
                    sh.light = "STUDIO"
                    sh.color_type = "MATERIAL"
                    sh.show_cavity = True
                    space.overlay.show_floor = True
    scene = bpy.context.scene
    if not getattr(scene, "pf_recipe", ""):
        try:
            bpy.ops.polyforge.example(name="bull")
        except Exception as exc:  # the add-on may not be enabled yet
            print("Globberator:", exc)
    return None


@persistent
def _on_load(_):
    bpy.app.timers.register(_configure, first_interval=0.2)


def register():
    import addon_utils
    bpy.utils.refresh_script_paths()
    addon_utils.enable("polyforge", default_set=True, persistent=True)
    bpy.app.handlers.load_post.append(_on_load)
    bpy.app.timers.register(_configure, first_interval=0.5)


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
