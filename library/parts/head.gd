## Horns and ears. Surface frame: +Y out of the body, +Z toward the head, +X lateral.
extends RefCounted

const Base = preload("res://library/part_base.gd")


static func all() -> Array:
	return [HornSpike.new(), HornCurl.new(), HornBull.new(), HornAntler.new(), HornRhino.new(), HornTusk.new(),
		EarPointy.new(), EarRound.new(), EarLong.new(), EarFan.new()]


class HornSpike extends Base:
	func _init():
		id = "horn_spike"; category = "horn"; default_mirror = true
		desc = "Straight or gently curved conical horn."
		tags = PackedStringArray(["goat", "demon", "dinosaur"])
		params = {"length": [0.2, 4.0, 1.0], "thickness": [0.4, 2.5, 1.0], "curve": [-1.0, 1.0, -0.3], "splay": [-1.0, 1.0, 0.2]}
		hint = {"u": 0.9, "theta": 70.0}

	func build(g, p):
		var L := 0.32 * pv(p, "length")
		var dir := Vector3(pv(p, "splay") * 0.5, 1, 0).normalized()
		var pts := curve_points(Vector3(0, -0.03, 0), dir, Vector3(0, 0, pv(p, "curve") * 0.6), L, 5)
		g.slot = "horn"
		g.tube(pts, taper(0.055 * pv(p, "thickness"), 0.004, 5, 0.9), 6, true, true, Vector3.BACK)


class HornCurl extends Base:
	func _init():
		id = "horn_curl"; category = "horn"; default_mirror = true
		desc = "Ram horn spiraling back, down and forward around the ear."
		tags = PackedStringArray(["ram", "sheep", "demon"])
		params = {"size": [0.4, 3.0, 1.0], "turns": [0.4, 1.3, 0.85], "thickness": [0.5, 2.0, 1.0], "drift": [0.0, 1.0, 0.4]}
		hint = {"u": 0.88, "theta": 60.0}

	func build(g, p):
		var R := 0.12 * pv(p, "size")
		var turns := pv(p, "turns")
		var n := 14
		var pts := PackedVector3Array()
		for i in n:
			var t := float(i) / (n - 1)
			var a := t * turns * TAU
			var r := R * (1.0 - 0.45 * t)
			pts.append(Vector3(t * pv(p, "drift") * 0.25 * pv(p, "size"), r * sin(a), -R + r * cos(a) + (R - r) * 0.0) + Vector3(0, -0.02, 0))
		g.slot = "horn"
		g.tube(pts, taper(0.055 * pv(p, "thickness") * pv(p, "size"), 0.008, n), 6, true, true, Vector3.RIGHT)


class HornBull extends Base:
	func _init():
		id = "horn_bull"; category = "horn"; default_mirror = true
		desc = "Bull / buffalo horn sweeping outward then curving up and forward."
		tags = PackedStringArray(["bull", "bovine", "minotaur", "buffalo"])
		params = {"length": [0.3, 3.0, 1.0], "thickness": [0.5, 2.0, 1.0], "rise": [-0.5, 1.5, 0.8], "forward": [-1.0, 1.0, 0.4]}
		hint = {"u": 0.9, "theta": 40.0}

	func build(g, p):
		var L := 0.45 * pv(p, "length")
		var pts := curve_points(Vector3(0, -0.03, 0), Vector3(0.3, 1.0, 0.0).normalized().rotated(Vector3.BACK, -0.9), Vector3(-0.2, pv(p, "rise"), pv(p, "forward")), L, 7)
		g.slot = "horn"
		g.tube(pts, taper(0.065 * pv(p, "thickness"), 0.006, 7, 0.8), 6, true, true, Vector3.BACK)


class HornAntler extends Base:
	func _init():
		id = "horn_antler"; category = "horn"; default_mirror = true
		desc = "Branching deer antler with forward tines."
		tags = PackedStringArray(["deer", "moose", "elk", "forest"])
		params = {"size": [0.4, 3.0, 1.0], "tines": [1.0, 4.0, 3.0], "spread": [0.0, 1.0, 0.5]}
		hint = {"u": 0.9, "theta": 70.0}

	func build(g, p):
		var S := pv(p, "size")
		var L := 0.5 * S
		var beam := curve_points(Vector3(0, -0.02, 0), Vector3(pv(p, "spread") * 0.5, 1, -0.4).normalized(), Vector3(0.1, -0.1, 0.35), L, 6)
		g.slot = "horn"
		var r := 0.03 * S
		g.tube(beam, taper(r, r * 0.3, 6), 5, true, true, Vector3.BACK)
		var nt := int(round(pv(p, "tines")))
		for i in nt:
			var k := clampi(1 + int(float(i) * 4.0 / maxf(nt, 1)), 1, 5)
			var base := beam[k]
			var tine := curve_points(base, Vector3(0.1, 0.6, 1).normalized(), Vector3(0, 0.4, 0), L * 0.4 * (1.0 - 0.15 * i), 3)
			g.tube(tine, taper(r * 0.7, r * 0.2, 3), 4, false, true, Vector3.RIGHT)


class HornRhino extends Base:
	func _init():
		id = "horn_rhino"; category = "horn"
		desc = "Thick single nose horn curving back (rhino, triceratops nose)."
		tags = PackedStringArray(["rhino", "dinosaur", "armored"])
		params = {"length": [0.3, 3.0, 1.0], "thickness": [0.5, 2.5, 1.0], "curve": [-1.0, 1.0, -0.5]}
		hint = {"u": 0.97, "theta": 70.0}

	func build(g, p):
		var L := 0.3 * pv(p, "length")
		var pts := curve_points(Vector3(0, -0.03, 0), Vector3(0, 1, 0.2).normalized(), Vector3(0, 0, pv(p, "curve") * 0.6), L, 5)
		g.slot = "horn"
		g.tube(pts, taper(0.085 * pv(p, "thickness"), 0.005, 5, 0.8), 6, true, true, Vector3.BACK)


class HornTusk extends Base:
	func _init():
		id = "horn_tusk"; category = "horn"; orient = "face"; default_mirror = true
		desc = "Ivory tusk curving out and up from the mouth (boar, elephant, walrus when curve is negative)."
		tags = PackedStringArray(["boar", "elephant", "walrus", "orc"])
		params = {"length": [0.3, 3.0, 1.0], "thickness": [0.5, 2.0, 1.0], "curve": [-1.0, 1.0, 0.7]}
		hint = {"u": 0.96, "theta": -40.0}

	func build(g, p):
		var L := 0.3 * pv(p, "length")
		var pts := curve_points(Vector3(0, -0.02, 0), Vector3(0.2, 1.0, -0.5).normalized(), Vector3(0, 0, pv(p, "curve")), L, 6)
		g.slot = "teeth"
		g.tube(pts, taper(0.035 * pv(p, "thickness"), 0.004, 6, 0.9), 6, true, true, Vector3.RIGHT)


# -------------------------------------------------------------------- ears

class EarPointy extends Base:
	func _init():
		id = "ear_pointy"; category = "ear"; cap = "flop"; default_mirror = true
		desc = "Pointed triangular ear (cats, foxes, wolves, goblins)."
		tags = PackedStringArray(["cat", "fox", "wolf", "goblin"])
		params = {"size": [0.3, 3.0, 1.0], "width": [0.4, 2.0, 1.0], "tilt": [-1.0, 1.0, 0.2]}
		hint = {"u": 0.86, "theta": 65.0}

	func build(g, p):
		var s := pv(p, "size")
		var w := 0.07 * s * pv(p, "width")
		var h := 0.2 * s
		var b := Basis(Vector3.RIGHT, -pv(p, "tilt") * 0.6)
		g.slot = "base"
		g.slab(PackedVector3Array([b * Vector3(-w, -0.02, 0), b * Vector3(w, -0.02, 0), b * Vector3(0, h, 0)]), b * Vector3.BACK, 0.03 * s)
		g.slot = "detail"
		g.slab(PackedVector3Array([b * Vector3(-w * 0.55, 0.01, 0.016 * s), b * Vector3(w * 0.55, 0.01, 0.016 * s), b * Vector3(0, h * 0.7, 0.016 * s)]), b * Vector3.BACK, 0.01 * s)


class EarRound extends Base:
	func _init():
		id = "ear_round"; category = "ear"; cap = "flop"; default_mirror = true
		desc = "Round ear (bears, mice, monkeys)."
		tags = PackedStringArray(["bear", "mouse", "monkey", "cute"])
		params = {"size": [0.3, 3.0, 1.0], "tilt": [-1.0, 1.0, 0.0]}
		hint = {"u": 0.86, "theta": 60.0}

	func build(g, p):
		var r := 0.09 * pv(p, "size")
		var b := Basis(Vector3.RIGHT, -pv(p, "tilt") * 0.6)
		var outline := PackedVector3Array()
		var inner := PackedVector3Array()
		for i in 8:
			var a := TAU * i / 8.0
			outline.append(b * Vector3(cos(a) * r, r * 0.8 + sin(a) * r, 0))
			inner.append(b * Vector3(cos(a) * r * 0.6, r * 0.8 + sin(a) * r * 0.6, 0.02 * r / 0.09))
		g.slot = "base"
		g.slab(outline, b * Vector3.BACK, r * 0.35)
		g.slot = "detail"
		g.slab(inner, b * Vector3.BACK, r * 0.1)


class EarLong extends Base:
	func _init():
		id = "ear_long"; category = "ear"; cap = "flop"; default_mirror = true
		desc = "Long upright ear (rabbits, donkeys, jackalopes)."
		tags = PackedStringArray(["rabbit", "donkey", "cute"])
		params = {"size": [0.3, 3.0, 1.0], "length": [0.5, 2.5, 1.0], "tilt": [-1.0, 1.0, 0.3]}
		hint = {"u": 0.85, "theta": 75.0}

	func build(g, p):
		var s := pv(p, "size")
		var h := 0.35 * s * pv(p, "length")
		var w := 0.06 * s
		var b := Basis(Vector3.RIGHT, -pv(p, "tilt") * 0.6)
		var outline := PackedVector3Array()
		var inner := PackedVector3Array()
		for i in 10:
			var a := TAU * i / 10.0
			outline.append(b * Vector3(cos(a) * w, h * 0.5 + sin(a) * h * 0.55, 0))
			inner.append(b * Vector3(cos(a) * w * 0.55, h * 0.5 + sin(a) * h * 0.42, 0.015 * s))
		g.slot = "base"
		g.slab(outline, b * Vector3.BACK, 0.03 * s)
		g.slot = "detail"
		g.slab(inner, b * Vector3.BACK, 0.01 * s)


class EarFan extends Base:
	func _init():
		id = "ear_fan"; category = "ear"; cap = "flop"; default_mirror = true
		desc = "Large flat fan ear on the side of the head (elephants)."
		tags = PackedStringArray(["elephant", "big"])
		params = {"size": [0.4, 3.0, 1.0], "droop": [0.0, 1.0, 0.5]}
		hint = {"u": 0.88, "theta": 20.0}

	func build(g, p):
		# Lies flat against the side of the head: local +X runs down the head side.
		var r := 0.22 * pv(p, "size")
		var d := pv(p, "droop")
		var outline := PackedVector3Array()
		for i in 10:
			var a := TAU * i / 10.0
			outline.append(Vector3(cos(a) * r + d * r * 0.7, 0.04, sin(a) * r * 0.85 - r * 0.55))
		g.slot = "base"
		g.slab(outline, Vector3.UP, 0.035)
