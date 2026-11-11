"""Start Play In Editor. Run in the editor: py "<absolute path>/pie_start.py" """
import unreal

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
unreal.log("PIE_START: play requested")
