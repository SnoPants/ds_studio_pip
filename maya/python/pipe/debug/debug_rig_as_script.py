# used for testing pipe enviorment

import importlib
import sys
import library.rigging.ds_rig as ds_rig
import maya.cmds as cmds
import library

import  library.rigging.rig_type.ds_biped_rig as biped
import library.rigging.rig_type.builders.ds_biped_limb_builder as limb
import library.rigging.rig_type.builders.ds_controller_builder as ctrl
import library.utilities.ds_util as util

importlib.reload(ds_rig)
importlib.reload(limb)
importlib.reload(ctrl)
importlib.reload(util)

#-----

sel = cmds.ls(sl=True)

This_Rig = biped.Biped_Rig("This_Rig")
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