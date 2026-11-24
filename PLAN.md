# PolyForge character builder

Design proposal for review • November 24, 2026

Give PolyForge one full-body reference image and get back a character you can turn around, edit, play in motion, and export. A viewer should recognize the subject from its silhouette, proportions, and distinctive features. The part library supplies the artistic interpretation. A person and the AI should have access to the same building controls.

## What to borrow from Spore

Maxis called its deformable parts *rigblocks*. An artist designed both the part and the shapes it could take as the player dragged a handle. One piece could cover a family of shapes while retaining a deliberate design. Buildings and vehicles could be assembled entirely from these pieces. Creatures combined a flexible spine and torso with limbs and detailed anatomical parts. For PolyForge, a horn could have editable length, taper, and curvature, while its edges and surface treatment always belong to the same art style. [Maxis rigblocks paper](https://www.cs.cmu.edu/~ajw/s2007/0248-Rigblocks.pdf) · [Maxis texturing paper](https://www.cs.cmu.edu/~ajw/s2007/0311-PaintingModels.pdf) · [Spore animation paper](https://chrishecker.com/images/c/cb/Sporeanim-siggraph08.pdf)

Spore carried information about anatomy into animation. Parts declared capabilities such as grasping or opening a mouth. Animators could express a movement in terms of participating body parts and their relationships. At runtime the game selected the actual parts, worked out targets, and bent the skeleton to reach them. Walking also had a gait system to coordinate the feet. For PolyForge, author the timing and character of a movement, and let the runtime adapt it to the body. [Maxis SIGGRAPH paper and demonstration videos](https://chrishecker.com/Real-time_Motion_Retargeting_to_Highly_Varied_User-Created_Morphologies)

## First character: a minotaur

The target is the far-right figure in the supplied five-character lineup (1000012403.png). Use the same image as the initial style target. When fitting the image, isolate the figure and its equipment; the adjacent fighter overlaps the left edge of the target area. Compare in the near-frontal reference pose.

- **Silhouette.** Thick ivory horns extend sideways before curling upward to dark tips. A heavy brow, blunt muzzle, broad armored shoulders, large hands, and widely spaced split hooves give the character its shape. A tufted tail appears on the viewer’s right.
- **Finish.** Large, sculpted forms, warm brown fur, dark steel with gold edging, a red hanging cloth panel, and bright cyan eyes. Repeat the cyan accent on the carried prop. Preserve these large color shapes when simplifying small surface marks.
- **Equipment and pose.** Include the nose ring, horn bands, layered shoulder armor, bracers, belt, cloth panel, and removable fantasy axe. The diagonal two-handed pose obscures part of the torso. Store the reference pose separately from the neutral body and render both equipped and unequipped previews.
- **Depth and motion.** The view establishes hoof spacing and the visible outline. Torso depth, rear armor, and the side profile of the lower legs are inferred. Keep those dimensions adjustable and judge the profile in motion.

First assemble the target by hand. Render a turntable and try a walk. Then give the AI the same reference and part controls. This gives us a direct comparison for likeness and motion. Buildings and vehicles remain interaction references.

## Which parts earn a place

Choose part boundaries around edits a creator would actually want to make. Keep the brow, cheeks, and muzzle together in the first head so the bull face reads as a deliberate design. Give muzzle length and width a controlled range. Split out ears and horns because changing their shape and placement can produce a distinct silhouette. Revisit the division if a later reference needs it.

| Start with | Useful controls | How to test transfer |
| --- | --- | --- |
| Humanoid torso and pelvis | Shoulder span, chest depth, waist width | Make a broad minotaur and a lean hornless biped with the same body. Watch the shoulder and hip joins through a stride. |
| Arms, hands, and two-legged skeleton | Segment lengths, thickness, resting pose | Reuse the arms on the lean biped. Change forearm length and verify the hand still reaches a common target. Keep body-specific lower-leg bends and foot contacts adjustable. |
| Paired horns | Base position, sweep, taper, length | Use the same horn on the minotaur and on a horned-helmet mock-up. Judge the silhouette in profile and from the front. |
| Bull head and foot ends | Muzzle shape, ear angle, footprint and contact | Spend a dedicated part where it earns recognition or a convincing walk. Check the split hoof in front view and test stable contact through the stride. |
| Shoulder armor and bracers | Width, depth, attachment angle, edge finish | Fit the same shoulder shell to the smaller shield-bearing fighter immediately to the left in the lineup. Compare both silhouettes and lift the arm to check clearance. |

Keep the reuse checks as rough assemblies. The first finished character is the minotaur. For each prospective part, first try fitting an existing part with its allowed controls. Record which reference feature or motion fails, what a new part would fix, and where else it might be useful. If making a part more generic spoils the likeness or its movement, keep the specialized shape. Use the selected equipment for the likeness review. Prototype the axe as one removable prop; an interchangeable weapon catalog can wait.

## The builder and its part library

- Shape a flexible trunk by moving a short spine and changing its thickness. Attach joint chains for limbs and deform the body around their roots. Fit detail pieces such as ears, eyes, and horns at artist-defined attachment regions. Test one shoulder through a full stride before making dozens of parts.
- Give every part a stable identity, preview images, attachment rules, allowed shape changes, color regions, and a role in motion. A foot needs a sole contact point and a forward direction. An ear needs an attachment and an allowed bend. Build just enough styles of each part to tell the first references apart.
- Store the character in a versioned, human-readable recipe containing the library version, parts, parent attachments, shape settings, and colors. Generate the mesh and skeleton from that recipe. The viewport editor and AI both change the recipe through the same operations. Save and reopen must reproduce the same character.
- In the editor, drag, mirror, resize, pose, undo, and pin a feature. A pinned head design should survive a request for shorter legs. Regenerate only the unlocked choices, then preview the result standing and walking.

## How the reference becomes a model

1. Isolate the figure and estimate its camera angle and pose. Mark visible landmarks, broad colors, and distinctive features. Record hidden or ambiguous features as guesses. A raised arm belongs to the reference pose, while the character still needs a neutral stance for walking.
2. Have a vision model propose a small set of recipes from the actual catalog, using part previews and allowed settings. The builder checks attachments, joint ranges, and part identities. Reject an invalid recipe before scoring it.
3. Pose each candidate to match the reference and render it from the estimated camera. Compare outline, proportions, landmark positions, and the agreed signature features. Refine camera, shape controls, and part choices in a bounded loop. Use a fixed human-made example to check whether the scoring favors recognizable results.
4. Give the user the closest valid candidate with a turntable and walking preview. When two plausible interpretations differ meaningfully, show the alternative or accept a second view. Keep uncertain features editable. On this target both horns are visible. The back armor is inferred, so its shape should stay easy to revise.

**Style tolerance.** Keep the library's surface treatment, palette rules, and allowed deformations consistent. Favor silhouette and feature placement over matching lighting or fine texture. For this minotaur, preserve the horns’ outward span and upturned tips, the brow over the cyan eyes, and the broad shoulder silhouette. Scratches on the steel can vary with the library style.

Single-image part assembly has been demonstrated for furniture using a known, complete set of parts. PolyForge must additionally select suitable parts, vary their shapes, and produce a moving creature. Validate those capabilities on our own references before choosing a model provider or investing in training. [Li et al., ECCV 2020](https://cs.stanford.edu/~liyichen/projects/assembly/)

## Motion and export

Start with idle, look, and a level-ground walk. Animate a biped shifting its pelvis toward the supporting leg. Hold the planted foot in world space while the opposite leg swings toward its next reachable contact. Coordinate the arms with the unequipped stride. With the prop equipped, use two hand targets on the handle and check that changing shoulder width preserves both contacts. Bend hips, knees, and ankles within their limits. Adapt stride and body height to limb length. Add authored timing for weight shifts and head motion so character survives the procedural adjustments. Extend to a second body family after these rules work across very different proportions.

Deliver both the editable recipe and a rigged GLB model with materials and baked idle and walk clips. Baking records the resulting movement so another 3D application can play it. The Godot builder retains the adaptive controller for live changes. Check the export by opening it in a fresh project and a second viewer.

## Milestones and review tests

| Milestone | What we should be able to see |
| --- | --- |
| 1. Establish the style and attainable likeness | A hand-built minotaur turntable beside the target image. Identify its defining features. Show the lean biped and helmet as rough reuse checks. |
| 2. Prove the body and movement | Short-legged, long-legged, and broad-chested minotaur variants use the same biped walk controller. In slow motion the planted feet stay put, knees bend consistently, and shoulders stay attached. Measure planted-foot drift relative to foot length. |
| 3. Prove the complete AI workflow | A fresh reference goes in and an editable, walking model comes out. Compare the first AI guess and the refined result with the best human assembly using the same parts. Record generation time and cost per accepted result. |
| 4. Prove it generalizes and travels | Set aside previously unseen drawings and photos. Check recognition, 360-degree plausibility, style, and walking separately. Include a case with a missing library feature. Pin a feature, revise another, reopen the saved recipe, and play the exported clips in another viewer. |

Use held-out renders of known recipes alongside real references. Known recipes reveal camera, attachment, and fitting errors. Real references reveal gaps in the library. When the best hand-built example misses the target, improve the parts; when the hand-built example succeeds and the AI falls short, improve selection and fitting.

## First visual review

Show the reference beside a flat-shaded front view at the same height. Toggle the equipment and check the span of the horns, the width of the armored shoulders, and the stance of the hooves. Then show a side view and a short walk to review the inferred depth and weight shift before detailing fur or metal.
