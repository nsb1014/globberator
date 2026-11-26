"""Build the research-derived part library spec (research/part_library.json).

    python3 research/build_library.py

Each library entry below lists the species parts it was derived from
("species.part_id"). Sizes, joint chains, attach positions and penetration
depths are computed from those research files; names, parameters and
category corrections are curated here. Nothing in this file builds geometry.
"""
import glob
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ["locomotion", "sensory", "feeding", "manipulation", "aesthetics"]

# kind: "limb" = joint chain grown from the body (PolyForge limb), "tip" = sits on a limb's end joint,
# "surface" = placed on the body or a limb surface, "core" = a body plan the spine itself must produce.
# polyforge: closest existing PolyForge part/limb setup, or None when the library has nothing usable.
LIB = [
    # ---------------- locomotion ----------------
    dict(id="leg_arthropod", category="locomotion", kind="limb", symmetry="pair",
         desc="Thin jointed walking leg with a coxa ball joint and hinge knees; sprawls out, then down.",
         sources=["beetle.foreleg_L", "beetle.midleg_L", "beetle.hindleg_L", "crab.walking_leg_L", "scorpion.walking_legs_L"],
         polyforge="limb (3-4 segments) + foot_spike",
         params={"segments": [3, 5, 4], "length": [0.6, 1.6, 1.0], "thickness": [0.4, 1.5, 0.8], "sprawl_deg": [20, 80, 55]}),
    dict(id="leg_digitigrade", category="locomotion", kind="limb", symmetry="pair",
         desc="Mammal leg standing on its toes: shoulder/hip ball, elbow/knee hinge, raised wrist/hock hinge.",
         sources=["canine.legs_fore_L", "canine.legs_hind_L", "feline.forelimb_L", "feline.hindlimb_L"],
         polyforge="limb (3 segments, reversed hock on hind legs) + foot_paw",
         params={"length": [0.6, 1.6, 1.0], "thickness": [0.5, 1.8, 1.0], "hock_lift": [0.0, 1.0, 0.6]}),
    dict(id="leg_plantigrade", category="locomotion", kind="limb", symmetry="pair",
         desc="Upright ape leg ending flat on the sole.",
         sources=["primate.leg_L"], polyforge="limb (2-3 segments)",
         params={"length": [0.6, 1.6, 1.0], "thickness": [0.5, 1.8, 1.0]}),
    dict(id="leg_sprawling", category="locomotion", kind="limb", symmetry="pair",
         desc="Reptile leg that leaves the body sideways and bends down at the elbow/knee.",
         sources=["lizard.leg_fore_L", "lizard.leg_hind_L"], polyforge="limb (2-3 segments) + foot_claw",
         params={"length": [0.6, 1.6, 1.0], "thickness": [0.5, 1.8, 1.0], "sprawl_deg": [30, 90, 70]}),
    dict(id="leg_jumping", category="locomotion", kind="limb", symmetry="pair",
         desc="Long folded hind leg (thigh, shank, long ankle) that rests in a Z and extends to jump.",
         sources=["frog.hind_leg_L"], polyforge="limb (3 segments, folded) + foot_webbed",
         params={"length": [0.6, 1.8, 1.0], "thickness": [0.5, 1.8, 1.0], "fold": [0.0, 1.0, 0.8]}),
    dict(id="leg_bird", category="locomotion", kind="limb", symmetry="pair",
         desc="Bird leg: short feathered thigh, long bare tarsus, reversed ankle.",
         sources=["raptor.leg_L"], polyforge="limb (3 segments) + foot_claw",
         params={"length": [0.6, 1.6, 1.0], "thickness": [0.5, 1.8, 1.0], "feathered": [0.0, 1.0, 0.7]}),
    dict(id="foot_paw", category="locomotion", kind="tip", symmetry="pair",
         desc="Padded paw with toe pads; claws optional.",
         sources=["canine.paws_fore_L", "canine.paws_hind_L", "feline.paw_pads_L"],
         polyforge="foot_paw", params={"size": [0.4, 3.0, 1.0], "toes": [0.0, 1.5, 1.0], "claws": [0.0, 1.5, 0.5]}),
    dict(id="foot_webbed", category="locomotion", kind="tip", symmetry="pair",
         desc="Long-toed foot with webbing between the toes.",
         sources=["frog.hind_foot_webbed_L"], polyforge="foot_webbed",
         params={"size": [0.4, 3.0, 1.0], "length": [0.5, 2.0, 1.0], "web": [0.0, 1.0, 0.8]}),
    dict(id="foot_grasping", category="locomotion", kind="tip", symmetry="pair",
         desc="Ape foot with an opposable big toe; walks flat, can grip.",
         sources=["primate.foot_L"], polyforge=None,
         params={"size": [0.4, 3.0, 1.0], "toe_spread": [0.0, 1.0, 0.5], "curl": [0.0, 1.0, 0.3]}),
    dict(id="wing_feather", category="locomotion", kind="surface", symmetry="pair",
         desc="Broad feathered wing with slotted primaries.",
         sources=["raptor.wing_L"], polyforge="wing_feather",
         params={"span": [0.4, 4.0, 1.0], "chord": [0.4, 2.5, 1.0], "slots": [0.0, 1.0, 0.6], "fold": [0.0, 1.0, 1.0]}),
    dict(id="elytron", category="locomotion", kind="surface", symmetry="pair",
         desc="Hard domed wing case covering the abdomen; hinges up and out before flight.",
         sources=["beetle.elytron_L"], polyforge=None,
         params={"length": [0.4, 2.0, 1.0], "dome": [0.2, 1.5, 0.8], "open_deg": [0, 60, 0]}),
    dict(id="wing_membrane_insect", category="locomotion", kind="surface", symmetry="pair",
         desc="Thin veined flight wing that folds under the elytron.",
         sources=["beetle.hindwing_L"], polyforge=None,
         params={"span": [0.4, 3.0, 1.0], "chord": [0.4, 2.0, 1.0], "fold": [0.0, 1.0, 1.0]}),
    dict(id="fin_paired", category="locomotion", kind="surface", symmetry="pair",
         desc="Swept lateral fin on the lower flank (pectoral, pelvic).",
         sources=["shark.pectoral_fin_L", "shark.pelvic_fin_L"], polyforge=None,
         params={"span": [0.3, 3.0, 1.0], "chord": [0.3, 2.5, 1.0], "sweep": [-1.0, 1.0, 0.5], "droop_deg": [0, 45, 20]}),
    dict(id="fin_median", category="locomotion", kind="surface", symmetry="centre",
         desc="Upright fin on the midline (dorsal, anal).",
         sources=["shark.dorsal_fin_1", "shark.dorsal_fin_2", "shark.anal_fin"], polyforge="fin_dorsal",
         params={"height": [0.3, 3.0, 1.0], "length": [0.3, 3.0, 1.0], "sweep": [-1.0, 1.0, 0.6]}),
    dict(id="tail_fin_heterocercal", category="locomotion", kind="tip", symmetry="centre",
         desc="Crescent tail fin with a longer upper lobe, on the end of the tail.",
         sources=["shark.caudal_fin"], polyforge=None,
         params={"size": [0.3, 3.0, 1.0], "upper_lobe": [0.5, 2.0, 1.4], "fork": [0.0, 1.0, 0.6]}),
    dict(id="tail_fan", category="locomotion", kind="surface", symmetry="centre",
         desc="Fan of tail feathers used for steering.",
         sources=["raptor.tail_fan"], polyforge="tail_fan",
         params={"size": [0.3, 3.0, 1.0], "spread": [0.3, 1.5, 0.8], "lift": [-1.0, 1.0, 0.3]}),
    dict(id="tail_flexible", category="locomotion", kind="limb", symmetry="centre",
         desc="Tapering flexible tail of many vertebrae (balance, steering).",
         sources=["canine.tail", "feline.tail", "lizard.tail"], polyforge="limb motion=tail (+ tail_tuft for a brush)",
         params={"length": [0.3, 2.5, 1.0], "thickness": [0.4, 2.0, 1.0], "taper": [0.1, 1.0, 0.6], "brush": [0.0, 1.5, 0.0]}),
    dict(id="siphon", category="locomotion", kind="surface", symmetry="centre",
         desc="Short muscular jet funnel beside the head; aims water for jet propulsion.",
         sources=["octopus.funnel"], polyforge=None,
         params={"length": [0.4, 2.5, 1.0], "radius": [0.4, 2.0, 1.0], "aim_deg": [0, 90, 30]}),
    dict(id="web_interbrachial", category="locomotion", kind="surface", symmetry="radial",
         desc="Skin web spanning the bases of the arms; spreads like an umbrella.",
         sources=["octopus.web"], polyforge=None,
         params={"depth": [0.1, 1.0, 0.3], "scallop": [0.0, 1.0, 0.5]}),
    dict(id="bell_radial", category="locomotion", kind="core", symmetry="radial",
         desc="Radially symmetric swimming bell (dome with a scalloped rim) that pulses to swim.",
         sources=["jellyfish.coronal_muscle_bell"], polyforge=None,
         params={"diameter": [0.4, 3.0, 1.0], "dome": [0.2, 1.5, 0.45], "lobes": [4, 16, 8], "rim_thickness": [0.2, 1.5, 0.5]}),
    # ---------------- sensory ----------------
    dict(id="eye_round", category="sensory", kind="surface", symmetry="pair",
         desc="Camera eye with a round pupil under lids.",
         sources=["frog.eye_L", "octopus.eye_L", "primate.eye_L", "raptor.eye_L", "shark.eye_L", "lizard.eye_L"],
         polyforge="eye_round", params={"size": [0.4, 3.0, 1.0], "pupil": [0.3, 0.9, 0.55], "lid": [0.0, 1.0, 0.3], "bulge": [0.0, 1.0, 0.3]}),
    dict(id="eye_slit", category="sensory", kind="surface", symmetry="pair",
         desc="Eye with a vertical slit pupil (cats, foxes).",
         sources=["feline.eye_L", "canine.eyes_L"], polyforge="eye_slit",
         params={"size": [0.4, 3.0, 1.0], "slit": [0.1, 0.6, 0.25], "lid": [0.0, 1.0, 0.4]}),
    dict(id="eye_compound", category="sensory", kind="surface", symmetry="pair",
         desc="Bulging faceted compound eye on the head side.",
         sources=["beetle.eye_L"], polyforge="eye_bug", params={"size": [0.4, 3.0, 1.0], "bulge": [0.4, 1.2, 0.8]}),
    dict(id="eye_simple", category="sensory", kind="surface", symmetry="any",
         desc="Small bead eye or light-sensing spot (ocelli, rhopalia, parietal eye).",
         sources=["scorpion.eyes_median", "scorpion.eyes_lateral", "jellyfish.rhopalia", "lizard.parietal_eye"],
         polyforge="eye_bead", params={"size": [0.2, 2.0, 1.0], "count": [1, 8, 2]}),
    dict(id="eye_stalk", category="sensory", kind="surface", symmetry="pair",
         desc="Eye on a movable stalk that folds into a socket.",
         sources=["crab.eye_stalk_L"], polyforge="eye_stalk",
         params={"size": [0.4, 3.0, 1.0], "height": [0.1, 0.8, 0.3], "lean": [-0.6, 0.6, 0.2]}),
    dict(id="antenna_segmented", category="sensory", kind="surface", symmetry="pair",
         desc="Jointed feeler; elbowed or with a lamellate club (beetles), or a long whip (crabs).",
         sources=["beetle.antenna_L", "crab.antennule_L", "crab.antenna_L"], polyforge="antenna (no elbow or club)",
         params={"length": [0.3, 3.0, 1.0], "elbow": [0.0, 1.0, 0.5], "club": [0.0, 2.0, 0.6], "curve": [-1.0, 1.0, -0.3]}),
    dict(id="ear_pinna", category="sensory", kind="surface", symmetry="pair",
         desc="External ear flap: pointed (fox, cat) or round (ape).",
         sources=["canine.ears_L", "feline.ear_L", "primate.ear_L"], polyforge="ear_leaf",
         params={"size": [0.4, 3.0, 1.0], "point": [0.0, 1.0, 0.7], "cup": [0.0, 1.0, 0.6], "droop": [0.0, 1.0, 0.0]}),
    dict(id="tympanum", category="sensory", kind="surface", symmetry="pair",
         desc="Flush round eardrum disc with a raised rim behind the eye (frogs, lizards).",
         sources=["frog.tympanum_L", "lizard.ear_opening_L"], polyforge=None,
         params={"size": [0.3, 3.0, 1.0], "rim": [0.0, 1.0, 0.4], "recess": [0.0, 1.0, 0.2]}),
    dict(id="nose_pad", category="sensory", kind="surface", symmetry="centre",
         desc="Moist nose pad (rhinarium) or ape nose with nostrils.",
         sources=["canine.nose", "feline.nose", "primate.nose"], polyforge="nose_button",
         params={"size": [0.4, 3.0, 1.0], "nostrils": [0.0, 1.5, 1.0]}),
    dict(id="nostril_slit", category="sensory", kind="surface", symmetry="pair",
         desc="Small slit nostril on the underside of the snout (fish).",
         sources=["shark.nostril_L"], polyforge=None, params={"size": [0.3, 2.0, 1.0], "flap": [0.0, 1.0, 0.5]}),
    dict(id="whiskers", category="sensory", kind="surface", symmetry="pair",
         desc="Fan of long vibrissae from a whisker pad on the muzzle.",
         sources=["canine.vibrissae_L", "feline.whiskers_L"], polyforge=None,
         params={"length": [0.3, 3.0, 1.0], "count": [3, 12, 6], "spread_deg": [10, 60, 35], "droop": [-1.0, 1.0, 0.2]}),
    dict(id="pectines", category="sensory", kind="surface", symmetry="pair",
         desc="Comb-shaped ground-sensing organs under the body.",
         sources=["scorpion.pectines_L"], polyforge=None,
         params={"length": [0.4, 2.5, 1.0], "teeth": [6, 30, 16], "splay_deg": [0, 45, 20]}),
    # ---------------- feeding ----------------
    dict(id="jaws_toothed", category="feeding", kind="surface", symmetry="centre",
         desc="Upper jaw plus a hinged lower jaw with teeth.",
         sources=["canine.jaws", "feline.jaws", "lizard.jaws", "primate.mouth_jaws", "shark.upper_jaw", "shark.lower_jaw"],
         polyforge="mouth_jaws", params={"length": [0.4, 2.5, 1.0], "width": [0.5, 2.0, 1.0], "teeth": [0.0, 1.5, 1.0], "gape_deg": [0, 60, 35]}),
    dict(id="muzzle", category="feeding", kind="surface", symmetry="centre",
         desc="Projecting mammal muzzle carrying the nose pad and jaws.",
         sources=["canine.head_muzzle"], polyforge="mouth_snout",
         params={"length": [0.3, 2.5, 1.0], "width": [0.5, 2.2, 1.0], "taper": [0.0, 1.0, 0.6]}),
    dict(id="mouth_wide", category="feeding", kind="surface", symmetry="centre",
         desc="Very wide lipless gape spanning the head (frogs).",
         sources=["frog.mouth"], polyforge="mouth_smile",
         params={"width": [0.4, 3.0, 1.0], "curve": [-1.0, 1.0, 0.2], "gape_deg": [0, 45, 30]}),
    dict(id="beak_hooked", category="feeding", kind="surface", symmetry="centre",
         desc="Hooked tearing beak (raptors) or parrot-like beak hidden among arms (octopus).",
         sources=["raptor.beak", "octopus.beak"], polyforge="mouth_beak",
         params={"length": [0.3, 3.0, 1.0], "width": [0.5, 2.0, 1.0], "hook": [0.0, 1.0, 0.8]}),
    dict(id="mandibles", category="feeding", kind="surface", symmetry="pair",
         desc="Pincer-like jaws that close sideways; from small chelicerae to huge stag-beetle antlers.",
         sources=["beetle.mandible_L", "scorpion.chelicera_L"], polyforge="mouth_mandibles (range too short for stag beetles)",
         params={"length": [0.4, 4.0, 1.0], "curl": [0.0, 1.5, 0.7], "tines": [0, 3, 1], "spread": [0.5, 2.0, 1.0]}),
    dict(id="mouth_palps", category="feeding", kind="surface", symmetry="pair",
         desc="Short jointed mouth feelers / mouth plates that handle food.",
         sources=["beetle.palp_L", "crab.maxilliped_3"], polyforge=None,
         params={"length": [0.3, 2.0, 1.0], "segments": [2, 4, 3]}),
    dict(id="tongue", category="feeding", kind="surface", symmetry="centre",
         desc="Projectile sticky tongue (frog) or flicking tongue (lizard), kept inside the mouth at rest.",
         sources=["frog.tongue", "lizard.tongue"], polyforge=None,
         params={"length": [0.3, 3.0, 1.0], "fork": [0.0, 1.0, 0.0], "tip_pad": [0.0, 1.0, 0.5], "extend": [0.0, 1.0, 0.0]}),
    dict(id="oral_arms", category="feeding", kind="surface", symmetry="radial",
         desc="Frilled arms hanging from the central mouth under a bell.",
         sources=["jellyfish.oral_arms", "jellyfish.manubrium_mouth"], polyforge=None,
         params={"count": [2, 8, 4], "length": [0.3, 3.0, 1.0], "frill": [0.0, 1.0, 0.6]}),
    dict(id="tentacle_fringe", category="feeding", kind="surface", symmetry="radial",
         desc="Ring of many fine tentacles around a bell margin.",
         sources=["jellyfish.marginal_tentacles"], polyforge=None,
         params={"count": [8, 128, 64], "length": [0.1, 3.0, 0.5], "sway": [0.0, 1.0, 0.5]}),
    dict(id="gill_slits", category="feeding", kind="surface", symmetry="pair",
         desc="Row of vertical slits behind the head (water leaving the mouth).",
         sources=["shark.gill_slits_L"], polyforge=None,
         params={"count": [3, 7, 5], "height": [0.3, 2.0, 1.0], "spacing": [0.5, 2.0, 1.0]}),
    # ---------------- manipulation ----------------
    dict(id="pincer_limb", category="manipulation", kind="limb", symmetry="pair",
         desc="Jointed arm ending in a chela (fixed finger + hinged finger).",
         sources=["crab.cheliped_L", "scorpion.pedipalp_L"], polyforge="limb (3 segments) + hand_pincer",
         params={"length": [0.5, 2.0, 1.0], "claw_bulk": [0.5, 2.5, 1.2], "asymmetry": [0.0, 1.0, 0.0]}),
    dict(id="arm_grasping", category="manipulation", kind="limb", symmetry="pair",
         desc="Shoulder ball + elbow + wrist arm ending in a hand (ape arm; frog forelimb).",
         sources=["primate.arm_L", "primate.hand_L", "frog.fore_leg_L"], polyforge="limb (3 segments) + hand_basic",
         params={"length": [0.4, 2.0, 1.0], "thickness": [0.5, 1.8, 1.0], "knuckle_walk": [0.0, 1.0, 0.0]}),
    dict(id="arm_hydrostatic", category="manipulation", kind="limb", symmetry="pair",
         desc="Boneless arm that bends anywhere along its length; tapers to a fine tip.",
         sources=["octopus.arm_L1", "octopus.arm_L2", "octopus.arm_L3", "octopus.arm_L4"],
         polyforge="limb motion=tail + hand_tentacle (bends only at segment joints)",
         params={"length": [0.3, 3.0, 1.0], "thickness": [0.3, 2.0, 1.0], "curl": [0.0, 1.5, 0.8], "suckers": [0.0, 1.0, 1.0]}),
    dict(id="suckers", category="manipulation", kind="surface", symmetry="pair",
         desc="Two rows of cupped suction discs along the underside of an arm, shrinking toward the tip.",
         sources=["octopus.arm_L1"], polyforge=None, on="limb",
         params={"count": [4, 40, 16], "size": [0.3, 2.0, 1.0], "rows": [1, 2, 2]}),
    dict(id="talons", category="manipulation", kind="tip", symmetry="pair",
         desc="Grasping foot with long curved talons (three forward, one back).",
         sources=["raptor.talon_L"], polyforge="foot_claw",
         params={"size": [0.4, 3.0, 1.0], "talons": [0.0, 2.0, 1.4], "grip": [0.0, 1.0, 0.0]}),
    dict(id="claws", category="manipulation", kind="tip", symmetry="pair",
         desc="Curved toe claws: sheathed and extendable in cats, fixed and blunt in dogs.",
         sources=["feline.claws_L", "canine.claws_L"], polyforge="foot_paw (claws not separate)",
         params={"length": [0.2, 2.0, 1.0], "curve": [0.0, 1.0, 0.6], "extend": [0.0, 1.0, 0.0]}),
    dict(id="tail_segmented", category="manipulation", kind="limb", symmetry="centre",
         desc="Chain of five hinged ring segments that arches up over the back to aim a stinger.",
         sources=["scorpion.metasoma"], polyforge="limb motion=tail (no ring segments)",
         params={"segments": [3, 8, 5], "length": [0.4, 2.0, 1.0], "arch": [0.0, 1.0, 0.8], "taper": [0.0, 1.0, 0.3]}),
    dict(id="stinger", category="manipulation", kind="tip", symmetry="centre",
         desc="Bulbous venom vesicle ending in a curved barb, on the tail tip.",
         sources=["scorpion.telson_stinger"], polyforge="spike (no bulb)",
         params={"size": [0.4, 3.0, 1.0], "bulb": [0.3, 2.0, 1.0], "hook": [0.0, 1.0, 0.7]}),
    # ---------------- aesthetics ----------------
    dict(id="carapace", category="aesthetics", kind="surface", symmetry="centre",
         desc="Hard dorsal shield over the body: broad crab carapace or beetle pronotum.",
         sources=["crab.carapace", "beetle.pronotum"], polyforge="shell",
         params={"width": [0.4, 3.0, 1.0], "length": [0.4, 3.0, 1.0], "height": [0.2, 2.0, 0.6], "rim_teeth": [0, 9, 5]}),
    dict(id="crest_dorsal", category="aesthetics", kind="surface", symmetry="centre",
         desc="Row of tall spines along the neck and back.",
         sources=["lizard.dorsal_crest"], polyforge="crest",
         params={"height": [0.3, 3.0, 1.0], "length": [0.3, 3.0, 1.0], "spines": [4, 30, 12]}),
    dict(id="dewlap", category="aesthetics", kind="surface", symmetry="centre",
         desc="Hanging throat fan that can be extended for display.",
         sources=["lizard.dewlap"], polyforge=None,
         params={"size": [0.3, 3.0, 1.0], "depth": [0.2, 2.0, 1.0], "extend_deg": [0, 60, 0]}),
    dict(id="vocal_sac", category="aesthetics", kind="surface", symmetry="centre",
         desc="Inflatable throat sac used for calling (display/communication).",
         sources=["frog.vocal_sac"], polyforge="bulge",
         params={"size": [0.3, 3.0, 1.0], "inflate": [0.0, 1.0, 0.0]}),
    dict(id="brow_ridge", category="aesthetics", kind="surface", symmetry="centre",
         desc="Bony ridge over the eyes (ape brow, raptor supraorbital shelf).",
         sources=["primate.brow_ridge", "raptor.brow_ridge_L"], polyforge="brow_ridge",
         params={"size": [0.4, 3.0, 1.0], "depth": [0.4, 2.0, 1.0], "frown": [-1.0, 1.0, 0.4]}),
]

# Recategorisations: the library category differs from the one the research file used.
RECATEGORISED = {
    "canine.claws_L": "locomotion -> manipulation (grouped with the cat claws; used for gripping and digging)",
    "raptor.brow_ridge_L": "sensory -> aesthetics (bony shelf; shades the eye but is not a sense organ)",
    "frog.vocal_sac": "sensory -> aesthetics (calling display; produces sound, does not sense it)",
    "crab.carapace": "kept aesthetics, but it is also the core armour the spine must shape",
}

# Research parts with no library entry, and why.
EXCLUDED = {
    "beetle.head": "core segment; shaped by the spine's front vertebrae",
    "crab.abdomen": "tucked flat under the body; not visible from normal angles",
    "feline.fur_coat": "surface finish; paint pattern, not geometry",
    "lizard.body_scales": "surface finish; paint pattern or normal map",
    "jellyfish.gonads": "visible through the bell as four rings; paint pattern",
    "jellyfish.radial_canals": "internal; paint pattern at most",
    "shark.ampullae_of_lorenzini_L": "pores; paint/normal detail",
    "shark.lateral_line_L": "line of pores; paint detail",
    "shark.claspers_L": "male-only reproductive organ; not a manipulation part in the taxonomy's sense",
    "worm.prostomium": "body tip; shaped by the spine's front vertebra",
    "worm.mouth": "opening under the prostomium; no geometry",
    "worm.anus_pygidium": "opening at the rear tip; no geometry",
    "worm.photoreceptor_cells": "cells in the skin; no visible structure",
    "worm.setae_L": "bristles under 1 mm; normal-map detail",
}


def status_of(equivalent):
    """covered: an existing part or limb setup models it; partial: it exists but misses a named
    feature; new: nothing in PolyForge fits."""
    if not equivalent:
        return "new"
    caveat = equivalent.split("(", 1)[1] if "(" in equivalent else ""
    return "partial" if any(w in caveat for w in ("no ", "not ", "too ", "only ")) else "covered"


def load_species():
    out = {}
    for path in sorted(glob.glob(os.path.join(HERE, "species", "*.json"))):
        d = json.load(open(path))
        L = d["physical_parsing"]["bounding_box_m"]["length_z"]
        for p in d["parts"]:
            if "category" in p:
                out["%s.%s" % (d["species_id"], p["id"])] = (d, p, L)
    return out


def rnd(v, k=3):
    return round(v, k) if isinstance(v, float) else v


def stats(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    return {"min": rnd(min(vals)), "median": rnd(float(st.median(vals))), "max": rnd(max(vals))}


def joint_chain(srcs):
    """Merge joint lists index by index: most common type, union of ranges, axes seen."""
    longest = max(len(p.get("joints") or []) for _, p, _ in srcs)
    chain = []
    for i in range(longest):
        js = [p["joints"][i] for _, p, _ in srcs if len(p.get("joints") or []) > i]
        types = [j.get("type") for j in js]
        rngs = [j["range_deg"] for j in js if isinstance(j.get("range_deg"), list) and len(j["range_deg"]) == 2]
        axes = sorted({a for j in js for a in (j.get("pivot_axes") or [])})
        chain.append({"name": js[0].get("name"), "type": max(set(types), key=types.count), "pivot_axes": axes,
                      "range_deg": [min(r[0] for r in rngs), max(r[1] for r in rngs)] if rngs else None,
                      "observed_in": len(js)})
    return chain


def main():
    data = load_species()
    used = set()
    entries = []
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
        entry = {
            "id": e["id"], "category": e["category"], "kind": e["kind"], "symmetry": e["symmetry"],
            "attach_to": e.get("on", "body" if e["kind"] in ("surface", "limb") else ("limb_end" if e["kind"] == "tip" else "spine")),
            "description": e["desc"],
            "params": {k: {"min": v[0], "max": v[1], "default": v[2]} for k, v in e["params"].items()},
            "size": {"length_vs_body_length": stats([p.get("length_m", 0) / L for _, p, L in srcs if p.get("length_m")]),
                     "root_radius_m": stats([p.get("root_radius_m") for _, p, _ in srcs]),
                     "length_m": stats([p.get("length_m") for _, p, _ in srcs])},
            "attach_pos_normalized": mean,
            "joints": joint_chain(srcs),
            "penetration": {"fraction_of_root_radius": stats([q.get("fraction_of_root_radius") for q in pen]),
                            "depth_m": stats([q.get("depth_m") for q in pen]),
                            "overlap_regions": [q.get("overlap_region") for q in pen if q.get("overlap_region")][:2]},
            "species": sorted({d["species_id"] for d, _, _ in srcs}),
            "sources": e["sources"],
            "polyforge_equivalent": e["polyforge"],
            "status": status_of(e["polyforge"]),
        }
        notes = [RECATEGORISED[s] for s in e["sources"] if s in RECATEGORISED]
        if notes:
            entry["category_notes"] = notes
        entries.append(entry)
    unmapped = sorted(set(data) - used - set(EXCLUDED))
    if unmapped:
        raise SystemExit("research parts with no library entry or exclusion: %s" % ", ".join(unmapped))
    by_cat = {c: [x["id"] for x in entries if x["category"] == c] for c in CATEGORIES}
    status = {s: [x["id"] for x in entries if x["status"] == s] for s in ("covered", "partial", "new")}
    lib = {
        "format": "polyforge.part_library_spec", "version": 1,
        "derived_from": "research/species/*.json (13 species)",
        "frame": {"normalized_box": "x and z in [-0.5, 0.5], y in [0, 1]; +Y up, +Z forward; ground at y = 0",
                  "attach_pos_normalized": "mean over the source parts, with x mirrored to the +X side",
                  "penetration": "how far the part's root sinks into the core mesh, from the research overlap estimates"},
        "kinds": {"limb": "joint chain grown from the body", "tip": "sits on a limb's end joint",
                  "surface": "placed on the body or a limb surface", "core": "body plan the spine itself must produce"},
        "categories": by_cat, "status": status, "parts": entries,
        "excluded": [{"source": k, "reason": v} for k, v in sorted(EXCLUDED.items())],
    }
    with open(os.path.join(HERE, "part_library.json"), "w") as f:
        json.dump(lib, f, indent=2)
        f.write("\n")
    print("%d library parts from %d research parts (%d excluded)" % (len(entries), len(used), len(EXCLUDED)))
    for c in CATEGORIES:
        print("  %-12s %2d  %s" % (c, len(by_cat[c]), ", ".join(by_cat[c])))
    print("  status: " + ", ".join("%s %d" % (k, len(v)) for k, v in status.items()))


if __name__ == "__main__":
    main()
