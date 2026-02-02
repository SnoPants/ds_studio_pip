import maya.cmds as cmds
from functools import singledispatch

#TODO: Realized that maya constraints are redundant with a single dispatching system, need to refactor this code into matrix constraints later.

'''
class ParentConstraint: pass
class PointConstraint: pass
class OrientConstraint: pass
class ScaleConstraint: pass
class AimConstraint: pass
'''

#TODO: Implement matrix constraints in future.
class MatrixParentConstraint: pass
class MatrixPointConstraint: pass
class MatrixOrientConstraint: pass
class MatrixScaleConstraint: pass
class MatrixAimConstraint: pass

CONSTRAINT_MAP = {
    'parent': MatrixParentConstraint,
    'point': MatrixPointConstraint,
    'orient': MatrixOrientConstraint,
    'scale': MatrixScaleConstraint,
    'aim': MatrixAimConstraint,
}

@singledispatch
def dispatch_constraint(constraint_type, objA, objB):
    raise NotImplementedError(f"Constraint type '{constraint_type}' is not supported.")

@dispatch_constraint.register
def _(constraint_type: MatrixParentConstraint, objA, objB):
    print(f"Applying Parent Constraint between - driver: {objA} ---> target: {objB}")
    

#TODO: Implement other constraint handlers as needed.

# dispatch_constraint(MatrixPointConstraint(), nodeA, nodeB) this is how to call.
# plan on using single dispatch to handle different constraint types. 
# more info on single dispatch: https://docs.python.org/3/library/functools.html and https://www.youtube.com/watch?v=TzvxBbv1eTI&list=PLQfJqgwyFLug6d7GFu7lDksl44sNSoLxW&index=2
