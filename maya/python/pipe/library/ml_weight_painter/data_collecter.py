import maya.cmds as cmds
import maya.mel as mel
import random
import math
from collections import defaultdict
import json
import os
from pathlib import Path
import numpy as np
import re

def get_json(sel):
    
    joints, skinCluster = get_skinned_joints(sel)
    print(joints, skinCluster)
    vrts = get_mesh_verts(sel)
    print(vrts)

    test_vrts = random.sample(vrts, 10)
    test_joints = random.sample(joints, 10)

    data = get_distance(test_joints, test_vrts)
    data['vert weights'] = get_skin_weights(skinCluster, test_vrts,test_joints,)

    json_folder = r"C:\Users\andre\Documents\maya\DS_STUDIO\ds_studio_pip\maya\python\pipe\library\ml_weight_painter\json_data"

    file_name = Path(cmds.file(q=True, sn=True)).stem
    print(file_name)

    file_path = os.path.join(json_folder, f"{file_name}.json")

    with open (file_path, "w") as file:
        json.dump(data, file, indent=4)
    

def get_skin_weights(skinCluster, vrts, joints):
    
    skin_percentages = defaultdict(dict)
    for v in vrts:
        for j in joints:
            percent = cmds.skinPercent(skinCluster, v, transform= j, query=True)
            skin_percentages[v][f'{j} weight'] = percent
    
    return skin_percentages

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
    print(joints)
    joints.sort()

    return joints, getSkinCluster

def get_mesh_verts(sel):
    selection = cmds.ls(sl=True)
    vertices = cmds.ls(selection[0]+'.vtx[*]', fl=True)
    vertices.sort(key=lambda v: int(re.search(r"\[(\d+)\]", v).group(1)))
    return vertices
    
def get_distance(joints, vrts):
    
    def get_positions(objs):
        
        objs_dict = defaultdict(dict)
        
        for i in objs:
            i_translation = cmds.xform(i, q=True, ws=True, t= True)
            objs_dict[i]["translation"] = i_translation
        
        return dict(objs_dict)
    
    vert_data = get_positions(vrts)
    joint_data = get_positions(joints)
    
    distance_data = defaultdict(dict)
    for v in vert_data:
        vrt_pos = vert_data[v]["translation"]
        for j in joint_data:
            joint_pos = joint_data[j]["translation"]
            dist = math.dist(vrt_pos, joint_pos)
            #cmds.distanceDimension(sp=vrt_pos, ep=joint_pos) USE ONLY FOR SMALL SAMPLE SIZE
            distance_data[v][j] = dist
    
    data_set = {}
    data_set['vert positions'] = vert_data
    data_set['joint positions'] = joint_data
    data_set['vert to joint distances'] = dict(distance_data) 
    
    #print(data_set)
    return data_set
    
def get_npz(sel):
    
    def get_npz_data(joints, verts):
        
        vert_positions = []
        
        for v in verts:
            i_translation = cmds.xform(i, q=True, ws=True, t= True)
            objs_dict[i]["translation"] = i_translation
        
        return
    
    joints, skinCluster = get_skinned_joints(sel)
    vrts = get_mesh_verts(sel)
    data = get_distance(test_joints, test_vrts)
    data['vert weights'] = get_skin_weights(skinCluster, test_vrts,test_joints,)
    return
    

sel = cmds.ls(selection=True)

try:
    get_json(sel)
except Exception as e:
    raise ValueError(f"ERROR: {e}") from e
    
#get_npz(sel)

