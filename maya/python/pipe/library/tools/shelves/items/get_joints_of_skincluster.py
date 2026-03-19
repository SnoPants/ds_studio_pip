import maya.cmds as cmds
import maya.mel as mel

def checkSel(sel):
    if len(sel) > 1:
        raise Exception('More than one object was selected. Please select one Mesh. This was your selection: {}'.format(sel))
        
def checkCluster(cluster, sel):
    if not cluster:
        raise Exception('This object has no skin cluster. This was your selection: {}'.format(sel))

def run():
    getSel= cmds.ls(sl=True)

    checkSel(getSel)

    mesh= getSel[0]

    getSkinCluster= mel.eval('findRelatedSkinCluster '+mesh)

    checkCluster(getSkinCluster, mesh)
    joints= cmds.skinCluster(getSkinCluster, query=True,inf=True)

    cmds.select(joints)

    if cmds.objExists('TEMP_FINDER_JNTS_set01') == True:
        cmds.delete('TEMP_FINDER_JNTS_set01')

    jntSet = cmds.sets(n=f'{getSel[0]}_JNTS_set')