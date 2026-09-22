import maya.cmds as cmds
from pipe.library.utilities.ds_maya_utils import get_centroid, create_joint

class SkeletonBuilder:
    def __init__(self, name, skeleton):
        self.skeleton = skeleton
        self.built = {}       # uid -> node name
        self.warnings = []

    def build(self):
        pass
    # builds each joint, attaches corresponding uuid
    # parents and reparents hierarchy

