"""Part catalog: every part definition in polyforge/parts, keyed by id."""
from importlib import import_module
from pathlib import Path
import re

from . import qualification

from .parts import anatomy, face, head, body, pilots, tips
from .parts import research, research_aesthetics, research_feeding, research_legs
from .parts import research_locomotion, research_manipulation, research_sensory

LIBRARY_VERSION = "6.3.0"

RESEARCH = research.load_parts((research_legs, research_locomotion, research_sensory,
                                research_feeding, research_manipulation, research_aesthetics))
LEGACY = {part.id: part for part in face.PARTS + head.PARTS + head.LEGACY + body.PARTS + tips.PARTS}
COMPLEMENTARY = (
    "horn_sweep", "horn_curl", "horn_antler", "horn_tusk", "foot_hoof", "hand_basic",
    "hand_pincer", "wing_bat", "mane", "frill", "shell", "tail_club", "tail_tuft",
    "mouth_trunk", "plate", "bulge",
)
QUALIFICATION = qualification.records()
RESERVED_IDS = set(LEGACY) | {part.id for part in RESEARCH + anatomy.PARTS + pilots.PARTS + head.CHARACTER_PARTS}
CANDIDATE_PARTS = {}
CANDIDATE_TRAITS = {}
for path in sorted((Path(__file__).resolve().parent / "parts").glob("candidate_*.py")):
    module = import_module(f".parts.{path.stem}", __package__)
    for part in module.PARTS:
        if part.id in RESERVED_IDS or part.id in CANDIDATE_PARTS or part.id not in QUALIFICATION:
            raise ValueError(f"Invalid or duplicate research candidate {part.id}")
        CANDIDATE_PARTS[part.id] = part
    CANDIDATE_TRAITS.update(getattr(module, "TRAITS", {}))

QUALIFIED_PARTS = [part for key, part in CANDIDATE_PARTS.items() if qualification.approved(QUALIFICATION[key])]
PARTS = RESEARCH + [LEGACY[pid] for pid in COMPLEMENTARY] + anatomy.PARTS + pilots.PARTS + QUALIFIED_PARTS
BY_ID = {**LEGACY, **{part.id: part for part in PARTS + head.CHARACTER_PARTS}, **CANDIDATE_PARTS}


# Common visual terms that may differ from the catalog's anatomical labels.
SEARCH_ALIASES = {
    "arm_grasping": "grasping arm forearm elbow forelimb",
    "beak_hooked": "hooked bill raptor beak",
    "crest_dorsal": "dorsal crest back ridge",
    "dolphin_gape": "dolphin mouth smile crease long snout rostrum",
    "dolphin_dorsal": "dolphin cetacean swept falcate dorsal fin",
    "bat_flight_wing": "bat wing webbed fingers scalloped membrane web skeletal wing",
    "bat_tail_membrane": "bat triangular tail membrane uropatagium",
    "bat_hindfoot": "bat hind foot toes",
    "ear_pinna": "outer ear mammal ear flap",
    "eye_camera": "eye eyeball iris pupil eyelids slit round pupil",
    "eye_simple": "simple eye eyespot ocellus",
    "fin_paired": "pectoral fin side fin flipper",
    "fin_median": "dorsal fin top midline back sail",
    "flukes_cetacean": "whale dolphin porpoise horizontal tail fin fluke axial foil",
    "foot_grasping": "ape foot grasping toes opposable big toe",
    "foot_hoof": "cloven hoof hooves split hoof boot shoe unsplit boot",
    "foot_webbed_long": "webbed foot swimming toes frog foot",
    "hand_basic": "humanoid hand human hand palm thumb fingers",
    "head_bovine": "bovine bull cattle cow skull head muzzle heavy brow jaw hinge",
    "leg_bird": "avian leg bird knee hock tarsus",
    "leg_digitigrade": "raised heel canine leg dog leg",
    "leg_plantigrade": "flat foot leg humanoid upright leg heel down",
    "mane": "neck mane neck fur",
    "mouth_wide": "wide mouth frog gape oral opening",
    "muzzle": "snout muzzle face projection",
    "paw_padded": "animal paw cat paw dog paw toe pads",
    "pincer_crescent": "crab claw pincer crescent grasping hinged claw",
    "suckers": "suction cups octopus suckers",
    "supraorbital_ridge": "brow ridge eyebrow bone eye ridge",
    "talons": "bird foot perching foot toes hallux",
    "tail_feather_fan": "bird tail fan tail feathers",
    "wing_feathered": "bird wing flight feathers feathered wing",
}

# Physical jobs are independent of the author's library categories. For example,
# an elytron is a protective cover despite being listed with insect locomotion.
FUNCTIONS = {
    "locomotion": "locomotion",
    "sensory": "sense",
    "feeding": "feed",
    "manipulation": "grasp",
    "aesthetics": "display",
    "foot": "support",
    "hand": "grasp",
    "tail": "display",
    "wing": "fly",
    "horn": "protect",
    "ear": "sense",
    "nose": "sense",
    "eye": "sense",
    "mouth": "feed",
}
FUNCTION_BY_ID = {
    **dict.fromkeys(("leg_arthropod", "leg_digitigrade", "leg_plantigrade", "leg_sprawling",
                     "leg_bird", "paw_padded", "foot_grasping", "talons", "claws"), "support"),
    **dict.fromkeys(("fin_paired", "fin_median", "dolphin_dorsal", "flukes_cetacean", "tail_fin_heterocercal",
                     "foot_webbed_long", "siphon", "web_interbrachial", "bell_radial"), "swim"),
    **dict.fromkeys(("wing_feathered", "wing_membrane_insect", "bat_flight_wing"), "fly"),
    **dict.fromkeys(("elytron", "carapace", "shell", "plate", "stinger"), "protect"),
    "gill_slits": "breathe", "muzzle": "bulk", "bulge": "bulk", "cheek": "bulk",
    "dolphin_gape": "feed", "head_bovine": "feed", "tail_segmented": "balance",
    "tail_flexible": "balance", "leg_jumping": "jump",
}
FUNCTION_ALIASES = {
    "walk": "support", "walking": "support", "run": "support", "stand": "support",
    "flight": "fly", "flap": "fly", "glide": "fly", "flying": "fly",
    "swimming": "swim", "paddle": "swim", "propulsion": "swim",
    "feeding": "feed", "bite": "feed", "sensory": "sense", "sensing": "sense",
    "manipulation": "grasp", "armor": "protect", "armour": "protect",
    "protection": "protect", "protective": "protect", "decoration": "display", "aesthetics": "display",
    "respiration": "breathe", "mass": "bulk",
}
HOST_ALIASES = {
    "torso": "body", "spine": "body", "head": "body", "skin": "body",
    "tip": "limb_end", "limb_tip": "limb_end", "limb_surface": "limb",
    "core": "body_plan",
}

METABALL_FAMILIES = frozenset(("bulge", "cheek", "dewlap", "muzzle", "supraorbital_ridge"))
DEFORMABLE_FAMILIES = frozenset((
    "bat_flight_wing", "wing_bat", "fin_paired", "flukes_cetacean", "mane", "oral_arms",
    "tail_flexible", "tail_fin_heterocercal", "tail_tuft", "tentacle_fringe",
    "siphon", "tongue", "vocal_sac", "web_interbrachial",
    "wing_membrane_insect", "dolphin_gape", "bat_tail_membrane",
))
RIGID_CHAINS = frozenset(("leg_arthropod", "pincer_limb", "tail_segmented"))
REGIONS = {
    "bat_flight_wing": {"root": "metaball", "base": "deformable"},
    "muzzle": {"skin": "metaball"},
    "jaws_toothed": {"base": "deformable", "teeth": "rigid"},
    "wing_feathered": {"base": "deformable", "accent": "rigid", "detail": "rigid"},
    "eye_camera": {"base": "deformable", "white": "rigid", "eye": "rigid", "black": "rigid", "horn": "rigid"},
    "crest_dorsal": {"base": "deformable", "detail": "rigid"},
    "head_bovine": {"base": "rigid", "detail": "rigid"},
    "pincer_crescent": {"accent": "rigid"},
}


def _search_terms(value):
    return {word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word
            for word in re.findall(r"[a-z0-9]+", value.casefold())}


def metadata(part):
    """Describe the host, visible form, physical job and construction of a family."""
    host = part.host or {"tip": "limb_end", "core": "body_plan"}.get(part.attach, "body")
    construction = "rigid"
    if part.id in METABALL_FAMILIES:
        construction = "metaball"
    elif part.id in DEFORMABLE_FAMILIES or part.preset and part.id not in RIGID_CHAINS:
        construction = "deformable"
    result = {"host": host, "function": FUNCTION_BY_ID.get(part.id, FUNCTIONS.get(part.category, "display")),
              "shape": SEARCH_ALIASES.get(part.id, part.id.replace("_", " ")), "construction": construction}
    if part.id in REGIONS:
        result["regions"] = REGIONS[part.id].copy()
    result.update(CANDIDATE_TRAITS.get(part.id, {}))
    if part.id in CANDIDATE_PARTS:
        result["qualification"] = "qualified" if part in QUALIFIED_PARTS else "draft"
    return result


def _filter_key(value, aliases):
    key = value.strip().casefold().replace("-", "_").replace(" ", "_")
    return aliases.get(key, key)


def search(query="", limit=5, *, host=None, function=None, shape=None):
    """Rank active families and match each supplied filter against one family."""
    limit = min(5, max(0, limit))
    exact = BY_ID.get(query.strip().casefold()) if query.strip() else None
    common = {"a", "an", "the", "of", "for", "with"}
    terms = _search_terms(query) - common
    if not limit or not (terms or host or function or shape):
        return []
    if exact is not None and exact not in PARTS:
        return []
    host = _filter_key(host, HOST_ALIASES) if host else None
    function = _filter_key(function, FUNCTION_ALIASES) if function else None
    shape_terms = _search_terms(shape) - common if shape else set()
    matches = []
    for part in (exact,) if exact else PARTS:
        data = metadata(part)
        if host and data["host"] != host:
            continue
        if function and data["function"] != function:
            if function != "locomotion" or data["function"] not in {"support", "fly", "swim", "jump", "balance"}:
                continue
        labels = _search_terms(part.id + " " + data["shape"])
        context = _search_terms(" ".join((part.desc, part.category, part.attach, *part.tags)))
        if (exact or terms <= labels | context) and shape_terms <= labels | _search_terms(part.desc):
            score = 3 * len((terms | shape_terms) & labels) + len(terms & context)
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
    out["anatomy"] = [p.id for p in anatomy.PARTS]
    out["pilots"] = [p.id for p in pilots.PARTS]
    if QUALIFIED_PARTS:
        out["qualified"] = [p.id for p in QUALIFIED_PARTS]
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
    traits = metadata(p)
    traits["shape_terms"] = traits.pop("shape")
    data.update(traits)
    if p.id in CANDIDATE_PARTS:
        record = QUALIFICATION[p.id]
        data["qualification_work"] = qualification.remaining_work(record)
        data["qualification_reason"] = record["reason"]
    if p.symmetry is not None:
        data["symmetry"] = p.symmetry
    if p.preset:
        data["default_chain"] = p.preset(p.defaults())
    return data


def describe():
    return {"library_version": LIBRARY_VERSION, "parts": [describe_part(p) for p in PARTS]}
