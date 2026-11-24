# PolyForge character builder

Design proposal for review • November 24, 2026

Give PolyForge one full-body reference image and get back a character you can turn around, edit, play in motion, and export. A viewer should recognize the subject from its silhouette, proportions, and distinctive features. The part library supplies the artistic interpretation. A person and the AI should have access to the same building controls.

## What to borrow from Spore

Maxis called its deformable parts *rigblocks*. An artist designed both the part and the shapes it could take as the player dragged a handle. One piece could cover a family of shapes while retaining a deliberate design. Buildings and vehicles could be assembled entirely from these pieces. Creatures combined a flexible spine and torso with limbs and detailed anatomical parts. For PolyForge, a beak could have editable length and curvature, while its edges and surface treatment always belong to the same art style. [Maxis rigblocks paper](https://www.cs.cmu.edu/~ajw/s2007/0248-Rigblocks.pdf) · [Maxis texturing paper](https://www.cs.cmu.edu/~ajw/s2007/0311-PaintingModels.pdf) · [Spore animation paper](https://chrishecker.com/images/c/cb/Sporeanim-siggraph08.pdf)

Spore carried information about anatomy into animation. Parts declared capabilities such as grasping or opening a mouth. Animators could express a movement in terms of participating body parts and their relationships. At runtime the game selected the actual parts, worked out targets, and bent the skeleton to reach them. Walking also had a gait system to coordinate the feet. For PolyForge, author the timing and character of a movement, and let the runtime adapt it to the body. [Maxis SIGGRAPH paper and demonstration videos](https://chrishecker.com/Real-time_Motion_Retargeting_to_Highly_Varied_User-Created_Morphologies)

## First product slice

Proposed starting point pending art direction: stylized ground creatures, beginning with one four-legged family. Use Godot for a standalone builder and live movement preview. Treat buildings and vehicles as interaction references. A clothed humanoid would be a different first family, with different priorities for joints, hair, garments, and identity. Choose the first family before commissioning a catalog.

Use three references to anchor the art direction. Pick one for distinctive proportions, one for an unmistakable feature, and one near the edge of the intended style. Record the two or three details each character must retain. Hand-build a best effort for each reference first. That shows how close the library itself can get and gives the AI a meaningful comparison.

## The builder and its part library

- Shape a flexible trunk by moving a short spine and changing its thickness. Attach joint chains for limbs and deform the body around their roots. Fit detail pieces such as ears, eyes, horns, and paws at artist-defined attachment regions. Test one shoulder through a full stride before making dozens of parts.
- Give every part a stable identity, preview images, attachment rules, allowed shape changes, color regions, and a role in motion. A foot needs a sole contact point and a forward direction. An ear needs an attachment and an allowed bend. Build just enough styles of each part to tell the first references apart.
- Store the character in a versioned, human-readable recipe containing the library version, parts, parent attachments, shape settings, and colors. Generate the mesh and skeleton from that recipe. The viewport editor and AI both change the recipe through the same operations. Save and reopen must reproduce the same character.
- In the editor, drag, mirror, resize, pose, undo, and pin a feature. A pinned head design should survive a request for shorter legs. Regenerate only the unlocked choices, then preview the result standing and walking.

## How the reference becomes a model

1. Isolate the figure and estimate its camera angle and pose. Mark visible landmarks, broad colors, and distinctive features. Record hidden or ambiguous features as guesses. A lifted front paw belongs to the reference pose, while the character still needs a neutral stance for walking.
2. Have a vision model propose a small set of recipes from the actual catalog, using part previews and allowed settings. The builder checks attachments, joint ranges, and part identities. Reject an invalid recipe before scoring it.
3. Pose each candidate to match the reference and render it from the estimated camera. Compare outline, proportions, landmark positions, and the agreed signature features. Refine camera, shape controls, and part choices in a bounded loop. Use a fixed human-made example to check whether the scoring favors recognizable results.
4. Give the user the closest valid candidate with a turntable and walking preview. When two plausible interpretations differ meaningfully, show the alternative or accept a second view. Keep uncertain features editable. An unseen tail may need a guess; the front paw visible in the image deserves a closer match.

**Style tolerance.** Keep the library's surface treatment, palette rules, and allowed deformations consistent. Favor silhouette and feature placement over matching lighting or fine texture. A realistic fox might become a simplified character and still read as that fox through its ear angles, narrow muzzle, and oversized tail. If the library lacks a forked tail that defines a character, flag the gap and show the nearest available shape.

Single-image part assembly has been demonstrated for furniture using a known, complete set of parts. PolyForge must additionally select suitable parts, vary their shapes, and produce a moving creature. Validate those capabilities on our own references before choosing a model provider or investing in training. [Li et al., ECCV 2020](https://cs.stanford.edu/~liyichen/projects/assembly/)

## Motion and export

Start with idle, look, and a level-ground walk. On each stride, choose which feet support the body, hold those soles in place in world space, and swing the other feet toward reachable targets. Bend hips, knees, and ankles within their limits. Adapt stride and body height to limb length. Add authored timing for weight shifts and head motion so character survives the procedural adjustments. Extend to a second body family after these rules work across very different proportions.

Deliver both the editable recipe and a rigged GLB model with materials and baked idle and walk clips. Baking records the resulting movement so another 3D application can play it. The Godot builder retains the adaptive controller for live changes. Check the export by opening it in a fresh project and a second viewer.

## Milestones and review tests

| Milestone | What we should be able to see |
| --- | --- |
| 1. Establish the style and attainable likeness | Three reference images beside three hand-built turntables. Agree on which features carry identity and which differences belong to the library style. |
| 2. Prove the body and movement | Short-legged, long-legged, and long-bodied variants use the same walk controller. In slow motion the planted feet stay put, knees bend consistently, and shoulders stay attached. Measure planted-foot drift relative to foot length. |
| 3. Prove the complete AI workflow | A fresh reference goes in and an editable, walking model comes out. Compare the first AI guess and the refined result with the best human assembly using the same parts. Record generation time and cost per accepted result. |
| 4. Prove it generalizes and travels | Set aside previously unseen drawings and photos. Check recognition, 360-degree plausibility, style, and walking separately. Include a case with a missing library feature. Pin a feature, revise another, reopen the saved recipe, and play the exported clips in another viewer. |

Use held-out renders of known recipes alongside real references. Known recipes reveal camera, attachment, and fitting errors. Real references reveal gaps in the library. When the best hand-built example misses the target, improve the parts; when the hand-built example succeeds and the AI falls short, improve selection and fitting.

## Decision for the first review

Which subjects and art style should define the first pack? Three representative images, including a preferred example of the finished style if it differs from the subjects, are enough to choose the first parts and motion test.
