"""Part catalog: every part definition in polyforge/parts, keyed by id."""
from .parts import face, head, body, tips
from .parts import research, research_aesthetics, research_feeding, research_legs
from .parts import research_locomotion, research_manipulation, research_sensory

LIBRARY_VERSION = "6.1.0"

RESEARCH = research.load_parts((research_legs, research_locomotion, research_sensory,
                                research_feeding, research_manipulation, research_aesthetics))
LEGACY = {part.id: part for part in face.PARTS + head.PARTS + head.LEGACY + body.PARTS + tips.PARTS}
COMPLEMENTARY = (
    "horn_sweep", "horn_curl", "horn_antler", "horn_tusk", "foot_hoof", "hand_basic",
    "hand_pincer", "wing_bat", "mane", "frill", "shell", "tail_club", "tail_tuft",
    "mouth_trunk", "plate", "bulge",
)
PARTS = RESEARCH + [LEGACY[pid] for pid in COMPLEMENTARY]
BY_ID = {**LEGACY, **{part.id: part for part in RESEARCH}}


def get(pid):
    return BY_ID.get(pid)


def by_category():
    out = {}
    for p in RESEARCH:
        out.setdefault(p.category, []).append(p.id)
    out["complementary"] = list(COMPLEMENTARY)
    return out


def normalize_params(part, src, what, warns):
    out = {}
    src = src if isinstance(src, dict) else {}
    for k in src:
        if k not in part.params:
            warns.append("%s: unknown param '%s' for %s ignored" % (what, k, part.id))
    for k, (lo, hi, d) in part.params.items():
        v = src.get(k, d)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            v = d
        c = min(max(float(v), lo), hi)
        if abs(c - float(v)) > 1e-6:
            warns.append("%s: %s.%s clamped %.3f -> %.3f" % (what, part.id, k, float(v), c))
        out[k] = round(c) if k in part.discrete else round(c, 4)
    return out


def describe_part(p):
    data = {"id": p.id, "category": p.category, "desc": p.desc, "tags": p.tags, "attach": p.attach,
            "orient": p.orient, "capability": p.cap, "hint": p.hint,
            "params": {k: {"min": v[0], "max": v[1], "default": v[2]} for k, v in p.params.items()}}
    if p.host is not None:
        data.update(host=p.host, symmetry=p.symmetry)
    if p.preset:
        data["default_chain"] = p.preset(p.defaults())
    return data


def describe():
    return {"library_version": LIBRARY_VERSION, "parts": [describe_part(p) for p in PARTS]}
