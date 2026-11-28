# Metaball dolphin and bat pilots

The recipes use a neutral clay material and native Blender animation. The authored axes are +Y dorsal and +Z forward. The pilots are independent of the active example recipes.

## Bottlenose dolphin

The target is an adult common bottlenose dolphin (*Tursiops truncatus*) in level transit. The reference profile shows a rounded melon stepping into a short rostrum, a small eye near the corner of the mouth, tapered paired pectoral flippers, and one swept dorsal fin near midbody. The top view should show a narrow tail stock widening into two transverse fluke lobes with a central trailing notch. Use the profile illustration for silhouette and dorsal placement, and the fin morphology study for the swept planform. [NOAA Fisheries profile illustration](https://www.fisheries.noaa.gov/species/common-bottlenose-dolphin) · [Ionian Dolphin Project scale illustration](https://ioniandolphinproject.org/portfolio-item/bottlenose-dolphin/) · [Cetacean fin study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8357180/)

Measure body length from rostrum tip to fluke notch. Measure depth perpendicular to that axis across the silhouette with dorsal fin, flippers and flukes excluded. The deepest body section should fall near 45% of body length from the rostrum, taper faster across 60–70% and continue into a compressed stock. A depth of 17–22% of body length and a stock depth near 85% length of 30–49% of maximum body depth are pilot fitting ranges. The maximum section location and taper follow the morphometric study. The normalized fitting ranges allow for illustration and individual variation. Skrovan and colleagues' adult specimens had a fluke span of 25.7–28.7% of body length. [Body cross-section study, Figure 1](https://doi.org/10.1113/JP290419) · [Dive biomechanics, Table 1](https://bpb-us-e1.wpmucdn.com/sites.ucsc.edu/dist/7/1769/files/2024/07/DolphinBiomechanics_SkrovanEtAl1999.pdf)

The rest pose has level flukes. During swim the posterior spine bends dorsoventrally, and the separately modeled flukes follow the end of the stock. The lower jaw and placement of the blowhole use inferred three-dimensional geometry based on the profile cues.

## Big brown bat

The target is an adult big brown bat (*Eptesicus fuscus*) in flight, with short rounded ears, a blunt muzzle, a broad hand membrane with four elongated digit supports, a short free thumb at the wrist, and a small triangular tail membrane between the hindfeet. The frontal flight photo shows the loaded stroke and forward-facing eyes. The near-ventral image shows the spread forearm and hand, and the side-oblique flight photo shows the deeper curvature of the membrane during a stroke. Maryland DNR gives a 32–40 cm wingspan, 103–130 mm body length and 45–48 mm forearm. These ranges guide the scale. The apparent proportions vary with shooting angle and wing phase. [Bat Conservation International flight photograph](https://www.batcon.org/whats-your-bat-sign/) · [iNaturalist ventral photograph](https://www.inaturalist.org/guide_taxa/363609) · [McGill Gault flight photograph](https://gault.mcgill.ca/fr/nouvelles/detail/des-echos-au-grenier-une-soiree-a-denombrer-les-chauves-souris-de-gault/) · [Maryland Department of Natural Resources measurements](https://dnr.maryland.gov/wildlife/Pages/plants_wildlife/bats/Battypes/Big-Brown-Bat.aspx)

Use a dorsal or ventral view to measure projected lateral span from tip to tip in the extended and retracted poses. Also measure shoulder-to-wingtip distance, which distinguishes flexion from shortening due to stroke elevation. The two poses should visibly change the elbow, wrist and membrane silhouette. The pilot review threshold is at least 15% reduction in projected span and at least 7% reduction in shoulder-to-tip distance during retraction. These are animation targets. Same-species measurements establish that the degree of flexion during upstroke changes with flight speed. [Konow et al., flight kinematics of big brown bats](https://pubmed.ncbi.nlm.nih.gov/28235906/) · [Bat forelimb and membrane anatomy](https://pmc.ncbi.nlm.nih.gov/articles/PMC5493806/)

The neutral pose displays both wings extended. The clip uses wings with linked shoulder, elbow and wrist chains. The dorsal camber, face volumes and hidden membrane thickness are inferred. The tail membrane is held in the splayed flight posture.

## Blender review

The normal recipe build produced both soft skins as one closed, handle-free component. The fins and membranes use their own surfaces and bones. Surface measurements use evaluated Blender mesh coordinates in recipe units. The dolphin cross-sections exclude its fins. Bat shoulder-to-tip uses the posed shoulder and terminal wing joints.

| Measurement | Dolphin | Bat |
| --- | --- | --- |
| Deepest body section | 19.9% of length at 49% from rostrum | — |
| Stock at 85% body length | 39.2% of maximum depth, 2.38 times as deep as wide | — |
| Fluke span or neutral wingspan | 1.039, 28.6% of body length | 3.29 |
| Animated motion | 0.96 vertical travel of fluke mount, up and down at 0.79 s and 0.09 s | Extended at 0.29 s, retracted at 0.69 s, approximately 20% reduction in projected span and 10% reduction in shoulder-to-tip distance |

Independent review of the revised stills and Blender reimport confirmed the dolphin's short rostrum, swept fins, seated pectoral and dorsal roots, recognizable horizontal flukes and dorsoventral stroke. The top and diagonal views still show bands around the melon and a slight collar where the tail stock meets the flukes. The eye reads as a raised pinpoint, and the pectoral roots sit slightly farther aft than in the profile reference.

Independent review of the revised stills and Blender reimport confirmed the bat's thumb, digit fan, tail membrane and coordinated shoulder, elbow and wrist flex. The ventral digit ridges and hind toes are subtler than the reference, the trailing notches are sharper, and the muzzle is rounder. The inner membrane loses some definition against the torso during retraction. The animation flexes the membrane with its bones and presents a simplified camber and slack profile. Exact ankle membrane attachment and species-specific fold detail are inferred.
