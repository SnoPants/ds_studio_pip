"""
influence_editor - bulk edit skin weights for pattern-matched influences.

Shelf entry point:
    from pipe.library.tools.shelves.items import influence_editor
    influence_editor.run()

Select verts (or a skinned mesh in object mode), type an influence pattern
like "Shoulder*", hit Apply. Replaces drag-selecting thousands of cells in
the Component Editor.

Notes:
  - Pattern matching is case-insensitive and supports fnmatch wildcards
    (* ? [seq]). Separate multiple patterns with commas or spaces.
  - Weights are written through the OpenMaya API, which is NOT covered by
    Maya's undo queue. Use the tool's own "Revert Last" button.
  - setWeights() takes PHYSICAL influence indices matching influenceObjects()
    order, NOT the logical matrix indices from indexForInfluenceObject().
    Those differ on any skinCluster that has had an influence removed, and
    passing logical indices raises kInvalidParameter.
"""

import fnmatch

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

WINDOW = 'influenceEditorWin'
EPS = 1e-6

_LAST_OP = []


# ----------------------------------------------------------------------------
# scene queries
# ----------------------------------------------------------------------------

def _resolve_shape(node):
    if not cmds.objExists(node):
        return None
    if cmds.nodeType(node) == 'mesh':
        return cmds.ls(node, long=True)[0]
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True,
                                fullPath=True, type='mesh') or []
    return shapes[0] if shapes else None


def _skin_cluster(shape):
    hist = cmds.listHistory(shape) or []
    skins = cmds.ls(hist, type='skinCluster') or []
    return skins[0] if skins else None


def _gather_targets():
    """Map {mesh shape: sorted vert ids}. Object-mode selection means all verts."""
    sel = cmds.ls(selection=True, long=True) or []
    if not sel:
        return {}

    targets = {}

    for v in cmds.filterExpand(sel, selectionMask=31, fullPath=True) or []:
        node, idx = v.rsplit('.vtx[', 1)
        shape = _resolve_shape(node)
        if shape:
            targets.setdefault(shape, set()).add(int(idx.rstrip(']')))

    for obj in [s for s in sel if '.' not in s]:
        shape = _resolve_shape(obj)
        if shape:
            targets[shape] = set(range(cmds.polyEvaluate(shape, vertex=True)))

    return dict((s, sorted(ids)) for s, ids in targets.items())


def _matched_indices(inf_names, patterns):
    pats = [p.strip().lower() for p in patterns.replace(',', ' ').split() if p.strip()]
    out = set()
    for i, name in enumerate(inf_names):
        short = name.split('|')[-1].split(':')[-1].lower()
        for p in pats:
            if fnmatch.fnmatch(short, p) or fnmatch.fnmatch(name.lower(), p):
                out.add(i)
                break
    return out


def _skin_fn(skin):
    sel = om.MSelectionList()
    sel.add(skin)
    return oma.MFnSkinCluster(sel.getDependNode(0))


def _dag_path(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def _components(vert_ids):
    fn = om.MFnSingleIndexedComponent()
    obj = fn.create(om.MFn.kMeshVertComponent)
    fn.addElements(vert_ids)
    return obj


# ----------------------------------------------------------------------------
# weight math
# ----------------------------------------------------------------------------

def _compute_rows(weights, num_inf, matched, mode, value):
    """Return (new flat weight list, orphaned row indices).

    Orphaned rows are left at their original values; the caller decides
    whether to skip or force-zero them.
    """
    new = list(weights)
    orphans = []
    m_list = sorted(matched)
    unmatched = [i for i in range(num_inf) if i not in matched]

    for r in range(len(weights) // num_inf):
        base = r * num_inf
        row = weights[base:base + num_inf]
        out = list(row)

        if mode == 'scale':
            for i in m_list:
                out[i] = row[i] * value
        else:
            for i in m_list:
                out[i] = value
            m_total = value * len(m_list)
            if m_total >= 1.0 - EPS:
                for i in m_list:
                    out[i] = out[i] / m_total if m_total > EPS else 0.0
                for i in unmatched:
                    out[i] = 0.0
            else:
                u_sum = sum(row[i] for i in unmatched)
                if u_sum > EPS:
                    fill = 1.0 - m_total
                    for i in unmatched:
                        out[i] = row[i] / u_sum * fill
                else:
                    for i in unmatched:
                        out[i] = 0.0

        total = sum(out)
        if total <= EPS:
            orphans.append(r)
            continue

        out = [0.0 if w / total < EPS else w / total for w in out]
        total = sum(out)
        if total <= EPS:
            orphans.append(r)
            continue

        for i in range(num_inf):
            new[base + i] = out[i] / total

    return new, orphans


# ----------------------------------------------------------------------------
# apply
# ----------------------------------------------------------------------------

def _build_plans(patterns, mode, value):
    plans = []
    orphan_verts = []

    for shape, vert_ids in _gather_targets().items():
        skin = _skin_cluster(shape)
        if not skin:
            cmds.warning('No skinCluster on %s - skipped.' % shape.split('|')[-1])
            continue

        fn = _skin_fn(skin)
        inf_paths = fn.influenceObjects()
        inf_names = [p.partialPathName() for p in inf_paths]
        matched = _matched_indices(inf_names, patterns)
        if not matched:
            cmds.warning('No influence on %s matched "%s" - skipped.' % (skin, patterns))
            continue

        dag = _dag_path(shape)
        comp = _components(vert_ids)
        weights, num_inf = fn.getWeights(dag, comp)
        new, orphan_rows = _compute_rows(list(weights), num_inf, matched, mode, value)

        plans.append({
            'skin': skin, 'shape': shape, 'fn': fn, 'dag': dag, 'comp': comp,
            'inf_idx': om.MIntArray(list(range(num_inf))),
            'num_inf': num_inf, 'new': new, 'orphans': orphan_rows,
            'vert_ids': vert_ids, 'matched': sorted(inf_names[i] for i in matched),
        })
        orphan_verts += ['%s.vtx[%d]' % (shape, vert_ids[r]) for r in orphan_rows]

    return plans, orphan_verts


def _write(plan):
    skin = plan['skin']
    normalize = cmds.getAttr(skin + '.normalizeWeights')

    locks = {}
    for inf in cmds.skinCluster(skin, query=True, influence=True) or []:
        attr = inf + '.liw'
        if cmds.objExists(attr) and not cmds.getAttr(attr, lock=True):
            locks[attr] = cmds.getAttr(attr)
            cmds.setAttr(attr, False)

    cmds.setAttr(skin + '.normalizeWeights', 0)
    try:
        old = plan['fn'].setWeights(plan['dag'], plan['comp'], plan['inf_idx'],
                                    om.MDoubleArray(plan['new']), False, True)
        return {'fn': plan['fn'], 'dag': plan['dag'], 'comp': plan['comp'],
                'inf_idx': plan['inf_idx'], 'old': old}
    finally:
        cmds.setAttr(skin + '.normalizeWeights', normalize)
        for attr, val in locks.items():
            cmds.setAttr(attr, val)


def apply_weights(patterns, mode, value):
    if not patterns.strip():
        cmds.warning('Enter at least one influence name or pattern.')
        return

    plans, orphan_verts = _build_plans(patterns, mode, value)
    if not plans:
        cmds.warning('Nothing to do. Select verts, or a skinned mesh in object mode.')
        return

    force = False
    if orphan_verts:
        answer = cmds.confirmDialog(
            title='Orphaned Vertices',
            message=('%d vert(s) are influenced ONLY by matched influences.\n'
                     'Applying would leave them with no influence at all,\n'
                     'collapsing them to the origin.\n\n'
                     'Nothing has been changed yet.' % len(orphan_verts)),
            button=['Skip Those Verts', 'Zero Anyway', 'Cancel'],
            defaultButton='Skip Those Verts', cancelButton='Cancel',
            dismissString='Cancel')
        if answer == 'Cancel':
            return
        force = (answer == 'Zero Anyway')

    if force:
        for plan in plans:
            for r in plan['orphans']:
                base = r * plan['num_inf']
                for i in range(plan['num_inf']):
                    plan['new'][base + i] = 0.0

    restores = []
    cmds.undoInfo(openChunk=True, chunkName='influenceEditor')
    try:
        for plan in plans:
            restores.append(_write(plan))
    finally:
        cmds.undoInfo(closeChunk=True)

    _LAST_OP[:] = restores

    touched = sum(len(p['vert_ids']) - (0 if force else len(p['orphans'])) for p in plans)
    print('// influence_editor: %d vert(s) across %d mesh(es), influences: %s'
          % (touched, len(plans), ', '.join(plans[0]['matched'])))

    if orphan_verts:
        cmds.select(orphan_verts, replace=True)
        cmds.warning('%d orphaned vert(s) %s - they are selected now.'
                     % (len(orphan_verts), 'zeroed' if force else 'skipped'))


def revert_last():
    if not _LAST_OP:
        cmds.warning('Nothing to revert.')
        return
    for r in _LAST_OP:
        r['fn'].setWeights(r['dag'], r['comp'], r['inf_idx'], r['old'], False, False)
    _LAST_OP[:] = []
    print('// influence_editor: reverted.')


# ----------------------------------------------------------------------------
# ui
# ----------------------------------------------------------------------------

def _mode_key():
    return 'scale' if cmds.optionMenuGrp('infEdMode', query=True, select=True) == 1 else 'set'


def _on_mode_change(*_):
    if _mode_key() == 'scale':
        cmds.floatFieldGrp('infEdValue', edit=True, label='Percent')
        cmds.text('infEdHint', edit=True,
                  label='0 = zero out.  50 = halve matched weights.  100 = no change.')
    else:
        cmds.floatFieldGrp('infEdValue', edit=True, label='Weight')
        cmds.text('infEdHint', edit=True,
                  label='Each matched influence is set to this weight (0-1), even if it had none.')


def refresh_preview(*_):
    patterns = cmds.textFieldGrp('infEdPattern', query=True, text=True)
    cmds.textScrollList('infEdList', edit=True, removeAll=True)

    targets = _gather_targets()
    if not targets:
        cmds.textScrollList('infEdList', edit=True,
                            append=['< select verts, or a skinned mesh in object mode >'])
        return

    for shape, vert_ids in sorted(targets.items()):
        name = shape.split('|')[-1]
        skin = _skin_cluster(shape)
        if not skin:
            cmds.textScrollList('infEdList', edit=True, append=['%s  - no skinCluster' % name])
            continue
        infs = [p.partialPathName() for p in _skin_fn(skin).influenceObjects()]
        matched = _matched_indices(infs, patterns)
        cmds.textScrollList('infEdList', edit=True, append=[
            '%s  (%d verts, %d/%d influences matched)' % (name, len(vert_ids),
                                                          len(matched), len(infs))])
        for i in sorted(matched):
            cmds.textScrollList('infEdList', edit=True, append=['      ' + infs[i]])
        if not matched:
            cmds.textScrollList('infEdList', edit=True, append=['      < no match >'])


def _on_apply(*_):
    patterns = cmds.textFieldGrp('infEdPattern', query=True, text=True)
    mode = _mode_key()
    value = cmds.floatFieldGrp('infEdValue', query=True, value1=True)
    if mode == 'scale':
        value = max(0.0, min(100.0, value)) / 100.0
    else:
        value = max(0.0, min(1.0, value))
    apply_weights(patterns, mode, value)
    refresh_preview()


def show():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    cmds.window(WINDOW, title='Influence Editor', widthHeight=(460, 440))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=('both', 10))
    cmds.separator(height=6, style='none')

    cmds.textFieldGrp('infEdPattern', label='Influences', text='Shoulder*',
                      columnWidth2=(70, 350), adjustableColumn=2,
                      changeCommand=refresh_preview)
    cmds.button(label='Preview Matches', height=26, command=refresh_preview)
    cmds.textScrollList('infEdList', height=170, font='fixedWidthFont')

    cmds.separator(height=4, style='in')
    cmds.optionMenuGrp('infEdMode', label='Mode', columnWidth2=(70, 140),
                       changeCommand=_on_mode_change)
    cmds.menuItem(label='Scale by %')
    cmds.menuItem(label='Set to')
    cmds.floatFieldGrp('infEdValue', label='Percent', numberOfFields=1, value1=0.0,
                       columnWidth2=(70, 90))
    cmds.text('infEdHint', align='left', label='')

    cmds.separator(height=4, style='in')
    cmds.button(label='Apply', height=34, backgroundColor=(0.35, 0.5, 0.35), command=_on_apply)
    cmds.button(label='Revert Last', height=24, command=lambda *_: revert_last())
    cmds.text(align='left', label='API writes bypass Ctrl+Z - use Revert Last.')

    _on_mode_change()
    refresh_preview()
    cmds.showWindow(WINDOW)


def run():
    """Shelf entry point."""
    show()
