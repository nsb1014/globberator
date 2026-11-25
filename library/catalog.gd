## Part catalog: loads the Blender-authored parts listed in library/manifest.json.
## Rebuild the assets with `python3 blender/build_library.py`.
extends RefCounted

const GlbPart = preload("res://library/glb_part.gd")
const DIR := "res://library/parts/"

static var _shared = null

var VERSION := "unknown"
var parts := {}
var order: Array[String] = []


static func shared():
	if _shared == null:
		_shared = load("res://library/catalog.gd").new()
	return _shared


func _init() -> void:
	var manifest = JSON.parse_string(FileAccess.get_file_as_string("res://library/manifest.json"))
	if typeof(manifest) != TYPE_DICTIONARY:
		push_error("library/manifest.json missing; run python3 blender/build_library.py")
		return
	VERSION = manifest["library_version"]
	for id in manifest["parts"]:
		var meta = JSON.parse_string(FileAccess.get_file_as_string(DIR + id + ".json"))
		var part = GlbPart.new()
		if typeof(meta) == TYPE_DICTIONARY and part.load_part(meta, DIR + id + ".glb"):
			parts[id] = part
			order.append(id)


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
