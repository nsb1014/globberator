"""Blender integration checks for metaball geometry and asymmetric mounts."""

from pathlib import Path
import math
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from polyforge import builder, recipe
from polyforge.animator import Animator


def source():
    raw = recipe.default_recipe()
    raw["construction"] = "metaball"
    raw["limbs"] = [{"uid": "support", "u": .5, "theta": 180, "mirror": False,
                     "segments": [[-.17, -.25, .06], [-.08, -.29, -.06]],
                     "radii": [.13, .095, .064], "tip": "foot_hoof"}]
    raw["parts"] = [{"uid": "horn", "part": "horn_sweep", "u": .7,
                     "theta": 156, "mirror": False, "scale": .75}]
    return raw


def measure():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    raw = source()
    normalized, warnings = recipe.normalize(raw)
    assert not warnings, warnings
    assert recipe.normalize(normalized)[0] == normalized
    creature = builder.build(normalized, "preview")
    body, stats, rig = creature["skin"], creature["report"], creature["rig"]
    assert stats["skin_construction"] == "metaball"
    assert not stats["warnings"], stats["warnings"]
    assert stats["skin_topology"] == {"components": 1, "handles": 0, "nonmanifold_edges": 0}
    assert stats["triangles"] <= stats["triangle_budget"]
    assert [part["uid"] for part in rig["parts"]] == ["horn"]
    assert len(rig["limbs"]) == 1 and rig["limbs"][0]["side"] == -1.0
    assert len(rig["limbs"][0]["joint_support"]) == 1
    assert all(1 <= len(v.groups) <= 4 and abs(sum(g.weight for g in v.groups) - 1) < .001
               for v in body.data.vertices)
    assert not bpy.data.metaballs
    return sorted(tuple(round(c, 6) for c in v.co) for v in body.data.vertices)


if __name__ == "__main__":
    assert measure() == measure(), "Repeated implicit builds produce different vertex positions"
    raw = source()
    raw["limbs"][0]["bend_limits"] = [[15, 28]]
    result = builder.build(raw, "preview")
    anim = Animator(result["rig"])
    assert anim.play("walk")
    bones = result["rig"]["limbs"][0]["bones"]
    for _ in range(32):
        anim.step(1 / 30)
        a, b, c = [anim.G[bone].o for bone in bones]
        assert 14.999 <= math.degrees((b - a).angle(c - b)) <= 28.001
    print("Metaball body, budget, weights, asymmetric mounts, and deterministic rebuild passed")
