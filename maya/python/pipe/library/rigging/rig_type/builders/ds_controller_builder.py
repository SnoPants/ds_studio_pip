import maya.cmds as cmds
import os
import json

# need to figure out a better algorithm for scaling based on distance
class RigCtrl:
    def __init__(self, name = "NULL", scale= 1.0, translate=[0,0,0], rotation=[0,0,0]):
        self.name = name
        self.scale = scale
        self.translate = translate
        self.rotation = rotation
        self.color = None
        self.shape = None

    # Left off here. (Below) - need to add the shape creation and color assignment.
    #TODO: Need to create a JSON or set of py files containing the shape data for the various control types. This will allow us to easily create different types of controls based on the shape data.

    def _create_nurbs_ctrl(self):

        def _load_nurbs_data():
            global _NURBS_DATA
            _NURBS_DATA = None

            if _NURBS_DATA:
                return _NURBS_DATA

            json_path = os.path.join(os.path.dirname(__file__), "ds_nurbs_curves.json")

            with open(json_path, "r") as f:
                _NURBS_DATA = json.load(f)

            return _NURBS_DATA
        
        data = _load_nurbs_data()
        #  Debug for json loading
        print(data)
        print('nurbs controls: ', data["controls"]["sphere"])

        if self.shape not in data["controls"]:
            raise ValueError(f"Shape '{self.shape}' not found in nurbs data.") # circle is not working.
        
        shape_data = data["controls"][self.shape]
        print(self.shape)
        ctrl = cmds.createNode('transform', name=self.name)

        for i, curve_data in enumerate(shape_data["curves"]):
            curve_name = f"{self.name}_shape_{i+1:02d}"
            nurbs_curve = cmds.curve(n=curve_name,
                                     d=curve_data["degree"],
                                     p=curve_data["points"],
                                     k=curve_data["knots"],
                                     per=curve_data["periodic"]
                                     )

            shape_node = cmds.listRelatives(nurbs_curve, shapes=True)[0]
            cmds.parent(shape_node, ctrl, shape=True, relative=True)
            cmds.delete(nurbs_curve)

        # left off here. need to create curve based on _SHAPE_DATA
        return ctrl

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
            new_ctrl = self._create_nurbs_ctrl()
            new_shapes = cmds.listRelatives(new_ctrl, shapes=True)
            #cmds.setAttr(f"{shape}.scaleX", ctrl_scale)
            #cmds.setAttr(f"{shape}.scaleY", ctrl_scale)
            #cmds.setAttr(f"{shape}.scaleZ", ctrl_scale)
            for shape in new_shapes:
                cmds.parent(shape, trg, s=True, r=True)
            
            cmds.delete(trg_shape)
            return
