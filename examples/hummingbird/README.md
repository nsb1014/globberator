# Hummingbird

A stylized hummingbird in a hover pose with layered flight feathers, shoulder-mounted wings, and independently articulated feet. The example includes a [clay preview](preview.png), [clay turnaround](clay-turnaround.png), and [review notes](review.md).

Run these commands from the checkout with Blender, SciPy in Blender's Python, and Pillow in your shell Python.

```sh
blender -b -t 4 --python-exit-code 1 -P examples/hummingbird/build_hummingbird.py
blender -b -t 8 --python-exit-code 1 -P examples/hummingbird/review_hummingbird.py
python3 examples/hummingbird/compose_preview.py
```

The scripts write the editable Blender file, Godot-ready GLB, renders, and geometry report to `out/hummingbird/`.
