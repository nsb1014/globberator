## Part catalog. Library version bumps whenever part geometry or params change
## in a way that alters existing recipes.
extends RefCounted

const VERSION := "1.0.0"
const SOURCES := [
	preload("res://library/parts/face.gd"),
	preload("res://library/parts/head.gd"),
	preload("res://library/parts/body.gd"),
	preload("res://library/parts/tips.gd"),
]

static var _shared = null

var parts := {}
var order: Array[String] = []


static func shared():
	if _shared == null:
		_shared = load("res://library/catalog.gd").new()
	return _shared


func _init() -> void:
	for src in SOURCES:
		for part in src.all():
			assert(not parts.has(part.id), "duplicate part id " + part.id)
			parts[part.id] = part
			order.append(part.id)


func get_part(id: String):
	return parts.get(id, null)


func by_category() -> Dictionary:
	var out := {}
	for id in order:
		var c: String = parts[id].category
		if not out.has(c):
			out[c] = []
		out[c].append(id)
	return out


func describe() -> Dictionary:
	var list := []
	for id in order:
		list.append(parts[id].describe())
	return {"library_version": VERSION, "parts": list}
