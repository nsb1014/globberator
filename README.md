# PolyForge

A Spore-style creature builder that runs inside Blender. You assemble creatures from a library of sculpted parts on a bendable spine. The body, limbs and every skin part fuse into one sculpted surface. The creature rigs itself, animates procedurally, and exports to glTF/GLB, FBX, USD or OBJ, so any engine can use it. An AI loop builds a creature from a reference image within the library's style.

![Examples](preview/gallery.png)

![Part library](preview/parts.png)

## Install

**Into Blender (the editor).** Requires Blender 4.2 or later with `scipy` available to Blender's Python.

```sh
<blender python> -m pip install scipy          # once
blender -b -P tools/install.py                  # installs the add-on + app template
blender --app-template PolyForge                # opens Blender as PolyForge
```

The editor lives in the 3D viewport sidebar, under the **PolyForge** tab.

**Headless (CLI, tests, AI loop).** Uses Blender as a Python module:

```sh
pip install bpy numpy scipy pillow
python3 pf.py --help
```

Any command also runs through a regular Blender: `blender -b -P pf.py -- <command>`.

## Using the editor

1. **Creature panel:** start a new creature or open an example. **Preview** rebuilds fast. **Sculpt** fuses the skin into one remeshed surface, which is what exports use.
2. **Parts panel:** click a part or limb button, then click the creature. Placement snaps to named sockets (head front, brow, eyes, ears, horns, cheeks, back, tail tip, shoulders, hips).
3. **Symmetry is automatic** (carried over from the original attachment code). Parts near the spine's midline snap onto it and stay single. Parts off the midline get a reflected twin. Centre-only parts (mouths, nose, brow, crest, frill, shell, mane, fins, tail tips, cyclops eye) are always centred, and paired parts (eyes, ears, horns, cheeks, wings, antennae) are always mirrored.
4. **Selection panel:** sliders for position, scale, rotation and every part parameter. **Spine panel:** move, grow, shrink, add or remove vertebrae. **Paint panel:** base, accent and detail colours plus pattern.
5. **Animate & export panel:** bake idle, walk, run, roar, wave and hop, play them, and export GLB, FBX, USDZ or OBJ.

Every edit goes through the recipe, so Blender's undo covers it.

## How it works

- **Recipe:** a small JSON file holding the spine, limbs, parts, parameters and paint (`examples/*.json`). The editor and the AI change it through the same operations (`polyforge/ops.py`). `polyforge/recipe.py` clamps every value into the library's style ranges and enforces the placement rules.
- **Parts** (`polyforge/parts/`) are modelled in code with the sculpt kit (`polyforge/kit.py`): smooth PCHIP lofts and dense ovals, boolean carving, then a voxel remesh, smoothing and decimation per paint region (`polyforge/finish.py`). Thin plates use subdivision instead. Parameters are exact, because each part is rebuilt from its parameters and cached.
- **Builder** (`polyforge/builder.py`):
  - Sweeps the spine body and smooth limbs, places the parts, and voxel-remeshes the body, limbs and all skin-slot regions into one surface. Detail parts (eyes, horns, hooves, teeth) stay as separate finished meshes.
  - Builds the armature (spine chain, limb chains, part and jaw bones) and computes skin weights that blend across joints and where limbs meet the body.
  - Paints vertex colours (patterns, belly) and sets one material per paint slot.
- **Animation** (`polyforge/animator.py`):
  - Footprint gait planning for 0 to 8 or more legs, with FABRIK leg IK and the body sinking to keep every foot in reach.
  - Spine, tail and neck motion, plus part behaviours: eyes look and blink, jaws open, ears flop, wings flap.
  - Role-based actions (roar, wave, hop) that work on any creature.
  - `polyforge/baker.py` bakes each clip to an action on its own NLA track, so every exporter carries all clips.

## Commands

```sh
python3 pf.py build examples/bull.json --out out/bull --formats glb,fbx,usdz,blend
python3 pf.py render examples/bull.json --out out/bull --views front,side,threequarter [--engine cycles]
python3 pf.py animate examples/bull.json --clip walk --out out/bull_walk.mp4
python3 pf.py turntable examples/bull.json --out out/bull_turntable.mp4
python3 pf.py gallery examples/*.json --out out/gallery.png
python3 pf.py library --out out/parts       # each part as its own GLB, for engines that assemble parts themselves
python3 pf.py describe                       # part catalog, sockets and ops as JSON (what the AI reads)
python3 pf.py test [--fast]

# Image -> creature (needs ANTHROPIC_API_KEY)
pip install anthropic
python3 ai/forge.py photo.png --out runs/photo
python3 ai/benchmark.py                      # fitter check on known recipes, no API key needed
```

## Layout

| Path | What it is |
| --- | --- |
| `polyforge/` | The Blender add-on: kit, parts, recipe, placement, builder, animator, baker, export, render, UI, CLI, tests |
| `app_template/` | Starts Blender as PolyForge |
| `tools/install.py` | Installs the add-on and app template into a Blender install |
| `pf.py` | Command-line entry point |
| `ai/` | Image-to-recipe loop (Claude + numeric fitting), scoring, benchmark |
| `examples/` | Example recipes |
| `library/thumbs/` | Part thumbnails used by the editor palette |
