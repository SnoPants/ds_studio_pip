import sys, os, maya.utils
import maya.mel as mel
import maya.cmds as cmds
import traceback

def load_pipe_tools():
# --- Going to have to change this eventually to dynamically find where this is installed
    PIPE_PATH = r"C:\Users\v-adespain\Documents\GitHub\ds_studio_pip\maya\python"
    SHELF_PATH = PIPE_PATH + r"\shelves\shelf_DS.mel"

    if os.path.exists(PIPE_PATH) == False:
        PIPE_PATH = r"C:\Users\andre\Documents\maya\DS_STUDIO\ds_studio_pip\maya\python"
        if os.path.exists(PIPE_PATH) == False:
            raise ValueError(f"The pathing to DS_STUDIO pipeline, does not exist. {PIPE_PATH}")
        
    print("DS_STUDIO pipeline pathing exists ...")

# ---

    if PIPE_PATH not in sys.path:
        sys.path.append(PIPE_PATH)

    cmds.warning("Attempting to load the DS_Studio pipeline...")

    try:
        import pipe

        print("DS Studio loaded successfully!")

    except Exception as e:
        tb = traceback.format_exc()
        maya.utils.executeInMainThreadWithResult(cmds.error, f"Failed to load DS Studio tools: {e} \n Traceback: {tb}")

    #load_shelves() #Add a custom shelf.

maya.utils.executeDeferred(load_pipe_tools)

# Still trying to see if i can autoload a shelf, problem with the current one is that it ported from 2024 so it acts funny anyways.
# check out https://bindpose.com/scripting-custom-shelf-in-maya-python/ this might help

# TODO:
# new idea, we make a repo of .py files that will autoload into a shelf if a shelf doesnt already exist with other basic Maya commands.
# need to grab py files from work. 

# mel commands to add to shelf for reference.
#menuItemToShelf "MayaWindow|mainSelectMenu|menuItem2259";
#menuItemToShelf "MayaWindow|mainDisplayMenu|objectsCompItem|toggleAxisItem";
#menuItemToShelf "MayaWindow|mainDisplayMenu|objectsCompItem|toggleAxisItem";

