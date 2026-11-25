"""Low-poly modeling kit for authoring parts in Blender.

Coordinates here use the Godot convention (+Y up, +Z forward). `to_blender`
converts when meshes are created, and the glTF exporter converts back, so a
part's local frame is identical in Blender scripts and in Godot.

Faces are wound counter-clockwise seen from outside (right-hand normals out).
Every call produces the same topology for any parameter values, which is what
lets parameters become shape keys.
"""
import math
from mathutils import Vector, Matrix

UP = Vector((0, 1, 0))
BACK = Vector((0, 0, 1))      # Godot Vector3.BACK (+Z, creature forward)
FORWARD = Vector((0, 0, -1))
RIGHT = Vector((1, 0, 0))


def V(x, y=None, z=None):
    if y is None:
        return Vector(x)
    return Vector((x, y, z))


def lerp(a, b, t):
    return a + (b - a) * t


def to_blender(p):
    return Vector((p.x, -p.z, p.y))


def rot(axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis))


class Piece:
    """Mesh under construction: shared vertices, polygon faces, per-face paint slot."""

    def __init__(self):
        self.v = []
        self.f = []
        self.slot = []
        self.cur = "base"

    def vert(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def verts(self, pts):
        return [self.vert(p) for p in pts]

    def face(self, *idx):
        self.f.append(tuple(idx))
        self.slot.append(self.cur)

    # -- primitives -----------------------------------------------------
    def ring_strip(self, a, b):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            self.face(a[i], a[j], b[j], b[i])

    def fan(self, center, ring, flip=False):
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            if flip:
                self.face(center, ring[j], ring[i])
            else:
                self.face(center, ring[i], ring[j])

    def ellipsoid(self, c, r, basis=None, segs=8, rings=5):
        basis = basis or Matrix.Identity(3)
        c = V(c)
        bx, by, bz = basis.col[0] * r[0], basis.col[1] * r[1], basis.col[2] * r[2]
        top = self.vert(c + by)
        prev = None
        for k in range(1, rings):
            phi = math.pi * k / rings
            rr, yy = math.sin(phi), math.cos(phi)
            cur = []
            for i in range(segs):
                a = 2 * math.pi * (i + 0.5 * (k % 2)) / segs
                cur.append(self.vert(c + by * yy + (bx * math.cos(a) - bz * math.sin(a)) * rr))
            if k == 1:
                for i in range(segs):
                    self.face(top, cur[i], cur[(i + 1) % segs])
            else:
                for i in range(segs):
                    j = (i + 1) % segs
                    self.face(prev[i], cur[i], cur[j], prev[j])
            prev = cur
        bottom = self.vert(c - by)
        for i in range(segs):
            self.face(bottom, prev[(i + 1) % segs], prev[i])

    def tube(self, points, radii, segs=6, cap_start=True, cap_end=True, up_hint=UP, squash=(1.0, 1.0), point_cap=False):
        points = [V(p) for p in points]
        n = len(points)
        frames = parallel_frames(points, V(up_hint))
        rings = []
        for i in range(n):
            fx, fy, fz = frames[i]
            ring = []
            for s in range(segs):
                a = 2 * math.pi * s / segs
                ring.append(self.vert(points[i] + fx * math.cos(a) * radii[i] * squash[0] + fy * math.sin(a) * radii[i] * squash[1]))
            rings.append(ring)
        for i in range(n - 1):
            self.ring_strip(rings[i], rings[i + 1])
        if cap_start:
            self.fan(self.vert(points[0] - frames[0][2] * radii[0] * 0.3), rings[0], flip=True)
        if cap_end:
            tip = points[-1] + frames[-1][2] * (radii[-1] * (2.5 if point_cap else 0.3))
            self.fan(self.vert(tip), rings[-1])

    def cone(self, base, tip, r, segs=6, up_hint=UP):
        base, tip = V(base), V(tip)
        fx, fy, _ = parallel_frames([base, tip], V(up_hint))[0]
        ring = [self.vert(base + fx * math.cos(2 * math.pi * s / segs) * r + fy * math.sin(2 * math.pi * s / segs) * r) for s in range(segs)]
        self.fan(self.vert(tip), ring)
        self.fan(self.vert(base), ring, flip=True)

    def box(self, c, size, basis=None):
        basis = basis or Matrix.Identity(3)
        c = V(c)
        h = V(size) * 0.5
        p = []
        for z in (-1, 1):
            for y in (-1, 1):
                for x in (-1, 1):
                    p.append(self.vert(c + basis @ Vector((h.x * x, h.y * y, h.z * z))))
        for q in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3)):
            self.face(*[p[i] for i in q])

    def slab(self, outline, n, thickness):
        """Flat polygon extruded along n (fins, wings, plates, ears)."""
        outline = [V(p) for p in outline]
        n = V(n).normalized()
        newell = Vector((0, 0, 0))
        for i in range(len(outline)):
            newell += outline[i].cross(outline[(i + 1) % len(outline)])
        if newell.dot(n) < 0:
            outline = outline[::-1]
        off = n * thickness * 0.5
        c = sum(outline, Vector((0, 0, 0))) / len(outline)
        ct, cb = self.vert(c + off), self.vert(c - off)
        top = self.verts([p + off for p in outline])
        bot = self.verts([p - off for p in outline])
        m = len(outline)
        for i in range(m):
            j = (i + 1) % m
            self.face(ct, top[i], top[j])
            self.face(cb, bot[j], bot[i])
            self.face(top[j], top[i], bot[i], bot[j])


def parallel_frames(points, up_hint):
    n = len(points)
    out = []
    prev_y = up_hint.copy()
    for i in range(n):
        if i == 0:
            t = points[1] - points[0]
        elif i == n - 1:
            t = points[-1] - points[-2]
        else:
            t = points[i + 1] - points[i - 1]
        t = t.normalized()
        y = prev_y - t * prev_y.dot(t)
        if y.length < 1e-4:
            y = FORWARD - t * FORWARD.dot(t)
            if y.length < 1e-4:
                y = RIGHT - t * RIGHT.dot(t)
        y = y.normalized()
        x = y.cross(t).normalized()
        out.append((x, y, t))
        prev_y = y
    return out


def curve_points(start, direction, bend, length, n, twist=(0, 0, 0)):
    start, direction, bend, twist = V(start), V(direction), V(bend), V(twist)
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(start + direction * length * t + bend * length * t * t + twist * length * t * t * t)
    return out


def taper(r0, r1, n, power=1.0):
    return [lerp(r0, r1, (i / (n - 1)) ** power) for i in range(n)]
