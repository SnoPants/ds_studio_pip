from functools import singledispatch

import maya.cmds as cmds
from library.rigging.ds_rig import Builder
from library.utilities.ds_maya_math import dot_product_pv, get_scale_by_distance
from library.utilities.ds_maya_utils import get_selected_joints_hier
from library.utilities.ds_maya_mtx_constraints import *
from library.utilities.validate.ds_validate import validate_chain
from library.rigging.rig_type.builders.ds_controller_builder import RigCtrl

class BipedLimbBuilder(Builder):
    def __init__(self, name, start_joint, end_joint, sc_joint):
        super().__init__(name)
        self.start_joint = start_joint
        self.end_joint = end_joint
        self.single_solver_joint = sc_joint
        self.kinematics = ['IK_', 'FK_']
        self.ik_ctrls = []
        self.fk_ctrls = []


    def build(self):
        print(f"Creating rig for limb... from {self.start_joint} to {self.end_joint} name: {self.name}")
    
        new_chains = self._build_joints()

        ik = self._ik_setup(new_chains[0])
        fk = self._fk_setup(new_chains[1])
        driver = new_chains[2]

        constraints = self._driver_setup(driver, ik, fk)

        switch = self._switch_setup(driver, ik, fk, constraints)




    def _build_joints(self):
        ### Helper function to create joint chains
        def make_chain(name, trg_chain, start, end):
            
            main_chain = get_selected_joints_hier(trg_chain, start, end)
            built_chain = [name + i for i in main_chain]

            selection_parent = cmds.listRelatives(start, p= True) # this needs work, currently only works if start joint has a parent,
            # will need to consider how to deal with with first selected joint parents in cases of clavicles etc...

            for j, joint in enumerate(built_chain):
                new_joint = cmds.createNode('joint', n = joint)
                cmds.xform(new_joint, worldSpace=True, matrix=cmds.xform(main_chain[j], query=True, worldSpace=True, matrix=True))
                cmds.makeIdentity(new_joint, apply=True, t=0, r=1, s=0)
                if j == 0:
                    if selection_parent:
                        cmds.parent(new_joint, selection_parent)
                    else:
                        cmds.parent(new_joint, w= True)
                else:
                    cmds.parent(new_joint, built_chain[j-1])

            return built_chain
        ###

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
    


    def _ik_setup(self, ik_chain):
        print(f"Setting up IK for joints: {ik_chain} for {self.name}")

        effector_joint = ik_chain[-1]

        if self.single_solver_joint is not None:
            ikhandle_sc = cmds.ikHandle(n= f"{self.name}_ikHandleSC_01", sol='ikSCsolver', sj= ik_chain[-2], ee= ik_chain[-1])[0]
            effector_joint = ik_chain[-2]

        ikhandle_rp = cmds.ikHandle(n= f"{self.name}_ikHandleRP_01", sol='ikRPsolver', sj= ik_chain[0], ee= effector_joint)[0]

        anchor_ik_transform = cmds.xform(ik_chain[0], q= True, t= True, ws= True)

        anchor_ik_ctrl = RigCtrl(f'{self.name}_IK_Anchor_Ctrl', scale = get_scale_by_distance(ik_chain), translate= [anchor_ik_transform[0] , anchor_ik_transform[1] ,anchor_ik_transform[2]])
        anchor_ik_loc = anchor_ik_ctrl._create_loc()[0]
        self.ik_ctrls.append(anchor_ik_loc)

        effector_ik_transform = cmds.xform(effector_joint, q= True, t= True, ws= True)
        effector_ik_rotation = cmds.xform(effector_joint, q= True, rotation= True, ws= True)
        effector_ik_ctrl = RigCtrl(f'{self.name}_IK_Effector_Ctrl', scale = get_scale_by_distance(ik_chain), translate= [effector_ik_transform[0] , effector_ik_transform[1] , effector_ik_transform[2]], rotation= [effector_ik_rotation[0] , effector_ik_rotation[1] ,effector_ik_rotation[2]])
        effector_ik_loc, effector_ik_grp = effector_ik_ctrl._create_loc()
        self.ik_ctrls.append(effector_ik_loc)

        print('effector ik loc created: ', effector_ik_loc)
        
        if self.single_solver_joint is not None:
            ik_chain.pop(-1)
            cmds.parent(ikhandle_sc, effector_ik_loc)

        pole_vector_loc = dot_product_pv(ik_chain, self.name)
        self.ik_ctrls.append(pole_vector_loc[0])

        cmds.parent(ikhandle_rp, effector_ik_loc)
        cmds.pointConstraint(anchor_ik_loc, ik_chain[0], mo= True)    
        cmds.poleVectorConstraint(pole_vector_loc, ikhandle_rp, wal= True)
        return ik_chain

    def _fk_setup(self, fk_chain):
        print(f"Setting up FK for joints: {fk_chain} for {self.name}")

        grp_ctrl = []

        for j, joint in enumerate(fk_chain):
            fk_transform = cmds.xform(joint, q= True, t= True, ws= True)
            fk_rotation = cmds.xform(joint, q= True, rotation= True, ws= True)
            fk_ctrl = RigCtrl(f'{joint}_FK_Ctrl', scale = get_scale_by_distance(fk_chain), translate= [fk_transform[0] , fk_transform[1] ,fk_transform[2]], rotation= [fk_rotation[0] , fk_rotation[1] ,fk_rotation[2]])
            fk_loc, fk_loc_grp = fk_ctrl._create_loc()
            self.fk_ctrls.append(fk_loc)
            grp_ctrl.append(fk_loc)
            cmds.parentConstraint(fk_loc, joint, mo= True)

            if j != 0:
                cmds.parent(fk_loc_grp, grp_ctrl[j-1])

        return fk_chain


    def _driver_setup(self, driver_chain, ik, fk):
        print(f"Setting up driver for joints: {driver_chain} and IK: {ik} and FK: {fk}")
    
        constraints = []

        for j, joint in enumerate(driver_chain):
            parent_constraint = cmds.parentConstraint(fk[j], ik[j], joint, mo= True)[0]
            constraints.append(parent_constraint)

        return constraints



    def _switch_setup(self, driver, ik, fk, constraints): # consider using color blend nodes instead of constraint. or a mix. need to test and compare if it would actually work doing a mix method.
        print(f"Setting up switch for {self.name}: {driver}")

        switch_target = self.end_joint

        switch_ctrl = RigCtrl(f'{self.name}_IK_FK_Switch_Ctrl', scale = get_scale_by_distance(driver), translate= cmds.xform(switch_target, q= True, t= True, ws= True))
        switch_loc, switch_loc_grp = switch_ctrl._create_loc()
        
        cmds.addAttr(switch_loc, ln= '_____', sn= '___', at='enum', en='SETTINGS' , dv =0)
        cmds.setAttr(f"{switch_loc}._____", e=True, channelBox=True, keyable=False)
        cmds.addAttr(switch_loc, ln= 'IK_Switch', sn= 'IK_FK_Switch', at='double', minValue=0.0, maxValue= 1.0, dv=0.0)
        cmds.setAttr(f"{switch_loc}.IK_Switch", keyable=True)

        reverse_node= cmds.createNode('reverse', n= f'{self.name}_IKFK_REVERSE_01')
        ik_switch_attr = cmds.listAttr(switch_loc)[-1]
        cmds.connectAttr(f"{switch_loc}.{ik_switch_attr}", f"{reverse_node}.input.inputX")
        cmds.connectAttr(f"{reverse_node}.output.outputX", f"{self.fk_ctrls[0]}.visibility")

        cmds.connectAttr(f"{switch_loc}.{ik_switch_attr}", f"{self.ik_ctrls[0]}.visibility")
        cmds.connectAttr(f"{switch_loc}.{ik_switch_attr}", f"{self.ik_ctrls[1]}.visibility")
        cmds.connectAttr(f"{switch_loc}.{ik_switch_attr}", f"{self.ik_ctrls[2]}.visibility")

        for c, con in enumerate(constraints):
            cons_weight= cmds.listAttr(constraints[c])
            cons_ik = cons_weight[-1]
            cons_fk = cons_weight[-2]
            cmds.connectAttr(f"{switch_loc}.{ik_switch_attr}", f"{constraints[c]}.{cons_ik}")
            cmds.connectAttr(f"{reverse_node}.output.outputX", f"{constraints[c]}.{cons_fk}")

        # need to add a arm matching setup here when user switches from ik to fk or vice versa. Expressions with a python script hooked up to an attr?


    def _stretch_setup(self, stretch_chain):
        print(f"Setting up stretch for chain: {stretch_chain}")