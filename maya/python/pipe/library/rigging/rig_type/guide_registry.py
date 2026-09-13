"""Declarative guide builders. Importing this module never imports Maya or Qt.

Register metadata explicitly: several legacy builder modules execute scene code
at import time, so discovery must not import them to inspect their classes.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    label: str
    kind: str
    default: object
    choices: tuple = ()
    minimum: float = 0
    maximum: float = 100
    help: str = ''


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple = ()
    joint_uids: tuple = ()

    @property
    def valid(self):
        return not self.errors


@dataclass(frozen=True)
class BuilderSpec:
    id: str
    label: str
    rig_type: str
    parameters: tuple
    validator: object

    def defaults(self):
        return {parameter.key: parameter.default for parameter in self.parameters}

    def validate(self, region, skeleton, values):
        errors = []
        for parameter in self.parameters:
            value = values.get(parameter.key, parameter.default)
            if parameter.kind == 'bool' and type(value) is not bool:
                errors.append('{} must be on or off.'.format(parameter.label))
            elif parameter.kind == 'string' and not isinstance(value, str):
                errors.append('{} must be text.'.format(parameter.label))
            elif parameter.kind == 'choice' and value not in parameter.choices:
                errors.append('{} has an unknown option.'.format(parameter.label))
            elif parameter.kind in ('int', 'float'):
                valid_type = type(value) is int if parameter.kind == 'int' else type(value) in (int, float)
                if not valid_type or not parameter.minimum <= value <= parameter.maximum:
                    errors.append('{} is outside its allowed range.'.format(parameter.label))
        if errors:
            return ValidationResult(tuple(errors))
        return self.validator(region, skeleton, dict(self.defaults(), **values))


class BuilderRegistry:
    def __init__(self):
        self.rig_types = {}
        self.builders = {}

    def register_type(self, type_id, label):
        if type_id in self.rig_types:
            raise ValueError('Duplicate rig type: ' + type_id)
        self.rig_types[type_id] = label

    def register(self, spec):
        if spec.id in self.builders or spec.rig_type not in self.rig_types:
            raise ValueError('Duplicate builder or unknown rig type: ' + spec.id)
        self.builders[spec.id] = spec

    def for_type(self, type_id):
        return tuple(spec for spec in self.builders.values() if spec.rig_type == type_id)


def validate_biped_limb(region, skeleton, values):
    """Conservative contract for the existing RP limb + optional SC extension.

    Three joints drive the limb. With SC enabled a fourth, terminal joint is
    used only by the IK extension, matching BipedLimbBuilder._ik_setup's pop.
    Parent references are joint UIDs, never display names or tree row indices.
    """
    errors = []
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', values['name']):
        errors.append('Rig name must start with a letter or underscore and contain only letters, digits and underscores.')
    expected = 4 if values['use_sc'] else 3
    joints = {joint.uid: joint for joint in region.joints}
    all_joints = {joint.uid: joint for joint in skeleton.joints()}
    if len(joints) != len(region.joints) or len(all_joints) != len(list(skeleton.joints())):
        errors.append('Joint IDs are duplicated in the mapping.')
    if len(joints) != expected:
        errors.append('Requires exactly {} joints in this region; found {}.'.format(expected, len(joints)))
    roots = []
    children = {uid: [] for uid in joints}
    for joint in joints.values():
        if joint.parent in joints:
            children[joint.parent].append(joint.uid)
        else:
            roots.append(joint.uid)
        seen = {joint.uid}
        parent = joint.parent
        while parent:
            if parent in seen:
                errors.append('Hierarchy contains a cycle.')
                break
            seen.add(parent)
            if parent not in all_joints:
                errors.append('A parent joint is missing from the mapping.')
                break
            parent = all_joints[parent].parent
    if len(roots) != 1 or any(len(items) > 1 for items in children.values()):
        errors.append('Arrange the region as one unbranched parent-to-child chain in the hierarchy tree.')
    chain = []
    current = roots[0] if len(roots) == 1 else None
    while current is not None and current not in chain:
        chain.append(current)
        descendants = children[current]
        current = descendants[0] if len(descendants) == 1 else None
    if len(chain) != len(joints):
        errors.append('Every region joint must belong to the same connected chain.')
    return ValidationResult(tuple(dict.fromkeys(errors)), tuple(chain))


REGISTRY = BuilderRegistry()
for type_id, label in (('biped', 'Biped'), ('quadruped', 'Quadruped'),
                       ('face', 'Face'), ('mechanical', 'Mechanical')):
    REGISTRY.register_type(type_id, label)

REGISTRY.register(BuilderSpec(
    id='biped.limb', label='Limb (IK / FK)', rig_type='biped',
    parameters=(
        ParameterSpec('name', 'Rig name', 'string', 'limb',
                      help='Prefix passed to BipedLimbBuilder.'),
        ParameterSpec('use_sc', 'Single-chain extension', 'bool', False,
                      help='Requires a fourth joint directly below the limb end; used by the IK single-chain solver.'),
    ),
    validator=validate_biped_limb,
))
