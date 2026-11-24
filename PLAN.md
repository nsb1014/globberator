# PolyForge character builder

Design proposal for review • November 24, 2026

Give PolyForge one full-body reference image and get back a character you can turn around, edit, play in motion, and export. A viewer should recognize the subject from its silhouette, proportions, and distinctive features. The part library supplies the artistic interpretation. A person and the AI should have access to the same building controls.

## What to borrow from Spore

Maxis called its deformable parts *rigblocks*. An artist designed both the part and the shapes it could take as the player dragged a handle. One piece could cover a family of shapes while retaining a deliberate design. Buildings and vehicles could be assembled entirely from these pieces. Creatures combined a flexible spine and torso with limbs and detailed anatomical parts. For PolyForge, a horn could have editable length, taper, and curvature, while its edges and surface treatment always belong to the same art style. [Maxis rigblocks paper](https://www.cs.cmu.edu/~ajw/s2007/0248-Rigblocks.pdf) · [Maxis texturing paper](https://www.cs.cmu.edu/~ajw/s2007/0311-PaintingModels.pdf) · [Spore animation paper](https://chrishecker.com/images/c/cb/Sporeanim-siggraph08.pdf)

Spore carried information about anatomy into animation. Parts declared capabilities such as grasping or opening a mouth. Animators could express a movement in terms of participating body parts and their relationships. At runtime the game selected the actual parts, worked out targets, and bent the skeleton to reach them. Walking also had a gait system to coordinate the feet. For PolyForge, author the timing and character of a movement, and let the runtime adapt it to the body. [Maxis SIGGRAPH paper and demonstration videos](https://chrishecker.com/Real-time_Motion_Retargeting_to_Highly_Varied_User-Created_Morphologies)

## First character: a minotaur

Use the far-right minotaur in the five-character lineup (1000012403.png) as the anatomical reference. Build the bare character in one neutral matte material. Exclude armor, garments, jewelry, the axe, and texture work from the model and its likeness score.

- **Visible landmarks.** Match the thick horns that sweep outward and curl up, the heavy brow and broad blunt muzzle, the substantial upper arms and hands, the wide-set split hooves, and the tufted tail. Give the mane and tail tuft simple sculpted masses.
- **Hidden anatomy.** Estimate shoulder joints from the visible upper arms and neck. The outer edges of the shoulder plates are an unreliable guide to body width. Keep chest depth, waist, and the lower-leg profile adjustable. Mark areas covered by equipment as unknown when comparing the render to the reference.
- **Review pose.** Use a relaxed stance with the hands clear of the torso so the chest, waist, and arm joins can be seen. For the likeness check, temporarily pose the model to align visible landmarks with the reference. Review the inferred volumes from the side and back.

First assemble the target by hand. Render a turntable and try a walk. Then give the AI the same reference and part controls. This gives us a direct comparison for likeness and motion. Buildings and vehicles remain interaction references.

## Which parts earn a place

Choose part boundaries around edits a creator would actually want to make. Keep the brow, cheeks, and muzzle together in the first head so the bull face reads as a deliberate design. Give muzzle length and width a controlled range. Split out ears and horns because changing their shape and placement can produce a distinct silhouette. Revisit the division if a later reference needs it.

| Start with | Useful controls | How to test transfer |
| --- | --- | --- |
| Humanoid torso and pelvis | Shoulder span, chest depth, waist width | Make a broad minotaur and a lean hornless biped with the same body. Watch the shoulder and hip joins through a stride. |
| Arms, hands, and two-legged skeleton | Segment lengths, thickness, resting pose | Reuse the arms on the lean biped. Change forearm length and verify the hand still reaches a common target. Keep body-specific lower-leg bends and foot contacts adjustable. |
| Paired horns | Base position, sweep, taper, length | Fit the same horn to a narrower skull with a different sweep. Judge the silhouette in profile and from the front. |
| Bull head and foot ends | Muzzle shape, ear angle, footprint and contact | Spend a dedicated part where it earns recognition or a convincing walk. Check the split hoof in front view and test stable contact through the stride. |

Keep the reuse checks as rough assemblies. The first finished character is the minotaur. For each prospective part, first try fitting an existing part with its allowed controls. Record which reference feature or motion fails, what a new part would fix, and where else it might be useful. If making a part more generic spoils the likeness or its movement, keep the specialized shape. Use a plain gray preview for every reuse check.

## The builder and its part library

- Shape a flexible trunk by moving a short spine and changing its thickness. Attach joint chains for limbs and deform the body around their roots. Fit detail pieces such as ears, eyes, and horns at artist-defined attachment regions. Test one shoulder through a full stride before making dozens of parts.
- Give every part a stable identity, preview images, attachment rules, allowed shape changes, and a role in motion. A foot needs a sole contact point and a forward direction. An ear needs an attachment and an allowed bend. Build just enough styles of each part to tell the first references apart.
- Store the character in a versioned, human-readable recipe containing the library version, parts, parent attachments, and shape settings. Generate the mesh and skeleton from that recipe. The viewport editor and AI both change the recipe through the same operations. Save and reopen must reproduce the same character.
- In the editor, drag, mirror, resize, pose, undo, and pin a feature. A pinned head design should survive a request for shorter legs. Regenerate only the unlocked choices, then preview the result standing and walking.

## How the reference becomes a model

1. Isolate the figure and estimate its camera angle and pose. Mark visible anatomical landmarks and distinctive shapes. Mask the other figures and all equipment. Record hidden or ambiguous features as guesses. A raised arm belongs to the reference pose, while the character still needs a neutral stance for walking.
2. Have a vision model propose a small set of recipes from the actual catalog, using part previews and allowed settings. The builder checks attachments, joint ranges, and part identities. Reject an invalid recipe before scoring it.
3. Pose each candidate to match the reference and render it from the estimated camera. Compare exposed contours, proportions, and landmark positions. Exclude hidden contours from the fit. Refine camera, shape controls, and part choices in a bounded loop. Use a fixed human-made example to check whether the scoring favors recognizable results.
4. Give the user the closest valid candidate with a turntable and walking preview. When two plausible interpretations differ meaningfully, show the alternative or accept a second view. Keep uncertain features editable. On this target both horns are visible. Torso depth is inferred, so its shape should stay easy to revise.

**Style tolerance.** Let the library simplify the shapes while preserving the horn span, muzzle proportions, and stance. Judge the turntable at thumbnail size and close up in neutral lighting.

Single-image part assembly has been demonstrated for furniture using a known, complete set of parts. PolyForge must additionally select suitable parts, vary their shapes, and produce a moving creature. Validate those capabilities on our own references before choosing a model provider or investing in training. [Li et al., ECCV 2020](https://cs.stanford.edu/~liyichen/projects/assembly/)

## Motion and export

Start with idle, look, and a level-ground walk. Animate a biped shifting its pelvis toward the supporting leg. Hold the planted foot in world space while the opposite leg swings toward its next reachable contact. Let the arms swing freely and check shoulder clearance when the torso widens. Bend hips, knees, and ankles within their limits. Adapt stride and body height to limb length. Add authored timing for weight shifts and head motion so character survives the procedural adjustments. Extend to a second body family after these rules work across very different proportions.

Deliver both the editable recipe and a rigged GLB model with the neutral preview material and baked idle and walk clips. Baking records the resulting movement so another 3D application can play it. The Godot builder retains the adaptive controller for live changes. Check the export by opening it in a fresh project and a second viewer.

## Milestones and review tests

| Milestone | What we should be able to see |
| --- | --- |
| 1. Establish the style and attainable likeness | A hand-built minotaur turntable beside the target image. Identify its defining features. Show the lean biped and narrower horned skull as rough reuse checks. |
| 2. Prove the body and movement | Short-legged, long-legged, and broad-chested minotaur variants use the same biped walk controller. In slow motion the planted feet stay put, knees bend consistently, and shoulders stay attached. Measure planted-foot drift relative to foot length. |
| 3. Prove the complete AI workflow | A fresh reference goes in and an editable, walking model comes out. Compare the first AI guess and the refined result with the best human assembly using the same parts. Record generation time and cost per accepted result. |
| 4. Prove it generalizes and travels | Set aside previously unseen drawings and photos. Check recognition, 360-degree plausibility, style, and walking separately. Include a case with a missing library feature. Pin a feature, revise another, reopen the saved recipe, and play the exported clips in another viewer. |

Use held-out renders of known recipes alongside real references. Known recipes reveal camera, attachment, and fitting errors. Real references reveal gaps in the library. When the best hand-built example misses the target, improve the parts; when the hand-built example succeeds and the AI falls short, improve selection and fitting.

## First visual review

Show a gray turntable in a relaxed pose and a reference-aligned front view. Check horn span, muzzle width, upper-arm mass, and hoof spacing against visible anatomy. Review the estimated chest and pelvis in profile, then inspect the weight shift and hoof contact in a short walk.
