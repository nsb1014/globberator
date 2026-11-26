"""Build the part library spec from the species research (research/part_library.json).

    python3 research/build_library.py

The library is derived only from research/species/*.json. Each entry lists the
researched parts it generalises ("species.part_id").

Measured from the research (computed here, never typed in):
  length, root_radius   relative to the body length, observed min/median/max
                        widened by STYLE_TOLERANCE into the allowed range
  count                 how many repeats the species have, where a part repeats
  joints                merged joint chain: types, axes, union of ranges
  attach_pos            mean normalized attach point (+X side for pairs)
  penetration           how deep the root sinks into the core mesh

Curated from the research descriptions: kind, symmetry, description and the
"shape" controls (the variations the species notes describe). Nothing here
builds geometry.
"""
import glob
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ["locomotion", "sensory", "feeding", "manipulation", "aesthetics"]
STYLE_TOLERANCE = 0.3    # measured ranges widen by 30% each way so a fit can deviate from the species seen

# kind: limb = joint chain grown from the body; tip = sits on a limb's end joint;
# surface = placed on the body or a limb surface; core = a body plan the body itself must form.
# shape: {name: [min, max, default, meaning]}
LIB = [
    # ---------------- locomotion ----------------
    dict(id="leg_arthropod", category="locomotion", kind="limb", symmetry="pair",
         desc="Thin jointed walking leg: ball joint at the coxa, hinged segments; leaves the body sideways, then turns down.",
         sources=["beetle.foreleg_L", "beetle.midleg_L", "beetle.hindleg_L", "crab.walking_leg_L", "scorpion.walking_legs_L"],
         shape={"segments": [3, 5, 4, "jointed segments after the coxa"], "sprawl_deg": [20, 80, 55, "angle out from the body before turning down"],
                "tibia_teeth": [0, 1, 0, "toothed outer edge for digging (beetles)"]}),
    dict(id="leg_digitigrade", category="locomotion", kind="limb", symmetry="pair",
         desc="Mammal leg standing on its toes: shoulder/hip ball, elbow/knee hinge, raised wrist/hock.",
         sources=["canine.legs_fore_L", "canine.legs_hind_L", "feline.forelimb_L", "feline.hindlimb_L"],
         shape={"hock_lift": [0.0, 1.0, 0.6, "how high the wrist/hock sits off the ground"], "dewclaw": [0, 1, 0, "raised inner digit on the foreleg"]}),
    dict(id="leg_plantigrade", category="locomotion", kind="limb", symmetry="pair",
         desc="Ape leg (hip ball, knee hinge, ankle) that stands on the whole sole.",
         sources=["primate.leg_L"],
         shape={"knee_bend_deg": [0, 60, 20, "resting knee flexion"]}),
    dict(id="leg_sprawling", category="locomotion", kind="limb", symmetry="pair",
         desc="Reptile leg: upper segment nearly horizontal, elbow/knee out to the side, five clawed digits.",
         sources=["lizard.leg_fore_L", "lizard.leg_hind_L"],
         shape={"sprawl_deg": [30, 90, 70, "upper segment angle out from vertical"], "digits": [3, 5, 5, "clawed digits"]}),
    dict(id="leg_jumping", category="locomotion", kind="limb", symmetry="pair",
         desc="Long hind leg folded in a Z at rest (thigh, shank, elongated ankle) that extends to jump.",
         sources=["frog.hind_leg_L"],
         shape={"fold": [0.0, 1.0, 0.8, "0 = extended, 1 = fully folded at rest"]}),
    dict(id="leg_bird", category="locomotion", kind="limb", symmetry="pair",
         desc="Bird leg: feathered thigh hidden in the body, bare scaled tarsus, reversed ankle.",
         sources=["raptor.leg_L"],
         shape={"feathered": [0.0, 1.0, 0.7, "how far down the leg the feathers reach"], "scutes": [0, 1, 1, "scaled tarsus"]}),
    dict(id="paw_padded", category="locomotion", kind="tip", symmetry="pair",
         desc="Paw with a central pad and four digital pads.",
         sources=["canine.paws_fore_L", "canine.paws_hind_L", "feline.paw_pads_L"],
         shape={"toe_pads": [3, 5, 4, "digital pads"], "spread": [0.0, 1.0, 0.4, "toe splay"]}),
    dict(id="foot_webbed_long", category="locomotion", kind="tip", symmetry="pair",
         desc="Long-toed hind foot with webbing between the toes.",
         sources=["frog.hind_foot_webbed_L"],
         shape={"toes": [4, 5, 5, "toes"], "web": [0.0, 1.0, 0.8, "how far the web reaches toward the toe tips"]}),
    dict(id="foot_grasping", category="locomotion", kind="tip", symmetry="pair",
         desc="Plantigrade ape foot with an opposable big toe.",
         sources=["primate.foot_L"],
         shape={"hallux_angle_deg": [10, 60, 35, "big-toe angle away from the other toes"], "curl": [0.0, 1.0, 0.3, "toe flexion"]}),
    dict(id="wing_feathered", category="locomotion", kind="limb", symmetry="pair",
         desc="Bird wing on a shoulder-elbow-wrist chain, with separate slotted primaries; folds along the body.",
         sources=["raptor.wing_L"],
         shape={"primaries": [6, 11, 10, "primary flight feathers"], "slots": [0.0, 1.0, 0.6, "gap between primary tips"], "fold": [0.0, 1.0, 1.0, "0 = spread, 1 = folded"]}),
    dict(id="elytron", category="locomotion", kind="surface", symmetry="pair",
         desc="Hard domed wing case over the abdomen, meeting its twin on the midline; hinges up and out for flight.",
         sources=["beetle.elytron_L"],
         shape={"dome": [0.2, 1.5, 0.8, "height of the dome"], "open_deg": [0, 60, 0, "raised for flight"]}),
    dict(id="wing_membrane_insect", category="locomotion", kind="surface", symmetry="pair",
         desc="Thin veined flight wing folded under the elytron at rest.",
         sources=["beetle.hindwing_L"],
         shape={"fold": [0.0, 1.0, 1.0, "0 = spread, 1 = folded under the elytron"], "veins": [0, 8, 4, "visible veins"]}),
    dict(id="fin_paired", category="locomotion", kind="surface", symmetry="pair",
         desc="Swept fin on the lower flank (pectoral, pelvic); wing-like for lift and steering.",
         sources=["shark.pectoral_fin_L", "shark.pelvic_fin_L"],
         shape={"sweep": [-1.0, 1.0, 0.5, "trailing-edge sweep"], "droop_deg": [0, 45, 20, "angle below horizontal"]}),
    dict(id="fin_median", category="locomotion", kind="surface", symmetry="centre",
         desc="Upright fin on the midline: tall first dorsal, small second dorsal, ventral anal fin.",
         sources=["shark.dorsal_fin_1", "shark.dorsal_fin_2", "shark.anal_fin"],
         shape={"sweep": [-1.0, 1.0, 0.6, "back-sweep of the tip"], "ventral": [0, 1, 0, "hangs below the body (anal fin)"]}),
    dict(id="tail_fin_heterocercal", category="locomotion", kind="tip", symmetry="centre",
         desc="Crescent tail fin with a longer upper lobe that carries the spine.",
         sources=["shark.caudal_fin"],
         shape={"upper_lobe": [1.0, 2.5, 1.6, "upper lobe length relative to the lower"], "fork": [0.0, 1.0, 0.6, "depth of the notch"]}),
    dict(id="tail_feather_fan", category="locomotion", kind="surface", symmetry="centre",
         desc="Fan of tail feathers that spreads for steering and braking.",
         sources=["raptor.tail_feathers"],
         shape={"feathers": [8, 14, 12, "tail feathers"], "spread_deg": [10, 120, 40, "fan opening"]}),
    dict(id="tail_flexible", category="locomotion", kind="limb", symmetry="centre",
         desc="Tapering tail of many vertebrae used for balance and steering; bushy in foxes, slim in cats, long and compressed in iguanas.",
         sources=["canine.tail", "feline.tail", "lizard.tail"],
         shape={"taper": [0.1, 1.0, 0.6, "tip radius relative to the root"], "brush": [0.0, 1.0, 0.0, "fur volume (fox brush)"],
                "compress": [0.0, 1.0, 0.0, "side-to-side flattening (iguana)"]}),
    dict(id="siphon", category="locomotion", kind="surface", symmetry="centre",
         desc="Short muscular funnel beside the head that aims a water jet.",
         sources=["octopus.funnel"],
         shape={"aim_deg": [0, 90, 30, "jet direction"]}),
    dict(id="web_interbrachial", category="locomotion", kind="surface", symmetry="radial",
         desc="Skin web spanning the bases of the arms; spreads like an umbrella.",
         sources=["octopus.web"],
         shape={"depth": [0.1, 1.0, 0.3, "how far along the arms the web reaches"], "scallop": [0.0, 1.0, 0.5, "edge curvature between arms"]}),
    dict(id="bell_radial", category="locomotion", kind="core", symmetry="radial",
         desc="Radially symmetric swimming bell (shallow dome, scalloped rim) that pulses to swim.",
         sources=["jellyfish.coronal_muscle_bell"],
         shape={"dome": [0.2, 1.5, 0.45, "height relative to the radius"], "lobes": [4, 16, 8, "rim lobes"], "translucent": [0, 1, 1, "gelatinous see-through tissue"]}),
    # ---------------- sensory ----------------
    dict(id="eye_camera", category="sensory", kind="surface", symmetry="pair",
         desc="Camera eye with a round pupil; set forward (ape, hawk) or to the side (frog, shark, octopus).",
         sources=["frog.eye_L", "octopus.eye_L", "primate.eye_L", "raptor.eye_L", "shark.eye_L", "lizard.eye_L"],
         shape={"facing_deg": [0, 90, 45, "0 = forward, 90 = sideways"], "bulge": [0.0, 1.0, 0.3, "how far it protrudes (frog high)"],
                "sclerotic_ring": [0, 1, 0, "bony ring around the eye (birds)"]}),
    dict(id="eye_slit_pupil", category="sensory", kind="surface", symmetry="pair",
         desc="Forward-facing eye with a vertical slit pupil (cats, foxes).",
         sources=["feline.eye_L", "canine.eyes_L"],
         shape={"slit": [0.1, 1.0, 0.3, "pupil width, 1 = round"], "facing_deg": [0, 45, 15, "0 = forward"]}),
    dict(id="eye_compound", category="sensory", kind="surface", symmetry="pair",
         desc="Faceted compound eye bulging from the side of the head.",
         sources=["beetle.eye_L"],
         shape={"bulge": [0.2, 1.0, 0.5, "protrusion"]}),
    dict(id="eye_simple", category="sensory", kind="surface", symmetry="any",
         desc="Small bead eye or light-sensing spot: scorpion median and lateral eyes, jellyfish rhopalia, lizard parietal eye.",
         sources=["scorpion.eyes_median", "scorpion.eyes_lateral", "jellyfish.rhopalia", "lizard.parietal_eye"],
         shape={"cluster": [1, 5, 2, "eyes per group"]}),
    dict(id="eye_stalked", category="sensory", kind="surface", symmetry="pair",
         desc="Eye on a movable stalk that folds down into a socket.",
         sources=["crab.eye_stalk_L"],
         shape={"stalk": [0.2, 1.0, 0.5, "stalk length relative to the eye"], "retract": [0.0, 1.0, 0.0, "folded into the socket"]}),
    dict(id="antenna_segmented", category="sensory", kind="surface", symmetry="pair",
         desc="Jointed feeler: elbowed with a lamellate club (beetle) or a long whip (crab).",
         sources=["beetle.antenna_L", "crab.antennule_L", "crab.antenna_L"],
         shape={"segments": [3, 12, 10, "segments"], "elbow_deg": [0, 120, 0, "bend after the first segment (geniculate)"],
                "club": [0.0, 1.0, 0.0, "fan-shaped club at the tip"]}),
    dict(id="ear_pinna", category="sensory", kind="surface", symmetry="pair",
         desc="External ear flap: tall pointed cone (fox, cat) or flat rounded ear close to the head (ape).",
         sources=["canine.ears_L", "feline.ear_L", "primate.ear_L"],
         shape={"point": [0.0, 1.0, 0.7, "0 = round, 1 = pointed"], "cup": [0.0, 1.0, 0.6, "depth of the opening"],
                "flat": [0.0, 1.0, 0.0, "lies against the head (ape)"]}),
    dict(id="tympanum", category="sensory", kind="surface", symmetry="pair",
         desc="Flush round eardrum behind the eye with a slight rim (frogs, iguanas).",
         sources=["frog.tympanum_L", "lizard.ear_opening_L"],
         shape={"rim": [0.0, 1.0, 0.4, "raised ring"], "recess": [0.0, 1.0, 0.2, "sunk below the skin"]}),
    dict(id="nose_pad", category="sensory", kind="surface", symmetry="centre",
         desc="Moist nose pad with comma-shaped nostrils (fox, cat) or a flat ape nose.",
         sources=["canine.nose", "feline.nose", "primate.nose"],
         shape={"projection": [0.0, 1.0, 0.5, "how far it stands out"]}),
    dict(id="nostril_slit", category="sensory", kind="surface", symmetry="pair",
         desc="Flush slit nostril with a skin flap under the snout (sharks).",
         sources=["shark.nostril_L"],
         shape={"flap": [0.0, 1.0, 0.5, "flap over the opening"]}),
    dict(id="whiskers", category="sensory", kind="surface", symmetry="pair",
         desc="Fan of long stiff vibrissae from a whisker pad beside the nose.",
         sources=["canine.vibrissae_L", "feline.whiskers_L"],
         shape={"count": [3, 12, 6, "whiskers per side"], "spread_deg": [10, 60, 35, "fan angle"], "droop": [-1.0, 1.0, 0.2, "curve down at the tips"]}),
    dict(id="pectines", category="sensory", kind="surface", symmetry="pair",
         desc="Comb-shaped ground-sensing organ under the body, teeth pointing back.",
         sources=["scorpion.pectines_L"],
         shape={"teeth": [6, 30, 16, "comb teeth"], "splay_deg": [0, 45, 20, "angle out from the midline"]}),
    # ---------------- feeding ----------------
    dict(id="jaws_toothed", category="feeding", kind="surface", symmetry="centre",
         desc="Upper jaw and hinged lower jaw with teeth: carnassials (fox, cat), serrated rows (shark, iguana), large canines (ape).",
         sources=["canine.jaws", "feline.jaws", "lizard.jaws", "primate.jaws", "shark.upper_jaw", "shark.lower_jaw"],
         shape={"teeth": [0.0, 1.0, 0.6, "tooth size"], "tooth_rows": [1, 5, 1, "replacement rows visible (shark)"], "underslung": [0, 1, 0, "mouth under the snout (shark)"]}),
    dict(id="muzzle", category="feeding", kind="surface", symmetry="centre",
         desc="Long tapering mammal muzzle carrying the nose pad and jaws.",
         sources=["canine.head_muzzle"],
         shape={"taper": [0.0, 1.0, 0.6, "narrowing toward the nose"]}),
    dict(id="mouth_wide", category="feeding", kind="surface", symmetry="centre",
         desc="Very wide lipless gape spanning the head (frog).",
         sources=["frog.mouth"],
         shape={"curve": [-1.0, 1.0, 0.2, "upturn at the corners"]}),
    dict(id="beak_hooked", category="feeding", kind="surface", symmetry="centre",
         desc="Hooked tearing beak with a cere (hawk) or a parrot-like beak hidden among the arms (octopus).",
         sources=["raptor.beak", "octopus.beak"],
         shape={"hook": [0.0, 1.0, 0.8, "downward hook of the tip"], "cere": [0, 1, 1, "fleshy band at the base"], "tomial_tooth": [0, 1, 1, "notch on the cutting edge"]}),
    dict(id="mandibles", category="feeding", kind="surface", symmetry="pair",
         desc="Jaws that close sideways: small pincer chelicerae (scorpion) to huge branched stag-beetle mandibles.",
         sources=["beetle.mandible_L", "scorpion.chelicera_L"],
         shape={"curl": [0.0, 1.5, 0.7, "inward curve"], "tines": [0, 3, 1, "inner branches"], "chelate": [0, 1, 0, "ends in a tiny pincer (chelicera)"]}),
    dict(id="mouth_palps", category="feeding", kind="surface", symmetry="pair",
         desc="Short jointed mouth feelers or plates that handle food (beetle palps, crab maxillipeds).",
         sources=["beetle.palp_L", "crab.maxilliped_3"],
         shape={"segments": [2, 4, 3, "segments"], "plate": [0.0, 1.0, 0.0, "flat lid-like plate (crab)"]}),
    dict(id="tongue", category="feeding", kind="surface", symmetry="centre",
         desc="Projectile sticky tongue fixed at the front of the jaw (frog) or forked flicking tongue (iguana); inside the mouth at rest.",
         sources=["frog.tongue", "lizard.tongue"],
         shape={"fork": [0.0, 1.0, 0.0, "split tip"], "tip_pad": [0.0, 1.0, 0.5, "sticky pad"], "extend": [0.0, 1.0, 0.0, "0 = at rest, 1 = fully out"]}),
    dict(id="oral_arms", category="feeding", kind="surface", symmetry="radial",
         desc="Frilled arms hanging from a four-lobed central mouth under a bell.",
         sources=["jellyfish.oral_arms", "jellyfish.manubrium_mouth"],
         shape={"frill": [0.0, 1.0, 0.6, "ruffled edges"]}),
    dict(id="tentacle_fringe", category="feeding", kind="surface", symmetry="radial",
         desc="Ring of many fine tentacles around a bell margin.",
         sources=["jellyfish.marginal_tentacles"],
         shape={"sway": [0.0, 1.0, 0.5, "drift amplitude"]}),
    dict(id="gill_slits", category="feeding", kind="surface", symmetry="pair",
         desc="Row of vertical slits behind the head where water leaves the mouth.",
         sources=["shark.gill_slits_L"],
         shape={"spacing": [0.5, 2.0, 1.0, "gap between slits relative to slit width"]}),
    # ---------------- manipulation ----------------
    dict(id="pincer_limb", category="manipulation", kind="limb", symmetry="pair",
         desc="Jointed arm ending in a chela: a fixed finger and a hinged finger.",
         sources=["crab.cheliped_L", "scorpion.pedipalp_L"],
         shape={"claw_bulk": [0.5, 2.5, 1.2, "chela thickness"], "asymmetry": [0.0, 1.0, 0.0, "one chela larger than the other"]}),
    dict(id="arm_grasping", category="manipulation", kind="limb", symmetry="pair",
         desc="Shoulder-elbow-wrist arm ending in a hand (ape arm, frog forelimb).",
         sources=["primate.arm_L", "primate.hand_L", "frog.fore_leg_L"],
         shape={"fingers": [4, 5, 5, "digits"], "knuckle_walk": [0.0, 1.0, 0.0, "weight on the backs of the flexed fingers"]}),
    dict(id="arm_hydrostatic", category="manipulation", kind="limb", symmetry="pair",
         desc="Boneless arm that bends anywhere along its length and tapers to a fine tip.",
         sources=["octopus.arm_L1", "octopus.arm_L2", "octopus.arm_L3", "octopus.arm_L4"],
         shape={"curl": [0.0, 1.5, 0.8, "tip coil"], "taper": [0.05, 0.5, 0.15, "tip radius relative to the root"]}),
    dict(id="suckers", category="manipulation", kind="surface", symmetry="pair", on="limb",
         desc="Two rows of cupped suction discs along the underside of an arm, shrinking toward the tip.",
         sources=["octopus.arm_L1"],
         shape={"per_arm": [20, 280, 120, "suckers per arm"], "rows": [1, 2, 2, "rows"]}),
    dict(id="talons", category="manipulation", kind="tip", symmetry="pair",
         desc="Grasping foot with four long curved talons (three forward, one back, the back one largest).",
         sources=["raptor.talon_L"],
         shape={"curve": [0.0, 1.0, 0.8, "talon curvature"], "grip": [0.0, 1.0, 0.0, "0 = open, 1 = closed"]}),
    dict(id="claws", category="manipulation", kind="tip", symmetry="pair",
         desc="Curved toe claws: sheathed and extendable in cats, fixed and blunt in dogs.",
         sources=["feline.claws_L", "canine.claws_L"],
         shape={"curve": [0.0, 1.0, 0.6, "claw curvature"], "extend": [0.0, 1.0, 0.0, "0 = sheathed, 1 = out"]}),
    dict(id="tail_segmented", category="manipulation", kind="limb", symmetry="centre",
         desc="Chain of hinged ring segments that arches up over the back to aim a stinger.",
         sources=["scorpion.metasoma"],
         shape={"segments": [3, 8, 5, "ring segments"], "arch": [0.0, 1.0, 0.8, "curl over the back"]}),
    dict(id="stinger", category="manipulation", kind="tip", symmetry="centre",
         desc="Bulbous venom vesicle ending in a curved sharp barb, on the tail tip.",
         sources=["scorpion.telson_stinger"],
         shape={"bulb": [0.3, 2.0, 1.0, "vesicle swelling"], "hook": [0.0, 1.0, 0.7, "barb curvature"]}),
    # ---------------- aesthetics ----------------
    dict(id="carapace", category="aesthetics", kind="surface", symmetry="centre",
         desc="Hard dorsal shield: broad toothed crab carapace or beetle pronotum.",
         sources=["crab.carapace", "beetle.pronotum"],
         shape={"rim_teeth": [0, 9, 5, "teeth along the front edge"], "dome": [0.1, 1.0, 0.4, "height relative to width"]}),
    dict(id="crest_dorsal", category="aesthetics", kind="surface", symmetry="centre",
         desc="Row of tall pointed scales from the nape along the back, largest over the neck.",
         sources=["lizard.dorsal_crest"],
         shape={"spines": [4, 60, 30, "spines"], "falloff": [0.0, 1.0, 0.7, "shrink toward the tail"]}),
    dict(id="dewlap", category="aesthetics", kind="surface", symmetry="centre",
         desc="Hanging throat fold that extends for display.",
         sources=["lizard.dewlap"],
         shape={"depth": [0.2, 2.0, 1.0, "hang below the jaw"], "extend_deg": [0, 60, 0, "display extension"]}),
    dict(id="vocal_sac", category="aesthetics", kind="surface", symmetry="centre",
         desc="Throat sac that inflates when calling.",
         sources=["frog.vocal_sac"],
         shape={"inflate": [0.0, 1.0, 0.0, "0 = flat, 1 = full"]}),
    dict(id="supraorbital_ridge", category="aesthetics", kind="surface", symmetry="centre",
         desc="Bony ridge over the eyes: heavy ape brow torus, hawk supraorbital shelf.",
         sources=["primate.supraorbital_torus", "raptor.supraorbital_shelf_L"],
         shape={"overhang": [0.0, 1.0, 0.5, "how far it shades the eye"], "split": [0, 1, 0, "one shelf per eye instead of a single bar"]}),
]

RECATEGORISED = {
    "canine.claws_L": "locomotion -> manipulation (grouped with the cat claws; used for gripping and digging)",
    "raptor.supraorbital_shelf_L": "sensory -> aesthetics (bony shelf; shades the eye but is not a sense organ)",
    "frog.vocal_sac": "sensory -> aesthetics (calling display; produces sound, does not sense it)",
}

EXCLUDED = {
    "beetle.head": "core segment; part of the body shape",
    "crab.abdomen": "folded flat under the body; not visible from normal angles",
    "feline.fur_coat": "surface finish; texture, not geometry",
    "lizard.body_scales": "surface finish; texture or normal map",
    "jellyfish.gonads": "visible through the bell as four rings; texture",
    "jellyfish.radial_canals": "internal; texture at most",
    "shark.ampullae_of_lorenzini_L": "pores; texture detail",
    "shark.lateral_line_L": "line of pores; texture detail",
    "shark.claspers_L": "male-only reproductive organ; outside the five categories",
    "worm.prostomium": "body tip; part of the body shape",
    "worm.mouth": "opening under the prostomium; no geometry",
    "worm.anus_pygidium": "opening at the rear tip; no geometry",
    "worm.photoreceptor_cells": "cells in the skin; no visible structure",
    "worm.setae_L": "bristles under 1 mm; texture detail",
}


def load_species():
    out = {}
    for path in sorted(glob.glob(os.path.join(HERE, "species", "*.json"))):
        d = json.load(open(path))
        L = d["physical_parsing"]["bounding_box_m"]["length_z"]
        for p in d["parts"]:
            out["%s.%s" % (d["species_id"], p["id"])] = (d, p, L)
    return out


def rnd(v, k=3):
    return round(v, k) if isinstance(v, float) else v


def stats(vals):
    vals = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not vals:
        return None
    return {"min": rnd(min(vals)), "median": rnd(float(st.median(vals))), "max": rnd(max(vals))}


def measured_range(vals, integer=False):
    """Allowed range from observations: observed span widened by STYLE_TOLERANCE, default = median."""
    s = stats(vals)
    if s is None:
        return None
    lo, hi = s["min"] * (1 - STYLE_TOLERANCE), s["max"] * (1 + STYLE_TOLERANCE)
    if integer:
        return {"min": max(1, int(lo)), "max": int(round(hi)), "default": int(round(s["median"])), "observed": s}
    return {"min": rnd(lo), "max": rnd(hi), "default": s["median"], "observed": s}


def joint_chain(srcs):
    """Merge joint lists index by index: most common type, axes seen, union of ranges."""
    longest = max(len(p.get("joints") or []) for _, p, _ in srcs)
    chain = []
    for i in range(longest):
        js = [p["joints"][i] for _, p, _ in srcs if len(p.get("joints") or []) > i]
        types = [j.get("type") for j in js]
        rngs = [j["range_deg"] for j in js if isinstance(j.get("range_deg"), list) and len(j["range_deg"]) == 2]
        chain.append({"name": js[0].get("name"), "type": max(set(types), key=types.count),
                      "pivot_axes": sorted({a for j in js for a in (j.get("pivot_axes") or [])}),
                      "range_deg": [min(r[0] for r in rngs), max(r[1] for r in rngs)] if rngs else None,
                      "observed_in": len(js)})
    return chain


def main():
    data = load_species()
    used, entries = set(), []
    for e in LIB:
        srcs = []
        for s in e["sources"]:
            if s not in data:
                raise SystemExit("unknown research part %s in %s" % (s, e["id"]))
            srcs.append(data[s])
            used.add(s)
        pos = [p["attach_pos"] for _, p, _ in srcs if p.get("attach_pos")]
        mean = [rnd(sum(abs(q[0]) for q in pos) / len(pos)), rnd(sum(q[1] for q in pos) / len(pos)),
                rnd(sum(q[2] for q in pos) / len(pos))] if pos else None
        pen = [p["penetration"] for _, p, _ in srcs]
        measured = {"length": measured_range([p["length_m"] / L for _, p, L in srcs if p.get("length_m")]),
                    "root_radius": measured_range([p["root_radius_m"] / L for _, p, L in srcs if p.get("root_radius_m")])}
        counts = [p.get("count") for _, p, _ in srcs if isinstance(p.get("count"), int) and p.get("count") > 2]
        if counts:
            measured["count"] = measured_range(counts, integer=True)
        frac = stats([q.get("fraction_of_root_radius") for q in pen])
        entry = {
            "id": e["id"], "category": e["category"], "kind": e["kind"], "symmetry": e["symmetry"],
            "attach_to": e.get("on", {"tip": "limb_end", "core": "body_plan"}.get(e["kind"], "body")),
            "description": e["desc"],
            "params": {
                "measured": {k: v for k, v in measured.items() if v},
                "shape": {k: {"min": v[0], "max": v[1], "default": v[2], "meaning": v[3]} for k, v in e["shape"].items()},
            },
            "size_m": {"length": stats([p.get("length_m") for _, p, _ in srcs]),
                       "root_radius": stats([p.get("root_radius_m") for _, p, _ in srcs])},
            "attach_pos_normalized": mean,
            "joints": joint_chain(srcs),
            "penetration": {"default_fraction_of_root_radius": frac["median"] if frac else None,
                            "fraction_of_root_radius": frac,
                            "depth_m": stats([q.get("depth_m") for q in pen]),
                            "overlap_regions": [q.get("overlap_region") for q in pen if q.get("overlap_region")][:2]},
            "species": sorted({d["species_id"] for d, _, _ in srcs}),
            "sources": e["sources"],
        }
        notes = [RECATEGORISED[s] for s in e["sources"] if s in RECATEGORISED]
        if notes:
            entry["category_notes"] = notes
        entries.append(entry)
    unmapped = sorted(set(data) - used - set(EXCLUDED))
    if unmapped:
        raise SystemExit("research parts with no library entry or exclusion: %s" % ", ".join(unmapped))
    by_cat = {c: [x["id"] for x in entries if x["category"] == c] for c in CATEGORIES}
    lib = {
        "format": "part_library_spec", "version": 2,
        "derived_from": "research/species/*.json (13 species)",
        "frame": {"normalized_box": "x and z in [-0.5, 0.5], y in [0, 1]; +Y up, +Z forward; ground at y = 0",
                  "attach_pos_normalized": "mean over the source parts; pairs are recorded once, on the +X side",
                  "symmetry": "pair = one entry, mirrored to -X when built; centre = on the midline; radial = repeated around the vertical axis",
                  "params.measured": "length and root_radius are fractions of the body length; min/max are the observed span widened by %d%%" % (STYLE_TOLERANCE * 100),
                  "params.shape": "variations the research describes; curated, not measured",
                  "penetration": "how far the root sinks into the core mesh, as a fraction of the root radius"},
        "kinds": {"limb": "joint chain grown from the body", "tip": "sits on a limb's end joint",
                  "surface": "placed on the body or a limb surface", "core": "body plan the body itself must form"},
        "categories": by_cat, "parts": entries,
        "excluded": [{"source": k, "reason": v} for k, v in sorted(EXCLUDED.items())],
    }
    with open(os.path.join(HERE, "part_library.json"), "w") as f:
        json.dump(lib, f, indent=2)
        f.write("\n")
    print("%d library parts from %d research parts (%d excluded)" % (len(entries), len(used), len(EXCLUDED)))
    for c in CATEGORIES:
        print("  %-12s %2d  %s" % (c, len(by_cat[c]), ", ".join(by_cat[c])))


if __name__ == "__main__":
    main()
