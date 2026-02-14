import maya.cmds as cmds
import math
import maya.api.OpenMaya as om
from decimal import *
from pipe.library.rigging.rig_type.builders.ds_controller_builder import RigCtrl



def get_distance(objA, objB):
    posA = om.MVector(cmds.xform(objA, q=True, ws=True, t=True))
    posB = om.MVector(cmds.xform(objB, q=True, ws=True, t=True))
    return (posB - posA).length()

#

def convert_to_decimal(value): # not sure if I have use for this yet
    s = str(value)
    places = int(len(s.split('.')[0]))
    target = Decimal(s)
    return float(target.shift(-places))

#

def get_scale_by_distance(joint_chain):
    distance_to_scale = get_distance(joint_chain[0], joint_chain[-1])

    if distance_to_scale > 100.0:
        distance_to_scale = distance_to_scale * .004

    if distance_to_scale < 1.0:
        distance_to_scale = 1.0

    return distance_to_scale

#

def dot_product_pv(chain, name):

    def get_middle_vector(list):

        length = len(list)

        if length % 2 == 0:
            middle_indices = (length//2 - 1, length//2)
            joints = ([list[i] for i in middle_indices])
            print(joints)

            posA = om.MVector(cmds.xform(joints[0], q=True, ws=True, t=True))
            posB = om.MVector(cmds.xform(joints[1], q=True, ws=True, t=True))
            return (posB - posA) / 2 + posA
        else:
            middle_indices = (length//2,)
            joint = list[middle_indices[0]]
            print(joint)

            pos = om.MVector(cmds.xform(joint, q=True, ws=True, t=True))
            return pos
        
    vectors= []
    for i, idx in enumerate(chain):
        objXform= cmds.xform(chain[i], q= True, t= True, ws= True)
        vectors.append(objXform)
    
    startV = om.MVector(vectors[0])
    midV = get_middle_vector(chain)
    endV = om.MVector(vectors[-1])

    startEnd = endV - startV
    startMid = midV - startV

    dotP = startMid * startEnd
    proj = float(dotP) / float(startEnd.length())
    startEndN = startEnd.normal()
    projV = startEndN * proj

    arrowV = startMid - projV
    arrowV*= float(1) ######################################################################################## needs to be automated
    finalV = arrowV + midV

    ctrl = RigCtrl(f'{name}_PV', scale = get_scale_by_distance(chain), translate= [finalV.x , finalV.y ,finalV.z])
    ctrl_pv = ctrl._create_loc()
    
    return ctrl_pv