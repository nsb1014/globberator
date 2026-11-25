@tool
extends EditorScenePostImport

# Godot 4.3 drops custom glTF node extras. Preserve the generated bindings in
# the imported scene so exported games never need to open the source GLB.
func _post_import(scene: Node) -> Object:
	var file := FileAccess.open(get_source_file(),FileAccess.READ)
	file.seek(12)
	var length := file.get_32()
	if file.get_32() == 0x4e4f534a:
		var document: Dictionary = JSON.parse_string(file.get_buffer(length).get_string_from_utf8())
		var profile := preload("res://ground_gait.gd").profile_from_nodes(document["nodes"])
		if not profile.is_empty():
			scene.set_meta("ground_gait",profile)
	return scene
