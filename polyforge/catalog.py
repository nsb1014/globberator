"""Part catalog: every part definition in polyforge/parts, keyed by id."""
import re

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
BY_ID = {**LEGACY, **{part.id: part for part in RESEARCH + head.CHARACTER_PARTS}}

# Common visual terms that may differ from the catalog's anatomical labels.
SEARCH_ALIASES = {
    "arm_grasping": "grasping arm forearm elbow forelimb",
    "beak_hooked": "hooked bill raptor beak",
    "crest_dorsal": "dorsal crest back ridge",
    "ear_pinna": "outer ear mammal ear flap",
    "eye_camera": "eye eyeball iris pupil eyelids slit round pupil",
    "eye_simple": "simple eye eyespot ocellus",
    "fin_paired": "pectoral fin side fin flipper",
    "foot_grasping": "ape foot grasping toes opposable big toe",
    "foot_hoof": "cloven hoof hooves split hoof boot shoe unsplit boot",
    "foot_webbed_long": "webbed foot swimming toes frog foot",
    "hand_basic": "humanoid hand human hand palm thumb fingers",
    "leg_bird": "avian leg bird knee hock tarsus",
    "leg_digitigrade": "raised heel canine leg dog leg",
    "leg_plantigrade": "flat foot leg humanoid upright leg heel down",
    "mane": "neck mane neck fur",
    "mouth_wide": "wide mouth frog gape oral opening",
    "muzzle": "snout muzzle face projection",
    "paw_padded": "animal paw cat paw dog paw toe pads",
    "suckers": "suction cups octopus suckers",
    "supraorbital_ridge": "brow ridge eyebrow bone eye ridge",
    "talons": "bird foot perching foot toes hallux",
    "tail_feather_fan": "bird tail fan tail feathers",
    "wing_feathered": "bird wing flight feathers feathered wing",
}


def _search_terms(value):
    return {word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word
            for word in re.findall(r"[a-z0-9]+", value.casefold())}


def search(query, limit=5):
    """Rank active families. Require every query term to match the same family."""
    exact = BY_ID.get(query.strip().casefold())
    if exact is not None:
        return [exact] if exact in PARTS else []
    terms = _search_terms(query) - {"a", "an", "the", "of", "for", "with"}
    if not terms:
        return []
    matches = []
    for part in PARTS:
        labels = _search_terms(part.id + " " + SEARCH_ALIASES.get(part.id, ""))
        context = _search_terms(" ".join((part.desc, part.category, part.attach, *part.tags)))
        if terms <= labels | context:
            score = 3 * len(terms & labels) + len(terms & context)
            matches.append((score, part))
    matches.sort(key=lambda hit: (-hit[0], hit[1].id))
    return [part for _, part in matches[:limit]]


def search_shape(part, query):
    if part.id == "foot_hoof" and _search_terms(query) & {"boot", "shoe", "unsplit"}:
        return {"part": part.id, "params": {"split": 0}}
    return {"family" if part.preset else "part": part.id}


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
