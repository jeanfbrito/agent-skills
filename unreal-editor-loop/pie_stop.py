"""Stop Play In Editor. Run in the editor: py "<absolute path>/pie_stop.py" """
import unreal

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.log("PIE_STOP: stop requested")
