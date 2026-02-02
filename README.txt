Documentation for commands.

# README – Maya Pipeline Pseudo Documentation

This document serves as a quick start and reference guide for the custom DS Studios pipeline and library.

---

### Module: `ds_biped_rig`
### Class: `Biped_Rig(name)`

Represents a rig builder for bipedal characters.  
Contains modular building systems for limbs, spines, feet, and more.

---

### Method: `limb_biped(name: str, start_joint: str, end_joint: str)`

**Parameters**
- `name` *(str)* — name of the limb.
- `start_joint` *(str)* — The name of the starting joint (Maya node type: `joint`).
- `end_joint` *(str)* — The name of the ending joint (Maya node type: `joint`).
- `sc_solver` *( -OPTIONAL- str)* — The name of the joint that will have a single solver ik attached to it. (Maya node type: `joint`).

> **TODO:** Add more documentation.
