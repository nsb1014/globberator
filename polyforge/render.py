"""Studio renders: Workbench (fast matte clay, the default) or Cycles.

Camera views use the same convention as the recipe: yaw 0 looks at the
creature's face, yaw 90 shows its +X side, pitch is elevation in degrees.
"""
import math

import bpy
from mathutils import Vector

from . import kit

VIEWS = {"front": (0.0, 8.0), "side": (90.0, 8.0), "threequarter": (38.0, 16.0), "back": (180.0, 10.0),
         "top": (0.0, 80.0), "otherside": (-90.0, 8.0), "threequarter_left": (-38.0, 16.0)}


def view_angles(view):
    if view in VIEWS:
        return VIEWS[view]
    yaw, pitch = (float(x) for x in view.split(","))
    return yaw, pitch


def setup(engine="workbench", size=512, samples=24):
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    if engine == "cycles":
        sc.render.engine = "CYCLES"
        sc.cycles.samples = samples
        sc.cycles.device = "CPU"
        sc.cycles.use_denoising = True
        world = sc.world or bpy.data.worlds.new("World")
        sc.world = world
        world.color = (0.05, 0.06, 0.07)
    else:
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        for name in ("VERTEX", "ATTRIBUTE"):
            try:
                sh.color_type = name
                break
            except TypeError:
                continue
        sh.show_shadows = True
        sh.shadow_intensity = 0.35
        sh.show_cavity = True
        sh.cavity_type = "WORLD"
        sh.cavity_ridge_factor = 0.4
        sh.cavity_valley_factor = 0.8
        sh.background_type = "VIEWPORT"
        sh.background_color = (0.12, 0.14, 0.17)
        sc.display.shadow_focus = 0.6
    cam = sc.camera
    if cam is None:
        cam = bpy.data.objects.new("PF_camera", bpy.data.cameras.new("PF_camera"))
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.data.lens = 70
    cam.data.clip_end = 500
    if engine == "cycles" and "PF_sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("PF_sun", bpy.data.lights.new("PF_sun", "SUN"))
        sun.data.energy = 3.5
        sun.data.angle = math.radians(12)
        sun.rotation_euler = (math.radians(50), 0, math.radians(35))
        sc.collection.objects.link(sun)
    return cam


def floor(on=True):
    ob = bpy.data.objects.get("PF_floor")
    if ob is None:
        me = bpy.data.meshes.new("PF_floor")
        s = 60
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        col = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        col.data.foreach_set("color", [0.32, 0.34, 0.36, 1.0] * 4)
        ob = bpy.data.objects.new("PF_floor", me)
        bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = not on
    return ob


def bounds(objects):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        if ob is None or ob.type != "MESH":
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        for v in me.vertices:
            p = mw @ v.co
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
        ev.to_mesh_clear()
    return lo, hi


def frame(cam, lo, hi, yaw, pitch, margin=1.08):
    c = (lo + hi) * 0.5
    radius = (hi - lo).length * 0.5
    fov = cam.data.angle
    dist = radius / math.sin(fov * 0.5) * margin
    y, p = math.radians(yaw), math.radians(pitch)
    d = kit.to_blender(Vector((math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p))))
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


def render(path, transparent=False):
    sc = bpy.context.scene
    sc.render.film_transparent = transparent
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_views(objects, out_dir, views, engine="workbench", size=512, mask=False, prefix=""):
    import os
    os.makedirs(out_dir, exist_ok=True)
    cam = setup(engine, size)
    lo, hi = bounds(objects)
    outs = []
    for v in views:
        yaw, pitch = view_angles(v)
        frame(cam, lo, hi, yaw, pitch)
        tag = prefix + v.replace(",", "_")
        floor(True)
        outs.append(render(os.path.join(out_dir, tag + ".png")))
        if mask:
            floor(False)
            outs.append(render(os.path.join(out_dir, tag + "_rgba.png"), transparent=True))
            floor(True)
    return outs
