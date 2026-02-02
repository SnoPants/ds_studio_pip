import sys, os, maya.utils
import maya.mel as mel
import maya.cmds as cmds
import traceback

PIPE_PATH = r"C:\Users\andre\Documents\maya\DS_STUDIO\maya\python"
SHELF_PATH = PIPE_PATH + r"\shelves\shelf_DS.mel"

if PIPE_PATH not in sys.path:
    sys.path.append(PIPE_PATH)

#def load_shelves():
    #mel_path = SHELF_PATH.replace("\\", "/")
    #maya.utils.executeDeferred(lambda: mel.eval(f'source "{mel_path}"')) #currently doesnt work.

def load_pipe_tools():

    cmds.warning("Attempting to load the DS_Studio pipline...")

    try:
        import pipe

        print("DS Studio loaded successfully!")

    except Exception as e:
        tb = traceback.format_exc()
        maya.utils.executeInMainThreadWithResult(cmds.error, f"Failed to load DS Studio tools: {e} \n Traceback: {tb}")

    #load_shelves() #Add a custom shelf.

maya.utils.executeDeferred(load_pipe_tools)

# Still trying to see if i can autoload a shelf, problem with the current one is that it ported from 2024 so it acts funny anyways.
# check out https://bindpose.com/scripting-custom-shelf-in-maya-python/ this might hel