"""Sculpt kit for authoring parts in Blender.

Parts are modelled the way the original bull was: smooth anatomical volumes
(PCHIP-interpolated lofts and dense ovals), boolean carving for recesses, then
each sculpt region is voxel-remeshed into one clay surface, smoothed and
decimated. Thin parts (ears, fins, wings) are finished with subdivision
surfaces instead, because a voxel remesh would perforate them.

Coordinates use the Godot convention (+Y up, +Z forward); `to_blender`
converts when meshes are created and the glTF exporter converts back.

Every primitive call produces the same cage topology for any parameter value.
That cage is what parameter shape keys are derived from (see build_library.py).
"""
import math

import numpy as np
from mathutils import Vector, Matrix
from scipy.interpolate import PchipInterpolator

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
    return Vector((p[0], -p[2], p[1]))


def rot(axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis))


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


class Prim:
    def __init__(self, verts, faces, slot, negative=False):
        self.v = verts
        self.f = faces
        self.slot = slot
        self.negative = negative


class Piece:
    """Primitives for one bone piece. `finish` is "remesh" or "subsurf"."""

    def __init__(self):
        self.prims = []
        self.cur = "base"
        self.finish = "remesh"
        self.voxel = None        # None = derived from size
        self.detail = 1.0        # decimation budget multiplier
        self.smooth = 0.5
        self.slot_finish = {}    # per sculpt region override, e.g. {"accent": "subsurf"}

    def finish_for(self, slot):
        return self.slot_finish.get(slot, self.finish)

    # ---- primitives ---------------------------------------------------
    def _add(self, verts, faces, negative=False):
        self.prims.append(Prim([Vector(v) for v in verts], faces, self.cur, negative))

    def oval(self, c, r, basis=None, segs=24, rings=14, negative=False):
        basis = basis or Matrix.Identity(3)
        c = V(c)
        r = (r, r, r) if isinstance(r, (int, float)) else r
        verts = [c + basis @ Vector((0, r[1], 0))]
        for k in range(1, rings):
            phi = math.pi * k / rings
            for i in range(segs):
                a = 2 * math.pi * i / segs
                verts.append(c + basis @ Vector((r[0] * math.sin(phi) * math.cos(a), r[1] * math.cos(phi), -r[2] * math.sin(phi) * math.sin(a))))
        verts.append(c + basis @ Vector((0, -r[1], 0)))
        faces = []
        for i in range(segs):
            faces.append((0, 1 + i, 1 + (i + 1) % segs))
        for k in range(rings - 2):
            a0, b0 = 1 + k * segs, 1 + (k + 1) * segs
            for i in range(segs):
                j = (i + 1) % segs
                faces.append((a0 + i, b0 + i, b0 + j, a0 + j))
        last, base = len(verts) - 1, 1 + (rings - 2) * segs
        for i in range(segs):
            faces.append((last, base + (i + 1) % segs, base + i))
        self._add(verts, faces, negative)

    def cut_oval(self, c, r, basis=None, segs=18, rings=10):
        self.oval(c, r, basis, segs, rings, negative=True)

    def loft(self, points, radii, sides=22, up=UP, exponent=1.0, density=5, caps=True, negative=False):
        """Smooth tube through `points`. radii: float or (w, d) per point (w across, d along `up`).
        Points and radii are PCHIP-interpolated, sections stay perpendicular to the path."""
        pts = np.array([[p[0], p[1], p[2]] for p in points], float)
        rad = np.array([[r, r] if isinstance(r, (int, float)) else [r[0], r[1]] for r in radii], float)
        n = len(pts)
        t = np.arange(n)
        ts = np.linspace(0, n - 1, (n - 1) * density + 1)
        P = PchipInterpolator(t, pts)(ts) if n > 2 else np.array([pts[0] + (pts[1] - pts[0]) * s for s in ts])
        R = PchipInterpolator(t, rad)(ts) if n > 2 else np.array([rad[0] + (rad[1] - rad[0]) * s for s in ts])
        R = np.maximum(R, 1e-4)
        frames = parallel_frames([Vector(p) for p in P], V(up))
        th = np.arange(sides) * 2 * math.pi / sides
        cx = np.sign(np.cos(th)) * np.abs(np.cos(th)) ** exponent
        cy = np.sign(np.sin(th)) * np.abs(np.sin(th)) ** exponent
        verts, faces = [], []
        for i, p in enumerate(P):
            fx, fy, _ = frames[i]
            for s in range(sides):
                verts.append(Vector(p) + fx * (cx[s] * R[i][0]) + fy * (cy[s] * R[i][1]))
        m = len(P)
        for i in range(m - 1):
            for s in range(sides):
                k = (s + 1) % sides
                faces.append((i * sides + s, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + s))
        if caps:
            # Domed caps: a centre vertex nudged outward keeps remesh results round.
            for end, sign in ((0, -1), (m - 1, 1)):
                c = Vector(P[end]) + frames[end][2] * sign * min(R[end]) * 0.6
                ci = len(verts)
                verts.append(c)
                for s in range(sides):
                    k = (s + 1) % sides
                    a, b = end * sides + s, end * sides + k
                    faces.append((ci, b, a) if sign < 0 else (ci, a, b))
        self._add(verts, faces, negative)

    def cut_loft(self, points, radii, **kw):
        self.loft(points, radii, negative=True, **kw)

    def slab(self, outline, n, thickness, bulge=0.6):
        """Pillowy plate (ears, fins, wing membranes): an outline with a raised centre,
        meant for the subsurf finish."""
        outline = [V(p) for p in outline]
        n = V(n).normalized()
        newell = Vector((0, 0, 0))
        for i in range(len(outline)):
            newell += outline[i].cross(outline[(i + 1) % len(outline)])
        if newell.dot(n) < 0:
            outline = outline[::-1]
        c = sum(outline, Vector((0, 0, 0))) / len(outline)
        m = len(outline)
        h = thickness * 0.5
        inner = [c + (p - c) * 0.55 for p in outline]
        verts = ([p + n * h * 0.35 for p in outline] + [p - n * h * 0.35 for p in outline]
                 + [p + n * h * (1 + bulge) for p in inner] + [p - n * h * (1 + bulge) for p in inner]
                 + [c + n * h * (1 + bulge * 1.3), c - n * h * (1 + bulge * 1.3)])
        faces = []
        for i in range(m):
            j = (i + 1) % m
            faces.append((j, i, m + i, m + j))                    # rim
            faces.append((i, j, 2 * m + j, 2 * m + i))            # top ring
            faces.append((m + j, m + i, 3 * m + i, 3 * m + j))    # bottom ring
            faces.append((2 * m + i, 2 * m + j, 4 * m))           # top centre
            faces.append((3 * m + j, 3 * m + i, 4 * m + 1))       # bottom centre
        self._add(verts, faces)

    def leaf(self, outline, n, thickness, cup=0.5):
        """Cupped plate (ears, petals): front face recessed by `cup`, back rounded.
        Use with the subsurf finish."""
        outline = [V(p) for p in outline]
        n = V(n).normalized()
        newell = Vector((0, 0, 0))
        for i in range(len(outline)):
            newell += outline[i].cross(outline[(i + 1) % len(outline)])
        if newell.dot(n) < 0:
            outline = outline[::-1]
        c = sum(outline, Vector((0, 0, 0))) / len(outline)
        m = len(outline)
        h = thickness * 0.5
        rings = [(1.0, 0.0), (0.72, 1.0), (0.4, 1.4)]
        verts = [p + n * h for p in outline] + [p - n * h for p in outline]
        for scale, depth in rings[1:]:
            verts += [c + (p - c) * scale + n * (h - cup * thickness * depth) for p in outline]
        for scale, depth in rings[1:]:
            verts += [c + (p - c) * scale - n * (h + thickness * 0.6 * depth) for p in outline]
        verts += [c + n * (h - cup * thickness * 1.6), c - n * (h + thickness * 0.9)]
        F1, F2, B1, B2 = 2 * m, 3 * m, 4 * m, 5 * m
        faces = []
        for i in range(m):
            j = (i + 1) % m
            faces.append((j, i, m + i, m + j))
            faces.append((i, j, F1 + j, F1 + i))
            faces.append((F1 + i, F1 + j, F2 + j, F2 + i))
            faces.append((F2 + i, F2 + j, 6 * m))
            faces.append((m + j, m + i, B1 + i, B1 + j))
            faces.append((B1 + j, B1 + i, B2 + i, B2 + j))
            faces.append((B2 + j, B2 + i, 6 * m + 1))
        self._add(verts, faces)

    def cone(self, base, tip, r, segs=12, up=UP):
        self.loft([V(base), lerp(V(base), V(tip), 0.5), V(tip)], [r, r * 0.55, r * 0.06], sides=segs, up=up, density=3)

    # ---- shorthands ----------------------------------------------------
    def tube(self, points, radii, segs=16, cap_start=True, cap_end=True, up_hint=UP, squash=(1.0, 1.0), point_cap=False):
        rr = [(r * squash[0], r * squash[1]) for r in radii]
        if point_cap:
            rr[-1] = (rr[-1][0] * 0.15, rr[-1][1] * 0.15)
        self.loft(points, rr, sides=max(segs, 14), up=up_hint, density=4)

    def ellipsoid(self, c, r, basis=None, segs=20, rings=12):
        self.oval(c, r, basis, max(segs, 18), max(rings, 10))

    def box(self, c, size, basis=None):
        """Rounded block (superellipse loft)."""
        basis = basis or Matrix.Identity(3)
        c = V(c)
        h = V(size) * 0.5
        a, b = c - basis @ Vector((0, 0, h.z)), c + basis @ Vector((0, 0, h.z))
        self.loft([a, lerp(a, b, 0.5), b], [(h.x, h.y)] * 3, sides=20, up=basis @ Vector((0, 1, 0)), exponent=0.45, density=2)

    # ---- data access --------------------------------------------------
    def slots(self):
        out = []
        for p in self.prims:
            if not p.negative and p.slot not in out:
                out.append(p.slot)
        return out

    def cage(self, slot=None, negative=False):
        verts, faces = [], []
        for p in self.prims:
            if p.negative != negative or (slot is not None and p.slot != slot and not negative):
                continue
            o = len(verts)
            verts += p.v
            faces += [tuple(i + o for i in f) for f in p.f]
        return verts, faces

    def signature(self):
        return [(len(p.v), len(p.f), p.slot, p.negative) for p in self.prims]


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
        if t.length < 1e-9:
            t = out[-1][2] if out else Vector((0, 0, 1))
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
    return [start + direction * length * (i / (n - 1)) + bend * length * (i / (n - 1)) ** 2 + twist * length * (i / (n - 1)) ** 3 for i in range(n)]


def taper(r0, r1, n, power=1.0):
    return [lerp(r0, r1, (i / (n - 1)) ** power) for i in range(n)]
