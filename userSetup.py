import os
import sys
import traceback
import maya.utils
import maya.cmds as cmds

def load_pipe_tools():
    scripts_dir = cmds.internalVar(userScriptDir=True)
    root = os.path.join(scripts_dir, "DS_STUDIO", "ds_studio_pip")
    pipe_path = os.path.join(root, "maya", "python")

    if not os.path.exists(pipe_path):
        cmds.warning(f"DS Studio path does not exist: {pipe_path}")
        return

    if pipe_path not in sys.path:
        sys.path.append(pipe_path)

    try:
        import pipe
        print("DS Studio loaded successfully!")
    except Exception as e:
        tb = traceback.format_exc()
        maya.utils.executeInMainThreadWithResult(
            cmds.error,
            f"Failed to load DS Studio tools: {e}\nTraceback: {tb}"
        )

maya.utils.executeDeferred(load_pipe_tools)