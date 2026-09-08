import uuid


class JointData:

    def __init__(self, name, parent=None, vertex_ids=None, uid=None):
        self.uid = uid or str(uuid.uuid4())
        self.name = name
        self.parent = parent
        self.vertex_ids = vertex_ids or []

    @staticmethod
    def validate_name(name, all_joint_names=None):
        """Return the reason a name is unusable, or "" if it is valid.

        Single source of truth for joint naming rules, shared by the model's
        own guard and by the UI's feedback, so the two cannot drift apart.
        """
        if not name or not name.strip():
            return "Joint name cannot be empty."
        if all_joint_names is not None and name in all_joint_names:
            return "Another joint already uses this name."
        return ""

    def rename(self, name, all_joint_names=None):
        """Rename the joint. Returns False if the name was rejected."""
        if JointData.validate_name(name, all_joint_names):
            return False
        self.name = name
        return True

    def set_vertices(self, vertex_ids):
        """Assign vertices. These index SkeletonData.mesh, the one target mesh."""
        self.vertex_ids = list(vertex_ids)

    def clear_vertices(self):
        self.vertex_ids = []

    def to_dict(self):
        return {
            "uid": self.uid,
            "name": self.name,
            "parent": self.parent,
            "vertex_ids": self.vertex_ids,
        }

    def from_dict(data):
        return JointData(
            name=data["name"],
            parent=data.get("parent"),
            vertex_ids=data.get("vertex_ids", []),
            uid=data.get("uid"),
        )


class RegionData:

    def __init__(self, name, uid=None):
        self.uid = uid or str(uuid.uuid4())
        self.name = name
        self.joints = []

    def add_joint(self, name):
        joint = JointData(name)
        self.joints.append(joint)
        return joint

    def remove_joint(self, joint):
        if joint in self.joints:
            self.joints.remove(joint)

    def rename(self, name):
        self.name = name

    def to_dict(self):
        return {
            "uid": self.uid,
            "name": self.name,
            "joints": [joint.to_dict() for joint in self.joints],
        }

    def from_dict(data):
        region = RegionData(name=data["name"], uid=data.get("uid"))
        for joint_data in data.get("joints", []):
            region.joints.append(JointData.from_dict(joint_data))
        return region


class SkeletonData:

    SCHEMA_VERSION = 2

    def __init__(self, mesh=None):
        self.mesh = mesh
        self.regions = []

    def add_region(self, name):
        region = RegionData(name)
        self.regions.append(region)
        return region

    def remove_region(self, region):
        if region in self.regions:
            self.regions.remove(region)

    def joints(self):
        """Iterate every joint in the mapping, across all regions."""
        for region in self.regions:
            for joint in region.joints:
                yield joint

    def all_joint_names(self, exclude=None):
        """Return a set of all joint names, optionally excluding one JointData."""
        return {
            joint.name for joint in self.joints()
            if joint is not exclude
        }

    def all_region_names(self, exclude=None):
        """Return a set of all region names, optionally excluding one RegionData."""
        return {
            region.name for region in self.regions
            if region is not exclude
        }

    def find_joint(self, name):
        for joint in self.joints():
            if joint.name == name:
                return joint
        return None

    def to_dict(self):
        return {
            "schema_version": self.SCHEMA_VERSION,
            "tool": "skeleton_mapper",
            "mesh": self.mesh,
            "regions": [region.to_dict() for region in self.regions],
        }

    def from_dict(data):
        skeleton = SkeletonData(mesh=data.get("mesh"))
        for region_data in data.get("regions", []):
            skeleton.regions.append(RegionData.from_dict(region_data))
        return skeleton
