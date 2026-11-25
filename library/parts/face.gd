## Eyes, mouths and noses. All use the "face" frame: +Y out of the head, +Z up.
extends RefCounted

const Base = preload("res://library/part_base.gd")


static func all() -> Array:
	return [EyeRound.new(), EyeBug.new(), EyeSlit.new(), EyeStalk.new(), EyeCyclops.new(), EyeBead.new(),
		MouthJaws.new(), MouthBeak.new(), MouthSnout.new(), MouthSmile.new(), MouthMandibles.new(), MouthTrunk.new(),
		NoseButton.new()]


class EyeRound extends Base:
	func _init():
		id = "eye_round"; category = "eye"; orient = "face"; cap = "look"; default_mirror = true
		desc = "Round cartoon eye: white ball with a black pupil and optional brow."
		tags = PackedStringArray(["cute", "mammal", "cartoon"])
		params = {"size": [0.4, 3.0, 1.0], "pupil": [0.3, 0.9, 0.55], "brow": [0.0, 1.0, 0.0]}
		hint = {"u": 0.93, "theta": 35.0}

	func build(g, p):
		var s := pv(p, "size")
		var r := 0.08 * s
		g.slot = "white"
		g.ellipsoid(Vector3(0, 0.25 * r, 0), Vector3(r, r, r), Basis(), 8, 5)
		g.slot = "black"
		var pr := r * pv(p, "pupil") * 0.65
		g.ellipsoid(Vector3(0, 1.08 * r, 0), Vector3(pr, r * 0.22, pr), Basis(), 6, 3)
		if pv(p, "brow") > 0.05:
			g.slot = "accent"
			var b := pv(p, "brow")
			g.box(Vector3(0, 0.7 * r, 0.95 * r), Vector3(2.2 * r, 0.5 * r, 0.35 * r * (0.5 + b)), Basis(Vector3.FORWARD, 0.15 * b))


class EyeBug extends Base:
	func _init():
		id = "eye_bug"; category = "eye"; orient = "face"; cap = "look"; default_mirror = true
		desc = "Large faceted compound eye, dark and glossy (insects, aliens)."
		tags = PackedStringArray(["insect", "alien", "creepy"])
		params = {"size": [0.4, 3.0, 1.0], "bulge": [0.4, 1.2, 0.8]}
		hint = {"u": 0.93, "theta": 30.0}

	func build(g, p):
		var r := 0.13 * pv(p, "size")
		g.slot = "dark"
		g.ellipsoid(Vector3.ZERO, Vector3(r, r * pv(p, "bulge"), r * 1.1), Basis(), 7, 4)
		g.slot = "white"
		g.ellipsoid(Vector3(r * 0.3, r * pv(p, "bulge") * 0.95, r * 0.35), Vector3.ONE * r * 0.15, Basis(), 4, 2)


class EyeSlit extends Base:
	func _init():
		id = "eye_slit"; category = "eye"; orient = "face"; cap = "look"; default_mirror = true
		desc = "Reptile eye: colored iris with a vertical slit pupil."
		tags = PackedStringArray(["reptile", "cat", "menacing"])
		params = {"size": [0.4, 3.0, 1.0], "slit": [0.1, 0.6, 0.25]}
		hint = {"u": 0.92, "theta": 40.0}

	func build(g, p):
		var r := 0.075 * pv(p, "size")
		g.slot = "eye"
		g.ellipsoid(Vector3(0, 0.2 * r, 0), Vector3(r, r, r), Basis(), 8, 5)
		g.slot = "black"
		g.box(Vector3(0, 1.12 * r, 0), Vector3(r * pv(p, "slit"), r * 0.12, r * 1.5))


class EyeStalk extends Base:
	func _init():
		id = "eye_stalk"; category = "eye"; orient = "face"; cap = "look"; default_mirror = true
		desc = "Eyeball on a bendy stalk (snails, crabs, aliens)."
		tags = PackedStringArray(["alien", "mollusk", "silly"])
		params = {"size": [0.4, 3.0, 1.0], "height": [0.1, 0.8, 0.3], "lean": [-0.6, 0.6, 0.2]}
		hint = {"u": 0.95, "theta": 70.0}

	func build(g, p):
		var s := pv(p, "size")
		var h := pv(p, "height")
		var pts := curve_points(Vector3(0, -0.02, 0), Vector3.UP, Vector3(0, 0, pv(p, "lean")), h, 4)
		g.slot = "skin"
		g.tube(pts, taper(0.035 * s, 0.022 * s, 4), 5, false, false, Vector3.BACK)
		var top := pts[3]
		var r := 0.07 * s
		g.slot = "white"
		g.ellipsoid(top + Vector3(0, r * 0.6, 0), Vector3.ONE * r, Basis(), 7, 4)
		g.slot = "black"
		g.ellipsoid(top + Vector3(0, r * 1.45, 0), Vector3(r * 0.4, r * 0.2, r * 0.4), Basis(), 5, 3)


class EyeCyclops extends Base:
	func _init():
		id = "eye_cyclops"; category = "eye"; orient = "face"; cap = "look"; default_mirror = false
		desc = "Single large central eye with a heavy brow."
		tags = PackedStringArray(["monster", "alien"])
		params = {"size": [0.5, 3.0, 1.0], "pupil": [0.3, 0.9, 0.5]}
		hint = {"u": 0.95, "theta": 60.0}

	func build(g, p):
		var r := 0.15 * pv(p, "size")
		g.slot = "white"
		g.ellipsoid(Vector3(0, 0.2 * r, 0), Vector3.ONE * r, Basis(), 9, 6)
		g.slot = "eye"
		var ir := r * pv(p, "pupil")
		g.ellipsoid(Vector3(0, 1.05 * r, 0), Vector3(ir, r * 0.2, ir), Basis(), 8, 3)
		g.slot = "black"
		g.ellipsoid(Vector3(0, 1.2 * r, 0), Vector3(ir * 0.5, r * 0.15, ir * 0.5), Basis(), 6, 3)
		g.slot = "accent"
		g.box(Vector3(0, 0.6 * r, 1.0 * r), Vector3(2.4 * r, 0.6 * r, 0.4 * r))


class EyeBead extends Base:
	func _init():
		id = "eye_bead"; category = "eye"; orient = "face"; cap = "look"; default_mirror = true
		desc = "Tiny black bead eye with a highlight (birds, rodents, small critters)."
		tags = PackedStringArray(["bird", "rodent", "small"])
		params = {"size": [0.4, 3.0, 1.0]}
		hint = {"u": 0.93, "theta": 30.0}

	func build(g, p):
		var r := 0.045 * pv(p, "size")
		g.slot = "black"
		g.ellipsoid(Vector3(0, 0.3 * r, 0), Vector3.ONE * r, Basis(), 6, 4)
		g.slot = "white"
		g.ellipsoid(Vector3(r * 0.35, r * 1.15, r * 0.4), Vector3.ONE * r * 0.25, Basis(), 4, 2)


# ---------------------------------------------------------------- mouths

class MouthJaws extends Base:
	func _init():
		id = "mouth_jaws"; category = "mouth"; orient = "face"; cap = "mouth"
		desc = "Toothy predator jaws (upper and hinged lower jaw)."
		tags = PackedStringArray(["predator", "reptile", "dinosaur", "menacing"])
		params = {"length": [0.4, 2.5, 1.0], "width": [0.5, 2.0, 1.0], "teeth": [0.0, 1.5, 1.0]}
		hint = {"u": 0.97, "theta": -20.0}
		bones = [{"name": "jaw", "pivot": Vector3(0, -0.05, -0.02), "axis": Vector3.RIGHT, "angle": -38.0}]

	func build(g, p):
		var L := 0.32 * pv(p, "length")
		var W := pv(p, "width")
		var up := PackedVector3Array([Vector3(0, -0.06, 0.03), Vector3(0, L * 0.5, 0.025), Vector3(0, L, 0.0)])
		g.slot = "base"
		g.tube(up, PackedFloat32Array([0.11, 0.09, 0.05]), 6, false, true, Vector3.BACK, Vector2(W, 0.55))
		var tn := int(round(3 * pv(p, "teeth")))
		g.slot = "teeth"
		for side in [-1, 1]:
			for i in tn:
				var y := L * (0.25 + 0.65 * float(i) / maxi(tn, 1))
				var x: float = side * W * lerpf(0.085, 0.04, y / L)
				g.cone(Vector3(x, y, -0.015), Vector3(x, y, -0.06), 0.014, 4, Vector3.RIGHT)
		g.bone = 1
		var lo := PackedVector3Array([Vector3(0, -0.06, -0.05), Vector3(0, L * 0.5, -0.06), Vector3(0, L * 0.92, -0.055)])
		g.slot = "detail"
		g.tube(lo, PackedFloat32Array([0.09, 0.07, 0.04]), 6, false, true, Vector3.BACK, Vector2(W, 0.4))
		g.slot = "teeth"
		for side in [-1, 1]:
			for i in maxi(tn - 1, 0):
				var y := L * (0.35 + 0.5 * float(i) / maxi(tn - 1, 1))
				var x: float = side * W * lerpf(0.07, 0.035, y / L)
				g.cone(Vector3(x, y, -0.04), Vector3(x, y, -0.005), 0.012, 4, Vector3.RIGHT)
		g.bone = 0


class MouthBeak extends Base:
	func _init():
		id = "mouth_beak"; category = "mouth"; orient = "face"; cap = "mouth"
		desc = "Bird beak, optionally hooked (parrots, raptors) or straight."
		tags = PackedStringArray(["bird", "turtle", "squid"])
		params = {"length": [0.3, 3.0, 1.0], "width": [0.5, 2.0, 1.0], "hook": [0.0, 1.0, 0.3]}
		hint = {"u": 0.98, "theta": -10.0}
		bones = [{"name": "jaw", "pivot": Vector3(0, -0.02, -0.03), "axis": Vector3.RIGHT, "angle": -25.0}]

	func build(g, p):
		var L := 0.28 * pv(p, "length")
		var W := pv(p, "width")
		var hk := pv(p, "hook")
		var up := curve_points(Vector3(0, -0.04, 0.01), Vector3(0, 1, 0.05), Vector3(0, 0, -0.5 * hk), L, 5)
		g.slot = "horn"
		g.tube(up, taper(0.085, 0.005, 5, 0.8), 6, false, true, Vector3.BACK, Vector2(W, 0.8))
		g.bone = 1
		var lo := curve_points(Vector3(0, -0.04, -0.04), Vector3(0, 1, 0.05), Vector3.ZERO, L * 0.72, 4)
		g.tube(lo, taper(0.06, 0.005, 4), 6, false, true, Vector3.BACK, Vector2(W * 0.9, 0.5))
		g.bone = 0


class MouthSnout extends Base:
	func _init():
		id = "mouth_snout"; category = "mouth"; orient = "face"; cap = "mouth"
		desc = "Blunt mammal muzzle with nostrils and a small lower jaw (bovines, pigs, dogs, bears)."
		tags = PackedStringArray(["mammal", "bovine", "pig", "dog"])
		params = {"length": [0.3, 2.5, 1.0], "width": [0.5, 2.2, 1.0], "nostrils": [0.0, 2.0, 1.0]}
		hint = {"u": 0.97, "theta": -15.0}
		bones = [{"name": "jaw", "pivot": Vector3(0, -0.02, -0.06), "axis": Vector3.RIGHT, "angle": -28.0}]

	func build(g, p):
		var L := 0.14 * pv(p, "length")
		var W := pv(p, "width")
		g.slot = "detail"
		g.ellipsoid(Vector3(0, L * 0.7, 0.0), Vector3(0.12 * W, L + 0.03, 0.1), Basis(), 8, 5)
		var nr := 0.022 * pv(p, "nostrils")
		if nr > 0.002:
			g.slot = "dark"
			for side in [-1, 1]:
				g.ellipsoid(Vector3(side * 0.05 * W, L * 1.65 + 0.02, 0.025), Vector3(nr, nr * 0.6, nr * 0.8), Basis(), 5, 3)
		g.bone = 1
		g.slot = "detail"
		g.ellipsoid(Vector3(0, L * 0.6, -0.1), Vector3(0.085 * W, L * 0.8, 0.04), Basis(), 6, 3)
		g.bone = 0


class MouthSmile extends Base:
	func _init():
		id = "mouth_smile"; category = "mouth"; orient = "face"; cap = "mouth"
		desc = "Flat friendly mouth with curved lips (cartoon, humanoid, frog)."
		tags = PackedStringArray(["cartoon", "humanoid", "frog", "friendly"])
		params = {"width": [0.4, 3.0, 1.0], "curve": [-1.0, 1.0, 0.5], "lips": [0.3, 2.0, 1.0]}
		hint = {"u": 0.97, "theta": -35.0}
		bones = [{"name": "jaw", "pivot": Vector3(0, -0.03, -0.02), "axis": Vector3.RIGHT, "angle": -22.0}]

	func build(g, p):
		var W := 0.12 * pv(p, "width")
		var c := pv(p, "curve")
		var lr := 0.018 * pv(p, "lips")
		var upper := PackedVector3Array()
		var lower := PackedVector3Array()
		for i in 7:
			var x := lerpf(-W, W, i / 6.0)
			var z := c * 1.2 * (x * x) / maxf(W, 0.01)
			upper.append(Vector3(x, 0.01 - absf(x) * 0.3, z + lr * 0.4))
			lower.append(Vector3(x, 0.005 - absf(x) * 0.3, z - lr * 1.4))
		g.slot = "dark"
		g.slab(PackedVector3Array([upper[0], upper[3], upper[6], lower[6], lower[3], lower[0]]), Vector3.UP, 0.02)
		g.slot = "accent"
		g.tube(upper, taper(lr * 0.6, lr * 0.6, 7), 4, true, true, Vector3.UP)
		g.bone = 1
		g.tube(lower, taper(lr * 0.6, lr * 0.6, 7), 4, true, true, Vector3.UP)
		g.bone = 0


class MouthMandibles extends Base:
	func _init():
		id = "mouth_mandibles"; category = "mouth"; orient = "face"; cap = "mouth"
		desc = "Pair of curved insect mandibles that open sideways."
		tags = PackedStringArray(["insect", "arachnid", "alien", "menacing"])
		params = {"length": [0.4, 2.5, 1.0], "curl": [0.0, 1.5, 0.7], "spread": [0.5, 2.0, 1.0]}
		hint = {"u": 0.98, "theta": -20.0}
		bones = [
			{"name": "jaw", "pivot": Vector3(0.05, 0.0, -0.01), "axis": Vector3.BACK, "angle": 25.0},
			{"name": "jaw2", "pivot": Vector3(-0.05, 0.0, -0.01), "axis": Vector3.BACK, "angle": -25.0},
		]

	func build(g, p):
		var L := 0.22 * pv(p, "length")
		var sp := 0.05 * pv(p, "spread")
		g.slot = "horn"
		for side in [1, -1]:
			g.bone = 1 if side == 1 else 2
			var pts := curve_points(Vector3(side * sp, -0.03, -0.01), Vector3(side * 0.25, 1, 0).normalized(), Vector3(-side * pv(p, "curl"), 0, 0), L, 5)
			g.tube(pts, taper(0.035, 0.004, 5), 5, true, true, Vector3.BACK)
		g.bone = 0


class MouthTrunk extends Base:
	func _init():
		id = "mouth_trunk"; category = "mouth"; orient = "face"; cap = "mouth"
		desc = "Long flexible trunk or proboscis that curls up when 'opened'."
		tags = PackedStringArray(["elephant", "tapir", "alien"])
		params = {"length": [0.3, 3.0, 1.0], "thickness": [0.4, 2.0, 1.0], "droop": [0.0, 1.5, 1.0]}
		hint = {"u": 0.97, "theta": 0.0}
		bones = [{"name": "jaw", "pivot": Vector3(0, 0.25, -0.12), "axis": Vector3.RIGHT, "angle": 50.0}]

	func build(g, p):
		var L := 0.55 * pv(p, "length")
		var T := pv(p, "thickness")
		var pts := curve_points(Vector3(0, -0.05, 0), Vector3.UP, Vector3(0, -0.3, -pv(p, "droop")), L, 8)
		var rad := taper(0.08 * T, 0.035 * T, 8)
		bones[0]["pivot"] = pts[3]
		g.slot = "skin"
		g.tube(pts.slice(0, 4), rad.slice(0, 4), 6, false, false, Vector3.BACK)
		g.bone = 1
		g.tube(pts.slice(3, 8), rad.slice(3, 8), 6, false, true, Vector3.BACK)
		g.bone = 0


class NoseButton extends Base:
	func _init():
		id = "nose_button"; category = "nose"; orient = "face"
		desc = "Small round nose (cartoon mammals)."
		tags = PackedStringArray(["cute", "mammal", "cartoon"])
		params = {"size": [0.4, 3.0, 1.0]}
		hint = {"u": 0.99, "theta": 20.0}

	func build(g, p):
		var r := 0.045 * pv(p, "size")
		g.slot = "dark"
		g.ellipsoid(Vector3(0, 0.3 * r, 0), Vector3(r * 1.2, r, r * 0.9), Basis(), 6, 4)
