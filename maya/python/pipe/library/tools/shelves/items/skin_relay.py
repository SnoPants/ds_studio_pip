"""
skin_relay - relay skin weights between two identical meshes by vertex ID,
with configurable joint remapping (mirror rules + a per-joint remap table).

Shelf entry point:
    from pipe.library.tools.shelves.items import skin_relay
    skin_relay.run()

Or headless:
    skin_relay.relay(source='body_L', target='body_R')
    skin_relay.relay(source='src:body', target='tgt:body', mirror=False,
                     overrides={'spine_01': 'Spine1'})

Select the SOURCE mesh, then the TARGET mesh, and hit Relay. Weights are
matched by vertex index, so the two meshes must share topology and point
order. This is NOT spatial/closest-point matching like Maya's own
copySkinWeights - it is a straight index-for-index transfer.

Modes
-----
Pick one with the radio buttons at the top. Each mode keeps its own remap
table, and the last-used mode is remembered.

    Mirror         Same skeleton, L <-> R. Blank rows use the mirror rules,
                   then the same name. Headless: relay(..., mirror=True).
    Copy Weights   Different skeletons (e.g. the same mesh imported from two
                   FBXs). Bind the target mesh to its own skeleton first.
                   Blank rows use the SAME name only - they are never
                   mirrored, so L can't silently land on R. The mirror rules
                   are only used by "Fill Opposite Side".
                   Headless: relay(..., mirror=False, overrides={...}).

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

Joint resolution order
----------------------
For every source influence the target joint is chosen as follows:

    1. Remap table   - if the row has a name typed in, that name is used and
                       NOTHING else. A typo is reported as NOT FOUND; it never
                       silently falls back to the rules.
    2. Mirror rules  - (Mirror mode only) the mirrored name.
    3. Same name     - the source joint's own name. In Mirror mode a SIDED
                       joint (arm_L) landing here means its opposite (arm_R)
                       doesn't exist: status NO OPPOSITE, weights stay on
                       arm_L. Center joints (spine_01) landing here are fine.
    4. Unresolved    - (NOT FOUND or AMBIGUOUS) weights are dropped and each
                       vertex is renormalized over the joints that did
                       resolve.

With "Strict" on, the relay refuses to run if any row is NOT FOUND,
AMBIGUOUS or NO OPPOSITE.

Status colors: red = needs attention (the three above). Mirror mode:
yellow = opposite found (or typed override), grey = center joint. Copy
mode: blue = typed override, grey = same name.

Where joints are looked up:
  - Mirror mode searches the whole scene (it is one shared skeleton). A
    namespaced exact match ("ns1:arm_R") is tried first, so several loaded
    characters don't collide.
  - Copy mode is scoped to the TARGET skeleton: only joints under the topmost
    joint of each target skinCluster influence's chain are considered
    (grouping transforms above the skeleton are not crossed, so two rigs
    under one group stay separate). That stops "spine_01" from resolving to
    the source skeleton's joint when both rigs share names.
Namespaces are ignored when matching, so a table entry "spine_01" finds
"tgt:spine_01". If a name matches more than one joint the row is AMBIGUOUS
(treated as unresolved) - type a longer DAG path such as "hips|spine_01" to
pick one.

Remap table
-----------
Rows are keyed by the joint's short name (no DAG path, no namespace). Each
mode has one table that persists between sessions; entries for joints not
on the current source mesh are kept, so one table can serve several meshes.
Save/Load JSON and Clear act on the current mode's table. Presets:

    {"version": 1, "overrides": {"spine_01": "Spine1", "neck_01": "Neck"}}

Fill Opposite Side (Copy Weights mode) runs the mirror rules over BOTH names
of every typed entry: "arm_L -> Arm_Left" adds "arm_R -> Arm_Right" (R fills
L too). It never overwrites a filled row and skips center joints. Entries
whose target name has no side token the rules recognize (e.g. "arm_L ->
ArmL01") are listed in a warning instead of guessed.

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
named "cleft_M"; the table shows every rename before anything is written.

Notes
-----
  - Weights are written through the OpenMaya API, which is NOT covered by
    Maya's undo queue. Use "Revert Last". Influences the relay had to add to
    the target skinCluster are not removed by a revert.
  - setWeights() takes PHYSICAL influence indices matching influenceObjects()
    order, NOT the logical indices from indexForInfluenceObject(). Those
    differ on any skinCluster that has had an influence removed.
"""

import json

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

WINDOW = 'skinRelayWin'
EPS = 1e-6

MODE_MIRROR = 'mirror'
MODE_COPY = 'copy'
MODES = (MODE_MIRROR, MODE_COPY)

OPT_RULES = 'skinRelayRules'
OPT_MODE = 'skinRelayMode'
OPT_STRICT = 'skinRelayStrict'
OPT_TABLES = {MODE_MIRROR: 'skinRelayOverridesMirror',
              MODE_COPY: 'skinRelayOverridesCopy'}

# Pre-modes settings, read once to seed the new ones.
LEGACY_OPT_MIRROR = 'skinRelayMirror'
LEGACY_OPT_OVERRIDES = 'skinRelayOverrides'

DEFAULT_RULES = [
    ('*_L', '*_R'),
    ('*_l', '*_r'),
    ('L_*', 'R_*'),
    ('l_*', 'r_*'),
    ('*Left*', '*Right*'),
    ('*left*', '*right*'),
]

HOW_TABLE = 'table'
HOW_MIRROR = 'mirror'
HOW_SAME = 'same'
HOW_NONE = 'NOT FOUND'
HOW_AMBIG = 'AMBIGUOUS'
HOW_NO_OPP = 'NO OPPOSITE'

_LAST_OP = []
_OVERRIDES = {}
_ROWS = {}
_STATE = {'mode': MODE_MIRROR}


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


# ----------------------------------------------------------------------------
# joint resolution (scoped to the target skeleton)
# ----------------------------------------------------------------------------

def joint_key(name):
    """Short name with DAG path and namespace stripped - the remap table key."""
    return name.rpartition('|')[2].rpartition(':')[2]


def _skeleton_root(node):
    """Topmost JOINT in node's parent chain (node itself if its parent isn't one).

    Stops at non-joint transforms on purpose: if both rigs live under a shared
    group, the world-level ancestor would contain the source skeleton too.
    """
    root = node
    parent = cmds.listRelatives(root, parent=True, fullPath=True)
    while parent and cmds.nodeType(parent[0]) == 'joint':
        root = parent[0]
        parent = cmds.listRelatives(root, parent=True, fullPath=True)
    return root


def target_roots(t_skin):
    """Skeleton roots of the target skinCluster's current influences."""
    infs = cmds.ls(cmds.skinCluster(t_skin, query=True, influence=True) or [],
                   long=True) or []
    return set(_skeleton_root(n) for n in infs)


def _under_roots(node, roots):
    return any(node == r or node.startswith(r + '|') for r in roots)


def _in_scope(nodes, roots):
    """roots=None means unscoped: whole scene, joints only (so a mesh or group
    that happens to be named arm_R can't make the lookup ambiguous)."""
    unique = list(dict.fromkeys(nodes))
    if roots is None:
        return [n for n in unique if cmds.nodeType(n) == 'joint']
    return [n for n in unique if _under_roots(n, roots)]


def lookup_scope(t_skin, mirror):
    """Where joints may be found: the whole scene in Mirror mode (one shared
    skeleton), only the target skeleton otherwise.

    Copy mode needs the restriction so a shared name like spine_01 can't land
    on the source skeleton. Mirror mode must NOT have it: a target bound only
    to _L joints, or with a group between limb and root, would hide every _R.
    """
    if mirror:
        return None
    return target_roots(t_skin) if t_skin else set()


def _lookup_joint(name, roots):
    """Find name within roots (None = whole scene). Returns (node, ambiguous).

    A unique exact match (e.g. a typed DAG path or namespaced name) wins.
    Otherwise the short name is searched in every namespace and must match
    exactly one in-scope node - several matches are reported as ambiguous
    rather than guessed.
    """
    if not name or (roots is not None and not roots):
        return None, False
    try:
        exact = _in_scope(cmds.ls(name, long=True) or [], roots)
        if len(exact) == 1:
            return exact[0], False
        loose = cmds.ls(joint_key(name), recursive=True, long=True) or []
    except (RuntimeError, ValueError):
        return None, False
    hits = _in_scope(exact + loose, roots)
    if len(hits) == 1:
        return hits[0], False
    return None, len(hits) > 1


def _resolve_joint(name, roots):
    return _lookup_joint(name, roots)[0]


def resolve_target(s_name, overrides, mirror, pairs, roots):
    """Pick the target joint for one source influence.

    Returns (wanted name, resolved node or None, how) where how is one of
    HOW_TABLE / HOW_MIRROR / HOW_SAME / HOW_NO_OPP / HOW_NONE / HOW_AMBIG.
    An ambiguous step stops the search instead of falling through.

    HOW_NO_OPP: a sided joint whose mirrored name doesn't exist. It falls back
    to the source joint itself (weights stay on the original side), so node is
    set, but it is a problem row - Strict blocks on it.
    """
    typed = (overrides or {}).get(joint_key(s_name), '').strip()
    if typed:
        node, ambiguous = _lookup_joint(typed, roots)
        return typed, node, _how(node, ambiguous, HOW_TABLE)

    want = mirror_name(s_name, pairs) if mirror else s_name
    sided = want != s_name
    if sided:
        node, ambiguous = _lookup_joint(want, roots)
        if node or ambiguous:
            return want, node, _how(node, ambiguous, HOW_MIRROR)

    node, ambiguous = _lookup_joint(s_name, roots)
    if node:
        return want, node, HOW_NO_OPP if sided else HOW_SAME
    if ambiguous:
        return s_name, None, HOW_AMBIG
    return want, None, HOW_NONE


def is_problem(node, how):
    """Rows that need attention: unresolved, ambiguous, or missing opposite."""
    return node is None or how == HOW_NO_OPP


def _how(node, ambiguous, found):
    if node:
        return found
    return HOW_AMBIG if ambiguous else HOW_NONE


# ----------------------------------------------------------------------------
# remap table storage
# ----------------------------------------------------------------------------

def _clean_overrides(data):
    """Keep only non-blank string entries, keyed by short joint name."""
    out = {}
    for k, v in (data or {}).items():
        k, v = str(k).strip(), str(v).strip()
        if k and v:
            out[joint_key(k)] = v
    return out


def _migrate_legacy_table():
    """Move the pre-modes single table into the Copy table (once)."""
    if not cmds.optionVar(exists=LEGACY_OPT_OVERRIDES):
        return
    if not cmds.optionVar(exists=OPT_TABLES[MODE_COPY]):
        cmds.optionVar(stringValue=(OPT_TABLES[MODE_COPY],
                                    cmds.optionVar(query=LEGACY_OPT_OVERRIDES)))
    cmds.optionVar(remove=LEGACY_OPT_OVERRIDES)


def saved_mode():
    """Last used mode. Without one, seed it from the old Mirror checkbox."""
    if cmds.optionVar(exists=OPT_MODE):
        mode = cmds.optionVar(query=OPT_MODE)
        if mode in MODES:
            return mode
    if cmds.optionVar(exists=LEGACY_OPT_MIRROR):
        return MODE_MIRROR if cmds.optionVar(query=LEGACY_OPT_MIRROR) else MODE_COPY
    return MODE_MIRROR


def load_overrides(mode=MODE_COPY):
    """Remap table for a mode from its optionVar, or {}."""
    _migrate_legacy_table()
    opt = OPT_TABLES[mode]
    if not cmds.optionVar(exists=opt):
        return {}
    try:
        return _clean_overrides(json.loads(cmds.optionVar(query=opt)))
    except (ValueError, TypeError, AttributeError):
        cmds.warning('skin_relay: stored %s remap table is corrupt - ignoring it.'
                     % mode)
        return {}


def save_overrides(overrides, mode=MODE_COPY):
    cmds.optionVar(stringValue=(OPT_TABLES[mode],
                                json.dumps(_clean_overrides(overrides),
                                           sort_keys=True)))


def fill_opposite(overrides, pairs):
    """Mirror each typed entry to the opposite side. Writes nothing.

    'arm_L' -> 'Arm_Left' yields 'arm_R' -> 'Arm_Right' (and R fills L, since
    rules are bidirectional). Only entries already in overrides are mirrored,
    and a key that already has an entry is never overwritten.

    Returns (added {src: tgt}, skipped [(src, tgt), ...]) where skipped are
    entries whose source mirrors but whose target name does not, so the
    opposite target can't be inferred.
    """
    typed = _clean_overrides(overrides)
    added, skipped = {}, []
    for src, tgt in sorted(typed.items()):
        m_src = mirror_name(src, pairs)
        if m_src == src or m_src in typed or m_src in added:
            continue
        m_tgt = mirror_name(tgt, pairs)
        if m_tgt == tgt:
            skipped.append((src, tgt))
            continue
        added[m_src] = m_tgt
    return added, skipped


def export_overrides(path, overrides):
    with open(path, 'w') as fh:
        json.dump({'version': 1, 'overrides': _clean_overrides(overrides)},
                  fh, indent=2, sort_keys=True)


def import_overrides(path):
    """Read a preset. Accepts {"overrides": {...}} or a flat {src: tgt} dict."""
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object in %s' % path)
    if isinstance(data.get('overrides'), dict):
        data = data['overrides']
    return _clean_overrides(data)


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


def _skin_of(node):
    shape = _resolve_shape(node)
    return _skin_cluster(shape) if shape else None


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

def build_mapping(source, target, mirror=True, pairs=None, overrides=None):
    """Return [(source joint, wanted name, resolved node or None, how), ...].

    Copy mode (mirror=False) is scoped to the target's skeleton, so the target
    must already have a skinCluster; without one every row is unresolved.
    """
    overrides = _clean_overrides(overrides)
    s_skin = _skin_of(source)
    if not s_skin:
        return []
    roots = lookup_scope(_skin_of(target), mirror)

    rows = []
    for p in _skin_fn(s_skin).influenceObjects():
        name = p.partialPathName()
        want, node, how = resolve_target(name, overrides, mirror, pairs, roots)
        rows.append((name, want, node, how))
    return rows


def _resolve_columns(s_names, t_skin, overrides, mirror, pairs):
    """Map source column -> target node.

    Returns (wanted, problems). problems lists (source, wanted, how) for every
    problem row; NO OPPOSITE rows are in both (they still relay, by fallback).
    """
    roots = lookup_scope(t_skin, mirror)
    wanted, problems = {}, []
    for i, s_name in enumerate(s_names):
        want, node, how = resolve_target(s_name, overrides, mirror, pairs, roots)
        if is_problem(node, how):
            problems.append((s_name, want, how))
        if node is not None:
            wanted[i] = node
    return wanted, problems


def _add_missing_influences(t_skin, nodes):
    existing = set(cmds.ls(cmds.skinCluster(t_skin, query=True, influence=True)
                           or [], long=True))
    missing = [n for n in dict.fromkeys(nodes) if n not in existing]
    for node in missing:
        cmds.skinCluster(t_skin, edit=True, addInfluence=node, weight=0.0)
    if missing:
        print('// skin_relay: added %d influence(s): %s'
              % (len(missing), ', '.join(n.split('|')[-1] for n in missing)))


def _column_map(t_skin, wanted):
    """Add missing influences, then map source column -> target column."""
    _add_missing_influences(t_skin, wanted.values())

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

def _validate_pair(source, target, brute):
    """Return (s_shape, t_shape, s_skin, t_skin, s_count, t_count) or None."""
    s_shape, t_shape = _resolve_shape(source), _resolve_shape(target)
    if not s_shape:
        cmds.error('No mesh shape under source "%s".' % source)
        return None
    if not t_shape:
        cmds.error('No mesh shape under target "%s".' % target)
        return None
    if s_shape == t_shape:
        cmds.error('Source and target are the same mesh.')
        return None

    s_skin, t_skin = _skin_cluster(s_shape), _skin_cluster(t_shape)
    if not s_skin:
        cmds.error('Source "%s" has no skinCluster.' % s_shape.split('|')[-1])
        return None
    if not t_skin:
        cmds.error('Target "%s" has no skinCluster. Bind it to the target '
                   'skeleton first.' % t_shape.split('|')[-1])
        return None

    s_count = cmds.polyEvaluate(s_shape, vertex=True)
    t_count = cmds.polyEvaluate(t_shape, vertex=True)
    if s_count != t_count and not brute:
        cmds.error('Vertex count mismatch: source %d, target %d. Skin Relay '
                   'matches by vertex ID. Tick "Force mismatched counts" to '
                   'copy the shared range anyway.' % (s_count, t_count))
        return None
    return s_shape, t_shape, s_skin, t_skin, s_count, t_count


def _remap_weights(s_weights, s_num, col_map, t_num, n_verts):
    """Build the target weight array. Returns (weights, unweighted count)."""
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
    return new, unweighted


def _report_problems(problems, strict):
    """Warn about problem rows. Returns False if strict should block."""
    if not problems:
        return True
    lines = ', '.join('%s (%s "%s")' % (s, how, w) for s, w, how in problems)
    if strict:
        cmds.error('Strict: %d source joint(s) unresolved or missing their '
                   'opposite: %s. Fill in the remap table or untick Strict.'
                   % (len(problems), lines))
        return False
    dropped = [p for p in problems if p[2] != HOW_NO_OPP]
    kept = [p for p in problems if p[2] == HOW_NO_OPP]
    if dropped:
        cmds.warning('%d source joint(s) unresolved - weights dropped and verts '
                     'renormalized: %s' % (len(dropped), ', '.join(
                         '%s (%s "%s")' % (s, how, w) for s, w, how in dropped)))
    if kept:
        cmds.warning('%d sided joint(s) have no opposite - weights kept on the '
                     'same joint: %s' % (len(kept), ', '.join(
                         '%s (wanted "%s")' % (s, w) for s, w, _ in kept)))
    return True


def relay(source=None, target=None, mirror=True, pairs=None, brute=False,
          overrides=None, strict=False):
    """Copy weights source -> target by vertex ID. Returns True on success.

    overrides: {source short name: target joint name} remap table. A filled-in
    entry always wins over the mirror rules and never falls back.
    strict=True refuses to run if any row is NOT FOUND, AMBIGUOUS or (mirror
    only) NO OPPOSITE; otherwise unresolved weights are dropped and verts
    renormalized, and NO OPPOSITE weights stay on the source-side joint.

    mirror=True looks joints up scene-wide; mirror=False only inside the
    target's skeleton (see "Where joints are looked up").

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

    overrides = _clean_overrides(overrides)
    checked = _validate_pair(source, target, brute)
    if not checked:
        return False
    s_shape, t_shape, s_skin, t_skin, s_count, t_count = checked

    n_verts = min(s_count, t_count)
    report = topology_report(s_shape, t_shape)

    s_fn = _skin_fn(s_skin)
    s_names = [p.partialPathName() for p in s_fn.influenceObjects()]

    wanted, problems = _resolve_columns(s_names, t_skin, overrides, mirror, pairs)
    if not _report_problems(problems, strict):
        return False
    if not wanted:
        cmds.error('No source influence could be matched to a target joint.')
        return False

    s_weights, s_num = s_fn.getWeights(_dag_path(s_shape), _all_verts(n_verts))
    col_map, t_num, t_names = _column_map(t_skin, wanted)
    new, unweighted = _remap_weights(s_weights, s_num, col_map, t_num, n_verts)

    _write(t_skin, t_shape, n_verts, t_num, new)

    print('// skin_relay: %d verts, %d influences, mirror=%s, table entries=%d'
          % (n_verts, len(col_map), mirror, len(overrides or {})))
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
        cmds.warning('%d vert(s) had no weight on any resolved joint - left at '
                     'zero on target.' % unweighted)
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
# ui - helpers
# ----------------------------------------------------------------------------

def _ui_rules():
    return parse_rules(cmds.scrollField('srRules', query=True, text=True))


def _ui_mirror():
    """Mirror mode resolves blank rows through the rules; Copy mode never does."""
    return _STATE['mode'] == MODE_MIRROR


def _persist():
    save_overrides(_OVERRIDES, _STATE['mode'])


def _ui_brute():
    return cmds.checkBoxGrp('srBrute', query=True, value1=True)


def _ui_strict():
    return cmds.checkBoxGrp('srStrict', query=True, value1=True)


def _ui_pair():
    return (cmds.textFieldGrp('srSource', query=True, text=True),
            cmds.textFieldGrp('srTarget', query=True, text=True))


def _save_prefs():
    cmds.optionVar(stringValue=(OPT_RULES,
                                cmds.scrollField('srRules', query=True, text=True)))
    cmds.optionVar(stringValue=(OPT_MODE, _STATE['mode']))
    cmds.optionVar(intValue=(OPT_STRICT, int(_ui_strict())))
    _persist()


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


# ----------------------------------------------------------------------------
# ui - text preview (mesh + vertex ID report)
# ----------------------------------------------------------------------------

def _topology_lines(s_shape, t_shape):
    rep = topology_report(s_shape, t_shape)
    lines = ['']
    if rep['s_count'] != rep['t_count']:
        if _ui_brute():
            lines.append('COUNT MISMATCH (%d vs %d) - will copy vtx[0:%d], '
                         'leave vtx[%d:%d] untouched'
                         % (rep['s_count'], rep['t_count'], rep['overlap'],
                            rep['overlap'], rep['t_count']))
        else:
            lines.append('*** VERT COUNT MISMATCH (%d vs %d) - tick '
                         '"Force mismatched counts" to relay anyway ***'
                         % (rep['s_count'], rep['t_count']))

    flag = 'OK' if rep['pct'] == 100.0 else '*** SUSPECT ***'
    lines.append('VERTEX ID MATCH  %.1f%%  (%d/%d by valence)  %s'
                 % (rep['pct'], rep['matched'], rep['overlap'], flag))
    if rep['first_bad'] >= 0:
        lines.append('    first mismatched ID: vtx[%d]' % rep['first_bad'])
    return lines


def _refresh_report(source, target):
    cmds.textScrollList('srList', edit=True, removeAll=True)
    if not source or not target:
        cmds.textScrollList('srList', edit=True,
                            append=['< pick a source and target mesh >'])
        return

    lines = ['SOURCE  %s  -  %s' % (source, _mesh_info(source)),
             'TARGET  %s  -  %s' % (target, _mesh_info(target))]
    s_shape, t_shape = _resolve_shape(source), _resolve_shape(target)
    if s_shape and t_shape:
        lines += _topology_lines(s_shape, t_shape)
    cmds.textScrollList('srList', edit=True, append=lines)


# ----------------------------------------------------------------------------
# ui - remap table
# ----------------------------------------------------------------------------

_OK_COLOR = (0.27, 0.27, 0.27)
_TABLE_COLOR = (0.25, 0.35, 0.45)
_FOUND_COLOR = (0.55, 0.48, 0.15)
_BAD_COLOR = (0.55, 0.22, 0.22)

_MODE_UI = {
    MODE_MIRROR: {
        'name': 'Mirror',
        'placeholder': '(mirror / same)',
        'blank': 'mirror rules, then same name',
        'title': 'Joint Remap Table (Mirror)  -  exceptions the rules miss '
                 '(Enter to apply)',
        'column': 'New name (blank = mirror)',
        'rules': 'Mirror rules - one per line, "from = to". *_L suffix, L_* '
                 'prefix, *Left* anywhere:',
    },
    MODE_COPY: {
        'name': 'Copy Weights',
        'placeholder': '(same name)',
        'blank': 'same name on the target skeleton (never mirrored)',
        'title': 'Joint Remap Table (Copy Weights)  -  source joint -> target '
                 'skeleton joint (Enter to apply)',
        'column': 'New name (blank = same)',
        'rules': 'Mirror rules - only used by Fill Opposite, never to '
                 'resolve rows:',
    },
}


def _status_text(want, node, how):
    if node is None:
        hint = '  - type a longer path' if how == HOW_AMBIG else ''
        return '%s  (wanted "%s")%s' % (how, want, hint)
    if how == HOW_NO_OPP:
        return '%s  (wanted "%s") - stays on %s' % (how, want, _short(node))
    return '%s -> %s' % (how, _short(node))


def _status_color(node, how):
    """Red = needs attention. Mirror mode: yellow = opposite found / typed,
    grey = center joint. Copy mode: blue = typed, grey = same name."""
    if is_problem(node, how):
        return _BAD_COLOR
    if how == HOW_MIRROR or (how == HOW_TABLE and _ui_mirror()):
        return _FOUND_COLOR
    return _TABLE_COLOR if how == HOW_TABLE else _OK_COLOR


def _set_status(row_id, want, node, how):
    row = _ROWS[row_id]
    row['ok'] = not is_problem(node, how)
    cmds.text(row['status'], edit=True, label=_status_text(want, node, how),
              backgroundColor=_status_color(node, how))


def _update_summary(message=None):
    if message is None:
        bad = sum(1 for r in _ROWS.values() if not r['ok'])
        message = '%d source joint(s), %d need attention, %d table entr%s stored' % (
            len(_ROWS), bad, len(_OVERRIDES), 'y' if len(_OVERRIDES) == 1 else 'ies')
    cmds.text('srTableSummary', edit=True, label=message)


def _clear_table():
    for child in cmds.columnLayout('srTableCol', query=True, childArray=True) or []:
        cmds.deleteUI(child)
    _ROWS.clear()


def _add_row(s_name, want, node, how):
    """One row per source influence; rows sharing a short name share a key."""
    key = joint_key(s_name)
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(170, 170, 190),
                   adjustableColumn=3, parent='srTableCol',
                   columnAttach3=('both', 'both', 'both'),
                   columnOffset3=(2, 2, 2))
    cmds.text(label=s_name, align='left', annotation=s_name)
    field = cmds.textField(text=_OVERRIDES.get(key, ''),
                           placeholderText=_MODE_UI[_STATE['mode']]['placeholder'],
                           annotation='Target joint for %s. Blank = %s.'
                                      % (key, _MODE_UI[_STATE['mode']]['blank']))
    cmds.textField(field, edit=True,
                   changeCommand=lambda text, k=key: _on_cell(k, text))
    status = cmds.text(label='', align='left', enableBackground=True)
    cmds.setParent('..')
    _ROWS[s_name] = {'key': key, 'field': field, 'status': status, 'ok': True}
    _set_status(s_name, want, node, how)


def _rebuild_table(source, target):
    _clear_table()
    if not source:
        _update_summary('< pick a source mesh >')
        return
    rows = build_mapping(source, target, _ui_mirror(), _ui_rules(), _OVERRIDES)
    if not rows:
        _update_summary('< source has no skinCluster >')
        return
    for s_name, want, node, how in rows:
        _add_row(s_name, want, node, how)
    if not _skin_of(target):
        _update_summary('< target has no skinCluster - bind it to the target '
                        'skeleton first >')
        return
    _update_summary()


def _on_cell(key, text):
    """A table cell changed: store it and update every row sharing that key.

    Only the affected rows are edited - the table is not rebuilt here, since
    that would delete the field whose callback is currently running.
    """
    text = text.strip()
    if text:
        _OVERRIDES[key] = text
    else:
        _OVERRIDES.pop(key, None)
    _persist()

    _, target = _ui_pair()
    mirror, rules = _ui_mirror(), _ui_rules()
    roots = lookup_scope(_skin_of(target), mirror)
    for s_name, row in _ROWS.items():
        if row['key'] != key:
            continue
        if cmds.textField(row['field'], query=True, text=True).strip() != text:
            cmds.textField(row['field'], edit=True, text=text)
        want, node, how = resolve_target(s_name, _OVERRIDES, mirror, rules, roots)
        _set_status(s_name, want, node, how)
    _update_summary()


def _on_save_json(*_):
    path = cmds.fileDialog2(fileFilter='Joint remap (*.json)', dialogStyle=2,
                            fileMode=0, caption='Save Joint Remap Table')
    if path:
        export_overrides(path[0], _OVERRIDES)
        print('// skin_relay: saved %d table entr%s to %s'
              % (len(_OVERRIDES), 'y' if len(_OVERRIDES) == 1 else 'ies', path[0]))


def _on_load_json(*_):
    path = cmds.fileDialog2(fileFilter='Joint remap (*.json)', dialogStyle=2,
                            fileMode=1, caption='Load Joint Remap Table')
    if not path:
        return
    try:
        loaded = import_overrides(path[0])
    except (IOError, OSError, ValueError) as exc:
        cmds.warning('skin_relay: could not load %s: %s' % (path[0], exc))
        return
    _OVERRIDES.clear()
    _OVERRIDES.update(loaded)
    _persist()
    refresh_preview()


def _on_clear_table(*_):
    if not _OVERRIDES:
        return
    answer = cmds.confirmDialog(
        title='Clear Remap Table',
        message='Clear all %d %s-mode table entries? This cannot be undone '
                '(Save JSON first if you want to keep them).'
                % (len(_OVERRIDES), _MODE_UI[_STATE['mode']]['name']),
        button=['Clear', 'Cancel'], defaultButton='Cancel',
        cancelButton='Cancel', dismissString='Cancel')
    if answer != 'Clear':
        return
    _OVERRIDES.clear()
    _persist()
    refresh_preview()


def _on_fill_opposite(*_):
    added, skipped = fill_opposite(_OVERRIDES, _ui_rules())
    if skipped:
        cmds.warning('Fill Opposite skipped %d entr%s whose target name has no '
                     'side token for the rules to swap: %s' % (
                         len(skipped), 'y' if len(skipped) == 1 else 'ies',
                         ', '.join('%s -> %s' % pair for pair in skipped)))
    if not added:
        if not skipped:
            cmds.warning('Fill Opposite: nothing to fill - every typed entry is a '
                         'center joint or already has its opposite filled.')
        return
    _OVERRIDES.update(added)
    _persist()
    print('// skin_relay: Fill Opposite added %d entr%s:'
          % (len(added), 'y' if len(added) == 1 else 'ies'))
    for src, tgt in sorted(added.items()):
        print('//    %-28s -> %s' % (src, tgt))
    refresh_preview()


# ----------------------------------------------------------------------------
# ui - actions + window
# ----------------------------------------------------------------------------

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
    source, target = _ui_pair()
    _refresh_report(source, target)
    _rebuild_table(source, target)


def _on_relay(*_):
    _save_prefs()
    source, target = _ui_pair()
    if not source or not target:
        cmds.warning('Pick a source and target first.')
        return
    relay(source, target, _ui_mirror(), _ui_rules(), brute=_ui_brute(),
          overrides=dict(_OVERRIDES), strict=_ui_strict())
    refresh_preview()


def _on_reset_rules(*_):
    cmds.scrollField('srRules', edit=True, text=format_rules(DEFAULT_RULES))
    refresh_preview()


def _set_mode(mode):
    """Swap in the mode's own table and relabel the UI. Does not refresh."""
    _STATE['mode'] = mode
    _OVERRIDES.clear()
    _OVERRIDES.update(load_overrides(mode))
    cmds.optionVar(stringValue=(OPT_MODE, mode))

    ui = _MODE_UI[mode]
    cmds.text('srTableTitle', edit=True, label=ui['title'])
    cmds.text('srColHeader', edit=True, label=ui['column'])
    cmds.text('srRulesLabel', edit=True, label=ui['rules'])
    cmds.button('srFillOpposite', edit=True, visible=(mode == MODE_COPY))


def _on_mode_change(*_):
    mode = MODES[cmds.radioButtonGrp('srMode', query=True, select=True) - 1]
    if mode == _STATE['mode']:
        return
    _persist()
    _set_mode(mode)
    refresh_preview()


def _saved_bool(opt, default):
    return bool(cmds.optionVar(query=opt)) if cmds.optionVar(exists=opt) else default


def _build_mode_section(mode):
    cmds.radioButtonGrp('srMode', label='Mode', numberOfRadioButtons=2,
                        labelArray2=('Mirror  (same skeleton, L <-> R)',
                                     'Copy Weights  (different skeletons)'),
                        columnWidth3=(60, 230, 240),
                        select=MODES.index(mode) + 1,
                        changeCommand=_on_mode_change,
                        annotation='Mirror: blank rows use the mirror rules. '
                                   'Copy Weights: blank rows use the same name and '
                                   'are never mirrored. Each mode keeps its own '
                                   'remap table.')


def _build_mesh_section():
    cmds.textFieldGrp('srSource', label='Source', columnWidth2=(60, 480),
                      adjustableColumn=2, changeCommand=refresh_preview)
    cmds.textFieldGrp('srTarget', label='Target', columnWidth2=(60, 480),
                      adjustableColumn=2, changeCommand=refresh_preview)
    cmds.button(label='Load Selection  (source first, then target)', height=26,
                command=load_selection)


def _build_options_section(rules):
    cmds.checkBoxGrp('srBrute', label='', label1='Force mismatched vert counts',
                     value1=False, columnWidth2=(4, 300),
                     annotation='Copy the shared ID range when vert counts differ. '
                                'Target verts past that range are left untouched.',
                     changeCommand=refresh_preview)
    cmds.checkBoxGrp('srStrict', label='', label1='Strict (block relay if any row '
                                                  'is red)',
                     value1=_saved_bool(OPT_STRICT, False), columnWidth2=(4, 400),
                     annotation='Off: unresolved joints are dropped and verts '
                                'renormalized; NO OPPOSITE joints keep their '
                                'weights. On: the relay refuses to run.')
    cmds.text('srRulesLabel', align='left', label='')
    cmds.scrollField('srRules', height=80, text=rules, wordWrap=False,
                     changeCommand=refresh_preview)
    cmds.button(label='Reset Rules to Default', height=22, command=_on_reset_rules)


def _build_table_section():
    cmds.text('srTableTitle', align='left', font='boldLabelFont', label='')
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(170, 170, 190),
                   adjustableColumn=3, columnAttach3=('both', 'both', 'both'),
                   columnOffset3=(2, 2, 2))
    cmds.text(label='Source joint', align='left', font='smallBoldLabelFont')
    cmds.text('srColHeader', label='', align='left', font='smallBoldLabelFont')
    cmds.text(label='Resolves to', align='left', font='smallBoldLabelFont')
    cmds.setParent('..')
    cmds.scrollLayout('srTableScroll', height=220, childResizable=True)
    cmds.columnLayout('srTableCol', adjustableColumn=True, rowSpacing=1)
    cmds.setParent('..')
    cmds.setParent('..')
    cmds.text('srTableSummary', align='left', label='')
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=4,
                   columnWidth4=(110, 110, 110, 140))
    cmds.button(label='Save JSON...', width=106, command=_on_save_json)
    cmds.button(label='Load JSON...', width=106, command=_on_load_json)
    cmds.button(label='Clear Table', width=106, command=_on_clear_table)
    cmds.button('srFillOpposite', label='Fill Opposite Side',
                command=_on_fill_opposite,
                annotation='Mirror each typed entry with the rules: arm_L -> '
                           'Arm_Left fills arm_R -> Arm_Right. Never overwrites '
                           'a filled row.')
    cmds.setParent('..')


def _build_relay_section():
    cmds.button(label='Refresh Preview', height=24, command=refresh_preview)
    cmds.textScrollList('srList', height=110, font='fixedWidthFont')
    cmds.separator(height=4, style='in')
    cmds.button(label='Relay Weights', height=34, backgroundColor=(0.35, 0.5, 0.35),
                command=_on_relay)
    cmds.button(label='Revert Last', height=24, command=lambda *_: revert_last())
    cmds.text(align='left', label='Matches by vertex ID, not position. Check the '
                                  'ID match % before relaying. API writes bypass '
                                  'Ctrl+Z, use Revert Last.')


def show():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    rules = (cmds.optionVar(query=OPT_RULES)
             if cmds.optionVar(exists=OPT_RULES) else format_rules(DEFAULT_RULES))
    mode = saved_mode()

    cmds.window(WINDOW, title='Skin Relay', widthHeight=(600, 900))
    cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnOffset=('both', 10))
    cmds.separator(height=6, style='none')

    _build_mode_section(mode)
    cmds.separator(height=4, style='in')
    _build_mesh_section()
    cmds.separator(height=4, style='in')
    _build_options_section(rules)
    cmds.separator(height=4, style='in')
    _build_table_section()
    cmds.separator(height=4, style='in')
    _build_relay_section()

    _set_mode(mode)
    load_selection(quiet=True)
    refresh_preview()
    cmds.showWindow(WINDOW)


def run():
    """Shelf entry point."""
    show()
