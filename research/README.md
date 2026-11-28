# PolyForge anatomy research

The original buildable anatomy families are derived from `species/*.json` through `build_library.py`. Those numeric records document normalized attachments, joint descriptions, proportions and image credits. Some measurements are estimates or appear in occluded areas. The species index preserves the original category totals and separately computes a count of distinct recorded part types per category.

The expansion is tracked in [observations.json](observations.json). Each observation records anatomy, named root and extent landmarks, and a separate geometry inference with its own confidence and missing evidence. Sources are cited for anatomical facts. The ledger distributes no source images. Current observation, candidate, and merge totals are in the generated index.

## What the counts mean

The generated [index](index.json) inventories 79 active families at this revision. It has 54 families derived from 105 legacy species-part observations, 16 complementary families, six pilot parts, two anatomy drafts and one qualified research candidate. A separate set of 14 legacy observations is excluded with reasons in the [library specification](part_library.json). The census records the evidence available for each family. Active status means the family is available in the catalog. Geometry, attachment, and likeness qualifications are separate checks.

The [qualification manifest](qualification.json) records the disposition and evidence for each candidate. A merge links source anatomy to a family without increasing the count. The report tracks an approximate 300-family planning target. The [coverage plan](coverage_plan.json) lists part gaps and also tracks which animal groups have been sampled.

## Expand by part gap

1. Start with a function, shape, joint or attachment the library cannot express. Compare the closest active parts and drafts first. Reuse controls for ordinary variation, and add a new family when a distinct construction or behavior warrants it.
2. Choose an animal specimen that exposes the missing feature well. Acquire the smallest useful set of views around the part and its root. Let the feature determine which source to use.
3. Model only the selected part. A bird may supply a bill edge while a fish supplies a gill cover. A whole body belongs in this workflow only when it is itself the target part, such as a continuous ray disc.
4. Test on a reusable local fixture, such as a cheek patch, wrist, digit, or jaw hinge. Use the ordinary Blender attachment path and vary the scale or host shape. Include enough surrounding anatomy to assess seating, overlap and clearance. Expand the fixture when another component directly determines fit or movement.

The research queue in `part_gaps` covers six parallel workstreams. Each entry names an animal, the closest catalog parts, the feature to verify, the model boundary and a small local fixture. A source URL is a starting point for acquisition. A specimen search brief identifies the view or pose to find when a suitable source still needs locating. Leads enter the evidence ledger once the relevant views and rights have been checked.

Use `coverage.part_gap_workstreams` in [the generated index](index.json) to assign each stream in parallel. Within a stream, group parts that can use the same wrist, jaw, fin seat or other fixture. If specimen evidence shows that an existing control can express a lead, record the merge decision and move on. Adopted leads stay in the plan as history and drop out of the queue. The planning total adds active families, modeled drafts and queued leads. It is an upper bound for this backlog before evidence review and merges. The active inventory measures progress toward the target.

See [game animal part coverage](game_animal_coverage.md) for reusable families and the added fantasy, farm, and pet anatomy.

## Inspect and qualify a draft

Drafts support explicit IDs in `describe --part`, `library --part`, and recipe shapes. The palette, search and one-shot pipeline use the qualified catalog.

The index and exact-ID description list `needs_revision` for observed failures and `needs_verification` for open evidence. Record a repaired check as pending until the revised mesh has been tested. Preserve earlier findings with their revision. A purely rigid or passive part can mark motion as `not_applicable`. Structure, fit, and likeness evidence are still required.

```sh
blender -b -P pf.py -- describe --part seahorse_coronet
blender -b -P pf.py -- library --part seahorse_coronet --out out/part-qualification/inspect
blender -b -t 2 --python-exit-code 1 -P tools/tests/qualify_parts.py -- --out out/part-qualification
```

The structure script sweeps defaults and control bounds, rebuilds defaults to check repeatability, and writes topology, triangle counts, and eight neutral-clay views from the reimported GLB. Local Blender fixtures establish functional placement, contact and clearance across two scales or hosts. For moving parts, exercise the intended range around the relevant joint or surface and check shape and attachment. Use a whole-creature motion pilot when the question concerns coordination across multiple parts.

Measure held-out reference views with the same view, crop, orientation, and scale. The likeness gate requires a silhouette IoU of at least .85 where the outline is visible, mean visible landmark error of at most .05 of the full reference dimension, and independent review with zero major findings. A view may supply only silhouette or landmark evidence when the remaining features cannot be scored. At least one view must contain measured landmarks. A wholly new family with no equivalent can set `require_incumbent` to `false` in the likeness spec. When there is a matched incumbent, score it in the same frame and check for regressions. Generated clay studies are design references. Record photographs, measured specimen views, rights, and their use separately.

## Adding an observation or candidate

1. Start from a part gap. Add the chosen source with a stable URL, publisher, section or figure locator, access date, rights and rights-policy URL. For individually reusable imagery, also supply an explicit open license, creator and asset URL. A text description may support anatomy without implying its pictures were viewed.
2. Name the taxon, rank, life stage and feature. Describe the root, free extent and profile. Label the landmark basis as text, viewed, measured or inferred. Record numeric values only with a measured landmark definition, unit, method and the source actually used.
3. Put modeling assumptions and their missing evidence in the inference field. Identify geometry that is occluded, whose scale is missing or whose pose is unclear.
4. Add a disposition comparing the closest active family. Keep a new candidate when topology, placement, profile or motion calls for a construction distinction and record precisely what still needs review. Use a merge when the evidence fits the same family. Each observation belongs to one disposition.
5. Register a buildable draft by its exact ID and keep the qualification record with the original observations. Update that record with the structure, fit, motion and likeness findings. Publication requires passing evidence for each applicable gate.

## Regeneration and checks

Run these commands from the repository root with Python 3:

```sh
python3 research/build_library.py              # Only needed after changing legacy species input or mappings.
python3 research/validate.py                   # Regenerate the index.
python3 research/validate.py --check           # Validate both generated files in place without writing.
python3 -m unittest research.test_coverage
```

The check does not require Blender or network access. Refresh rights or external links by visiting the cited source when doing another evidence pass. The metadata checks verify that documentation fields and references are present and consistent.
