''' #Remember pipe init is...#

import traceback
import maya.utils

try:
    # Core Maya
    import maya.cmds as cmds

    # Rigging
    from pipe.library.rigging import ds_rig
    from pipe.library.rigging.rig_type import ds_biped_rig as biped
    from pipe.library.rigging.rig_type.builders import ds_biped_limb_builder as limb
    from pipe.library.rigging.rig_type.builders import ds_controller_builder as ctrl

    # Utilities
    from pipe.library.utilities import ds_maya_math as math
    from pipe.library.utilities import ds_maya_utils as utils

    __all__ = [
        "cmds",
        "ds_rig",
        "biped",
        "limb",
        "ctrl",
        "math",
        "utils",
    ]

    print(f"Successfully imported: {__all__}")

except Exception as e:
    tb = traceback.format_exc()
    try:
        import maya.cmds as cmds
        maya.utils.executeInMainThreadWithResult(cmds.error, f"Failed to load DS Studio tools: {e}\n{tb}")
    except Exception:
        # last resort: print to script editor
        print(f"Failed to load DS Studio tools: {e}\n{tb}")

'''
#-----

import pipe

# Testing Limb Rig
sel = pipe.cmds.ls(sl=True)
This_Rig = pipe.biped.Biped_Rig("This_Rig")
This_Rig.limb_biped("R_Brute_Arm", sel[0], sel[1], sel[2])

# Testing Ctrl
sel_ctrl = pipe.cmds.ls(sl=True)
loc = pipe.ctrl.RigCtrl()
loc.shape = 'sphere'
#loc.name = 'test'
newctrl = loc.replace_with_new_nurbs(sel_ctrl)