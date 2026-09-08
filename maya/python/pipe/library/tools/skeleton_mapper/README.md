# Skeleton Mapper

`skeleton_mapper` is a Maya tool for defining a reusable relationship between mesh vertices and skeleton joints. Artists will be able to organize joints into regions, assign vertices to each joint, validate the mapping, save or load it as JSON, and build a joint hierarchy from the stored data.

The package should live inside the existing pipeline repo and remain self-contained until a component proves useful enough to promote into a shared library.

## Hierarchy navigation

Click a joint's arrow to expand or collapse it normally. Hold **Shift** while clicking the arrow to expand or collapse that joint and all its descendants, leaving unrelated branches unchanged. **Expand All** still opens the entire hierarchy. These controls only change the tree display, not joint parent relationships.

## Proposed structure

```text
skeleton_mapper/
├── __init__.py
├── ui.py
├── model.py
├── maya_utils.py
├── builder.py
├── validator.py
├── io_utils.py
└── README.md
```

## Module responsibilities

### `ui.py`

- Define Qt widgets, layouts, panels, and user-facing signals.
- Display regions, joints, vertex assignments, hierarchy, and validation results.
- Collect user intent and delegate work to the other modules.
- Avoid embedding Maya scene operations, JSON handling, or skeleton-building logic.

### `model.py`

- Define the tool's Maya-independent data model, such as `MappingData`, `RegionData`, and `JointData`.
- Store mesh identity once on `SkeletonData`, plus regions, joint names, parent relationships, and vertex IDs.
- Expose `joints()` to walk every joint across all regions, so callers do not re-nest the loop.
- Give every joint *and every region* a stable `uid` at creation, independent of its name.
- Expose `all_joint_names()` and `all_region_names()` so the UI can validate names without reaching across widgets.
- Own the naming rules in `JointData.validate_name()`, which returns the reason a name is unusable or `""` when it is valid. `rename()` calls it internally and the UI calls it for feedback, so there is one implementation of the rules rather than one per caller.
- Own the orientation configuration: a global default, with optional per-region overrides.
- Convert model objects to and from plain dictionaries when useful.
- Contain no `maya.cmds` calls or Qt widgets.

### `maya_utils.py`

- Read the selected mesh and selected mesh vertices.
- Convert components to stable vertex IDs.
- Restore component selections for inspection or editing.
- Query vertex positions and calculate placement points, such as an average center.
- Isolate Maya selection and scene-query behavior from the rest of the tool.

### `builder.py`

- Create joints from validated mapping data.
- Calculate and apply joint positions from assigned vertices.
- Apply parent relationships in a safe order.
- Rebuild idempotently: locate prior output by its `uid` attribute, then replace it.
- Refuse to rebuild joints that have downstream dependents, reporting what is connected.
- Later support joint orientation, naming rules, namespaces, and weight-preserving updates.

### `validator.py`

- Detect duplicate or invalid joint names.
- Detect duplicate `uid` values, which `cmds.duplicate()` can introduce.
- Report joints with no assigned vertices.
- Verify that the target mesh and referenced vertex IDs are valid.
- Detect missing parent references, self-parenting, and hierarchy cycles.
- Report existing scene dependents that would block a rebuild.
- Return structured results that both the UI and automated checks can consume.

### `io_utils.py`

- Serialize mappings to JSON and deserialize them back into model objects.
- Handle schema-version checks and future migrations.
- Keep file-dialog UI outside this module; accept explicit paths where possible.
- Produce actionable errors for missing, malformed, or incompatible files.

## Mock-up code cross-reference

The current UI mock-up is [`skeleton_mapper_example.py`](./skeleton_mapper_example.py). The references below point to the code that already demonstrates a responsibility or marks its intended integration point. Line numbers describe the current saved version and may move as the example is edited.

| Planned area | Where to look in the mock-up | Current status |
| --- | --- | --- |
| `ui.py` | [`JointRowWidget`, lines 11–520](./skeleton_mapper_example.py#L11-L520); [`RegionWidget`, lines 523–999](./skeleton_mapper_example.py#L523-L999); 
[`HierarchyTree`, lines 1004–1057](./skeleton_mapper_example.py#L1004-L1057); [`JointPlacementMapper`, lines 1065–2266](./skeleton_mapper_example.py#L1065-L2266) | Implemented as the main substance of the mock-up. These classes would move into `ui.py`. |
| `model.py` | Temporary joint state at [lines 21–44](./skeleton_mapper_example.py#L21-L44); rename/model note at [lines 373–404](./skeleton_mapper_example.py#L373-L404); region and joint model hooks at [lines 773–892](./skeleton_mapper_example.py#L773-L892); temporary `parent_map` at [lines 1094–1113](./skeleton_mapper_example.py#L1094-L1113); assembled mapping data at [lines 2008–2071](./skeleton_mapper_example.py#L2008-L2071) | No separate model exists yet. Widgets currently own `joint_name`, `vertex_ids`, region lists, and hierarchy data. |
| `maya_utils.py` | Set selected vertices at [lines 406–466](./skeleton_mapper_example.py#L406-L466); reselect vertices at [lines 469–498](./skeleton_mapper_example.py#L469-L498); target-mesh selection at [lines 1477–1510](./skeleton_mapper_example.py#L1477-L1510); placement-center example at [lines 2220–2230](./skeleton_mapper_example.py#L2220-L2230) | Only comments, example calls, and temporary mock data exist. There are no working Maya queries yet. |
| `builder.py` | Build button creation/connections at [lines 1404–1421](./skeleton_mapper_example.py#L1404-L1421) and [lines 1472–1473](./skeleton_mapper_example.py#L1472-L1473); recommended build flow at [lines 2193–2265](./skeleton_mapper_example.py#L2193-L2265) | Not implemented. The callback gathers and validates data, then prints a TODO instead of creating Maya joints. |
| `validator.py` | Validation integration point at [lines 2156–2190](./skeleton_mapper_example.py#L2156-L2190); validation call before building at [lines 2250–2258](./skeleton_mapper_example.py#L2250-L2258) | No standalone validator exists. The current method documents the intended checks and is a placeholder. |
| `io_utils.py` | Save integration point at [lines 2075–2112](./skeleton_mapper_example.py#L2075-L2112); load integration point at [lines 2119–2153](./skeleton_mapper_example.py#L2119-L2153) | Not implemented. The save/load methods contain the proposed workflow and TODO output only. |
| Package launcher | Maya-safe launch notes at [lines 2274–2292](./skeleton_mapper_example.py#L2274-L2292) | A mock-up launch pattern is present, but it has not yet been exposed through `skeleton_mapper/__init__.py`. |

Two ordering concepts are intentionally separate in the mock-up: joint list reordering is handled at [lines 937–999](./skeleton_mapper_example.py#L937-L999), while hierarchy drag-and-drop and parent-map updates are handled at [lines 1004–1057](./skeleton_mapper_example.py#L1004-L1057) and [lines 1762–1929](./skeleton_mapper_example.py#L1762-L1929). The former is visual organization; the latter represents actual parent relationships for the eventual builder.

## Intended data flow

```text
Maya selection
    ↓
maya_utils.py
    ↓
model.py data objects ←→ ui.py
    ↓                 ↘
validator.py          io_utils.py ←→ JSON
    ↓
builder.py
    ↓
Maya joint hierarchy
```

The UI should coordinate the workflow, but the model remains the source of truth. Validation should run before saving or building, and the builder should receive model data rather than reading widget state directly.

## Design decisions

These are settled. The reasoning matters as much as the outcome, so it is recorded here rather than left in commit messages.

### Build is idempotent, and there is no separate Preview

Build deletes and replaces its own prior output on every press. A Preview action would read the same model, run the same computation, and produce the same scene content — the only difference being disposable versus committed output. Once Build is re-runnable, that distinction disappears, so no Preview button is added.

Build does still differ from a hypothetical preview in one respect: validation runs first, and Build refuses on error. A read-only visualization, if one is ever wanted, would instead need to *show* the invalid state rather than block on it.

### Build refuses when its joints have downstream dependents

Because Build recreates joints, rebuilding over a skeleton that is already skinned, constrained, or keyed would destroy that work. Build detects dependents on the joints it owns and stops with a report of what is connected, rather than deleting them.

The weight-preserving path is deferred, not abandoned.

### Joint identity is a tool-generated `uid`, not a Maya node UUID

Every `JointData` carries a `uid` generated once with `uuid.uuid4()`. It is stored in the model, written to the JSON, and applied to the built joint as a string attribute.

Maya's native node UUID was considered and rejected:

- A mapping is authored *before* any joint exists, so there is no node to take identity from. A fresh mapping needs identity immediately, for JSON round-trip and rename tracking.
- Native UUIDs do not survive delete-and-recreate. Verified in Maya 2025: recreating a deleted joint yields a different UUID. Identity would be destroyed by the exact operation it exists to survive.

`MFnDependencyNode.setUuid()` can write a stored UUID back after a rebuild, but that makes identity model-owned anyway — in a namespace the tool does not control, where a collision with an existing node is undefined under referencing and import. A custom attribute is the same design with fewer failure modes, and `ds_maya_utils.create_joint(tags=...)` already writes string attributes alongside the existing `objectTag`.

One identifier answers three problems: which nodes Build owns, how renames are tracked, and how skin weights are later remapped.

Note that `cmds.duplicate()` copies custom attributes, so a duplicated joint carries a twin `uid`. The validator should catch that.

### Regions carry a `uid` too, so their names are a soft constraint

`RegionData` gets its own `uid` for the same reason joints do. Regions are referenced by more than the tree: per-region orientation overrides, region filtering, and the mirror token swap all need a handle that survives a rename.

That changes what a region *name* is for. It is a label, not a key, and unlike a joint name it is never a Maya node name — so Maya imposes no uniqueness requirement on it. The two therefore validate differently:

| | Duplicate name | Behavior |
| --- | --- | --- |
| Joint | Breaks the build — Maya cannot create two siblings with one name | **Hard.** Revert the edit, red border |
| Region | Only makes the UI ambiguous to a human | **Soft.** Accept the edit, amber border and tooltip |

Empty names follow the same split: hard for joints, soft for regions. Hard rejection is two-stage — while typing, the field turns red and the model is simply not written to; the revert to the last valid name happens on `editingFinished`, so clearing a field to retype it is not fought mid-edit.

A soft warning is the right severity because a duplicate region name during editing is usually transient — a user renaming `Region_1` to `arm_l` may briefly collide with something else. Reverting mid-edit is hostile when nothing downstream is at risk. Empty names warn the same way.

Auto-generated names (`Region_N`) are chosen by scanning existing names rather than counting regions, so deleting a middle region cannot make the next add collide.

### One target mesh per mapping, stored once

`SkeletonData.mesh` is the single target. `JointData` does **not** carry its own mesh.

A vertex ID is an index into one specific mesh's vertex array — `body_GEO.vtx[1204]` and `head_GEO.vtx[1204]` are unrelated points — so every `vertex_ids` list is meaningless without a resolvable mesh. Storing that per joint was duplicate state of the worst kind: it was written by `set_vertices`, omitted from `to_dict()`, and read back as `None` by `from_dict()`, so it silently vanished on every round-trip.

Rather than serialize the duplicate, the constraint is enforced at the point of entry: `set_vertices` refuses vertices that are not on the target mesh, and refuses entirely when no target is set. That makes `JointData.mesh` provably redundant, so it was removed. Removing it is not a schema change, because it was never written to JSON.

The consequence to accept is that one mapping covers one mesh. Multi-mesh characters need either a merged mesh or one mapping per mesh — and the latter splits the hierarchy, since parenting spans the whole skeleton. If that becomes a real constraint, the fix is per-joint mesh plus a derived `SkeletonData.meshes()` accessor, not a second stored field.

Both entry points share one validity check. `use_selected_mesh()` takes the Maya selection, `commit_target_mesh()` takes hand-typed text from `mesh_field`, and both go through `set_target_mesh()`. Changing the target while joints still hold vertex IDs warns, since those indices do not carry over.

`mesh_field` is wired with `editingFinished`, not `textChanged`: `setText()` does not emit `editingFinished`, so `use_selected_mesh()` writing the field cannot feed back into the model.

**Known limitation.** Mesh names are compared as plain strings. Two nodes sharing a short name under different parents would compare equal. Resolving full DAG paths belongs in `maya_utils.py` when that module lands.

### Orientation is configured, and the configuration is model data

Orientation is exposed through an **Orientation Settings** item under the **Configure** menu, reusing the `mirror_settings.ui` pattern for dialog scaffolding.

It deliberately does *not* reuse that pattern for storage. `mirror_settings` lives on the UI class and never reaches `to_dict()`. Mirroring survives that because it bakes its result into the regions when invoked. Orientation config is read on *every* build, so a mapping that round-trips through JSON without it would rebuild differently than it was authored. It belongs in the model.

Granularity is a global default on `SkeletonData`, with an optional per-region override on `RegionData`, because a spine and a finger chain want different conventions.

The convention itself — aim axis, up axis, world-up source, and behavior at chain ends — is **not yet decided**. The schema below shows the shape, not the final fields.

### Deferred: weight-preserving rebuild

The goal is to update an existing skeleton without losing skin weights. This splits into two cases with very different costs, and they should not be built as one feature:

| Case | Approach |
| --- | --- |
| Influence set unchanged; joints only moved or reoriented | `skinCluster -recacheBindMatrices` re-derives `bindPreMatrix` from the new positions. No unbind, no weight I/O, no loss. Covers most mapper edits. |
| Influence set changed by adding, removing, renaming, or reparenting joints | Export weights, unbind, rebuild, rebind, reimport. `deformerWeights` matches influences *by name*, so this depends on `uid` to resolve names that have since changed. |

Both are available in Maya 2025 (`skinCluster -rbm/-ubk`, `deformerWeights -path/-method/-skip`).

## Example mapping schema

```json
{
  "schema_version": 2,
  "tool": "skeleton_mapper",
  "mesh": "body_geo",
  "orientation": {
    "_comment": "Shape only. The actual convention is not yet decided.",
    "aim_axis": "X",
    "up_axis": "Y",
    "world_up": [0.0, 1.0, 0.0]
  },
  "regions": [
    {
      "uid": "3c9f0e21-77ab-4d0e-8b52-19d4f6a7c803",
      "name": "spine",
      "orientation": null,
      "joints": [
        {
          "uid": "8f14e45f-ceea-467a-9c1f-2f0a1b3d4c5e",
          "name": "root_jnt",
          "parent": null,
          "vertex_ids": [120, 121, 144, 145]
        },
        {
          "uid": "b1d7c3a2-40e8-4f11-9c6d-7e2a5b8f0139",
          "name": "spine_01_jnt",
          "parent": "8f14e45f-ceea-467a-9c1f-2f0a1b3d4c5e",
          "vertex_ids": [302, 303, 326, 327]
        }
      ]
    }
  ]
}
```

`"orientation": null` on a region means it inherits the global default.

**Consequence to confirm:** `parent` now references a `uid` rather than a joint name. This follows from making `uid` the identity — a name-based reference breaks the moment a user renames a joint, which the UI allows freely. The cost is that the JSON is no longer readable at a glance. Joint names should still be unique within a mapping, because Maya requires it and because errors need to be legible.

Vertex IDs are stored as integers; Maya component strings can be reconstructed when needed.

Bumping to `schema_version` 2 covers both additions. Version 1 files can be migrated by generating a `uid` per region and per joint, rewriting `parent` from name to `uid`, and applying the default orientation config. `from_dict()` already generates a `uid` when one is absent, so version 1 files load without a separate migration pass.

## Development phases

1. **UI scaffold** — Build region and joint rows, reordering, renaming, deletion, and hierarchy display using temporary in-memory data. Mostly represented by [lines 11–1929](./skeleton_mapper_example.py#L11-L1929).
2. **Data model** — Introduce model classes and make widgets read from and update those objects instead of owning authoritative data. Planned hooks appear at [lines 21–44](./skeleton_mapper_example.py#L21-L44), [lines 773–892](./skeleton_mapper_example.py#L773-L892), and [lines 2008–2071](./skeleton_mapper_example.py#L2008-L2071), but the model does not yet exist.
3. **Maya selection tools** — Connect mesh selection, vertex capture, selection restoration, and placement previews. Placeholder integration points are at [lines 406–498](./skeleton_mapper_example.py#L406-L498) and [lines 1477–1510](./skeleton_mapper_example.py#L1477-L1510).
4. **Persistence** — Add versioned JSON save/load with round-trip tests. Planned only at [lines 2075–2153](./skeleton_mapper_example.py#L2075-L2153).
5. **Validation** — Add structured preflight checks and clear UI feedback. Planned only at [lines 2156–2190](./skeleton_mapper_example.py#L2156-L2190).
6. **Skeleton build** — Create positioned and parented joints, then add orientation and naming options as requirements settle. Planned only at [lines 2193–2265](./skeleton_mapper_example.py#L2193-L2265).
7. **Pipeline hardening** — Add tests, logging, reload-safe launch behavior, documentation, and version migration support. Maya-safe launch guidance appears at [lines 2274–2292](./skeleton_mapper_example.py#L2274-L2292); the remaining hardening work is not represented in the mock-up.

> **Blocking gap in phase 2.** `JointData.parent` is never populated. `JointWidget` always creates top-level tree items, and the hierarchy tree's `InternalMove` drag-and-drop has no `dropEvent` handler syncing drops back to the model — that exists only in the mock-up. Until drops write `parent`, a build produces unparented joints, and orientation cannot be derived from child direction. This blocks phase 6 and should be closed in phase 2.

Phase 2 also introduces `uid` and the orientation config. Phase 6 builds idempotently and refuses on existing dependents; weight-preserving rebuild is explicitly out of scope until after phase 7.

## Integration notes

- Keep `skeleton_mapper` under `pipe.library.tools` and use package-relative imports internally.
- Expose a small public launcher from `__init__.py`, for example `show()` or `launch()`.
- Follow the repo's existing Maya main-window parenting and workspace-control pattern if one already exists.
- Support PySide6 with a PySide2 fallback only if the pipeline must run across Maya versions that require both.
- Keep Maya-specific imports at module boundaries so `model.py`, schema handling, and most validation can be tested outside Maya.
- Do not turn tool-specific functions into global pipeline utilities prematurely.
- Treat saved mappings as versioned data. Increment `schema_version` when the stored contract changes and migrate older data explicitly.
- Decide later whether mesh references should use short names, full DAG paths, UUIDs, or a combination; vertex IDs alone do not protect against topology changes.
- Prefer explicit model-to-UI synchronization over reading every value from widgets during save or build.

## Initial success criteria

The first usable version should let a user select a mesh, define and reorder joints, assign vertices, specify parent relationships, save and reload the mapping, validate it, and build a correctly positioned joint hierarchy without manually editing JSON.
