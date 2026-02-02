# used for testing pipe enviorment

import importlib
import sys
import library.rigging.ds_rig as ds_rig
import maya.cmds as cmds
import library

import library.rigging.builders.ds_limb_builder as limb
import library.rigging.builders.ds_limb_kinematics as kine
import library.rigging.builders.ds_controller_builder as ctrl
import library.utilities.ds_util as util

importlib.reload(ds_rig)
importlib.reload(limb)
importlib.reload(kine)
importlib.reload(ctrl)
importlib.reload(util)

#-----

sel = cmds.ls(sl=True)

This_Rig = ds_rig.Biped_Rig("This_Rig")
This_Rig.limb_biped("L_Arm", sel[0], sel[1]) 

#-----



# would be really cool if i got this to work
'''def reload_package(package):
    """Reloads all submodules of a given package recursively."""
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if name in sys.modules:
            print(f"Reloading: {loader}_{name}_{is_pkg}")
            importlib.reload(sys.modules[name])
        else:
            __import__(name)
            
reload_package(library)'''