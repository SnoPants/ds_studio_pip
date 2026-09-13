# Skeleton Mapper roadmap

## Scope decision: the skeleton is the rig guide

Use the existing joint hierarchy and per-joint orientation settings as the structural input for rig builders. Do not introduce a separate guide hierarchy or synchronize two representations of the same skeleton at this stage.

The current rig-type, builder and parameter controls are **Rig Settings**: configuration attached to a region, not separate Maya guide objects. The internal `RigGuideWidget` name remains for now; it does not imply that guide nodes exist.

The intended flow is:

```text
Mapping data → validated skeleton → rig builder
                                  + region rig settings
```

Mapping data remains the source of truth during authoring. A future builder should read that data and its built skeleton references rather than reading UI widgets directly.

## Now: finish the skeleton mapper

- Refine joint and region editing, hierarchy organization, and orientation controls.
- Complete versioned save/load so the authored mapping and settings can be restored.
- Complete skeleton validation and then build the skeleton end to end from the mapping.
- Keep **Build skeleton only** as the path for working without rig configuration. It disables rig controls and skips builder validation while retaining their settings; skeleton validation will still be required when building is implemented.

Current UI/model work includes stable joint IDs, tree-to-model parent synchronization, per-joint primary/secondary axes, region builder settings, and the skeleton-only toggle. Primary and secondary axes must be distinct X/Y/Z choices, defaulting to X/Y. Settings are included in dictionary serialization, but the Save/Load actions and actual Build operation remain placeholders. No Maya DAG updates or rig execution have been added as part of this UI work.

## Next: rig builders consume the skeleton

- Start with the existing biped limb builder once skeleton creation works.
- Use the region's skeleton hierarchy and Rig Settings to validate and configure the builder.
- Keep builder rules independent of Qt, and keep Maya scene operations outside the widgets.
- Add further builders as concrete requirements emerge.

## Later: specialized guides only where needed

Add extra guide data or scene objects when a builder needs information the skeleton cannot express, such as foot-roll pivots, a pole-vector placement override, or control placement offsets.

These should supplement the skeleton, not duplicate its hierarchy. Decide their ownership, persistence and update behavior when implementing the first builder that needs them. A general guide system and live bidirectional skeleton/guide synchronization are deferred.

The milestone before expanding scope is a usable skeleton mapper: author a mapping, save and reload it, validate it, and build a correctly positioned and oriented skeleton.
