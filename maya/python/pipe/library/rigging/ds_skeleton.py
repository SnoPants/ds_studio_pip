import maya.cmds as cmds
import os
from pipe.library.utilities.validate import ds_validate
print("From rigging module - ds_skeleton.py loaded")

class Skeleton:
    def __init__(self, name, description=None):
        self.skeleton_name = name
        self.hierarchy = description if description else {}

    def build_skeleton(self):
        print(f"Building skeleton: {self.skeleton_name}")
        # Implementation for building the skeleton goes here

    def validate_skeleton(self):
        print(f"Validating skeleton: {self.skeleton_name}")
        # Implementation for validating the skeleton should go to ds_validate module

    def create_joints(self):
        print(f"Creating joints for skeleton: {self.skeleton_name}")
        # Implementation for creating joints in Maya goes here

    def parent_joints(self):
        print(f"Parenting joints for skeleton: {self.skeleton_name}")
        # Implementation for parenting joints in Maya goes here

    def orient_joints(self):
        print(f"Orienting joints for skeleton: {self.skeleton_name}")
        # Implementation for orienting joints in Maya goes here

    def add_metadata(self):
        print(f"Adding metadata for skeleton: {self.skeleton_name}")
        # Implementation for adding metadata to joints in Maya goes here

    def build_result(self):
        print(f"Building result for skeleton: {self.skeleton_name}")
        # Implementation for building the final result of the skeleton goes here


    