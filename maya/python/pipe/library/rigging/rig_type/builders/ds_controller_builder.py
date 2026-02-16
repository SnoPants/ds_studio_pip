import maya.cmds as cmds
import os
import json

# need to figure out a better algorithm for scaling based on distance

class RigCtrl:
    def __init__(self, name = None, scale= 1.0, translate=[0,0,0], rotation=[0,0,0]):
        self.name = name
        self.scale = scale
        self.translate = translate
        self.rotation = rotation
        self.color = None
        self.shape = None

    def _create_ctrl(self):
        print("creating ctrl")

    # Left off here. (Below) - need to add the shape creation and color assignment.
    #TODO: Need to create a JSON or set of py files containing the shape data for the various control types. This will allow us to easily create different types of controls based on the shape data.

    def _create_nurbs_shape(self):
        #temp shape creation. Need to replace with actual shape data.

        json_path = os.path.join(os.path.dirname(__file__), "ds_nurbs_curves.json")

        with open(json_path, "r") as f:
            _SHAPE_DATA = json.load(f)

        # left off here. need to create curve based on _SHAPE_DATA
        shapes = shape = cmds.listRelatives(nurbs, shapes=True)
        return shapes

    def _create_loc(self):
        loc = cmds.spaceLocator(n= f"{self.name}_loc_01")
        loc_grp = cmds.group(loc, n=f"{self.name}_null_01")
        print('scaling ctrl to ',self.scale)
        cmds.setAttr(f"{loc[0]}.localScaleX", 45 + self.scale)
        cmds.setAttr(f"{loc[0]}.localScaleY", 45 + self.scale)
        cmds.setAttr(f"{loc[0]}.localScaleZ", 45 + self.scale)
        cmds.xform(loc_grp , ws =1 , t= (self.translate[0] , self.translate[1] ,self.translate[2]))
        cmds.xform(loc_grp , ws =1 , ro= (self.rotation[0] , self.rotation[1] ,self.rotation[2]))

        return loc[0], loc_grp

    def _set_color_shape(self, shape):
        return

    def replace_with_new_nurbs(self, targets):

        # TODO: Need to figure out scaling here.

        for trg in targets:
            trg_shape = cmds.listRelatives(trg, shapes=True)
            #ctrl_scale = cmds.getAttr(f'{trg}.localScaleX')
            new_shapes = self._create_nurbs_shape()

            #cmds.setAttr(f"{shape}.scaleX", ctrl_scale)
            #cmds.setAttr(f"{shape}.scaleY", ctrl_scale)
            #cmds.setAttr(f"{shape}.scaleZ", ctrl_scale)
            for shape in new_shapes:
                cmds.parent(shape, trg, s=True, r=True)
            
            cmds.delete(trg_shape)
            return
