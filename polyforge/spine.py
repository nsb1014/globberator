"""Spine curve in the sagittal plane (x = 0), recipe coordinates (+Y up, +Z forward).

Vertebrae are interpolated with Catmull-Rom. Samples carry position, tangent,
ellipse radii, arc parameter u in [0, 1] (rear tip to front tip, end caps
included) and a fractional vertebra index used for skin weights.
"""
import math

from mathutils import Vector, Matrix

SUB = 9
CAP = 8
RIGHT = Vector((1, 0, 0))
BACK = Vector((0, 0, 1))


def cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)


def up_of(t):
    return t.cross(RIGHT).normalized()


class Spine:
    def __init__(self, spine, shift=Vector((0, 0, 0))):
        self.vpos = [Vector((0.0, v["y"], v["z"])) + shift for v in spine]
        self.vw = [v["w"] for v in spine]
        self.vh = [v["h"] for v in spine]
        self._sample()

    def _sample(self):
        n = len(self.vpos)
        S = []
        for i in range(n - 1):
            i0, i3 = max(i - 1, 0), min(i + 2, n - 1)
            steps = SUB if i < n - 2 else SUB + 1
            for k in range(steps):
                t = k / SUB
                p = cr(self.vpos[i0], self.vpos[i], self.vpos[i + 1], self.vpos[i3], t)
                w = max(0.03, cr(self.vw[i0], self.vw[i], self.vw[i + 1], self.vw[i3], t))
                h = max(0.03, cr(self.vh[i0], self.vh[i], self.vh[i + 1], self.vh[i3], t))
                S.append({"p": p, "w": w, "h": h, "v": i + t})
        self.samples = S
        self._tangents()
        self._caps()
        self._tangents()
        self._arc()

    def _tangents(self):
        S = self.samples
        for k in range(len(S)):
            t = S[min(k + 1, len(S) - 1)]["p"] - S[max(k - 1, 0)]["p"]
            t.x = 0.0
            S[k]["t"] = t.normalized() if t.length > 1e-6 else BACK.copy()

    def _caps(self):
        first, last = self.samples[0], self.samples[-1]
        rear, front = [], []
        for k in range(1, CAP + 1):
            a = math.pi * 0.5 * k / CAP
            for src, sign, out in ((first, -1.0, rear), (last, 1.0, front)):
                cl = min(src["w"], src["h"]) * 0.95
                c = math.cos(a) if k < CAP else 0.0
                out.append({"p": src["p"] + src["t"] * sign * cl * math.sin(a), "w": max(src["w"] * c, 0.0),
                            "h": max(src["h"] * c, 0.0), "v": src["v"], "tip": k == CAP})
        self.samples = rear[::-1] + self.samples + front

    def _arc(self):
        S = self.samples
        acc = 0.0
        for k in range(len(S)):
            if k:
                acc += (S[k]["p"] - S[k - 1]["p"]).length
            S[k]["s"] = acc
        self.length = max(acc, 1e-4)
        for k, sm in enumerate(S):
            sm["u"] = sm["s"] / self.length
            a, b = S[max(k - 1, 0)], S[min(k + 1, len(S) - 1)]
            ds = max(b["s"] - a["s"], 1e-5)
            sm["dw"] = min(max((b["w"] - a["w"]) / ds, -20.0), 20.0)
            sm["dh"] = min(max((b["h"] - a["h"]) / ds, -20.0), 20.0)

    def at(self, u):
        u = min(max(u, 0.0), 1.0)
        S = self.samples
        for k in range(1, len(S)):
            if S[k]["u"] >= u:
                a, b = S[k - 1], S[k]
                span = b["u"] - a["u"]
                f = 0.0 if span < 1e-6 else (u - a["u"]) / span
                return {"p": a["p"].lerp(b["p"], f), "t": a["t"].lerp(b["t"], f).normalized(),
                        "w": a["w"] + (b["w"] - a["w"]) * f, "h": a["h"] + (b["h"] - a["h"]) * f,
                        "v": a["v"] + (b["v"] - a["v"]) * f, "dw": a["dw"] + (b["dw"] - a["dw"]) * f,
                        "dh": a["dh"] + (b["dh"] - a["dh"]) * f, "u": u}
        return S[-1]

    def surface(self, u, theta_deg, offset=0.0):
        """Surface point at (u, theta): theta 0 = +X side, 90 = top, -90 = belly.
        Returns position, outward normal, tangent and cross-section up."""
        s = self.at(u)
        t = s["t"]
        up = up_of(t)
        a = math.radians(theta_deg)
        w, h = max(s["w"], 0.005), max(s["h"], 0.005)
        ca, sa = math.cos(a), math.sin(a)
        p = s["p"] + RIGHT * ca * w + up * sa * h
        nr = (RIGHT * (ca / w) + up * (sa / h)).normalized()
        r = math.sqrt((w * ca) ** 2 + (h * sa) ** 2)
        drds = (w * s["dw"] * ca * ca + h * s["dh"] * sa * sa) / max(r, 1e-4)
        n = (nr - t * min(max(drds, -8.0), 8.0)).normalized()
        return {"p": p + n * offset, "n": n, "t": t, "up": up, "v": s["v"], "u": u}

    def project(self, point):
        """Nearest (u, theta, d) on the body surface for a point."""
        best = {"u": 0.5, "theta": 90.0, "d": float("inf")}
        S = self.samples
        lim = self.length / len(S) * 1.5
        for i, s in enumerate(S):
            rel = point - s["p"]
            along = rel.dot(s["t"])
            if abs(along) > lim and 0 < i < len(S) - 1:
                continue
            w, h = max(s["w"], 1e-3), max(s["h"], 1e-3)
            up = up_of(s["t"])
            lx, ly = rel.dot(RIGHT) / w, rel.dot(up) / h
            th = math.atan2(ly, lx)
            radial = math.hypot(lx * w, ly * h)
            surf_r = math.hypot(math.cos(th) * w, math.sin(th) * h)
            d = abs(radial - surf_r) + abs(along)
            if d < best["d"]:
                best = {"u": s["u"], "theta": math.degrees(th), "d": d, "inside": radial < surf_r}
        return best

    def bottom_y(self):
        return min(s["p"].y - s["h"] for s in self.samples)
