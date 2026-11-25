## Back, side and tail details plus wings. Surface frame unless noted.
extends RefCounted

const Base = preload("res://library/part_base.gd")


static func all() -> Array:
	return [Spike.new(), Plate.new(), FinDorsal.new(), Crest.new(), Shell.new(), Mane.new(), Frill.new(),
		Antenna.new(), WingBat.new(), WingFeather.new(), TailClub.new(), TailTuft.new(), TailFan.new()]


class Spike extends Base:
	func _init():
		id = "spike"; category = "detail"
		desc = "Single conical spike; place several along the back or tail."
		tags = PackedStringArray(["armored", "dinosaur", "hedgehog", "menacing"])
		params = {"length": [0.2, 4.0, 1.0], "thickness": [0.4, 2.5, 1.0], "lean": [-1.0, 1.0, -0.3]}
		hint = {"u": 0.5, "theta": 90.0}

	func build(g, p):
		var L := 0.2 * pv(p, "length")
		g.slot = "horn"
		g.cone(Vector3(0, -0.02, 0), Vector3(0, L, pv(p, "lean") * L * 0.6), 0.05 * pv(p, "thickness"), 5, Vector3.BACK)


class Plate extends Base:
	func _init():
		id = "plate"; category = "detail"
		desc = "Upright armor plate (stegosaurus back plates)."
		tags = PackedStringArray(["dinosaur", "armored"])
		params = {"height": [0.3, 3.0, 1.0], "width": [0.3, 2.5, 1.0], "lean": [-1.0, 1.0, -0.2]}
		hint = {"u": 0.5, "theta": 90.0}

	func build(g, p):
		var h := 0.28 * pv(p, "height")
		var w := 0.14 * pv(p, "width")
		var l := pv(p, "lean") * h * 0.5
		g.slot = "accent"
		g.slab(PackedVector3Array([Vector3(0, -0.03, -w), Vector3(0, -0.03, w), Vector3(0, h * 0.6, w * 0.8 + l * 0.6), Vector3(0, h, l), Vector3(0, h * 0.6, -w * 0.8 + l * 0.6)]), Vector3.RIGHT, 0.035)


class FinDorsal extends Base:
	func _init():
		id = "fin_dorsal"; category = "detail"
		desc = "Swept dorsal fin or sail (sharks, fish, dimetrodon sail when long)."
		tags = PackedStringArray(["fish", "shark", "aquatic", "sail"])
		params = {"height": [0.3, 3.0, 1.0], "length": [0.3, 3.0, 1.0], "sweep": [-1.0, 1.0, 0.6]}
		hint = {"u": 0.55, "theta": 90.0}

	func build(g, p):
		var h := 0.35 * pv(p, "height")
		var l := 0.25 * pv(p, "length")
		var sw := pv(p, "sweep")
		g.slot = "accent"
		g.slab(PackedVector3Array([Vector3(0, -0.03, -l), Vector3(0, -0.03, l), Vector3(0, h * 0.5, l * 0.4 - sw * l * 0.4), Vector3(0, h, -sw * l), Vector3(0, h * 0.35, -l * 0.9 - sw * l * 0.3)]), Vector3.RIGHT, 0.03)


class Crest extends Base:
	func _init():
		id = "crest"; category = "detail"
		desc = "Spiky zig-zag crest ridge for heads and backs (dragons, iguanas)."
		tags = PackedStringArray(["dragon", "lizard", "punk"])
		params = {"height": [0.3, 3.0, 1.0], "length": [0.3, 3.0, 1.0], "points": [2.0, 7.0, 4.0]}
		hint = {"u": 0.85, "theta": 90.0}

	func build(g, p):
		var h := 0.16 * pv(p, "height")
		var l := 0.2 * pv(p, "length")
		var n := int(round(pv(p, "points")))
		var outline := PackedVector3Array([Vector3(0, -0.03, l)])
		for i in n:
			var z0 := lerpf(l, -l, float(i) / n)
			var z1 := lerpf(l, -l, float(i + 0.6) / n)
			outline.append(Vector3(0, h * (1.0 - 0.3 * float(i) / n), z1 + 0.02))
			outline.append(Vector3(0, h * 0.3, lerpf(z1, lerpf(l, -l, float(i + 1) / n), 0.5)))
		outline.append(Vector3(0, -0.03, -l))
		outline.reverse()
		g.slot = "accent"
		g.slab(outline, Vector3.RIGHT, 0.025)


class Shell extends Base:
	func _init():
		id = "shell"; category = "detail"
		desc = "Domed shell or carapace covering the back (turtles, beetles, armadillos)."
		tags = PackedStringArray(["turtle", "beetle", "armored", "snail"])
		params = {"width": [0.4, 3.0, 1.0], "length": [0.4, 3.0, 1.0], "height": [0.3, 2.0, 1.0]}
		hint = {"u": 0.5, "theta": 90.0}

	func build(g, p):
		var w := 0.45 * pv(p, "width")
		var l := 0.55 * pv(p, "length")
		var h := 0.3 * pv(p, "height")
		g.slot = "accent"
		g.ellipsoid(Vector3(0, -h * 0.35, 0), Vector3(w, h, l), Basis(), 9, 6)
		g.slot = "detail"
		g.ellipsoid(Vector3(0, -h * 0.55, 0), Vector3(w * 1.06, h * 0.25, l * 1.04), Basis(), 9, 3)


class Mane extends Base:
	func _init():
		id = "mane"; category = "detail"
		desc = "Shaggy mane of tufts over the neck or head (lions, minotaurs, horses, punk crests)."
		tags = PackedStringArray(["lion", "horse", "minotaur", "hairy"])
		params = {"size": [0.3, 3.0, 1.0], "length": [0.3, 2.5, 1.0], "spread": [0.2, 1.5, 1.0]}
		hint = {"u": 0.75, "theta": 90.0}

	func build(g, p):
		var s := pv(p, "size")
		var L := 0.18 * pv(p, "length") * s
		var sp := pv(p, "spread")
		g.slot = "accent"
		var k := 0
		for row in 3:
			for i in 5:
				var a := lerpf(-1.2, 1.2, i / 4.0) * sp
				var z := (0.08 - row * 0.09) * s
				var base := Vector3(sin(a) * 0.12 * s, -0.03 + cos(a) * 0.02, z)
				var dir := Vector3(sin(a) * 0.9, cos(a), -0.5).normalized()
				var jitter := 0.8 + 0.4 * fmod(k * 0.618, 1.0)
				g.cone(base, base + dir * L * jitter, 0.05 * s, 4, Vector3.BACK)
				k += 1


class Frill extends Base:
	func _init():
		id = "frill"; category = "detail"
		desc = "Fan-shaped neck frill or bony shield behind the head (triceratops, frilled lizard)."
		tags = PackedStringArray(["dinosaur", "lizard", "display"])
		params = {"size": [0.3, 3.0, 1.0], "tilt": [-1.0, 1.0, 0.4], "scallops": [3.0, 9.0, 6.0]}
		hint = {"u": 0.82, "theta": 90.0}

	func build(g, p):
		var r := 0.35 * pv(p, "size")
		var n := int(round(pv(p, "scallops")))
		var b := Basis(Vector3.RIGHT, -pv(p, "tilt") * 0.8)
		var outline := PackedVector3Array([b * Vector3(r * 0.6, -0.05, 0)])
		for i in n * 2 + 1:
			var a := PI * float(i) / (n * 2)
			var rr := r if i % 2 == 0 else r * 0.82
			outline.append(b * Vector3(cos(a) * rr, sin(a) * rr * 0.9, 0))
		outline.append(b * Vector3(-r * 0.6, -0.05, 0))
		g.slot = "accent"
		g.slab(outline, b * Vector3.BACK, 0.04)


class Antenna extends Base:
	func _init():
		id = "antenna"; category = "detail"; cap = "sway"; default_mirror = true
		desc = "Thin antenna with a bulb tip (insects, aliens)."
		tags = PackedStringArray(["insect", "alien", "cute"])
		params = {"length": [0.3, 3.0, 1.0], "curve": [-1.0, 1.0, -0.4], "bulb": [0.0, 2.0, 1.0]}
		hint = {"u": 0.93, "theta": 75.0}

	func build(g, p):
		var L := 0.4 * pv(p, "length")
		var pts := curve_points(Vector3(0, -0.02, 0), Vector3(0.15, 1, 0.3).normalized(), Vector3(0, 0, pv(p, "curve")), L, 5)
		g.slot = "dark"
		g.tube(pts, taper(0.018, 0.01, 5), 4, false, true, Vector3.BACK)
		var b := 0.035 * pv(p, "bulb")
		if b > 0.003:
			g.slot = "accent"
			g.ellipsoid(pts[4], Vector3.ONE * b, Basis(), 6, 4)


class WingBat extends Base:
	func _init():
		id = "wing_bat"; category = "wing"; cap = "flap"; default_mirror = true
		desc = "Membrane wing with finger struts (bats, dragons, demons)."
		tags = PackedStringArray(["bat", "dragon", "demon", "flying"])
		params = {"span": [0.4, 4.0, 1.0], "chord": [0.4, 2.5, 1.0], "fold": [0.0, 1.0, 0.2]}
		hint = {"u": 0.62, "theta": 55.0}

	func build(g, p):
		var L := 0.9 * pv(p, "span")
		var C := pv(p, "chord")
		var f := pv(p, "fold")
		var bend := Basis(Vector3.BACK, 0.0)
		var tipd := Vector3(0, L, -0.1 * L).rotated(Vector3.RIGHT, -f * 0.9)
		var wrist := Vector3(0, L * 0.45, 0.18 * L * C)
		var pts := [Vector3(0, -0.02, 0.1 * L * C), wrist, tipd,
			Vector3(0, L * 0.72, -0.3 * L * C) + (tipd - Vector3(0, L, -0.1 * L)) * 0.6,
			Vector3(0, L * 0.55, -0.22 * L * C),
			Vector3(0, L * 0.38, -0.42 * L * C),
			Vector3(0, L * 0.18, -0.32 * L * C),
			Vector3(0, -0.02, -0.25 * L * C)]
		g.slot = "accent"
		g.slab(PackedVector3Array(pts), Vector3.RIGHT, 0.015)
		g.slot = "skin"
		g.tube(PackedVector3Array([pts[0], wrist, tipd]), PackedFloat32Array([0.04, 0.03, 0.01]), 5, true, true, Vector3.RIGHT)
		for k in [3, 5]:
			g.tube(PackedVector3Array([wrist, pts[k]]), PackedFloat32Array([0.022, 0.008]), 4, false, true, Vector3.RIGHT)


class WingFeather extends Base:
	func _init():
		id = "wing_feather"; category = "wing"; cap = "flap"; default_mirror = true
		desc = "Feathered bird wing made of layered flight feathers."
		tags = PackedStringArray(["bird", "angel", "griffin", "flying"])
		params = {"span": [0.4, 4.0, 1.0], "chord": [0.4, 2.5, 1.0], "feathers": [3.0, 8.0, 5.0]}
		hint = {"u": 0.62, "theta": 55.0}

	func build(g, p):
		var L := 0.85 * pv(p, "span")
		var C := 0.3 * pv(p, "chord") * L
		var n := int(round(pv(p, "feathers")))
		g.slot = "base"
		g.slab(PackedVector3Array([Vector3(0, -0.02, 0.12 * L), Vector3(0, L * 0.55, 0.1 * L), Vector3(0, L * 0.6, -0.05 * L), Vector3(0, 0, -0.1 * L)]), Vector3.RIGHT, 0.04)
		for i in n:
			var t := float(i) / maxf(n - 1, 1)
			var root := Vector3(0, lerpf(0.1, 0.62, t) * L, lerpf(-0.08, 0.04, t) * L)
			var dirv := Vector3(0, lerpf(0.05, 0.75, t), -lerpf(1.0, 0.45, t)).normalized()
			var flen := C * lerpf(1.0, 1.4, t)
			var side := Vector3(0, -dirv.z, dirv.y) * 0.06 * L
			g.slot = "accent" if i % 2 == 0 else "detail"
			g.slab(PackedVector3Array([root - side, root + side, root + dirv * flen + side * 0.6, root + dirv * flen * 1.12, root + dirv * flen - side * 0.6]), Vector3.RIGHT, 0.012 + 0.002 * i)


class TailClub extends Base:
	func _init():
		id = "tail_club"; category = "tail"; orient = "face"
		desc = "Bony club for the tail tip (ankylosaurus); place at the rear tip (u near 0)."
		tags = PackedStringArray(["dinosaur", "armored"])
		params = {"size": [0.4, 3.0, 1.0], "spikes": [0.0, 1.5, 1.0]}
		hint = {"u": 0.0, "theta": 90.0}

	func build(g, p):
		var r := 0.14 * pv(p, "size")
		g.slot = "horn"
		g.ellipsoid(Vector3(0, r * 0.7, 0), Vector3(r * 1.25, r, r * 0.8), Basis(), 7, 5)
		var sp := pv(p, "spikes")
		if sp > 0.05:
			for side in [-1, 1]:
				g.cone(Vector3(side * r, r * 0.7, 0), Vector3(side * r * (1.6 + 0.5 * sp), r * 0.8, 0), r * 0.3, 4, Vector3.UP)


class TailTuft extends Base:
	func _init():
		id = "tail_tuft"; category = "tail"; orient = "face"
		desc = "Hairy tuft for the tail tip (lions, bulls, donkeys); place at the rear tip (u near 0)."
		tags = PackedStringArray(["lion", "bull", "minotaur", "hairy"])
		params = {"size": [0.3, 3.0, 1.0], "length": [0.3, 2.5, 1.0]}
		hint = {"u": 0.0, "theta": 90.0}

	func build(g, p):
		var s := pv(p, "size")
		var L := 0.2 * s * pv(p, "length")
		g.slot = "accent"
		for i in 7:
			var a := TAU * i / 7.0
			var off := Vector3(cos(a), 0, sin(a)) * 0.03 * s
			var dir := Vector3(cos(a) * 0.4, 1, sin(a) * 0.4).normalized()
			g.cone(off - Vector3(0, 0.02, 0), off + dir * L * (0.8 + 0.3 * (i % 3) / 2.0), 0.045 * s, 4, Vector3.BACK)


class TailFan extends Base:
	func _init():
		id = "tail_fan"; category = "tail"; orient = "face"
		desc = "Spread fan of tail feathers (birds, peacocks) or a fish tail fin; place at the rear tip."
		tags = PackedStringArray(["bird", "peacock", "fish", "display"])
		params = {"size": [0.3, 3.0, 1.0], "spread": [0.3, 1.5, 0.8], "feathers": [3.0, 9.0, 5.0], "lift": [-1.0, 1.0, 0.3]}
		hint = {"u": 0.0, "theta": 90.0}

	func build(g, p):
		var s := pv(p, "size")
		var n := int(round(pv(p, "feathers")))
		var L := 0.4 * s
		for i in n:
			var t := float(i) / maxf(n - 1, 1)
			var a := lerpf(-1.0, 1.0, t) * pv(p, "spread")
			var dirv := Vector3(sin(a), cos(a), pv(p, "lift") * 0.6).normalized()
			var side := dirv.cross(Vector3.BACK).normalized() * 0.05 * s
			g.slot = "accent" if i % 2 == 0 else "base"
			g.slab(PackedVector3Array([-side * 0.3, side * 0.3, dirv * L + side, dirv * L * 1.1, dirv * L - side]), Vector3.BACK, 0.015)
