''' #Remember pipe init is...#

# pipe/__init__.py

import traceback
import maya.utils

try:
    # Core Maya
    import maya.cmds as cmds

    # DS maya menu
    from pipe import ds_menus
    ds_menus.create_ds_menu()

    # Rigging
    from pipe.library.rigging import ds_rig as ds_rig
    from pipe.library.rigging.rig_type import ds_biped_rig as ds_biped
    from pipe.library.rigging.rig_type.builders import ds_biped_limb_builder as ds_limb
    from pipe.library.rigging.rig_type.builders import ds_controller_builder as ds_ctrl

    # Utilities
    from pipe.library.utilities import ds_maya_math as ds_math
    from pipe.library.utilities import ds_maya_utils as ds_utils

    __all__ = [
        "cmds",
        "ds_rig",
        "ds_biped",
        "ds_limb",
        "ds_ctrl",
        "ds_math",
        "ds_utils",
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
#This_Rig = pipe.rig.Rig("Soldier_Stan")
This_Rig = pipe.ds_biped.Biped_Rig("Soldier_Stan")
This_Rig.limb_biped("R_Brute_Arm", sel[0], sel[1], sel[2])

# Testing Ctrl
sel_ctrl = pipe.cmds.ls(sl=True)
loc = pipe.ds_ctrl.RigCtrl()
loc.shape = 'cube'
loc.color = 'yellow'
newctrl = loc.replace_with_new_nurbs(sel_ctrl)
# Testing Color swap
sel_ctrl = pipe.cmds.ls(sl=True)
swap = pipe.ds_ctrl.RigCtrl()
swap.color = 'green'
swap.set_color_shape(sel_ctrl)

#Test Full Build
pipe.ds_rig.Rig("Test_Rig").run_rig(r"C:\Users\andre\Documents\maya\DS_STUDIO\ds_studio_pip\maya\python\pipe\rigs\test.py", r"C:\Game_Dev\Content_Source\Characters\Test\empty_skeleton_biped.mb")




# Prototyping



    
