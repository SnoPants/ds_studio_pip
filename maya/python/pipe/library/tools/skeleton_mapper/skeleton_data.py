class JointData:

    def __init__(self, name, parent=None, mesh=None, vertex_ids=None):
        self.name = name
        self.parent = parent
        self.mesh = mesh
        self.vertex_ids = vertex_ids or []

    def rename(self, name, all_joint_names=None):
        """Rename the joint. Returns False if the name is a duplicate."""
        if all_joint_names is not None and name in all_joint_names:
            if name != self.name:
                return False
        self.name = name
        return True

    def set_vertices(self, mesh, vertex_ids):
        self.mesh = mesh
        self.vertex_ids = list(vertex_ids)

    def clear_vertices(self):
        self.vertex_ids = []

    def to_dict(self):
        return {
            "name": self.name,
            "parent": self.parent,
            "vertex_ids": self.vertex_ids,
        }

    def from_dict(data):
        return JointData(
            name=data["name"],
            parent=data.get("parent"),
            mesh=data.get("mesh"),
            vertex_ids=data.get("vertex_ids", []),
        )


class RegionData:

    def __init__(self, name):
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
            "name": self.name,
            "joints": [joint.to_dict() for joint in self.joints],
        }

    def from_dict(data):
        region = RegionData(name=data["name"])
        for joint_data in data.get("joints", []):
            region.joints.append(JointData.from_dict(joint_data))
        return region


class SkeletonData:

    SCHEMA_VERSION = 1

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

    def all_joint_names(self, exclude=None):
        """Return a set of all joint names, optionally excluding one JointData."""
        names = set()
        for region in self.regions:
            for joint in region.joints:
                if joint is not exclude:
                    names.add(joint.name)
        return names

    def find_joint(self, name):
        for region in self.regions:
            for joint in region.joints:
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
