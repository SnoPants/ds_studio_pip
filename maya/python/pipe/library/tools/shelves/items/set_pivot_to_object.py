import maya.cmds as cmds
def parent_and_reset_with_options(apply_t=True, apply_r=True):
    sel = cmds.ls(orderedSelection=True)
    
    joint = sel.pop(-1)
    
    if cmds.objectType(joint) != 'joint':
        cmds.warning(f'Your last selection "{joint}" is not a joint. Please select a joint as your last selection')
        return
        
    for s, sdx in enumerate(sel):
        print(sdx)
        has_parent = cmds.listRelatives(sdx, parent= True) or []
        print(has_parent)
        cmds.parent(sdx, joint)
        cmds.makeIdentity(sdx, apply=True, t=1 if apply_t else 0, r=1 if apply_r else 0, s=0, n=0)

        pivot_pos = cmds.xform(joint, q=True, ws=True, rp=True)
        cmds.xform(sdx, ws=True, pivots=pivot_pos)

        if has_parent:
            cmds.parent(sdx, has_parent[0])
        else:
            cmds.parent(sdx, w=True)
    
        mode = "Both" if (apply_t and apply_r) else ("Translation only" if apply_t else "Rotation only")
        print(f"[{mode}] Successfully adjusted pivot from {sdx} to {joint}.")

# -------------------------
# Simple UI
# -------------------------
def show_parent_reset_ui():
    win = "ParentResetUI"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(win, title="Parent + Reset Options", sizeable=False, mnb=False, mxb=False)
    col = cmds.columnLayout(adj=True, rs=6, cat=("both", 10))

    cmds.text(label="Choose what to transform/freeze on the FIRST selected object:")

    # 3-option radio group: Translation only, Rotation only, Both
    # We'll store this control's name to query later.
    mode_grp = cmds.radioButtonGrp(
        labelArray3=["Translation only", "Rotation only", "Both"],
        numberOfRadioButtons=3,
        sl=3,  # default to Both
        cw4=[1, 120, 120, 80],  # column widths (label column is 1px since no label)
        label="",  # no left label
    )

    def _apply_callback(*_):
        sel_mode = cmds.radioButtonGrp(mode_grp, q=True, sl=True)
        # Map selection to booleans
        if sel_mode == 1:      # Translation only
            t_flag, r_flag = True, False
        elif sel_mode == 2:    # Rotation only
            t_flag, r_flag = False, True
        else:                  # Both
            t_flag, r_flag = True, True

        parent_and_reset_with_options(apply_t=t_flag, apply_r=r_flag)

    cmds.button(label="Apply", h=32, c=_apply_callback)

    cmds.separator(h=8, style="none")
    cmds.text(label="Usage: select FIRST (child) then SECOND (temporary parent).")
    cmds.separator(h=8, style="none")

    cmds.showWindow(win)

show_parent_reset_ui()