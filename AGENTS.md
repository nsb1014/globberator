# Build and review assets in Globberator

For an automated neutral-clay humanoid with runtime motion bindings, use the [one-shot command](README.md#one-shot-characters). If you are the image classifier, serialize your classification using `polyforge/character_brief.py` and pass it with `--brief` to use the same compiler without a second model call. The procedure below applies to bespoke assets and manual reviews.

Use this procedure for reference-driven builds. It uses local commands and a fresh vision subagent without a third-party model API. Run the commands from the checkout root. If shell Python lacks `bpy`, replace `python3 pf.py` with `blender -b --python-exit-code 1 -P pf.py --`.

## 0. Check the runtime

- Prefer an installed Blender CLI. If neither Blender nor `bpy` is available, use an isolated Python environment with `bpy`, NumPy, SciPy, and Pillow. Check that `pf.py --help` runs in the chosen runtime. Import `bpy` before `mathutils` in shell Python scripts.
- Verify the first small render exists and opens before building a review set. An import check alone does not exercise the renderer. If the host reports missing `libEGL.so.1`, resolve its EGL and software OpenGL runtime or report that rendering is blocked. Judge driver warnings by whether a usable image was written.

## 1. Establish the target

- Use the current user's target images and written intent. List the target images separately from any supplied failed outputs. Repository examples and previous renders demonstrate the tool. Library thumbnails and clay sheets show individual part shapes. Use either as design references only when the user designates them.
- If the target is missing or inaccessible, report the specific gap. Keep uncertain details marked as inferred. Never substitute a repository image. Make the actual reference available to the reviewer when possible. If they cannot open it, keep reference fidelity pending.
- Before building, record the view and pose, silhouette and proportion landmarks, recognisable features, and color regions. Define what a proportion measures. For a keychain figure, for example, measure body height from hair to soles, exclude hardware, and distinguish hair height from face height. Treat ranges from tilted photos as estimates. If defining features or colors need custom geometry or materials, choose that route before assembling a detailed library draft.

## 2. Find parts and build a first pass

1. Create a fresh working folder. For a recipe build, start with `mkdir -p out/asset` and `python3 pf.py new --out out/asset/recipe.json`. Use an existing recipe when the user asks to revise that asset.
2. Run `python3 pf.py search "human hand"` or search for the actual feature by shape or anatomy. Read each result's description and attachment type. Use `python3 pf.py describe --part PART_ID` to see its exact controls and ranges. Copy the result's `shape` object to a JSON file and run `python3 pf.py part SHAPE_JSON --out PART_DRAFT_DIR` for a closer look.
3. Compare candidate shapes in front and profile. Choose by visible form and host fit. For a simple rounded boot, try `foot_hoof` with `split: 0` and check the silhouette. A dorsal crest is a back ridge, and a biological gape is a wide opening. If the target requires a distinct crown of hair, a shaped boot, or a shallow sculpted mouth, model that feature directly when the candidates fail. An empty search result is a reason to try a simpler term or use custom geometry.
4. Fit the body and limb proportions first. Use `set_spine` in an operations JSON array and apply it with `python3 pf.py apply RECIPE OPS_JSON --out NEXT_RECIPE`. `w` and `h` are the ring half-width and half-depth in the local cross-section. Use `python3 pf.py surface RECIPE X Y Z` to estimate `u` and `theta` for a landmark in the authored body frame (+Y up, +Z forward, before grounding). `u` follows the spine from its first end to its last. On a vertical spine directed upward, `theta -90` faces forward and `theta 90` faces back. Inspect the coordinates before trusting a named socket.
5. Place the shape with `python3 pf.py attach RECIPE SHAPE_JSON --u U --theta THETA --out NEXT_RECIPE`. Use `--on LIMB_UID` for a limb tip such as a hand. Verify the side and front renders because placement symmetry and part orientation can change the result.
6. Check the assembled silhouette and main attachment locations before refining details. A part passing contact checks can still sit in the wrong anatomical region. Inspect normalize and build warnings for any removed parts or clamped dimensions.

## 3. Build the target colors

- For a colored target, list each region and its intended color before choosing the build method. Check the face, eyes, hair, clothing, hands, footwear, and markings individually where applicable. Use neutral clay for shape checks and render the complete assembled asset in color for final review. A monochrome final is appropriate when the user requests one.
- Recipes support shared base, accent and detail colors, patterns, a belly region, and some fixed part slots. Belly paint follows the underside of the spine. It cannot assign colors by semantic region. If the recipe cannot separate important colors, switch to an editable Blender build script with named mesh/material regions, or finish those regions on the Blender assembly. Use surface-following geometry or painted textures for markings as appropriate.
- Verify a face close-up and a full-body color render before sending for review. Check that the intended assignments survive export and reimport.

## 4. Review independently and verify

1. Render the current assembly in a view matched to the target and in front, side, and additional angles that expose key attachments. Include labeled close-ups for defining features and alternate poses for articulation changes. For example, `python3 pf.py render out/asset/recipe.json --out out/asset/face --views front,side,threequarter --focus head` produces a facial review set.
2. Start a fresh vision-capable subagent without inherited history. Share only the task intent and pose, the actual target images, and the current labeled renders. Keep failed drafts and your own diagnosis out of the first review. Ask the reviewer to inspect the images directly and report the part, view, visible evidence and severity for each finding. Have them identify obscured details. The reviewer leaves the files untouched.
3. Verify each finding against the target and the rendered model before editing. If a reviewer calls the eyes black spheres but a target close-up shows pale sclera, colored irises and black pupils, follow the close-up. Record supported issues, disputed observations, and features that remain uncertain. Resolve material mismatches in shape, fit or color, then rerender the affected views and have a fresh reviewer check visible changes. Leave unresolved material issues pending and identify them in the delivery.
4. For recipes, use `python3 pf.py review out/asset/recipe.json --out out/asset/review` to generate the review record. Run the same command with `--accept "inspection findings"` after the draft passes. Build with `python3 pf.py build out/asset/recipe.json --review out/asset/review/review.json --out out/asset/export --formats glb,blend`. For custom builds, use the asset's own build and render script. Reimport the export and verify silhouette, attachment, and color. If the reviewer, target, or a required view was unavailable, mark that check pending.
5. A `build --no-anim` run before acceptance is a draft export. If Blender reports missing vertex colors or invalid mesh data, inspect the reimported mesh and material regions. A similar warning on an example can help locate the cause. Confirm the actual asset's geometry and colors before delivery.
