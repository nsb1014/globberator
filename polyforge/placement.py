"""Placement rules carried over from the original attachment code
(tools/attachments.py, mounted_part):

* Symmetry is automatic. A part on the spine's midline is a single centred part;
  a part off the midline always gets a reflected twin. There is no mirror flag
  to forget.
* Snap to centre. A socket close to the midline is forced exactly onto it
  (x = 0, no turn or roll), and anything authored on the -X side is reflected to
  the canonical +X side, so recipes are always stored one way.
* Snap into place. Each part category has named sockets on the spine (head front,
  brow, eyes, ears, horns, cheeks, back, tail tip, shoulders, hips). Interactive
  placement and AI ops snap to the nearest matching socket within a small radius.

Body coordinates: u runs 0 (rear tip) to 1 (front tip); theta is the angle
around the cross-section (0 = +X side, 90 = top, -90 = belly, 180 = -X side).
The midline is theta = +/-90.
"""
CENTER_SNAP_DEG = 12.0

# "center": always on the midline, "pair": always mirrored, "any": snap to the
# midline when close, otherwise mirrored.
SYMMETRY_BY_CATEGORY = {"mouth": "center", "nose": "center", "tail": "center", "wing": "pair", "ear": "pair", "eye": "any",
                        "horn": "pair", "detail": "any", "foot": "pair", "hand": "pair"}
SYMMETRY_BY_PART = {"brow_ridge": "center", "crest": "center", "frill": "center", "shell": "center", "mane": "center",
                    "fin_dorsal": "center", "plate": "center", "horn_rhino": "center", "eye_cyclops": "center",
                    "cheek": "pair", "antenna": "pair", "horn_tusk": "pair", "spike": "any", "bulge": "any", "horn_spike": "any"}

# Named sockets: (u, theta). Parts snap to sockets of their category.
SOCKETS = {
    "mouth": {"mouth": (0.985, -90.0), "muzzle": (0.975, -90.0)},
    "nose": {"nose": (0.995, -90.0)},
    "eye": {"eyes": (0.95, 32.0), "eyes_high": (0.93, 55.0), "eyes_front": (0.97, 20.0), "cyclops": (0.965, 90.0)},
    "ear": {"ears": (0.91, 28.0), "ears_top": (0.89, 60.0)},
    "horn": {"horns": (0.925, 55.0), "horns_side": (0.92, 30.0), "nose_horn": (0.975, 90.0)},
    "tail": {"tail_tip": (0.0, 90.0)},
    "wing": {"wings": (0.62, 50.0)},
    "detail": {"brow": (0.945, 90.0), "cheeks": (0.95, 5.0), "crown": (0.9, 90.0), "neck_top": (0.78, 90.0),
               "back": (0.5, 90.0), "shoulders": (0.6, 20.0), "haunches": (0.3, 15.0), "belly": (0.45, -90.0)},
}
LIMB_SOCKETS = {"shoulders": (0.62, -60.0), "hips": (0.28, -55.0), "arms": (0.7, 5.0), "center_leg": (0.45, -90.0)}
SNAP_U = 0.035
SNAP_THETA = 14.0


def symmetry(part):
    return SYMMETRY_BY_PART.get(part.id, SYMMETRY_BY_CATEGORY.get(part.category, "any"))


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def canonical_theta(theta):
    """Reflect -X side angles onto the +X side (theta in [-90, 90])."""
    theta = wrap(theta)
    if theta > 90.0:
        theta = 180.0 - theta
    elif theta < -90.0:
        theta = -180.0 - theta
    return theta


def centred(theta, mode="any"):
    """Return (theta, is_centre) after the symmetry rules."""
    t = canonical_theta(theta)
    if mode == "center":
        return (90.0 if t >= 0 else -90.0), True
    if mode == "pair":
        if abs(abs(t) - 90.0) < 1e-3:
            t = 89.0 if t > 0 else -89.0     # a paired part needs a side
        return t, False
    if abs(t - 90.0) <= CENTER_SNAP_DEG:
        return 90.0, True
    if abs(t + 90.0) <= CENTER_SNAP_DEG:
        return -90.0, True
    return t, False


def snap_part(category, u, theta, radius_u=SNAP_U, radius_t=SNAP_THETA):
    """Nearest socket of the category within the snap radius, else the input."""
    best, bd = None, 1e9
    t0 = canonical_theta(theta)
    for name, (su, st) in SOCKETS.get(category, {}).items():
        du, dt = abs(su - u) / radius_u, abs(wrap(st - t0)) / radius_t
        if du <= 1 and dt <= 1 and du + dt < bd:
            best, bd = (name, su, st), du + dt
    return best


def snap_limb(u, theta):
    best, bd = None, 1e9
    t0 = canonical_theta(theta)
    for name, (su, st) in LIMB_SOCKETS.items():
        du, dt = abs(su - u) / 0.05, abs(wrap(st - t0)) / 18.0
        if du <= 1 and dt <= 1 and du + dt < bd:
            best, bd = (name, su, st), du + dt
    return best
