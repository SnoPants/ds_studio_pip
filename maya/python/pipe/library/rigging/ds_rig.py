import maya.cmds as cmds
import os
from pipe.library.utilities.validate import ds_validate
print("From rigging module - ds_rig.py loaded")

#### Base Rig class
class Rig:
    def __init__(self, name, skeleton=None):
        self.rig_name = name
        #self.skeleton = skeleton

    def run_rig(self, python_script, skeleton_path):
        print(f"Running rig setup for: {self.rig_name}")
        self.import_skeleton(skeleton_path)
        if os.path.exists(python_script):
            with open(python_script, 'r') as file:
                script_content = file.read()
            exec(script_content)
        else:
            raise FileNotFoundError(f"Python script not found: {python_script}")

    def import_skeleton(self, skeleton_path):
        print(f"Importing skeleton for rig: {self.rig_name}")

        if os.path.exists(skeleton_path):
            cmds.file(force=True, new = True)
            cmds.file(skeleton_path, i=True)
        else:
            raise FileNotFoundError(f"Skeleton file not found: {skeleton_path}")
    
#### Builder base class, uses "Abstract Factory Pattern" for building all rig types.
class Builder:
    def __init__(self, name):
        print("Building: ", name)
        self.name = name

    def build(self):
        pass

    def post_build(self):
        pass