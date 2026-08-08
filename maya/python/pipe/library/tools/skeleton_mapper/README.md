# Skeleton Mapper

`skeleton_mapper` is a Maya tool for defining a reusable relationship between mesh vertices and skeleton joints. Artists will be able to organize joints into regions, assign vertices to each joint, validate the mapping, save or load it as JSON, and build a joint hierarchy from the stored data.

The package should live inside the existing pipeline repo and remain self-contained until a component proves useful enough to promote into a shared library.

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
- Store mesh identity, regions, joint names, parent relationships, and vertex IDs.
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
- Later support joint orientation, naming rules, namespaces, and rebuild options.

### `validator.py`

- Detect duplicate or invalid joint names.
- Report joints with no assigned vertices.
- Verify that the target mesh and referenced vertex IDs are valid.
- Detect missing parent references, self-parenting, and hierarchy cycles.
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

## Example mapping schema

```json
{
  "schema_version": 1,
  "tool": "skeleton_mapper",
  "mesh": "body_geo",
  "regions": [
    {
      "name": "spine",
      "joints": [
        {
          "name": "root_jnt",
          "parent": null,
          "vertex_ids": [120, 121, 144, 145]
        },
        {
          "name": "spine_01_jnt",
          "parent": "root_jnt",
          "vertex_ids": [302, 303, 326, 327]
        }
      ]
    }
  ]
}
```

Joint names should be unique within a mapping so parent references remain unambiguous. Vertex IDs are stored as integers; Maya component strings can be reconstructed when needed.

## Development phases

1. **UI scaffold** — Build region and joint rows, reordering, renaming, deletion, and hierarchy display using temporary in-memory data. Mostly represented by [lines 11–1929](./skeleton_mapper_example.py#L11-L1929).
2. **Data model** — Introduce model classes and make widgets read from and update those objects instead of owning authoritative data. Planned hooks appear at [lines 21–44](./skeleton_mapper_example.py#L21-L44), [lines 773–892](./skeleton_mapper_example.py#L773-L892), and [lines 2008–2071](./skeleton_mapper_example.py#L2008-L2071), but the model does not yet exist.
3. **Maya selection tools** — Connect mesh selection, vertex capture, selection restoration, and placement previews. Placeholder integration points are at [lines 406–498](./skeleton_mapper_example.py#L406-L498) and [lines 1477–1510](./skeleton_mapper_example.py#L1477-L1510).
4. **Persistence** — Add versioned JSON save/load with round-trip tests. Planned only at [lines 2075–2153](./skeleton_mapper_example.py#L2075-L2153).
5. **Validation** — Add structured preflight checks and clear UI feedback. Planned only at [lines 2156–2190](./skeleton_mapper_example.py#L2156-L2190).
6. **Skeleton build** — Create positioned and parented joints, then add orientation and naming options as requirements settle. Planned only at [lines 2193–2265](./skeleton_mapper_example.py#L2193-L2265).
7. **Pipeline hardening** — Add tests, logging, reload-safe launch behavior, documentation, and version migration support. Maya-safe launch guidance appears at [lines 2274–2292](./skeleton_mapper_example.py#L2274-L2292); the remaining hardening work is not represented in the mock-up.

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
