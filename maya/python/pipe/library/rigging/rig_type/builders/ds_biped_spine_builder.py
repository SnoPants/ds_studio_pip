from functools import singledispatch

import maya.cmds as cmds
from pipe.library.rigging.ds_rig import Builder
from pipe.library.utilities.ds_maya_math import dot_product_pv, get_scale_by_distance
from pipe.library.utilities.ds_maya_utils import make_chain, get_selected_joints_hier
from pipe.library.utilities.ds_maya_mtx_constraints import *
from pipe.library.utilities.validate.ds_validate import validate_chain
from pipe.library.rigging.rig_type.builders.ds_controller_builder import RigCtrl

class BipedSpineBuilder(Builder):
    def __init__(self, name, start_joint, end_joint, sc_joint):
        super().__init__(name)
        self.start_joint = start_joint
        self.end_joint = end_joint
        self.single_solver_joint = sc_joint
        self.kinematics = ['IK_', 'FK_']
        self.ik_ctrls = []
        self.fk_ctrls = []

    def build(self):
        print(f"Creating rig for spine... from {self.start_joint} to {self.end_joint} name: {self.name}")

        new_chains = self._build_joints()

        ik = self._ik_setup(new_chains[0])
        fk = self._fk_setup(new_chains[1])
        driver = new_chains[2]

        constraints = self._driver_setup(driver, ik, fk)

        switch = self._switch_setup(driver, ik, fk, constraints)

    def _build_joints(self):

        joint_chain = cmds.listRelatives(self.start_joint, ad = True, type='joint') or []
        joint_chain.append(self.start_joint)
        joint_chain.reverse()
        
        new_chains = []

        for kinematic in self.kinematics:
            end_joint = self.end_joint

            if kinematic == "IK_" and self.single_solver_joint:
                print(f"SC joint exists: {self.single_solver_joint}")
                end_joint = self.single_solver_joint

            new_chains.append(make_chain(kinematic, joint_chain, self.start_joint, end_joint))

        main_chain = get_selected_joints_hier(joint_chain, self.start_joint, self.end_joint)
        new_chains.append(main_chain)

        print('new chains created: ', new_chains)

        return new_chains

    def Inc(increment):
        
        CurveLimit= 1.0
        
        for i in range(1,increment):
            quotientInc = CurveLimit / float(increment)
            
        IncList= [0.0]
        addInc= 0.0
        for i in range(1,increment):
            addInc = addInc + quotientInc
            IncList.append(addInc)
        
        IncList.append(1.0)  

        return IncList
        
    def POCI_Nodes(Num):
        
        itterPCI= 1
        POCI_List= []
        for i in range(0, Num+1):
            cI= cmds.shadingNode("pointOnCurveInfo", asUtility=True, n=getShape+'_curveInfo_0'+str(itterPCI))
            cmds.connectAttr( getShape+'.worldSpace', cI+'.inputCurve')
            POCI_List.append(cI)
            itterPCI= itterPCI + 1
            
        return POCI_List
        
    def POCI_Locs(Num, getSel):
        
        loc_num= 1
        grp_locList= []
        
        for i in range(0, Num+1):
            loc= cmds.spaceLocator(n= getSel+'_loc_0'+ str(loc_num))
            jnt= cmds.joint(n= getSel+'_SKjnt_0'+ str(loc_num))
            grploc= cmds.group(loc, n= getSel+'_loc_grp_0'+ str(loc_num))
            grp_locList.append(grploc)
            loc_num= loc_num + 1
            
            cmds.select(d=True)
            
        return grp_locList
        
    def POCI_Connect_Att(Inc, Nodes, Locs):

        for i, idx in enumerate(Nodes):
            cmds.connectAttr(Nodes[i]+'.result.position', Locs[i]+'.translate')
            cmds.setAttr(Nodes[i]+'.parameter', Inc[i])

    def BND_JNTs_CVs(sel):
        
        cvs = cmds.ls('{0}.cv[:]'.format(sel), fl = True)
        
        print(cvs)
        
        list=[]
        ppList=[]
        
        x= 0.0
        y= 0.0
        z= 0.0
        for i, idx in enumerate(cvs):
            pp= cmds.pointPosition(cvs[i])
            x= pp[0]
            y= pp[1]
            z= pp[2]
            bJnt= cmds.joint(n= getSel+'_Bjnt_0'+ str(i))
            cmds.move(x, y, z)
            cmds.select(d=True)
        
    getSel= cmds.ls(sl=True)[0]
    getShape= cmds.listRelatives(getSel, shapes=True)[0]
    print(getSel,getShape)

    NumOfLocs= int(input())-1

    Inc_List = Inc(NumOfLocs)
    print(Inc_List)

    POCI_List= POCI_Nodes(NumOfLocs)
    print(POCI_List)

    Loc_List= POCI_Locs(NumOfLocs, getSel)
    print(Loc_List)
        
    POCI_Connect_Att(Inc_List, POCI_List, Loc_List)

    BND_JNTs_CVs(getSel)


''' 

def  Main(LocAmount, locName, *pArgs):
    
    getSelection = cmds.ls(sl=True)
    getShape = cmds.listRelatives(c=True)[0]
    getHistory= cmds.listHistory(getSelection)[1]
    
    print(getHistory)

    getPV= cmds.listAttr(getHistory)[-2]
    getPU= cmds.listAttr(getHistory)[-3]
    
    print(getPU,getPV)

    getVn= cmds.getAttr(getHistory+'.'+getPV)
    getUn= cmds.getAttr(getHistory+'.'+getPU)
    
    print(getVn,getUn)

    numberLoc= cmds.intField(LocAmount, q=True, value = True)
    nameLoc= cmds.textField(locName, q=True, text= True)

    spaceUV= 0.0
    spaceUVList= [0.0]

    if numberLoc < 1 or numberLoc > 14:
        raise ValueError
    
    if numberLoc > 1:
        divNurbs = 1.0/float(numberLoc)
        print(divNurbs)

        for i in range(0,numberLoc):
            spaceUV = spaceUV + divNurbs
            spaceUVList.append(spaceUV)

    v= []
    u= []
    boolU = 0
    halfUV = .5
    
    if numberLoc > 1:
        if getVn < getUn: # U is greater
            u.append(spaceUVList)
            v.append(halfUV)
            boolU = 1
        elif getUn < getVn: # V is greater
            v.append(spaceUVList)
            u.append(halfUV)
            boolU = 2
            
    else:
        u.append(halfUV)
        v.append(halfUV)
        boolU = 3

    print(spaceUVList)
    
    for i, idx in enumerate(spaceUVList):

        POSI = cmds.createNode('pointOnSurfaceInfo', n= nameLoc+'_pointOnSurfaceInfo_01')
        FBFM = cmds.createNode('fourByFourMatrix', n= nameLoc+'_fourByFourMatrix_01')
        DM1 = cmds.createNode('decomposeMatrix', n= nameLoc+'_decomposeMatrix_01')
        #DM2 = cmds.createNode('decomposeMatrix', n= nameLoc+'_decomposeMatrix_02')
        #MM = cmds.createNode('multMatrix', n= nameLoc+'_multMatrix_01')


    #____________________________________________________________________nurbsShape--------> PointsOnSurfaceInfo__________________

        cmds.connectAttr(getShape+'.worldSpace', POSI+'.inputSurface')

    #____________________________________________________________________PointsOnSurfaceInfo--------> fourByFourMatrix__________________

        cmds.connectAttr(POSI+'.result.positionX', FBFM+'.in30')
        cmds.connectAttr(POSI+'.result.positionY', FBFM+'.in31')
        cmds.connectAttr(POSI+'.result.positionZ', FBFM+'.in32')

        cmds.connectAttr(POSI+'.result.normal.normalX', FBFM+'.in00')
        cmds.connectAttr(POSI+'.result.normal.normalY', FBFM+'.in01')
        cmds.connectAttr(POSI+'.result.normal.normalZ', FBFM+'.in02')

        cmds.connectAttr(POSI+'.result.tangentU.tangentUx', FBFM+'.in10')
        cmds.connectAttr(POSI+'.result.tangentU.tangentUy', FBFM+'.in11')
        cmds.connectAttr(POSI+'.result.tangentU.tangentUz', FBFM+'.in12')

        cmds.connectAttr(POSI+'.result.tangentV.tangentVx', FBFM+'.in20')
        cmds.connectAttr(POSI+'.result.tangentV.tangentVy', FBFM+'.in21')
        cmds.connectAttr(POSI+'.result.tangentV.tangentVz', FBFM+'.in22')

    #____________________________________________________________________fourByFourMatrix----------> decomposeMatrix__________________

        cmds.connectAttr(FBFM+'.output', DM1+'.inputMatrix')

        loc= cmds.spaceLocator(n= nameLoc+'_01')

        cmds.connectAttr(DM1+'.outputTranslate', loc[0]+'.translate')
        cmds.connectAttr(DM1+'.outputRotate', loc[0]+'.rotate')

    #____________________________________________________________________set UV's__________________

        if boolU == 1:
            cmds.setAttr(POSI+'.parameterU', u[0][i])
            cmds.setAttr(POSI+'.parameterV', v[0])
        elif boolU == 2:
            cmds.setAttr(POSI+'.parameterV', v[0][i])
            cmds.setAttr(POSI+'.parameterU', u[0])
        elif boolU == 3:
            cmds.setAttr(POSI+'.parameterV', v[0])
            cmds.setAttr(POSI+'.parameterU', u[0])'''
        
