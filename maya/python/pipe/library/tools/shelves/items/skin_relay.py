"""
skin_relay - relay skin weights between two identical meshes by vertex ID,
with configurable left/right joint remapping.

Shelf entry point:
    from pipe.library.tools.shelves.items import skin_relay
    skin_relay.run()

Or headless:
    skin_relay.relay(source='body_L', target='body_R')

Select the SOURCE mesh, then the TARGET mesh, and hit Relay. Weights are
matched by vertex index, so the two meshes must share topology and point
order. This is NOT spatial/closest-point matching like Maya's own
copySkinWeights - it is a straight index-for-index transfer.

Vertex ID check
---------------
The preview always reports what percentage of vertex IDs actually correspond,
measured by face valence (how many faces each vert belongs to). Valence is
position-independent, so it still works on a mirrored or offset target. 100%
means the IDs line up; anything less means some ID refers to a different
point on each mesh and the weights written there will be wrong.

Mismatched vert counts
----------------------
By default a count mismatch is refused. Tick "Force mismatched vert counts"
to copy the shared range vtx[0:min(src,tgt)] and leave the target's remaining
verts untouched. Whether that is safe depends on WHY the counts differ:

    target = source + added geometry   IDs 0..n-1 still line up, safe
    target = source - deleted geometry everything after the deletion shifts,
                                       and brute force writes garbage

The valence percentage tells you which case you are in before you commit.

Mirror rules
------------
Each rule is a pair of patterns, written "from = to". The '*' marks where the
rest of the name goes, and its position sets how the token is anchored:

    *_L = *_R          suffix    Shoulder_L  ->  Shoulder_R
    L_* = R_*          prefix    L_Shoulder  ->  R_Shoulder
    *Left* = *Right*   anywhere  LeftHand    ->  RightHand

Matching is CASE-SENSITIVE and the first matching rule wins, so list more
specific tokens first. Rules are bidirectional - the same line maps _R back
to _L. Center joints (Root_M, Spine_M, anything matching no rule) map to
themselves.

Both sides of a rule must use the same anchoring, so "*_L = R_*" is rejected.
An anywhere-rule matches substrings, so "*left*" would also fire on a joint
named "cleft_M"; the preview shows every rename before anything is written.

Notes
-----
  - Weights are written through the OpenMaya API, which is NOT covered by
    Maya's undo queue. Use "Revert Last".
  - setWeights() takes PHYSICAL influence indices matching influenceObjects()
    order, NOT the logical indices from indexForInfluenceObject(). Those
    differ on any skinCluster that has had an influence removed.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

WINDOW = 'skinRelayWin'
EPS = 1e-6

OPT_RULES = 'skinRelayRules'
OPT_MIRROR = 'skinRelayMirror'

DEFAULT_RULES = [
    ('*_L', '*_R'),
    ('*_l', '*_r'),
    ('L_*', 'R_*'),
    ('l_*', 'r_*'),
    ('*Left*', '*Right*'),
    ('*left*', '*right*'),
]

_LAST_OP = []


# ----------------------------------------------------------------------------
# name mirroring
# ----------------------------------------------------------------------------

def _split_pattern(pat):
    """Return (token, anchor) for a pattern, or (None, None) if malformed.

        '*_L'     -> ('_L',   'end')    name must end with the token
        'L_*'     -> ('L_',   'start')  name must start with the token
        '*Left*'  -> ('Left', 'any')    token appears anywhere in the name
    """
    parts = pat.split('*')
    if len(parts) == 2:
        pre, suf = parts
        if pre and not suf:
            return pre, 'start'
        if suf and not pre:
            return suf, 'end'
        return None, None
    if len(parts) == 3 and not parts[0] and not parts[2] and parts[1]:
        return parts[1], 'any'
    return None, None


def parse_rules(text):
    """Parse 'a = b' lines into pattern pairs. Blank and # lines are ignored."""
    pairs = []
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line or '=' not in line:
            continue
        a, _, b = line.partition('=')
        a, b = a.strip(), b.strip()
        a_tok, a_anchor = _split_pattern(a)
        b_tok, b_anchor = _split_pattern(b)
        if a_tok and b_tok and a_anchor == b_anchor:
            pairs.append((a, b))
    return pairs


def format_rules(pairs):
    return '\n'.join('%s = %s' % (a, b) for a, b in pairs)


def _apply_pattern(name, src_pat, dst_pat):
    """If name matches src_pat, rewrite it as dst_pat, else None."""
    s_tok, s_anchor = _split_pattern(src_pat)
    d_tok, d_anchor = _split_pattern(dst_pat)
    if not s_tok or not d_tok or s_anchor != d_anchor:
        return None

    if s_anchor == 'end':
        if len(name) > len(s_tok) and name.endswith(s_tok):
            return name[:len(name) - len(s_tok)] + d_tok
        return None

    if s_anchor == 'start':
        if len(name) > len(s_tok) and name.startswith(s_tok):
            return d_tok + name[len(s_tok):]
        return None

    if s_tok in name:
        return name.replace(s_tok, d_tok, 1)
    return None


def mirror_name(name, pairs=None):
    """Mirror a joint name. DAG path and namespace are preserved."""
    pairs = DEFAULT_RULES if pairs is None else pairs

    path, _, leaf = name.rpartition('|')
    ns, sep, short = leaf.rpartition(':')

    for a, b in pairs:
        for src, dst in ((a, b), (b, a)):
            out = _apply_pattern(short, src, dst)
            if out is not None:
                return (path + '|' if path else '') + ns + sep + out

    return name


def _resolve_joint(name):
    """Find a unique existing node for a (possibly mirrored) name."""
    hits = cmds.ls(name, long=True) or []
    if not hits:
        hits = cmds.ls('*:' + name.rpartition(':')[2], long=True) or []
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        cmds.warning('"%s" is ambiguous (%d matches) - using %s.'
                     % (name, len(hits), hits[0]))
        return hits[0]
    return None


# ----------------------------------------------------------------------------
# scene queries
# ----------------------------------------------------------------------------

def _resolve_shape(node):
    if not node or not cmds.objExists(node):
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


def _skin_fn(skin):
    sel = om.MSelectionList()
    sel.add(skin)
    return oma.MFnSkinCluster(sel.getDependNode(0))


def _dag_path(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def _all_verts(count):
    fn = om.MFnSingleIndexedComponent()
    obj = fn.create(om.MFn.kMeshVertComponent)
    fn.addElements(list(range(count)))
    return obj


def _selected_pair():
    objs = [s for s in (cmds.ls(selection=True, long=True) or []) if '.' not in s]
    return (objs[0], objs[1]) if len(objs) == 2 else (None, None)


def _valence(shape):
    """Face-valence per vertex: how many faces each vertex ID belongs to.

    Position-independent, so it survives the mirrored/offset placement that
    Skin Relay exists for. If vertex N has a different valence on the two
    meshes, that ID does not refer to the same point and any weight written
    there is garbage.
    """
    fn = om.MFnMesh(_dag_path(shape))
    counts, indices = fn.getVertices()
    tally = [0] * fn.numVertices
    for v in indices:
        tally[v] += 1
    return tally


def topology_report(s_shape, t_shape):
    """Compare vertex IDs between two meshes. Writes nothing.

    Returns dict: s_count, t_count, overlap, matched, pct, first_bad.
    """
    s_val, t_val = _valence(s_shape), _valence(t_shape)
    overlap = min(len(s_val), len(t_val))

    matched, first_bad = 0, -1
    for v in range(overlap):
        if s_val[v] == t_val[v]:
            matched += 1
        elif first_bad < 0:
            first_bad = v

    return {'s_count': len(s_val), 't_count': len(t_val), 'overlap': overlap,
            'matched': matched, 'first_bad': first_bad,
            'pct': (100.0 * matched / overlap) if overlap else 0.0}


# ----------------------------------------------------------------------------
# mapping
# ----------------------------------------------------------------------------

def build_mapping(source, target=None, mirror=True, pairs=None):
    """Return [(source joint, wanted name, resolved node or None), ...]."""
    s_shape = _resolve_shape(source)
    s_skin = _skin_cluster(s_shape) if s_shape else None
    if not s_skin:
        return []

    rows = []
    for p in _skin_fn(s_skin).influenceObjects():
        name = p.partialPathName()
        want = mirror_name(name, pairs) if mirror else name
        node = _resolve_joint(want)
        if node is None and want != name:
            node = _resolve_joint(name)
            if node is not None:
                want = name + '  (mirror missing, fell back)'
        rows.append((name, want, node))
    return rows


def _column_map(s_names, t_skin, mirror, pairs):
    """Add missing influences, then map source column -> target column."""
    wanted = {}
    for i, s_name in enumerate(s_names):
        want = mirror_name(s_name, pairs) if mirror else s_name
        node = _resolve_joint(want)

        if node is None and want != s_name:
            node = _resolve_joint(s_name)
            if node is not None:
                cmds.warning('Mirror "%s" -> "%s" not found; using "%s".'
                             % (s_name, want, s_name))

        if node is None:
            cmds.warning('No joint for "%s" (wanted "%s") - weights dropped.'
                         % (s_name, want))
            continue
        wanted[i] = node

    existing = set(cmds.ls(cmds.skinCluster(t_skin, query=True, influence=True) or [],
                           long=True))
    missing = [n for n in dict.fromkeys(wanted.values()) if n not in existing]
    for node in missing:
        cmds.skinCluster(t_skin, edit=True, addInfluence=node, weight=0.0)
    if missing:
        print('// skin_relay: added %d influence(s): %s'
              % (len(missing), ', '.join(n.split('|')[-1] for n in missing)))

    # Re-read AFTER adding - physical indices shift when influences are added.
    t_paths = _skin_fn(t_skin).influenceObjects()
    lookup = dict((p.fullPathName(), j) for j, p in enumerate(t_paths))

    col_map = {}
    for i, node in wanted.items():
        if node in lookup:
            col_map[i] = lookup[node]
        else:
            cmds.warning('Influence "%s" missing after add - skipped.' % node)

    return col_map, len(t_paths), [p.partialPathName() for p in t_paths]


# ----------------------------------------------------------------------------
# relay
# ----------------------------------------------------------------------------

def relay(source=None, target=None, mirror=True, pairs=None, brute=False):
    """Copy weights source -> target by vertex ID. Returns True on success.

    brute=False (default) refuses to run when the vertex counts differ.
    brute=True copies the shared ID range 0..min(src,tgt)-1 and leaves the
    target's remaining verts untouched. Use topology_report() first - a count
    mismatch caused by DELETED geometry renumbers every vert after the
    deletion, and brute force will happily write plausible-looking garbage.
    """
    if source is None or target is None:
        source, target = _selected_pair()
        if not source or not target:
            cmds.error('Select exactly 2 objects: SOURCE first, then TARGET.')
            return False

    s_shape, t_shape = _resolve_shape(source), _resolve_shape(target)
    if not s_shape:
        cmds.error('No mesh shape under source "%s".' % source)
        return False
    if not t_shape:
        cmds.error('No mesh shape under target "%s".' % target)
        return False
    if s_shape == t_shape:
        cmds.error('Source and target are the same mesh.')
        return False

    s_skin, t_skin = _skin_cluster(s_shape), _skin_cluster(t_shape)
    if not s_skin:
        cmds.error('Source "%s" has no skinCluster.' % s_shape.split('|')[-1])
        return False
    if not t_skin:
        cmds.error('Target "%s" has no skinCluster. Bind it first.'
                   % t_shape.split('|')[-1])
        return False

    s_count = cmds.polyEvaluate(s_shape, vertex=True)
    t_count = cmds.polyEvaluate(t_shape, vertex=True)
    if s_count != t_count and not brute:
        cmds.error('Vertex count mismatch: source %d, target %d. Skin Relay '
                   'matches by vertex ID. Tick "Force mismatched counts" to '
                   'copy the shared range anyway.' % (s_count, t_count))
        return False

    n_verts = min(s_count, t_count)
    report = topology_report(s_shape, t_shape)

    s_fn = _skin_fn(s_skin)
    s_names = [p.partialPathName() for p in s_fn.influenceObjects()]
    s_weights, s_num = s_fn.getWeights(_dag_path(s_shape), _all_verts(n_verts))

    col_map, t_num, t_names = _column_map(s_names, t_skin, mirror, pairs)
    if not col_map:
        cmds.error('No source influence could be matched to a target joint.')
        return False

    new = [0.0] * (n_verts * t_num)
    unweighted = 0
    touched = sorted(set(col_map.values()))

    for r in range(n_verts):
        s_base, t_base = r * s_num, r * t_num
        total = 0.0
        for i, j in col_map.items():
            w = s_weights[s_base + i]
            if w > EPS:
                new[t_base + j] += w
                total += w
        if total <= EPS:
            unweighted += 1
        elif abs(total - 1.0) > EPS:
            for j in touched:
                new[t_base + j] /= total

    _write(t_skin, t_shape, n_verts, t_num, new)

    print('// skin_relay: %d verts, %d influences, mirror=%s' %
          (n_verts, len(col_map), mirror))
    for i, j in sorted(col_map.items()):
        print('//    %-28s -> %s' % (s_names[i], t_names[j]))

    if report['pct'] < 100.0:
        cmds.warning('Vertex IDs only %.1f%% valence-matched (%d/%d); first '
                     'mismatch at vtx[%d]. Weights past that point are likely '
                     'wrong - check before saving.'
                     % (report['pct'], report['matched'], report['overlap'],
                        report['first_bad']))
    if s_count != t_count:
        cmds.warning('Count mismatch: copied vtx[0:%d]. Target vtx[%d:%d] left '
                     'untouched.' % (n_verts, n_verts, t_count))
    if unweighted:
        cmds.warning('%d source vert(s) had no weight - left at zero on target.'
                     % unweighted)
    return True


def _write(skin, shape, vert_count, num_inf, weights):
    normalize = cmds.getAttr(skin + '.normalizeWeights')

    locks = {}
    for inf in cmds.skinCluster(skin, query=True, influence=True) or []:
        attr = inf + '.liw'
        if cmds.objExists(attr) and not cmds.getAttr(attr, lock=True):
            locks[attr] = cmds.getAttr(attr)
            cmds.setAttr(attr, False)

    fn = _skin_fn(skin)
    dag = _dag_path(shape)
    comp = _all_verts(vert_count)
    idx = om.MIntArray(list(range(num_inf)))

    cmds.setAttr(skin + '.normalizeWeights', 0)
    cmds.undoInfo(openChunk=True, chunkName='skinRelay')
    try:
        old = fn.setWeights(dag, comp, idx, om.MDoubleArray(weights), False, True)
        _LAST_OP[:] = [{'fn': fn, 'dag': dag, 'comp': comp, 'idx': idx, 'old': old}]
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.setAttr(skin + '.normalizeWeights', normalize)
        for attr, val in locks.items():
            cmds.setAttr(attr, val)


def revert_last():
    """Undo the last relay. API writes bypass Ctrl+Z."""
    if not _LAST_OP:
        cmds.warning('Nothing to revert.')
        return
    for r in _LAST_OP:
        r['fn'].setWeights(r['dag'], r['comp'], r['idx'], r['old'], False, False)
    _LAST_OP[:] = []
    print('// skin_relay: reverted.')


# ----------------------------------------------------------------------------
# ui
# ----------------------------------------------------------------------------

def _ui_rules():
    return parse_rules(cmds.scrollField('srRules', query=True, text=True))


def _ui_mirror():
    return cmds.checkBoxGrp('srMirror', query=True, value1=True)


def _ui_brute():
    return cmds.checkBoxGrp('srBrute', query=True, value1=True)


def _save_prefs():
    cmds.optionVar(stringValue=(OPT_RULES,
                                cmds.scrollField('srRules', query=True, text=True)))
    cmds.optionVar(intValue=(OPT_MIRROR, int(_ui_mirror())))


def _short(node):
    """Shortest name that still uniquely identifies the node."""
    if not node:
        return ''
    hits = cmds.ls(node, shortNames=True) or []
    return hits[0] if hits else node.split('|')[-1]


def _mesh_info(node):
    shape = _resolve_shape(node)
    if not shape:
        return 'not a mesh'
    skin = _skin_cluster(shape)
    return '%d verts, %s' % (cmds.polyEvaluate(shape, vertex=True),
                             skin if skin else 'NO skinCluster')


def load_selection(*_, **kw):
    source, target = _selected_pair()
    if not source:
        if not kw.get('quiet'):
            cmds.warning('Select exactly 2 objects: SOURCE first, then TARGET.')
        return
    cmds.textFieldGrp('srSource', edit=True, text=_short(source))
    cmds.textFieldGrp('srTarget', edit=True, text=_short(target))
    refresh_preview()


def refresh_preview(*_):
    cmds.textScrollList('srList', edit=True, removeAll=True)
    source = cmds.textFieldGrp('srSource', query=True, text=True)
    target = cmds.textFieldGrp('srTarget', query=True, text=True)

    if not source or not target:
        cmds.textScrollList('srList', edit=True,
                            append=['< pick a source and target mesh >'])
        return

    s_shape, t_shape = _resolve_shape(source), _resolve_shape(target)
    cmds.textScrollList('srList', edit=True, append=[
        'SOURCE  %s  -  %s' % (source, _mesh_info(source)),
        'TARGET  %s  -  %s' % (target, _mesh_info(target))])

    if s_shape and t_shape:
        rep = topology_report(s_shape, t_shape)
        rows_top = ['']
        if rep['s_count'] != rep['t_count']:
            if _ui_brute():
                rows_top.append('COUNT MISMATCH (%d vs %d) - will copy vtx[0:%d], '
                                'leave vtx[%d:%d] untouched'
                                % (rep['s_count'], rep['t_count'], rep['overlap'],
                                   rep['overlap'], rep['t_count']))
            else:
                rows_top.append('*** VERT COUNT MISMATCH (%d vs %d) - tick '
                                '"Force mismatched counts" to relay anyway ***'
                                % (rep['s_count'], rep['t_count']))

        flag = 'OK' if rep['pct'] == 100.0 else '*** SUSPECT ***'
        rows_top.append('VERTEX ID MATCH  %.1f%%  (%d/%d by valence)  %s'
                        % (rep['pct'], rep['matched'], rep['overlap'], flag))
        if rep['first_bad'] >= 0:
            rows_top.append('    first mismatched ID: vtx[%d]' % rep['first_bad'])
        cmds.textScrollList('srList', edit=True, append=rows_top)

        if rep['s_count'] != rep['t_count'] and not _ui_brute():
            return

    rows = build_mapping(source, target, _ui_mirror(), _ui_rules())
    if not rows:
        cmds.textScrollList('srList', edit=True,
                            append=['', '< source has no skinCluster >'])
        return

    missing = sum(1 for _, _, node in rows if node is None)
    cmds.textScrollList('srList', edit=True, append=[
        '', 'JOINT MAPPING  (%d influences, %d unresolved)' % (len(rows), missing), ''])
    for name, want, node in rows:
        cmds.textScrollList('srList', edit=True, append=[
            '  %-26s -> %-26s %s' % (name, want, '' if node else '*** NOT FOUND ***')])


def _on_relay(*_):
    _save_prefs()
    source = cmds.textFieldGrp('srSource', query=True, text=True)
    target = cmds.textFieldGrp('srTarget', query=True, text=True)
    if not source or not target:
        cmds.warning('Pick a source and target first.')
        return
    relay(source, target, _ui_mirror(), _ui_rules(), brute=_ui_brute())
    refresh_preview()


def _on_reset_rules(*_):
    cmds.scrollField('srRules', edit=True, text=format_rules(DEFAULT_RULES))
    refresh_preview()


def show():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    rules = (cmds.optionVar(query=OPT_RULES)
             if cmds.optionVar(exists=OPT_RULES) else format_rules(DEFAULT_RULES))
    mirror = (bool(cmds.optionVar(query=OPT_MIRROR))
              if cmds.optionVar(exists=OPT_MIRROR) else True)

    cmds.window(WINDOW, title='Skin Relay', widthHeight=(560, 620))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=('both', 10))
    cmds.separator(height=6, style='none')

    cmds.textFieldGrp('srSource', label='Source', columnWidth2=(60, 440),
                      adjustableColumn=2, changeCommand=refresh_preview)
    cmds.textFieldGrp('srTarget', label='Target', columnWidth2=(60, 440),
                      adjustableColumn=2, changeCommand=refresh_preview)
    cmds.button(label='Load Selection  (source first, then target)', height=26,
                command=load_selection)

    cmds.separator(height=4, style='in')
    cmds.checkBoxGrp('srMirror', label='', label1='Mirror joint names',
                     value1=mirror, columnWidth2=(4, 300), changeCommand=refresh_preview)
    cmds.checkBoxGrp('srBrute', label='', label1='Force mismatched vert counts',
                     value1=False, columnWidth2=(4, 300),
                     annotation='Copy the shared ID range when vert counts differ. '
                                'Target verts past that range are left untouched.',
                     changeCommand=refresh_preview)
    cmds.text(align='left', label='Mirror rules - one per line, "from = to". '
                                  '*_L suffix, L_* prefix, *Left* anywhere:')
    cmds.scrollField('srRules', height=92, text=rules, wordWrap=False,
                     changeCommand=refresh_preview)
    cmds.button(label='Reset Rules to Default', height=22, command=_on_reset_rules)

    cmds.separator(height=4, style='in')
    cmds.button(label='Refresh Preview', height=24, command=refresh_preview)
    cmds.textScrollList('srList', height=190, font='fixedWidthFont')

    cmds.separator(height=4, style='in')
    cmds.button(label='Relay Weights', height=34, backgroundColor=(0.35, 0.5, 0.35),
                command=_on_relay)
    cmds.button(label='Revert Last', height=24, command=lambda *_: revert_last())
    cmds.text(align='left', label='Matches by vertex ID, not position. Check the '
                                  'ID match % before relaying. API writes bypass '
                                  'Ctrl+Z, use Revert Last.')

    load_selection(quiet=True)
    refresh_preview()
    cmds.showWindow(WINDOW)


def run():
    """Shelf entry point."""
    show()
