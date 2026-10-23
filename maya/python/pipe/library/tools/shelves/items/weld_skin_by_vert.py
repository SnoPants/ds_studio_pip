import maya.cmds as cmd
import maya.mel as mel

def weldTheVerts():
    verts = cmd.ls(os= True, fl = True)
    cmd.select(verts[0])
    mel.eval('artAttrSkinWeightCopy')
    cmd.select(verts)
    this = mel.eval('artAttrSkinWeightPaste')
    print(verts)

weldTheVerts()