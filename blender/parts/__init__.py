"""Part definitions. Each module exposes PARTS: a list of Part objects."""
from mathutils import Vector
from kit import Piece


class Ctx:
    """Build context: several pieces (one per bone). `use(name)` switches piece,
    `slot(name)` sets the paint slot; other calls forward to the current piece."""

    def __init__(self, bones):
        self.pieces = {"self": Piece()}
        for b in bones:
            self.pieces[b["name"]] = Piece()
        self.current = self.pieces["self"]
        self.pivots = {b["name"]: Vector(b["pivot"]) for b in bones}

    def use(self, name):
        self.current = self.pieces[name]

    def slot(self, name):
        for p in self.pieces.values():
            p.cur = name

    def setup(self, finish=None, voxel=None, detail=None, smooth=None, slot_finish=None):
        """Finishing options for the current piece."""
        if slot_finish is not None:
            self.current.slot_finish.update(slot_finish)
        if finish is not None:
            self.current.finish = finish
        if voxel is not None:
            self.current.voxel = voxel
        if detail is not None:
            self.current.detail = detail
        if smooth is not None:
            self.current.smooth = smooth

    def __getattr__(self, k):
        return getattr(self.current, k)


class Part:
    def __init__(self, id, category, desc, tags, params, build, attach="surface", orient="surface", cap="",
                 mirror=False, hint=None, bones=None):
        self.id = id
        self.category = category
        self.desc = desc
        self.tags = tags
        self.params = params        # name -> (min, max, default)
        self.build_fn = build
        self.attach = attach
        self.orient = orient
        self.cap = cap
        self.mirror = mirror
        self.hint = hint or {"u": 0.5, "theta": 90.0}
        self.bones = bones or []    # [{"name", "pivot": (x,y,z), "axis": (x,y,z), "angle": deg}]

    def defaults(self):
        return {k: v[2] for k, v in self.params.items()}

    def build(self, p):
        ctx = Ctx(self.bones)
        ctx.slot("base")
        self.build_fn(ctx, p)
        return ctx
