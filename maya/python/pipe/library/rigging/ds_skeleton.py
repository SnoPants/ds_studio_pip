import maya.cmds as cmds
import os
from pipe.library.utilities.validate import ds_validate
from pipe.library.utilities.ds_maya_utils import get_centroid, create_joint

print("From rigging module - ds_skeleton.py loaded")

class Skeleton:
    def __init__(self, name, description=None):
        self.skeleton_name = name
        self.hierarchy = description if description else {}

    def build_skeleton(self, skeleton):
        self.create_joints(skeleton)
        self.parent_joints(skeleton)


        # Implementation for building the skeleton goes here

    def validate_skeleton(self):
        print(f"Validating skeleton: {self.skeleton_name}")
        # Implementation for validating the skeleton should go to ds_validate module

    def create_joints(self, skeleton):

        print(f"Creating joints for skeleton: {self.skeleton_name}")

        def joint_position(skeleton, joint):

            if not joint.vertex_ids:
                cmds.warning(f"{joint.name} has no vertices assigned; {joint.name} wil be set at origin.")
                return(0.0, 0.0, 0.0)

            vertices = [f"{skeleton.mesh}.vtx[{index}]" for index in joint.vertex_ids]
            return get_centroid(vertices)

        print(f"Building skeleton for: {self.skeleton_name}")
        built = {}

        for joint in skeleton.joints():
            position = joint_position(skeleton, joint)
            cmds.select(clear= True)
            node = create_joint(tags={"mapperUid": joint.uid})
            node = cmds.rename(node, joint.name)
            cmds.xform(node, worldSpace= True, translation= position)

            built[joint.uid] = node

            cmds.select(clear= True)

        return built

    def parent_joints(self, skeleton):
        print(f"Parenting joints for skeleton: {self.skeleton_name}")
        # Implementation for parenting joints in Maya goes here
        print(skeleton.parent_order())
        for (_, joint), (_, parent_joint) in skeleton.parent_order().items():
            parent_name = parent_joint.name if parent_joint is not None else "World"
            try:
                cmds.parent(joint.name, parent_name)
            except Exception as e:
                cmds.warning(f"Failed to parent {joint.name} to {parent_name}: {e}")

    def orient_joints(self):
        print(f"Orienting joints for skeleton: {self.skeleton_name}")
        # Implementation for orienting joints in Maya goes here

    def add_metadata(self):
        print(f"Adding metadata for skeleton: {self.skeleton_name}")
        # Implementation for adding metadata to joints in Maya goes here

    def build_result(self):
        print(f"Building result for skeleton: {self.skeleton_name}")
        # Implementation for building the final result of the skeleton goes here


    