# PolyForge · Character studies

## Bull

An unarmored adult bull built from a fresh recipe. Its bovine head, swept horns, split hooves and tufted tail are the same catalog parts used by the minotaur. The `heavy_quadruped` body supplies a horizontal torso with paired shoulder and hip sockets. Each socket accepts one `ungulate_leg` part. The recipe selects the fore or hind profile and can set fullness from 0 to 1. A continuous surface connects brisket, belly and rump.

![Neutral bull](preview/bull.jpg)

[Foreleg shape comparison](preview/bull-forelegs.jpg) · [Neutral turntable](preview/bull-turntable.mp4) · [Side-view walk](preview/bull-walk.mp4) · [Rigged bull](godot/bull.glb) · [Bull recipe](models/bull.json)

At build time each socket constructs its leg and shared hoof once. The attachment mirrors the assembled geometry and joint positions across the body. An edit to the shoulder attachment updates both forelegs on rebuild. Each side gets its own bones in the 26-joint skeleton. During its walk the bull advances 2.08 model units over two strides. Each hoof bears weight for 66% of its cycle and lifts in turn. Both the idle and walk are baked into the GLB.

## Minotaur

A runnable Godot character study of the far-right minotaur in the supplied lineup. The model opens in a neutral stance, uses one matte gray material, and has a 22-joint skeleton.

![Neutral minotaur](preview/minotaur.jpg)

[Rear mane detail](preview/minotaur-mane.jpg) · [Rear shape comparison](preview/minotaur-back.jpg) · [Step in place from behind](preview/minotaur-motion.mp4) · [Neutral turntable](preview/minotaur-turntable.mp4) · [Rigged 3D model](godot/minotaur.glb)

## Open the studio

Import `godot/project.godot` in Godot 4.3 and press **F6** with the studio scene open, or **F5** to launch the project. Both models are included. Choose **Minotaur** or **Bull** in the character menu. Drag the viewport to orbit, scroll to zoom, and use the sliders for horn span, muzzle length, and chest depth. Select **Idle** for either character, **Walk forward** for the bull, or **Step in place** for the minotaur. **Neutral** restores the original stance. **Save proportions** remembers the slider values for that character on that computer.

The minotaur GLB also opens independently in Blender or another glTF viewer. It carries the neutral mesh, shape controls, and baked idle and step-in-place clips (the latter uses the animation key `Walk`). The Godot studio stores edits locally. To bake a different base model for distribution, edit the JSON recipe and rebuild it.

## How this reference is fitted

The anatomical interpretation of the supplied image is in `models/reference.json` and `models/minotaur.json`. The fitting tool uses the annotated horn windows to detect the visible tips and outside contours, calibrates their size from eye height above the ground, and solves for the corresponding catalog horn width and rise. The source image stays local. The exposed muzzle, torso, arms, hooves, and tail are shaped in the procedural builder. Hidden anatomy is estimated. The bull uses an authored recipe. Image fitting currently supports the annotated minotaur horns.

With Python, NumPy, SciPy, and Pillow installed:

```sh
python tools/fit_reference.py path/to/lineup.png --output models/minotaur.json
```

## Generate the rig and previews

The generator was run with Blender 4.3.2, NumPy, and SciPy. The recipe selects the core parts and sets horn span and rise, shoulder width, chest depth, and muzzle length. The builder creates the anatomy, binds the skeleton, adds shape controls, and solves and bakes the gait. The minotaur’s two-second step cycle keeps each hoof fixed in world space for 60% of its cycle. Both feet briefly share the load as the pelvis shifts toward the next support. The ribs turn against the pelvis, followed by the arms, head and tail. The idle breath originates in the upper body.

```sh
blender -b --python-exit-code 1 -P tools/build.py
blender -b --python-exit-code 1 -P tools/build.py -- --recipe models/bull.json
blender -b --python-exit-code 1 -P tools/render.py -- godot/minotaur.glb review --clip still
```

For the editable Blender scene, pass `-- --review review` to the build script. Render accepts `--clip turn` or `--clip walk` for PNG sequences. The review uses independent videos for the neutral orbit and the stationary step. The step preview uses `--azimuth 146` to show how the back and hips deform under load. The renderer uses 64 samples per minotaur motion frame and 36 per bull motion frame. The bull walk uses a fixed side camera. Supply `--oidn /path/to/oidnDenoise` to apply Open Image Denoise before the display transform. The preview images come from reimporting the exported GLB.

To check the imported sole contacts, run `godot --headless --editor --import --path godot`, then `godot --headless --path godot --script "$PWD/tools/tests/ground_contact.gd"` from the repository root. The check samples the soles through idle and both sides of the step, including between baked keyframes.

To verify bilateral placement on a rotated and translated socket, run `blender -b --python-exit-code 1 -P tools/tests/paired_attachment.py`.

For the bull, run `godot --headless --path godot --script "$PWD/tools/tests/bull_walk.gd"`. This checks all four soles, forward displacement, shape controls and character switching. The Blender check `blender -b --python-exit-code 1 -P tools/tests/back_deformation.py -- godot/bull.glb` measures how the flank stretches across the walk.

The design plan and research are in [PLAN.md](PLAN.md).
