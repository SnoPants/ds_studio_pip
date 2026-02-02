import maya.cmds as cmds
from library.utilities.validate.ds_validate import validate_chain

def get_selected_joints_hier(chain, start, end):

    chain_list = []

    # Need to add listRelatives command here for chain building to be more robust. 
    # including anytime that I have called it prior to calling this function in the limb builder code.

    for joint in chain:
        child = cmds.listRelatives(joint, children= True, type='joint', ad= True)
        if child and joint != start:
            if end in child:
                chain_list.append(joint)
            else:
                continue

    validate_chain(chain_list)
    chain_heir = [start] + chain_list + [end]

    return chain_heir

