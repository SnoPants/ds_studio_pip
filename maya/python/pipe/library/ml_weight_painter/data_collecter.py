import maya.cmds as cmds
import maya.mel as mel
import random
import math
from collections import defaultdict


def get_skinned_joints(sel):
    
    def checkSel(sel):
        if len(sel) > 1:
            raise Exception('More than one object was selected. Please select one Mesh. This was your selection: {}'.format(sel))
        
    def checkCluster(cluster, sel):
        if not cluster:
            raise Exception('This object has no skin cluster. This was your selection: {}'.format(sel))
        
    checkSel(sel)
    mesh= sel[0]

    getSkinCluster= mel.eval('findRelatedSkinCluster '+mesh)

    checkCluster(getSkinCluster, mesh)
    joints= cmds.skinCluster(getSkinCluster, query=True,inf=True)

    return joints

def get_mesh_verts(sel):
    selection = cmds.ls(sl=True)
    vertices = cmds.ls(selection[0]+'.vtx[*]', fl=True)
    return vertices
    
def get_distance(joints, vrts):
    
    def get_positions(objs):
        
        objs_dict = defaultdict(dict)
        
        for i in objs:
            i_translation = cmds.xform(i, q=True, ws=True, t= True)
            objs_dict[i]["translation"] = i_translation
        
        return objs_dict
        
    data_set = defaultdict(dict)
    
    vert_data = get_positions(vrts)
    joint_data = get_positions(joints)
    
    distance_data = defaultdict(dict)
    for v in vert_data:
        vrt_pos = vert_data[v]["translation"]
        for j in joint_data:
            joint_pos = joint_data[j]["translation"]
            dist = math.dist(vrt_pos, joint_pos)
            cmds.distanceDimension(sp=vrt_pos, ep=joint_pos)
            distance_data[v][j] = dist
            
    print(vert_data)
    print(joint_data)
    print(distance_data)

sel = cmds.ls(selection=True)
joints = get_skinned_joints(sel)
print(joints)
vrts = get_mesh_verts(sel)
print(vrts)

test_vrts = random.sample(vrts, 3)
test_joints = random.sample(joints, 3)

get_distance(test_joints, test_vrts)

