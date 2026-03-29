import maya.cmds as cmds

def rebuildBindPose():
    """Deletes all existing bind poses and recreates a single new bind pose."""
    
    # Get selected object(s)
    sel = cmds.ls(selection=True)
    
    if not sel:
        cmds.error("Please select character root")
        return

    root_joint = sel[0]

    # Build list of joints
    joint_list = cmds.listRelatives(root_joint, allDescendents=True, type="joint", fullPath=True) or []
    joint_list.append(root_joint)  # Add root joint at the end

    dag_poses = []
    
    # Find all connected dagPose nodes
    for joint in joint_list:
        dag_connections = cmds.listConnections(joint, type="dagPose") or []
        dag_poses.extend(dag_connections)

    # Remove duplicates from the list
    dag_poses = list(set(dag_poses))

    connected_skin_clusters = []

    # Build list of connected skin clusters
    for pose in dag_poses:
        skin_clusters = cmds.listConnections(pose, type="skinCluster") or []
        connected_skin_clusters.extend(skin_clusters)

    # Remove duplicates from the skinCluster list
    connected_skin_clusters = list(set(connected_skin_clusters))

    # Delete existing bind poses
    if dag_poses:
        print("Deleting dagPoses:")
        print(dag_poses)
        cmds.delete(dag_poses)

    # Create new bind pose
    cmds.select(joint_list, replace=True)
    new_dag_pose = cmds.dagPose(save=True, bindPose=True)

    print(f"New dagPose created: {new_dag_pose}")

    # Reconnect the new bind pose to skinClusters
    for skin_cluster in connected_skin_clusters:
        print(f"Connecting {new_dag_pose}.message to {skin_cluster}.bindPose")
        cmds.connectAttr(f"{new_dag_pose}.message", f"{skin_cluster}.bindPose", force=True)

# Run the function
rebuildBindPose()