from functools import singledispatch

import maya.cmds as cmds
from pipe.library.rigging.ds_rig import Builder
from pipe.library.utilities.ds_maya_math import dot_product_pv, get_scale_by_distance
from pipe.library.utilities.ds_maya_utils import get_selected_joints_hier
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

    def _create_nurbs_plane(self):
        print("Creating nurbs plane for spine rig...")

    def _create_locator_rivets(self, nurbs_plane, joints):
        
        # TODO: Need to refactor this code potentially.

        print("Creating locator rivets for spine rig...")

        #def  Main(LocAmount, locName, *pArgs):
    
        getShape = cmds.listRelatives(c=True)[0]
        getHistory= cmds.listHistory(nurbs_plane)[1]
        
        #print(getHistory)

        getPV= cmds.listAttr(getHistory)[-2]
        getPU= cmds.listAttr(getHistory)[-3]
        
        #print(getPU,getPV)

        getVn= cmds.getAttr(getHistory+'.'+getPV)
        getUn= cmds.getAttr(getHistory+'.'+getPU)
        
        #print(getVn,getUn)

        numberLoc= len(joints)
        nameLoc= cmds.textField(locName, q=True, text= True)

        spaceUV= 0.0
        spaceUVList= [0.0]
        
        if numberLoc > 1:
            divNurbs = 1.0/float(numberLoc)
            #print(divNurbs)

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


        #nurbsShape---> PointsOnSurfaceInfo

            cmds.connectAttr(getShape+'.worldSpace', POSI+'.inputSurface')

        #PointsOnSurfaceInfo---> fourByFourMatrix

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

        #fourByFourMatrix---> decomposeMatrix

            cmds.connectAttr(FBFM+'.output', DM1+'.inputMatrix')

            loc= cmds.spaceLocator(n= nameLoc+'_01')

            cmds.connectAttr(DM1+'.outputTranslate', loc[0]+'.translate')
            cmds.connectAttr(DM1+'.outputRotate', loc[0]+'.rotate')

        #set UV's

            if boolU == 1:
                cmds.setAttr(POSI+'.parameterU', u[0][i])
                cmds.setAttr(POSI+'.parameterV', v[0])
            elif boolU == 2:
                cmds.setAttr(POSI+'.parameterV', v[0][i])
                cmds.setAttr(POSI+'.parameterU', u[0])
            elif boolU == 3:
                cmds.setAttr(POSI+'.parameterV', v[0])
                cmds.setAttr(POSI+'.parameterU', u[0])
            
    def _build_joints(self):
        print("Building joint chains for spine rig...")

    def _ik_setup(self, chain):
        print("Setting up IK for spine rig...")

    def _fk_setup(self, chain):
        print("Setting up FK for spine rig...")

    def _driver_setup(self, driver_chain, ik_chain, fk_chain):
        print("Setting up driver joints and constraints for spine rig...")

    def _switch_setup(self, driver_chain, ik_chain, fk_chain, constraints):
        print("Setting up IK/FK switch for spine rig...")


''' 

def  Main(LocAmount, locName, *pArgs):
    
    getSelection = cmds.ls(sl=True)
    getShape = cmds.listRelatives(c=True)[0]
    getHistory= py.listHistory(getSelection)[1]
    
    print(getHistory)

    getPV= py.listAttr(getHistory)[-2]
    getPU= py.listAttr(getHistory)[-3]
    
    print(getPU,getPV)

    getVn= py.getAttr(getHistory+'.'+getPV)
    getUn= py.getAttr(getHistory+'.'+getPU)
    
    print(getVn,getUn)

    numberLoc= py.intField(LocAmount, q=True, value = True)
    nameLoc= py.textField(locName, q=True, text= True)

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

        POSI = py.createNode('pointOnSurfaceInfo', n= nameLoc+'_pointOnSurfaceInfo_01')
        FBFM = py.createNode('fourByFourMatrix', n= nameLoc+'_fourByFourMatrix_01')
        DM1 = py.createNode('decomposeMatrix', n= nameLoc+'_decomposeMatrix_01')
        #DM2 = py.createNode('decomposeMatrix', n= nameLoc+'_decomposeMatrix_02')
        #MM = py.createNode('multMatrix', n= nameLoc+'_multMatrix_01')


    #____________________________________________________________________nurbsShape--------> PointsOnSurfaceInfo__________________

        py.connectAttr(getShape+'.worldSpace', POSI+'.inputSurface')

    #____________________________________________________________________PointsOnSurfaceInfo--------> fourByFourMatrix__________________

        py.connectAttr(POSI+'.result.positionX', FBFM+'.in30')
        py.connectAttr(POSI+'.result.positionY', FBFM+'.in31')
        py.connectAttr(POSI+'.result.positionZ', FBFM+'.in32')

        py.connectAttr(POSI+'.result.normal.normalX', FBFM+'.in00')
        py.connectAttr(POSI+'.result.normal.normalY', FBFM+'.in01')
        py.connectAttr(POSI+'.result.normal.normalZ', FBFM+'.in02')

        py.connectAttr(POSI+'.result.tangentU.tangentUx', FBFM+'.in10')
        py.connectAttr(POSI+'.result.tangentU.tangentUy', FBFM+'.in11')
        py.connectAttr(POSI+'.result.tangentU.tangentUz', FBFM+'.in12')

        py.connectAttr(POSI+'.result.tangentV.tangentVx', FBFM+'.in20')
        py.connectAttr(POSI+'.result.tangentV.tangentVy', FBFM+'.in21')
        py.connectAttr(POSI+'.result.tangentV.tangentVz', FBFM+'.in22')

    #____________________________________________________________________fourByFourMatrix----------> decomposeMatrix__________________

        py.connectAttr(FBFM+'.output', DM1+'.inputMatrix')

        loc= py.spaceLocator(n= nameLoc+'_01')

        py.connectAttr(DM1+'.outputTranslate', loc[0]+'.translate')
        py.connectAttr(DM1+'.outputRotate', loc[0]+'.rotate')

    #____________________________________________________________________set UV's__________________

        if boolU == 1:
            py.setAttr(POSI+'.parameterU', u[0][i])
            py.setAttr(POSI+'.parameterV', v[0])
        elif boolU == 2:
            py.setAttr(POSI+'.parameterV', v[0][i])
            py.setAttr(POSI+'.parameterU', u[0])
        elif boolU == 3:
            py.setAttr(POSI+'.parameterV', v[0])
            py.setAttr(POSI+'.parameterU', u[0])'''
        
