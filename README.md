# PolyForge

A Spore-style creature builder for Godot 4. Creatures are assembled from a library of sculpted parts on a bendable spine. They rig themselves, walk with procedural animation, and export to GLB. An AI loop builds a creature from a reference image within the library's style.

See [PLAN.md](PLAN.md) for the design and milestones.

## Layout

| Path | What it is |
| --- | --- |
| `blender/` | Part authoring in Blender (`bpy`): sculpt kit, the part definitions, and the library build script |
| `library/` | Built parts (`parts/*.glb` + `*.json`), `manifest.json`, `parts.blend` (every part, for browsing or hand edits), thumbnails |
| `core/` | Godot runtime: recipe, ops, spine, builder, animator, baker, render studio |
| `editor/` | The interactive creature editor (main scene) |
| `cli/main.gd` | Headless command line used by tests and the AI loop |
| `ai/` | Image-to-recipe loop (Claude + numeric fitting), scoring, benchmark |
| `examples/` | Example recipes (bull, minotaur, bird, beetle, spider, crab, dragon, serpent, hopper) |
| `tests/` | Godot test suite |

## How it fits together

1. **Parts are sculpted in Blender.** `python3 blender/build_library.py` (needs `pip install bpy scipy`) builds each part from smooth lofts and ovals, carves recesses with booleans, voxel-remeshes each paint region into one clay surface, then smooths and decimates it. Thin parts use subdivision surfaces instead. Every parameter becomes a pair of shape keys (`length.min` / `length.max`), and hinged pieces (jaws, pincers) are separate objects pivoted at the hinge. Output is one GLB plus JSON metadata per part.
2. **Godot does everything at runtime.** The builder loads the GLBs, blends the shape keys for the recipe's parameter values, sweeps the spine body and smooth limbs, places and mirrors parts, computes skin weights and smooth normals, and builds one skinned mesh. Blender is not needed to run, edit or export creatures.
3. **A recipe is the whole creature**: a small JSON file with spine, limbs, parts, parameters and paint. The editor and the AI change it through the same operations (`core/ops.gd`).
4. **Animation is procedural**: footprint gait planning for 0 to 8 or more legs, FABRIK leg IK, body height adapting to leg reach, spine, tail and neck motion, and part behaviours (eyes look and blink, jaws open, ears flop, wings flap). Role-based actions (roar, wave, hop) work on any creature. `build` bakes idle, walk, run, roar, wave and hop clips into the GLB.

## Commands

```sh
# Rebuild the part library (Blender as a Python module)
pip install bpy scipy
python3 blender/build_library.py

# Run the editor
godot --path .

# Headless tools (rendering commands need a display; use xvfb-run on servers)
godot --headless --path . -s res://cli/main.gd -- test
godot --headless --path . -s res://cli/main.gd -- build examples/bull.json --out out/bull
godot --path . -s res://cli/main.gd -- render examples/bull.json --out out/bull --views front,side,threequarter
godot --path . -s res://cli/main.gd -- animate examples/bull.json --clip walk --out out/bull_walk.mp4
godot --path . -s res://cli/main.gd -- describe        # part catalog + ops as JSON

# Image -> creature (needs ANTHROPIC_API_KEY)
pip install anthropic numpy pillow
python3 ai/forge.py photo.png --out runs/photo
python3 ai/benchmark.py        # fitter check on known recipes, no API key needed
```

## Editor controls

Pick a part or limb in the palette, then click the creature to place it. Drag parts to slide them over the surface. Drag the blue spine handles to reshape the body (scroll over a handle to fatten it), and drag the yellow joint handles to reshape a selected limb. Right-drag orbits, middle-drag pans, and the scroll wheel zooms. Delete removes the selection, and Ctrl+Z / Ctrl+Y undo and redo. In Test drive, W/S moves, A/D turns, Shift runs, and 1/2/3 play roar, wave and hop.
