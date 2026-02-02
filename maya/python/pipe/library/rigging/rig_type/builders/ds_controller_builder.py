import maya.cmds as cmds

class RigCtrl:
    def __init__(self, name, scale= 1.0, translate=[0,0,0], rotation=[0,0,0]):
        self.name = name
        self.scale = scale
        self.translate = translate
        self.rotation = rotation
        self.color = None
        self.shape = None
        self.type_tag = None

    def _create_ctrl(self):
        print("creating ctrl")
        self.type_tag = 'rig_ctrl'

    def _create_loc(self):
        loc = cmds.spaceLocator(n= f"{self.name}_loc_01")
        loc_grp = cmds.group(loc, n=f"{self.name}_null_01")
        print('scaling ctrl to ',self.scale)
        cmds.setAttr(f"{loc[0]}.localScaleX", 45 + self.scale)
        cmds.setAttr(f"{loc[0]}.localScaleY", 45 + self.scale)
        cmds.setAttr(f"{loc[0]}.localScaleZ", 45 + self.scale)
        self.type_tag = 'temp_ctrl'
        cmds.xform(loc_grp , ws =1 , t= (self.translate[0] , self.translate[1] ,self.translate[2]))
        cmds.xform(loc_grp , ws =1 , ro= (self.rotation[0] , self.rotation[1] ,self.rotation[2]))

        return loc[0], loc_grp

        # Left off here. (Below) - need to add the shape creation and color assignment.

    def _get_shape(self, shape):
        return

    def _replace_ctrl(self, trg):
        return


