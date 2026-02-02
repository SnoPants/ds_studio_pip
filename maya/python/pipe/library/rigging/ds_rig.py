import maya.cmds as cmds
from library.utilities.validate import ds_validate
print("From rigging module - ds_rig.py loaded")

#### Base Rig class
class Rig:
    def __init__(self, name):
        self.rig_name = name
    
#### Builder base class, uses "Abstract Factory Pattern" for building all rig types.
class Builder:
    def __init__(self, name):
        print("Building: ", name)
        self.name = name

    def build(self):
        pass

    def post_build(self):
        pass