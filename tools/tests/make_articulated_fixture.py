"""Build an opt-in comparison with rigid, overlapping joints on one limb pair.

From the checkout root:
    blender -b --python-exit-code 1 -P tools/tests/make_articulated_fixture.py -- \
        examples/minotaur.json arm out/articulated-minotaur
"""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from polyforge import baker, builder, export, kit, recipe, runtime_motion


class ArticulatedBuilder(builder.Builder):
    def __init__(self, source, selection):
        super().__init__(source, "final")
        self.selection = selection
        if not any(limb["uid"] == selection for limb in self.recipe["limbs"]):
            raise ValueError(f"unknown limb instance {selection}")

    def limb_prim(self, limb):
        if limb["uid"] != self.selection:
            return super().limb_prim(limb)
        joints, radii, bones = limb["joints"], limb["radii"], limb["bones"]
        for i, (start, end) in enumerate(zip(joints, joints[1:])):
            radius, next_radius = radii[i:i + 2]
            delta = end - start
            piece = kit.Piece()
            # Keep the hinge concentric with its two overlapping surfaces.
            # The round mount belongs to the proximal section.
            mount = kit.Piece()
            mount.oval(start, Vector((radius, radius, radius)) * .91, segs=28, rings=16)
            verts, faces = mount.cage()
            self.details.append((verts, faces, self.parents[bones[i]]))
            piece.loft([start - delta * .07, start, start + delta * .37, start + delta * .70,
                        start + delta * .90, end + delta * .06],
                       [.76 * radius, radius, 1.08 * (radius + next_radius) / 2,
                        .55 * radius + .45 * next_radius, .17 * radius + .83 * next_radius,
                        .93 * next_radius], sides=30, density=8)
            verts, faces = piece.cage()
            self.details.append((verts, faces, bones[i]))

    def place_tips(self):
        limbs = self.limbs
        try:
            for limb in limbs:
                self.limbs = [limb]
                start = len(self.skin_prims)
                super().place_tips()
                if limb["uid"] == self.selection:
                    for verts, faces in self.skin_prims[start:]:
                        self.details.append((verts, faces, limb["bones"][-1]))
                    del self.skin_prims[start:]
        finally:
            self.limbs = limbs

    def skin_weights(self, skin):
        limbs = self.limbs
        try:
            self.limbs = [limb for limb in limbs if limb["uid"] != self.selection]
            super().skin_weights(skin)
        finally:
            self.limbs = limbs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("limb", help="recipe limb UID")
    parser.add_argument("out", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = ArticulatedBuilder(recipe.load(args.recipe), args.limb).build()
    name = args.recipe.stem
    export.export(result, str(args.out / f"{name}.glb"), animated=False)
    runtime_motion.save(result["rig"], args.out / f"{name}.motion.json")
    baker.bake_all(result["armature"], clips=["walk", "run", "wave"])
    export.export(result, str(args.out / f"{name}-motion.glb"))


if __name__ == "__main__":
    main()
