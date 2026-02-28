import maya.cmds as cmds

# Function to calculate the vector between two points
def get_vector(pt0=None, pt1=None):
    dx = pt1[0] - pt0[0]
    dy = pt1[1] - pt0[1]
    dz = pt1[2] - pt0[2]
    return [dx, dy, dz]

# Function to calculate the centroid of a set of nodes
def get_centroid(node_array):
    posX, posY, posZ = 0, 0, 0  # Initialize positions

    for node in node_array:
        # Query world space translation of each node
        position = cmds.xform(node, query=True, translation=True, worldSpace=True)
        posX += position[0]
        posY += position[1]
        posZ += position[2]

    # Calculate the centroid as the average position
    node_count = len(node_array)
    centroid = [posX / node_count, posY / node_count, posZ / node_count]
    return centroid

# Get selected nodes and calculate their centroid
selected_nodes = cmds.ls(selection=True, flatten=True)
cmds.select(clear=True)  # Deselect everything
centroid_position = get_centroid(selected_nodes)

# Create a joint and move it to the calculated centroid
joint = cmds.joint(rad= 5.0)
joint_position = cmds.xform(joint, query=True, translation=True, worldSpace=True)

# Calculate the vector from the joint's current position to the centroid
vector_to_centroid = get_vector(joint_position, centroid_position)

# Move the joint to the centroid by setting its translation attributes
cmds.setAttr(f"{joint}.translateX", vector_to_centroid[0])
cmds.setAttr(f"{joint}.translateY", vector_to_centroid[1])
cmds.setAttr(f"{joint}.translateZ", vector_to_centroid[2])
