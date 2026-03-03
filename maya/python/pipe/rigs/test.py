import pipe
import maya.cmds as cmds

This_Rig = pipe.ds_biped.Biped_Rig("Soldier_Stan")
This_Rig.limb_biped("L_Arm", 'l_shoulder', 'l_wrist', 'l_arm_end')