import maya.cmds as cmds
from pipe.library.utilities.validate.ds_validate import validate_chain

def get_selected_joints_hier(chain, start, end):

    chain_list = []

    # Need to add listRelatives command here for chain building to be more robust. 
    # including anytime that I have called it prior to calling this function in the limb builder code.

    for joint in chain:
        child = cmds.listRelatives(joint, children= True, type='joint', ad= True)
        if child and joint != start:
            if end in child:
                chain_list.append(joint)
            else:
                continue

    validate_chain(chain_list)
    chain_heir = [start] + chain_list + [end]

    return chain_heir

# This will be for something fancier when i want save custom nurb controls to a json, for later. This means i would need to store all my nurb controls on the same json, for conistency.
def get_nurbs_points(nurbs):
    '''# Note: degree for the curve, but for knots it is spans+degree - 1
        shape = cmds.listRelatives(nurbs, s=True, f=True)[0]
        num_cvs = cmds.getAttr(shape + ".controlPoints", size=True)
        curve_degree = cmds.getAttr(f'{nurbs}.degree') 
        print(num_cvs, curve_degree)
        
        shapes = cmds.listRelatives(nurbs, shapes=True)
        form = cmds.getAttr(f"{shapes[0]}.form")
        print(form)
        
        knots = list(range(num_cvs + curve_degree - 1))
        
        print(knots)
        
        cv_positions = []

        for i in range(num_cvs):
            # Query world-space position of each CV
            # Format for querying components is 'curveName.cv[index]'
            pos = cmds.pointPosition(f'{nurbs}.cv[{i}]', world=True)
            cv_positions.append(pos)
            
        curve_node = cmds.curve(n='myNurbsCurve', d=curve_degree, p=cv_positions, per = True, k=[-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        cmds.curve( p =[(0.783611624891225, 0.0, -0.7836116248912237), (-1.2643170607829324e-16, 0.0, -1.1081941875543877), (-0.7836116248912243, 0.0, -0.7836116248912242), (-1.108194187554388, 0.0, 0.0), (-0.7836116248912245, 0.0, 0.7836116248912237), (-3.3392053635905195e-16, 0.0, 1.1081941875543881), (0.7836116248912238, 0.0, 0.7836116248912246), (1.108194187554388, 0.0, 8.881784197001252e-16), (0.783611624891225, 0.0, -0.7836116248912237), (-1.2643170607829324e-16, 0.0, -1.1081941875543877), (-0.7836116248912243, 0.0, -0.7836116248912242)],
        per = True, d=3, k=[-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            
        return print(cv_positions)'''
    return