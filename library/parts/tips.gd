## Limb tips: feet and hands. Origin at the limb's end joint.
## Feet: +Y up, +Z forward, sole below origin. Hands: +Y along the arm, +Z forward.
extends RefCounted

const Base = preload("res://library/part_base.gd")


static func all() -> Array:
	return [FootPaw.new(), FootHoof.new(), FootClaw.new(), FootPad.new(), FootSpike.new(), FootWebbed.new(),
		HandBasic.new(), HandClaw.new(), HandPincer.new(), HandTentacle.new(), HandMitt.new()]


class FootPaw extends Base:
	func _init():
		id = "foot_paw"; category = "foot"; attach = "tip"; cap = "foot"
		desc = "Padded paw with three toe beads (cats, dogs, bears)."
		tags = PackedStringArray(["mammal", "cat", "dog", "bear", "cute"])
		params = {"size": [0.4, 3.0, 1.0], "toes": [0.0, 1.5, 1.0]}

	func sole(p):
		return Vector3(0, -0.1 * pv(p, "size"), 0.03 * pv(p, "size"))

	func build(g, p):
		var s := pv(p, "size")
		g.slot = "skin"
		g.ellipsoid(Vector3(0, -0.055 * s, 0.03 * s), Vector3(0.09, 0.05, 0.11) * s, Basis(), 7, 4)
		if pv(p, "toes") > 0.05:
			g.slot = "detail"
			for i in 3:
				var x := (i - 1) * 0.055 * s
				g.ellipsoid(Vector3(x, -0.07 * s, 0.13 * s), Vector3.ONE * 0.032 * s * pv(p, "toes"), Basis(), 5, 3)


class FootHoof extends Base:
	func _init():
		id = "foot_hoof"; category = "foot"; attach = "tip"; cap = "foot"
		desc = "Cloven hoof (bulls, goats, deer, minotaurs)."
		tags = PackedStringArray(["bovine", "goat", "deer", "minotaur", "horse"])
		params = {"size": [0.4, 3.0, 1.0], "split": [0.0, 1.0, 0.6]}

	func sole(p):
		return Vector3(0, -0.13 * pv(p, "size"), 0.02 * pv(p, "size"))

	func build(g, p):
		var s := pv(p, "size")
		var gap := 0.012 * s * pv(p, "split")
		g.slot = "dark"
		for side in [-1, 1]:
			var c := Vector3(side * (0.035 * s + gap), 0, 0.02 * s)
			var pts := PackedVector3Array([c + Vector3(0, 0.0, 0), c + Vector3(0, -0.08 * s, 0.01 * s), c + Vector3(0, -0.13 * s, 0.03 * s)])
			g.tube(pts, PackedFloat32Array([0.04 * s, 0.05 * s, 0.055 * s]), 6, true, true, Vector3.BACK, Vector2(0.8, 1.1))


class FootClaw extends Base:
	func _init():
		id = "foot_claw"; category = "foot"; attach = "tip"; cap = "foot"
		desc = "Bird / raptor foot: three forward toes and one back toe with talons."
		tags = PackedStringArray(["bird", "dinosaur", "raptor", "dragon"])
		params = {"size": [0.4, 3.0, 1.0], "spread": [0.3, 1.5, 1.0], "talons": [0.0, 2.0, 1.0]}

	func sole(p):
		return Vector3(0, -0.045 * pv(p, "size"), 0.05 * pv(p, "size"))

	func build(g, p):
		var s := pv(p, "size")
		var sp := pv(p, "spread")
		for i in 4:
			var a := (i - 1) * 0.45 * sp if i < 3 else PI
			var dir := Vector3(sin(a), 0, cos(a))
			var L := (0.16 if i < 3 else 0.08) * s
			var base := Vector3(0, -0.02 * s, 0)
			var pts := PackedVector3Array([base, base + dir * L * 0.5 + Vector3(0, -0.015 * s, 0), base + dir * L + Vector3(0, -0.02 * s, 0)])
			g.slot = "skin"
			g.tube(pts, PackedFloat32Array([0.025 * s, 0.02 * s, 0.015 * s]), 4, true, false, Vector3.UP)
			if pv(p, "talons") > 0.05:
				g.slot = "claw"
				g.cone(pts[2], pts[2] + dir * 0.05 * s * pv(p, "talons") + Vector3(0, -0.02 * s, 0), 0.016 * s, 4, Vector3.UP)


class FootPad extends Base:
	func _init():
		id = "foot_pad"; category = "foot"; attach = "tip"; cap = "foot"
		desc = "Thick round column foot with toenails (elephants, sauropods, golems)."
		tags = PackedStringArray(["elephant", "sauropod", "heavy"])
		params = {"size": [0.4, 3.0, 1.0], "nails": [0.0, 1.5, 1.0]}

	func sole(p):
		return Vector3(0, -0.14 * pv(p, "size"), 0)

	func build(g, p):
		var s := pv(p, "size")
		g.slot = "skin"
		g.tube(PackedVector3Array([Vector3(0, 0.02 * s, 0), Vector3(0, -0.14 * s, 0)]), PackedFloat32Array([0.1 * s, 0.13 * s]), 8, false, true, Vector3.BACK)
		if pv(p, "nails") > 0.05:
			g.slot = "detail"
			for i in 3:
				var a := (i - 1) * 0.5
				g.ellipsoid(Vector3(sin(a) * 0.125 * s, -0.11 * s, cos(a) * 0.125 * s), Vector3(0.03, 0.03, 0.02) * s * pv(p, "nails"), Basis(Vector3.UP, a), 5, 3)


class FootSpike extends Base:
	func _init():
		id = "foot_spike"; category = "foot"; attach = "tip"; cap = "foot"
		desc = "Pointed leg tip (insects, spiders, crabs)."
		tags = PackedStringArray(["insect", "spider", "crab", "arthropod"])
		params = {"size": [0.4, 3.0, 1.0]}

	func sole(p):
		return Vector3(0, -0.12 * pv(p, "size"), 0)

	func build(g, p):
		var s := pv(p, "size")
		g.slot = "dark"
		g.cone(Vector3(0, 0.02 * s, 0), Vector3(0, -0.12 * s, 0), 0.035 * s, 5, Vector3.BACK)


class FootWebbed extends Base:
	func _init():
		id = "foot_webbed"; category = "foot"; attach = "tip"; cap = "foot"
		desc = "Flat webbed foot or flipper (ducks, frogs, seals)."
		tags = PackedStringArray(["duck", "frog", "aquatic"])
		params = {"size": [0.4, 3.0, 1.0], "length": [0.5, 2.0, 1.0]}

	func sole(p):
		return Vector3(0, -0.04 * pv(p, "size"), 0.08 * pv(p, "size"))

	func build(g, p):
		var s := pv(p, "size")
		var L := 0.22 * s * pv(p, "length")
		g.slot = "accent"
		g.slab(PackedVector3Array([Vector3(-0.03 * s, -0.025 * s, 0), Vector3(0.03 * s, -0.025 * s, 0), Vector3(0.1 * s, -0.03 * s, L), Vector3(0.0, -0.03 * s, L * 0.85), Vector3(-0.1 * s, -0.03 * s, L)]), Vector3.UP, 0.02 * s)
		g.slot = "skin"
		g.ellipsoid(Vector3(0, -0.01 * s, 0), Vector3.ONE * 0.04 * s, Basis(), 5, 3)


# ------------------------------------------------------------------- hands

class HandBasic extends Base:
	func _init():
		id = "hand_basic"; category = "hand"; attach = "tip"; cap = "hand"
		desc = "Four-fingered hand with palm and thumb (humanoids, apes, minotaurs)."
		tags = PackedStringArray(["humanoid", "ape", "minotaur", "cartoon"])
		params = {"size": [0.4, 3.0, 1.0], "fingers": [0.5, 1.8, 1.0], "curl": [0.0, 1.0, 0.4]}

	func build(g, p):
		var s := pv(p, "size")
		var fl := 0.08 * s * pv(p, "fingers")
		var c := pv(p, "curl")
		g.slot = "skin"
		g.ellipsoid(Vector3(0, 0.05 * s, 0), Vector3(0.06, 0.06, 0.035) * s, Basis(), 6, 4)
		for i in 3:
			var x := (i - 1) * 0.035 * s
			var b := Vector3(x, 0.1 * s, 0)
			g.tube(PackedVector3Array([b, b + Vector3(0, fl * 0.6, c * fl * 0.2), b + Vector3(0, fl * (1.0 - 0.3 * c), c * fl * 0.6)]), PackedFloat32Array([0.017 * s, 0.015 * s, 0.012 * s]), 4, false, true, Vector3.BACK)
		var tb := Vector3(0.05 * s, 0.05 * s, 0.02 * s)
		g.tube(PackedVector3Array([tb, tb + Vector3(0.04 * s, 0.03 * s, 0.03 * s)]), PackedFloat32Array([0.018 * s, 0.013 * s]), 4, false, true, Vector3.BACK)


class HandClaw extends Base:
	func _init():
		id = "hand_claw"; category = "hand"; attach = "tip"; cap = "hand"
		desc = "Clawed hand with three long curved talons (raptors, monsters, sloths)."
		tags = PackedStringArray(["monster", "raptor", "dragon", "menacing"])
		params = {"size": [0.4, 3.0, 1.0], "claw": [0.4, 2.5, 1.0]}

	func build(g, p):
		var s := pv(p, "size")
		var cl := 0.12 * s * pv(p, "claw")
		g.slot = "skin"
		g.ellipsoid(Vector3(0, 0.04 * s, 0), Vector3(0.055, 0.05, 0.035) * s, Basis(), 6, 4)
		g.slot = "claw"
		for i in 3:
			var x := (i - 1) * 0.035 * s
			var pts := curve_points(Vector3(x, 0.07 * s, 0.01 * s), Vector3.UP, Vector3(0, -0.3, 0.9), cl, 4)
			g.tube(pts, taper(0.018 * s, 0.002, 4), 4, false, true, Vector3.BACK)


class HandPincer extends Base:
	func _init():
		id = "hand_pincer"; category = "hand"; attach = "tip"; cap = "grasp"
		desc = "Crab / scorpion pincer with a hinged finger."
		tags = PackedStringArray(["crab", "scorpion", "lobster", "arthropod"])
		params = {"size": [0.4, 3.0, 1.0], "bulk": [0.5, 2.0, 1.0]}
		bones = [{"name": "jaw", "pivot": Vector3(0.03, 0.14, 0), "axis": Vector3.BACK, "angle": -30.0}]

	func build(g, p):
		var s := pv(p, "size")
		var bk := pv(p, "bulk")
		bones[0]["pivot"] = Vector3(0.03 * s, 0.14 * s, 0)
		g.slot = "accent"
		g.ellipsoid(Vector3(0, 0.08 * s, 0), Vector3(0.07 * bk, 0.1, 0.05 * bk) * s, Basis(), 7, 4)
		var fixed := curve_points(Vector3(-0.02 * s, 0.15 * s, 0), Vector3.UP, Vector3(0.3, 0, 0), 0.14 * s, 4)
		g.tube(fixed, taper(0.03 * s * bk, 0.004, 4), 5, false, true, Vector3.BACK)
		g.bone = 1
		var mov := curve_points(Vector3(0.035 * s, 0.14 * s, 0), Vector3.UP, Vector3(-0.35, 0, 0), 0.12 * s, 4)
		g.tube(mov, taper(0.024 * s * bk, 0.004, 4), 5, true, true, Vector3.BACK)
		g.bone = 0


class HandTentacle extends Base:
	func _init():
		id = "hand_tentacle"; category = "hand"; attach = "tip"; cap = "hand"
		desc = "Curling tentacle tip in place of a hand (octopus, aliens)."
		tags = PackedStringArray(["octopus", "alien", "aquatic", "creepy"])
		params = {"size": [0.4, 3.0, 1.0], "curl": [0.0, 1.5, 0.8]}

	func build(g, p):
		var s := pv(p, "size")
		var pts := PackedVector3Array()
		var c := pv(p, "curl")
		for i in 7:
			var t := i / 6.0
			var a := t * c * PI
			pts.append(Vector3(0, sin(a) / maxf(c * PI, 0.01) if c > 0.01 else t, (1.0 - cos(a)) / maxf(c * PI, 0.01)) * 0.3 * s)
		g.slot = "skin"
		g.tube(pts, taper(0.035 * s, 0.006, 7), 5, false, true, Vector3.RIGHT)


class HandMitt extends Base:
	func _init():
		id = "hand_mitt"; category = "hand"; attach = "tip"; cap = "hand"
		desc = "Simple rounded mitten hand with a thumb (cartoon, toy-like)."
		tags = PackedStringArray(["cartoon", "toy", "cute"])
		params = {"size": [0.4, 3.0, 1.0]}

	func build(g, p):
		var s := pv(p, "size")
		g.slot = "skin"
		g.ellipsoid(Vector3(0, 0.08 * s, 0), Vector3(0.07, 0.09, 0.045) * s, Basis(), 7, 4)
		g.ellipsoid(Vector3(0.06 * s, 0.06 * s, 0.02 * s), Vector3(0.025, 0.04, 0.025) * s, Basis(Vector3.BACK, -0.6), 5, 3)
