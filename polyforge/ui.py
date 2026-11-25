"""PolyForge editor inside Blender: View3D > Sidebar > PolyForge.

The recipe (JSON) lives on the scene, so Blender's undo covers every edit.
Each edit rebuilds a fast preview (parts finished, skin not fused); "Sculpt"
fuses the skin into one remeshed surface, as exports do.
"""
import json
import math
import os

import bpy
import bpy.utils.previews
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Vector

from . import builder, catalog, export, ops, placement
from . import recipe as R
from .spine import Spine

_HERE = os.path.dirname(os.path.abspath(__file__))
# Installed add-ons carry their data in _data/; a repo checkout uses the repo folders.
ROOT = os.path.join(_HERE, "_data") if os.path.isdir(os.path.join(_HERE, "_data")) else os.path.dirname(_HERE)
EXAMPLES = os.path.join(ROOT, "examples")
THUMBS = os.path.join(ROOT, "library", "thumbs")
COLLECTION = "PolyForge"
PARAM_SLOTS = 8
_previews = None
_busy = False


# ------------------------------------------------------------------ recipe io

def get_recipe(scene):
    try:
        return json.loads(scene.pf_recipe) if scene.pf_recipe else R.default_recipe()
    except ValueError:
        return R.default_recipe()


def set_recipe(scene, r, rebuild=True):
    r, _ = R.normalize(r)
    scene.pf_recipe = json.dumps(r)
    if rebuild and scene.pf_auto:
        rebuild_creature(scene, "preview")
    sync_edit(scene)


def apply_ops(scene, op_list, rebuild=True):
    r, errs = ops.apply_all(get_recipe(scene), op_list)
    set_recipe(scene, r, rebuild)
    return errs


def creature_collection(scene):
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        scene.collection.children.link(col)
    return col


def rebuild_creature(scene, quality="preview"):
    col = creature_collection(scene)
    for ob in list(col.objects):
        me = ob.data if ob.type == "MESH" else None
        bpy.data.objects.remove(ob, do_unlink=True)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    if quality == "preview" and scene.pf_solo:
        from .shapes import isolated, extract
        item = selected_limb(scene) or selected_part(scene)
        if item:
            isolated(extract(item), col)
            scene.pf_report = ""
            return
    res = builder.build(get_recipe(scene), quality, col)
    scene.pf_report = json.dumps(res["report"])
    return res


def creature_armature(scene):
    col = bpy.data.collections.get(COLLECTION)
    if col:
        for ob in col.objects:
            if ob.type == "ARMATURE":
                return ob
    return None


# ------------------------------------------------------------ edit mirror

def selected_part(scene, r=None):
    r = r or get_recipe(scene)
    for p in r["parts"]:
        if p["uid"] == scene.pf_selected:
            return p
    return None


def selected_limb(scene, r=None):
    r = r or get_recipe(scene)
    for l in r["limbs"]:
        if l["uid"] == scene.pf_selected:
            return l
    return None


def sync_edit(scene):
    """Copy the selection's values into the edit properties without triggering updates."""
    global _busy
    _busy = True
    try:
        e = scene.pf_edit
        r = get_recipe(scene)
        p = selected_part(scene, r)
        l = selected_limb(scene, r)
        target, part = None, None
        if p:
            target, part = p, catalog.get(p["part"])
            e.u, e.theta, e.offset, e.scale = p["u"], p["theta"], p["offset"], p["scale"]
            e.rot = [math.radians(a) for a in p["rot"]]
            params = p["params"]
        elif l:
            target, part = l, catalog.get(l["tip"]) if l["tip"] else None
            e.u, e.theta = l["u"], l["theta"]
            idx = min(e.joint_index, len(l["segments"]) - 1)
            e.joint_index = idx
            e.segment = l["segments"][idx]
            e.joint_radius = l["radii"][idx + 1]
            e.radius = l["radii"][0]
            e.scale = l["scale"]
            e.rot = [math.radians(a) for a in l["rot"]]
            params = l["tip_params"]
        if part:
            for i, (k, (lo, hi, d)) in enumerate(part.params.items()):
                if i < PARAM_SLOTS:
                    setattr(e, "p%d" % i, (params.get(k, d) - lo) / max(hi - lo, 1e-6))
        pa = r["paint"]
        e.base, e.accent, e.detail = (builder.hex_rgb(pa[k]) for k in ("base", "accent", "detail"))
        e.pattern = pa["pattern"]
        e.pattern_scale = pa["pattern_scale"]
        e.belly = pa["belly"]
    finally:
        _busy = False


def _hex(c):
    def enc(v):
        v = max(0.0, min(1.0, v))
        v = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        return int(round(v * 255))
    return "#%02x%02x%02x" % tuple(enc(x) for x in c[:3])


def _edit_update(field):
    def upd(self, context):
        if _busy:
            return
        scene = context.scene
        r = get_recipe(scene)
        p, l = selected_part(scene, r), selected_limb(scene, r)
        op = None
        if field in ("base", "accent", "detail"):
            op = {"op": "set_paint", field: _hex(getattr(self, field))}
        elif field in ("pattern", "pattern_scale", "belly"):
            op = {"op": "set_paint", field: getattr(self, field)}
        elif p is not None:
            part = catalog.get(p["part"])
            op = {"op": "set_part", "uid": p["uid"]}
            if field.startswith("p") and field[1:].isdigit():
                i = int(field[1:])
                keys = list(part.params)
                if i >= len(keys):
                    return
                lo, hi, _ = part.params[keys[i]]
                op["params"] = {keys[i]: lo + (hi - lo) * getattr(self, field)}
            elif field == "rot":
                op["rot"] = [math.degrees(a) for a in self.rot]
            else:
                op[field] = getattr(self, field)
        elif l is not None:
            op = {"op": "set_limb", "uid": l["uid"]}
            if field.startswith("p") and field[1:].isdigit() and l["tip"]:
                part = catalog.get(l["tip"])
                keys = list(part.params)
                i = int(field[1:])
                if i >= len(keys):
                    return
                lo, hi, _ = part.params[keys[i]]
                op["tip_params"] = {keys[i]: lo + (hi - lo) * getattr(self, field)}
            elif field == "joint_index":
                sync_edit(scene)
                return
            elif field in ("segment", "joint_radius"):
                idx = min(self.joint_index, len(l["segments"]) - 1)
                if field == "segment":
                    op["segments"] = list(l["segments"])
                    op["segments"][idx] = list(self.segment)
                else:
                    op["radii"] = list(l["radii"])
                    op["radii"][idx + 1] = self.joint_radius
            elif field == "radius":
                k = self.radius / max(l["radii"][0], 1e-4)
                op["radii"] = [x * k for x in l["radii"]]
            elif field == "rot":
                op["rot"] = [math.degrees(a) for a in self.rot]
            elif field in ("u", "theta", "scale"):
                op[field] = getattr(self, field)
            else:
                return
        if op:
            apply_ops(scene, [op])
    return upd


class PF_Edit(bpy.types.PropertyGroup):
    u: FloatProperty(name="Along body", min=0.0, max=1.0, update=_edit_update("u"))
    theta: FloatProperty(name="Around", min=-180.0, max=180.0, update=_edit_update("theta"))
    offset: FloatProperty(name="Offset", min=-0.6, max=0.6, update=_edit_update("offset"))
    scale: FloatProperty(name="Scale", min=0.2, max=4.0, default=1.0, update=_edit_update("scale"))
    rot: FloatVectorProperty(name="Rotation", subtype="EULER", size=3, update=_edit_update("rot"))
    joint_index: IntProperty(name="Segment", min=0, max=4, update=_edit_update("joint_index"))
    segment: FloatVectorProperty(name="Joint offset", size=3, update=_edit_update("segment"))
    joint_radius: FloatProperty(name="End radius", min=0.02, max=1.2, update=_edit_update("joint_radius"))
    radius: FloatProperty(name="Thickness", min=0.02, max=1.2, default=0.1, update=_edit_update("radius"))
    base: FloatVectorProperty(name="Base", subtype="COLOR", min=0, max=1, update=_edit_update("base"))
    accent: FloatVectorProperty(name="Accent", subtype="COLOR", min=0, max=1, update=_edit_update("accent"))
    detail: FloatVectorProperty(name="Detail", subtype="COLOR", min=0, max=1, update=_edit_update("detail"))
    pattern: EnumProperty(name="Pattern", items=[(p, p.title(), "") for p in R.PATTERNS], update=_edit_update("pattern"))
    pattern_scale: FloatProperty(name="Pattern scale", min=0.25, max=4.0, default=1.0, update=_edit_update("pattern_scale"))
    belly: BoolProperty(name="Light belly", default=True, update=_edit_update("belly"))


for _i in range(PARAM_SLOTS):
    PF_Edit.__annotations__["p%d" % _i] = FloatProperty(name="p%d" % _i, min=0.0, max=1.0, update=_edit_update("p%d" % _i))


# -------------------------------------------------------------- operators

def _example_items(self, context):
    files = sorted(f[:-5] for f in os.listdir(EXAMPLES) if f.endswith(".json")) if os.path.isdir(EXAMPLES) else []
    return [(f, f.title(), "") for f in files] or [("none", "none", "")]


class PF_OT_new(bpy.types.Operator):
    bl_idname = "polyforge.new"
    bl_label = "New creature"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.pf_selected = ""
        set_recipe(context.scene, R.default_recipe())
        rebuild_creature(context.scene)
        return {"FINISHED"}


class PF_OT_example(bpy.types.Operator):
    bl_idname = "polyforge.example"
    bl_label = "Open example"
    bl_options = {"REGISTER", "UNDO"}
    name: EnumProperty(items=_example_items)

    def execute(self, context):
        context.scene.pf_selected = ""
        set_recipe(context.scene, R.load(os.path.join(EXAMPLES, self.name + ".json")), rebuild=False)
        rebuild_creature(context.scene)
        return {"FINISHED"}


class PF_OT_open(bpy.types.Operator):
    bl_idname = "polyforge.open"
    bl_label = "Open recipe"
    bl_options = {"REGISTER", "UNDO"}
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        set_recipe(context.scene, R.load(self.filepath), rebuild=False)
        rebuild_creature(context.scene)
        return {"FINISHED"}


class PF_OT_save(bpy.types.Operator):
    bl_idname = "polyforge.save"
    bl_label = "Save recipe"
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        self.filepath = (get_recipe(context.scene)["name"] or "creature").lower() + ".json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        R.save(get_recipe(context.scene), self.filepath)
        return {"FINISHED"}


class PF_OT_build(bpy.types.Operator):
    bl_idname = "polyforge.build"
    bl_label = "Rebuild"
    bl_description = "Rebuild the creature (Sculpt fuses the skin into one remeshed surface)"
    bl_options = {"REGISTER", "UNDO"}
    quality: EnumProperty(items=[("preview", "Preview", ""), ("final", "Sculpt", "")])

    def execute(self, context):
        rebuild_creature(context.scene, self.quality)
        return {"FINISHED"}


def _hit_to_recipe(context, event):
    region, rv3d = context.region, context.region_data
    co = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, co)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, co)
    hit, loc, normal, idx, ob, mat = context.scene.ray_cast(context.evaluated_depsgraph_get(), origin, direction)
    if not hit or ob is None or ob.name not in creature_collection(context.scene).objects:
        return None
    return Vector((loc.x, loc.z, -loc.y))


def _attach_point(scene, p, body_only=False):
    """Nearest attachment for a recipe-space point: body (u, theta) or a limb."""
    arm = creature_armature(scene)
    r = get_recipe(scene)
    rig = json.loads(arm["polyforge_rig"]) if arm else None
    sp = Spine(r["spine"], Vector((0, rig.get("shift_y", 0.0), 0)) if rig else Vector())
    body = sp.project(p)
    best = {"on": "body", "u": body["u"], "theta": body["theta"], "d": body["d"]}
    if rig and not body_only:
        for l in rig["limbs"]:
            if l["mirrored"]:
                continue
            J = [Vector(j) for j in l["joints"]]
            q = Vector((abs(p.x), p.y, p.z)) if l["side"] != 0 else p
            for k in range(len(J) - 1):
                ab = J[k + 1] - J[k]
                t = max(0.0, min(1.0, (q - J[k]).dot(ab) / max(ab.length_squared, 1e-9)))
                radial = q - (J[k] + ab * t)
                d = abs(radial.length - (l["radii"][k] + (l["radii"][k + 1] - l["radii"][k]) * t))
                if d < best["d"] - 0.01:
                    acc = sum((J[i + 1] - J[i]).length for i in range(k)) + ab.length * t
                    direction = ab.normalized()
                    up = builder.UP - direction * builder.UP.dot(direction)
                    if up.length < 0.2:
                        up = builder.BACK - direction * builder.BACK.dot(direction)
                    up.normalize()
                    theta = math.degrees(math.atan2(radial.dot(up), radial.dot(up.cross(direction))))
                    best = {"on": l["uid"], "u": acc / max(l["length"], 1e-3), "theta": theta, "d": d}
    return best


class PF_OT_place(bpy.types.Operator):
    """Click the creature to place the chosen part or limb (Shift keeps placing, Esc cancels)"""
    bl_idname = "polyforge.place"
    bl_label = "Place"
    bl_options = {"REGISTER", "UNDO"}
    what: StringProperty()

    def invoke(self, context, event):
        if context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "Use this in a 3D viewport")
            return {"CANCELLED"}
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("Click the creature to place %s · Shift-click keeps placing · Esc cancels" % self.what)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE"}:
            context.workspace.status_text_set(None)
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            p = _hit_to_recipe(context, event)
            if p is None:
                return {"RUNNING_MODAL"}
            self.place(context.scene, p)
            if not event.shift:
                context.workspace.status_text_set(None)
                return {"FINISHED"}
        return {"PASS_THROUGH"} if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"} else {"RUNNING_MODAL"}

    def place(self, scene, p):
        w = self.what
        at = _attach_point(scene, p, body_only=w.startswith("limb:") or w == "move_limb")
        if w in ("move_limb", "move_part"):
            op = {"op": "set_limb" if w == "move_limb" else "set_part", "uid": scene.pf_selected,
                  "u": at["u"], "theta": at["theta"]}
            if w == "move_part":
                op["on"] = at["on"]
            apply_ops(scene, [op])
            return
        if w.startswith("limb:"):
            kind = w[5:]
            seg = {"tail": [[0,-0.08,-0.22],[0,-0.18,-0.16],[0,-0.18,-0.08]], "leg": [[0.12, -0.32, 0.05], [0.0, -0.32, 0.0]], "arm": [[0.25, -0.12, 0.05], [0.1, -0.25, 0.12]],
                   "feeler": [[0.15, 0.2, 0.15], [0.1, 0.2, 0.2], [0.05, 0.1, 0.2]]}.get(kind, [[0.0, -0.32, 0.05], [0.0, -0.32, 0.0]])
            tip = {"leg": "foot_paw", "arm": "hand_basic", "feeler": "", "center": "foot_pad", "tail": ""}[kind]
            theta = -90.0 if kind == "center" else at["theta"]
            apply_ops(scene, [{"op": "add_limb", "u": at["u"], "theta": theta, "segments": seg,
                               "radii": [0.11, 0.08, 0.06, 0.04][:len(seg) + 1], "motion": "tail" if kind == "tail" else "auto", "tip": tip}])
            scene.pf_selected = get_recipe(scene)["limbs"][-1]["uid"]
        else:
            part = catalog.get(w)
            if part.attach == "tip":
                if at["on"] == "body":
                    return
                apply_ops(scene, [{"op": "set_limb", "uid": at["on"], "tip": w, "tip_params": {}}])
                scene.pf_selected = at["on"]
            else:
                apply_ops(scene, [{"op": "add_part", "part": w, "on": at["on"], "u": at["u"], "theta": at["theta"]}])
                scene.pf_selected = get_recipe(scene)["parts"][-1]["uid"]
        sync_edit(scene)


class PF_OT_select(bpy.types.Operator):
    bl_idname = "polyforge.select"
    bl_label = "Select"
    uid: StringProperty()

    def execute(self, context):
        context.scene.pf_selected = self.uid
        sync_edit(context.scene)
        if context.scene.pf_solo:
            rebuild_creature(context.scene)
        return {"FINISHED"}


class PF_OT_remove(bpy.types.Operator):
    bl_idname = "polyforge.remove"
    bl_label = "Remove selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene
        r = get_recipe(s)
        if selected_part(s, r):
            apply_ops(s, [{"op": "remove_part", "uid": s.pf_selected}])
        elif selected_limb(s, r):
            apply_ops(s, [{"op": "remove_limb", "uid": s.pf_selected}])
        s.pf_selected = ""
        return {"FINISHED"}


class PF_OT_vertebra(bpy.types.Operator):
    bl_idname = "polyforge.vertebra"
    bl_label = "Edit vertebra"
    bl_options = {"REGISTER", "UNDO"}
    action: StringProperty()
    index: IntProperty()
    dy: FloatProperty()
    dz: FloatProperty()
    scale: FloatProperty(default=1.0)

    def execute(self, context):
        s = context.scene
        r = get_recipe(s)
        n = len(r["spine"])
        if self.action == "add_head":
            op = {"op": "insert_vertebra", "index": -1}
        elif self.action == "add_tail":
            op = {"op": "insert_vertebra", "index": 0}
        elif self.action == "remove":
            op = {"op": "remove_vertebra", "index": self.index}
        else:
            v = r["spine"][self.index]
            op = {"op": "set_vertebra", "index": self.index, "y": v["y"] + self.dy, "z": v["z"] + self.dz, "w": v["w"] * self.scale, "h": v["h"] * self.scale}
        apply_ops(s, [op])
        return {"FINISHED"}


class PF_OT_review_views(bpy.types.Operator):
    bl_idname = "polyforge.review_views"
    bl_label = "Render assembly review views"

    def execute(self, context):
        import subprocess
        import tempfile
        from pathlib import Path
        from .review import signature
        source = get_recipe(context.scene)
        folder = Path(tempfile.mkdtemp(prefix="polyforge-review-"))
        path = folder / "creature.json"
        R.save(source, path)
        # Render in a separate Blender process to preserve this scene and its undo history.
        script = "import sys; sys.path.insert(0, %r); from polyforge import cli; cli.main(%r)" % (
            os.path.dirname(_HERE), ["review", str(path), "--out", str(folder)])
        subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1",
                        "--python-expr", script], check=True)
        context.scene.pf_viewed = signature(source)
        bpy.ops.wm.path_open(filepath=str(folder))
        return {"FINISHED"}


class PF_OT_accept_review(bpy.types.Operator):
    bl_idname = "polyforge.accept_review"
    bl_label = "I inspected the assembled front, side and head views"

    def execute(self, context):
        from .review import signature
        s = context.scene
        if s.pf_solo:
            self.report({"ERROR"}, "Return to assembled view first")
            return {"CANCELLED"}
        if s.pf_viewed != signature(get_recipe(s)):
            self.report({"ERROR"}, "Render and inspect the current assembly views first")
            return {"CANCELLED"}
        rebuild_creature(s, "final")
        s.pf_review = signature(get_recipe(s))
        return {"FINISHED"}


class PF_OT_bake(bpy.types.Operator):
    bl_idname = "polyforge.bake"
    bl_label = "Bake animations"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from .review import signature
        if context.scene.pf_review != signature(get_recipe(context.scene)):
            self.report({"ERROR"}, "Inspect and accept this assembly first")
            return {"CANCELLED"}
        from . import baker
        arm = creature_armature(context.scene)
        if arm is None:
            return {"CANCELLED"}
        clips = baker.bake_all(arm)
        self.report({"INFO"}, "Baked %s" % ", ".join(clips))
        return {"FINISHED"}


class PF_OT_play(bpy.types.Operator):
    bl_idname = "polyforge.play"
    bl_label = "Play clip"
    clip: StringProperty()

    def execute(self, context):
        arm = creature_armature(context.scene)
        if arm is None or arm.animation_data is None:
            self.report({"WARNING"}, "Bake animations first")
            return {"CANCELLED"}
        ad = arm.animation_data
        for t in ad.nla_tracks:
            t.mute = t.name != self.clip
            for st in t.strips:
                if t.name == self.clip:
                    context.scene.frame_start, context.scene.frame_end = int(st.frame_start), int(st.frame_end)
        context.scene.frame_set(context.scene.frame_start)
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


class PF_OT_export(bpy.types.Operator):
    bl_idname = "polyforge.export"
    bl_label = "Export"
    bl_description = "Sculpt, bake and export the creature"
    filepath: StringProperty(subtype="FILE_PATH")
    fmt: EnumProperty(items=[(f, f.upper(), "") for f in export.FORMATS])

    def invoke(self, context, event):
        self.filepath = "%s.%s" % ((get_recipe(context.scene)["name"] or "creature").lower(), self.fmt)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        from .review import signature
        if context.scene.pf_review != signature(get_recipe(context.scene)):
            self.report({"ERROR"}, "Inspect and accept this assembly first")
            return {"CANCELLED"}
        from . import baker
        res = rebuild_creature(context.scene, "final")
        baker.bake_all(res["armature"])
        export.export(res, self.filepath, self.fmt)
        self.report({"INFO"}, "Exported " + self.filepath)
        return {"FINISHED"}


# ------------------------------------------------------------------ panels

def thumbs():
    global _previews
    if _previews is None:
        _previews = bpy.utils.previews.new()
        if os.path.isdir(THUMBS):
            for f in os.listdir(THUMBS):
                if f.endswith(".png"):
                    _previews.load(f[:-4], os.path.join(THUMBS, f), "IMAGE")
    return _previews


class PF_PT_base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PolyForge"


class PF_PT_creature(PF_PT_base, bpy.types.Panel):
    bl_label = "Creature"

    def draw(self, context):
        s = context.scene
        col = self.layout.column(align=True)
        row = col.row(align=True)
        row.operator("polyforge.new", icon="FILE_NEW")
        row.operator_menu_enum("polyforge.example", "name", text="Examples", icon="PRESET")
        row = col.row(align=True)
        row.operator("polyforge.open", icon="FILE_FOLDER")
        row.operator("polyforge.save", icon="FILE_TICK")
        row = col.row(align=True)
        row.operator("polyforge.build", text="Preview", icon="FILE_REFRESH").quality = "preview"
        row.operator("polyforge.build", text="Sculpt", icon="SCULPTMODE_HLT").quality = "final"
        col.prop(s, "pf_auto")
        if s.pf_report:
            rep = json.loads(s.pf_report)
            self.layout.label(text="%d legs · %d arms · %d parts · %d tris" % (rep["legs"], rep["arms"], rep["parts"], rep["triangles"]))
            for w in rep["warnings"][:4]:
                self.layout.label(text=w, icon="ERROR")


class PF_PT_palette(PF_PT_base, bpy.types.Panel):
    bl_label = "Parts"

    def draw(self, context):
        lay = self.layout
        if context.scene.pf_solo:
            lay.label(text="Show creature to place parts")
            return
        lay.label(text="Pick a part, then click the surface")
        row = lay.row(align=True)
        for kind, label in (("leg", "Legs"), ("arm", "Arms"), ("center", "Centre leg"), ("feeler", "Feelers"), ("tail", "Tail")):
            row.operator("polyforge.place", text=label).what = "limb:" + kind
        pv = thumbs()
        for cat, ids in catalog.by_category().items():
            box = lay.box()
            box.label(text=cat.title())
            grid = box.grid_flow(columns=4, even_columns=True, align=True)
            for pid in ids:
                icon = pv[pid].icon_id if pid in pv else 0
                if icon:
                    grid.operator("polyforge.place", text="", icon_value=icon).what = pid
                else:
                    grid.operator("polyforge.place", text=pid).what = pid


class PF_PT_edit(PF_PT_base, bpy.types.Panel):
    bl_label = "Selection"

    def draw(self, context):
        s = context.scene
        lay = self.layout
        r = get_recipe(s)
        col = lay.column(align=True)
        for p in r["parts"]:
            col.operator("polyforge.select", text="%s (%s)" % (p["uid"], p["part"]), depress=p["uid"] == s.pf_selected).uid = p["uid"]
        for l in r["limbs"]:
            col.operator("polyforge.select", text="%s (limb%s)" % (l["uid"], ", " + l["tip"] if l["tip"] else ""), depress=l["uid"] == s.pf_selected).uid = l["uid"]
        p, l = selected_part(s, r), selected_limb(s, r)
        e = s.pf_edit
        if p or l or s.pf_solo:
            lay.prop(s, "pf_solo", toggle=True)
            if not s.pf_solo:
                lay.operator("polyforge.place", text="Move to surface").what = "move_limb" if l else "move_part"
        if p:
            part = catalog.get(p["part"])
            box = lay.box()
            box.label(text=part.id)
            for k in ("u", "theta", "offset", "scale", "rot"):
                box.prop(e, k)
            for i, (k, (lo, hi, d)) in enumerate(part.params.items()):
                if i < PARAM_SLOTS:
                    box.prop(e, "p%d" % i, text="%s (%.2f)" % (k, p["params"].get(k, d)), slider=True)
            box.operator("polyforge.remove", icon="TRASH")
        elif l:
            box = lay.box()
            box.label(text="Limb %s" % l["uid"])
            for k in ("u", "theta", "scale", "rot", "radius"):
                box.prop(e, k)
            for field in ("joint_index", "segment", "joint_radius"):
                box.prop(e, field)
            if l["tip"]:
                part = catalog.get(l["tip"])
                for i, (k, (lo, hi, d)) in enumerate(part.params.items()):
                    if i < PARAM_SLOTS:
                        box.prop(e, "p%d" % i, text="%s (%.2f)" % (k, l["tip_params"].get(k, d)), slider=True)
            box.operator("polyforge.remove", icon="TRASH")


class PF_PT_spine(PF_PT_base, bpy.types.Panel):
    bl_label = "Spine"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout
        r = get_recipe(context.scene)
        row = lay.row(align=True)
        row.operator("polyforge.vertebra", text="+ Head").action = "add_head"
        row.operator("polyforge.vertebra", text="+ Tail").action = "add_tail"
        for i, v in enumerate(r["spine"]):
            row = lay.row(align=True)
            row.label(text="%d  y %.2f z %.2f  r %.2f" % (i, v["y"], v["z"], v["w"]))
            for txt, kw in (("↑", {"dy": 0.05}), ("↓", {"dy": -0.05}), ("←", {"dz": -0.05}), ("→", {"dz": 0.05}), ("+", {"scale": 1.1}), ("−", {"scale": 0.9})):
                o = row.operator("polyforge.vertebra", text=txt)
                o.action, o.index = "set", i
                for k, val in kw.items():
                    setattr(o, k, val)
            o = row.operator("polyforge.vertebra", text="", icon="X")
            o.action, o.index = "remove", i


class PF_PT_paint(PF_PT_base, bpy.types.Panel):
    bl_label = "Paint"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        e = context.scene.pf_edit
        for k in ("base", "accent", "detail", "pattern", "pattern_scale", "belly"):
            self.layout.prop(e, k)


class PF_PT_animate(PF_PT_base, bpy.types.Panel):
    bl_label = "Animate & export"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        lay = self.layout
        lay.operator("polyforge.review_views")
        lay.operator("polyforge.accept_review")
        lay.operator("polyforge.bake", icon="ACTION")
        grid = lay.grid_flow(columns=3, align=True)
        for c in ("idle", "walk", "run", "roar", "wave", "hop"):
            grid.operator("polyforge.play", text=c.title()).clip = c
        row = lay.row(align=True)
        for f in ("glb", "fbx", "usdz", "obj"):
            row.operator("polyforge.export", text=f.upper()).fmt = f


CLASSES = [PF_Edit, PF_OT_new, PF_OT_example, PF_OT_open, PF_OT_save, PF_OT_build, PF_OT_place, PF_OT_select,
           PF_OT_remove, PF_OT_vertebra, PF_OT_review_views, PF_OT_accept_review, PF_OT_bake, PF_OT_play, PF_OT_export,
           PF_PT_creature, PF_PT_palette, PF_PT_edit, PF_PT_spine, PF_PT_paint, PF_PT_animate]


def _solo_changed(scene, context):
    rebuild_creature(scene)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    S = bpy.types.Scene
    S.pf_recipe = StringProperty(name="Recipe", default="")
    S.pf_viewed = StringProperty(default="")
    S.pf_review = StringProperty(default="")
    S.pf_report = StringProperty(default="")
    S.pf_selected = StringProperty(default="")
    S.pf_solo = BoolProperty(name="Isolate shape", update=_solo_changed)
    S.pf_auto = BoolProperty(name="Rebuild on edit", default=True)
    S.pf_edit = bpy.props.PointerProperty(type=PF_Edit)


def unregister():
    global _previews
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    for k in ("pf_recipe", "pf_report", "pf_review", "pf_viewed", "pf_selected", "pf_auto", "pf_solo", "pf_edit"):
        delattr(bpy.types.Scene, k)
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
