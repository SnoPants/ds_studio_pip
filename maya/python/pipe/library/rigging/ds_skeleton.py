import maya.cmds as cmds
from maya.api import OpenMaya as om
import os
from pipe.library.utilities.validate import ds_validate
from pipe.library.utilities.ds_maya_utils import create_joint, node_path

print("From rigging module - ds_skeleton.py loaded")

class Skeleton:
    def __init__(self, name, description=None):
        self.skeleton_name = name
        self.hierarchy = description if description else {}

    def build_skeleton(self, skeleton):
        built = self.create_joints(skeleton)
        self.parent_joints(skeleton, built)
        self.orient_joints(skeleton, built)

        return {uid: self.joint_path(node_uuid) for uid, node_uuid in built.items()}

    @staticmethod
    def joint_path(node_uuid):
        # Built joints are tracked by Maya UUID; paths go stale once parented.
        return node_path(node_uuid)

    def validate_skeleton(self):
        print(f"Validating skeleton: {self.skeleton_name}")
        # Implementation for validating the skeleton should go to ds_validate module

    def create_joints(self, skeleton):

        print(f"Creating joints for skeleton: {self.skeleton_name}")

        def existing_joint_names():
            joints_by_uid = {}

            for node in cmds.ls(type="joint", long=True) or []:
                if not cmds.attributeQuery("mapperUid", node=node, exists=True):
                    continue

                uid = cmds.getAttr(f"{node}.mapperUid")

                if not uid:
                    continue

                if uid in joints_by_uid:
                    raise ValueError(f"Duplicate mapperUid '{uid}': "f"{joints_by_uid[uid]} and {node}")
                joints_by_uid[uid] = node

            return joints_by_uid

        def joint_position(skeleton, joint):

            if joint.position is None:
                cmds.warning(f"{joint.name} has no position; {joint.name} will be set at origin.")
                return(0.0, 0.0, 0.0)

            return tuple(joint.position)

        print(f"Building skeleton for: {self.skeleton_name}")
        built = {}
        joints_by_uid = existing_joint_names()

        for joint in skeleton.joints():
            node = joints_by_uid.get(joint.uid)
            position = joint_position(skeleton, joint)

            if node is None:
                cmds.select(clear= True)
                node = create_joint(tags={"mapperUid": joint.uid})
                node = cmds.rename(node, joint.name)

            # On a rebuild the joint may already have children; keep them in place.
            cmds.move(*position, node, worldSpace= True, absolute= True, preserveChildPosition= True)

            built[joint.uid] = cmds.ls(node, uuid= True)[0]

            cmds.select(clear= True)

        return built

    def parent_joints(self, skeleton, built):
        targets = {}

        for (uid, joint), (parent_uid, parent_joint) in skeleton.parent_order().items():
            node = self.joint_path(built.get(uid))
            if node is None:
                continue

            parent_node = None
            if parent_uid is not None:
                parent_node = self.joint_path(built.get(parent_uid))
                if parent_node is None:
                    cmds.warning(f"Parent of {joint.name} was not built; {joint.name} left at world.")

            targets[built[uid]] = built.get(parent_uid) if parent_node else None

        # Unparent first so a rebuild that reverses a branch never parents a joint under its own child.
        for node_uuid, parent_uuid in targets.items():
            node = self.joint_path(node_uuid)
            current = cmds.listRelatives(node, parent= True, fullPath= True)
            if current and current[0] != self.joint_path(parent_uuid):
                cmds.parent(node, world= True)

        for node_uuid, parent_uuid in targets.items():
            if parent_uuid is None:
                continue
            node = self.joint_path(node_uuid)
            parent_node = self.joint_path(parent_uuid)
            current = cmds.listRelatives(node, parent= True, fullPath= True)
            if current and current[0] == parent_node:
                continue
            cmds.parent(node, parent_node)

    def orient_joints(self, skeleton, built):
        print(f"Orienting joints for skeleton: {self.skeleton_name}")
        joints = {joint.uid: joint for joint in skeleton.joints()}
        paths = {uid: self.joint_path(node_uuid) for uid, node_uuid in built.items()}

        # Top-down, so each joint is oriented against its parent's final matrix.
        for uid in sorted(paths, key=lambda uid: paths[uid].count("|")):
            joint = joints[uid]
            node = self.joint_path(built[uid])

            # No stored rotation keeps the joint aligned to world, as before.
            radians = [om.MAngle(angle, om.MAngle.kDegrees).asRadians() for angle in joint.rotation or (0.0, 0.0, 0.0)]
            matrix = om.MEulerRotation(*radians).asMatrix()
            parent = cmds.listRelatives(node, parent= True, fullPath= True)
            if parent:
                matrix *= om.MMatrix(cmds.xform(parent[0], query= True, worldSpace= True, matrix= True)).inverse()
            orient = om.MTransformationMatrix(matrix).rotation()

            # Frozen: the rotation lives in jointOrient and rotate stays zero.
            cmds.setAttr(f"{node}.rotate", 0, 0, 0)
            cmds.setAttr(f"{node}.jointOrient", *[om.MAngle(angle).asDegrees() for angle in (orient.x, orient.y, orient.z)])

            # A parent's new orient swings its children; put this one back on its preview.
            position = joint.position or (0.0, 0.0, 0.0)
            cmds.move(*position, node, worldSpace= True, absolute= True, preserveChildPosition= True)

    def add_metadata(self):
        print(f"Adding metadata for skeleton: {self.skeleton_name}")
        # Implementation for adding metadata to joints in Maya goes here

    def build_result(self):
        print(f"Building result for skeleton: {self.skeleton_name}")
        # Implementation for building the final result of the skeleton goes here


    