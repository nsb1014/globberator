"""Globberator: a Spore-style creature builder for Blender.

Build creatures from a sculpted part library on a bendable spine; they fuse
into one clay surface, rig themselves, animate procedurally and export to
glTF / FBX / USD / OBJ for any engine.
"""
bl_info = {
    "name": "Globberator Creature Builder",
    "author": "Globberator",
    "version": (0, 4, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Globberator",
    "description": "Assemble, rig, animate and export creatures from a sculpted part library",
    "category": "Add Mesh",
}


def register():
    from . import ui
    ui.register()


def unregister():
    from . import ui
    ui.unregister()
