# PolyForge · Minotaur study

A runnable Godot character study of the far-right minotaur in the supplied lineup. The model opens in a neutral stance, uses one matte gray material, and has a 22-joint skeleton.

![Neutral minotaur](preview/minotaur.jpg)

[Turntable and walk preview](preview/minotaur-motion.mp4) · [Rigged 3D model](godot/minotaur.glb)

## Open the studio

Import `godot/project.godot` in Godot 4.3 and press **F6** with the studio scene open, or **F5** to launch the project. The model is included. Drag the viewport to orbit, scroll to zoom, and use the sliders for horn span, muzzle length, and chest depth. Select **Idle** or **Walk** to play an animation, or **Neutral** to restore the original stance. **Save proportions** remembers the slider values for the next session on that computer.

The GLB also opens independently in Blender or another glTF viewer. It carries the neutral mesh, shape controls, and baked idle and in-place walk clips. The Godot studio stores edits locally. To bake a different base model for distribution, edit the JSON recipe and rebuild it.

## How this reference is fitted

The anatomical interpretation of the supplied image is in `models/reference.json` and `models/minotaur.json`. The fitting tool uses the annotated horn windows to detect the visible tips and outside contours, calibrates their size from eye height above the ground, and solves for the corresponding catalog horn width and rise. The source image stays local. The exposed muzzle, torso, arms, hooves, and tail are shaped in the procedural builder. Hidden anatomy is estimated. The first prototype has one anatomical family; new subjects currently need a part recipe and visible landmarks.

With Python, NumPy, SciPy, and Pillow installed:

```sh
python tools/fit_reference.py path/to/lineup.png --output models/minotaur.json
```

## Generate the rig and previews

The generator was run with Blender 4.3.2, NumPy, and SciPy. The recipe selects the core parts and sets horn span and rise, shoulder width, chest depth, and muzzle length. The builder creates the anatomy, binds the skeleton, adds shape controls, and solves and bakes the gait. Each supporting hoof moves backward at constant speed relative to the body during the in-place stride. The opposite leg swings forward.

```sh
blender -b --python-exit-code 1 -P tools/build.py
blender -b --python-exit-code 1 -P tools/render.py -- godot/minotaur.glb review --clip still
```

For the editable Blender scene, pass `-- --review review` to the build script. Render accepts `--clip turn` or `--clip walk` for PNG sequences. The preview images come from reimporting the exported GLB.

The design plan and research are in [PLAN.md](PLAN.md).
