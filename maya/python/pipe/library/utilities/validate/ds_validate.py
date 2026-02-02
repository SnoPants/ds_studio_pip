import functools
import maya.cmds as cmds

def validator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[VALIDATOR] Running {func.__name__}...")
        print("   args:", args)
        print("   kwargs:", kwargs)
        return func(*args, **kwargs)
    return wrapper

@ validator
def validate_limb_inputs(start_joint, end_joint, sc_joint= None):

    if not start_joint or not end_joint: 
        raise ValueError(f"Invalid input, start joint: {start_joint}, end joint: {end_joint}")
    if start_joint == end_joint:
        raise ValueError(f"Your inputs of start joint and end joint cannot be the same.")
    if cmds.objectType(start_joint) != 'joint' or cmds.objectType(end_joint) != 'joint':
        raise TypeError(f"Both start and end inputs must be joint types: start joint type: {cmds.objectType(start_joint)}, end joint type: {cmds.objectType(end_joint)}")
    
    if sc_joint:
        if cmds.objectType(sc_joint) != "joint":
            raise TypeError(f"Single Chain joint must be of type joint. Received: {cmds.objectType(sc_joint)}")

    print("Intial Validation Successful ----> Starting limb rig build...")

@ validator
def validate_chain(chain):
    if not chain or len(chain) < 1:
        raise ValueError(f"There are no/missing joints in between inputs.")

    
"""
================================================================================
DECORATOR NOTES – WHAT THEY ARE & WHY THIS FILE USES THEM
================================================================================

A decorator in Python is a function that *wraps another function* to add 
extra behavior without modifying the original function's code. This is 
very similar to adding a "pre-step" or "post-step" around a Maya command.

WHY WE USE DECORATORS FOR VALIDATION
------------------------------------
Our validators (validate_limb_inputs, validate_chain, etc.) perform checks 
before building rigs. We want each validator to automatically print a 
"VALIDATOR RUNNING..." message every time one is executed, without adding 
print statements inside every validator function.

Normally, this would force us to repeat print() calls many times. A decorator 
solves this cleanly by wrapping all validator functions with a single logger.

HOW THE @validator DECORATOR WORKS
----------------------------------
The decorator below takes a function (like validate_limb_inputs), wraps it 
inside a "wrapper" function, prints a message, then calls the original 
function using the same arguments. This lets us add behavior to many 
functions at once.

IMPORTANT: 
The wrapper uses *args and **kwargs because validators may take different 
numbers of arguments. Using *args/**kwargs allows the wrapper to accept ANY 
combination of inputs and forward them to the original function safely.

EXAMPLE FLOW:
-------------
Calling:
    validate_limb_inputs("L_shoulder", "L_wrist")

Actually runs:
    wrapper("L_shoulder", "L_wrist")
Which prints:
    [VALIDATOR] Running validate_limb_inputs...
Then executes the real function:
    validate_limb_inputs("L_shoulder", "L_wrist")

WHY THIS IS BEST PRACTICE HERE
------------------------------
- Avoids repeating code in every validator function
- Keeps validation behavior consistent across the pipeline
- Clean, maintainable, and modular
- Works well with many future validators
- Matches real AAA pipeline patterns (Bungie, Riot, Ubisoft)

TL;DR:
------
The decorator adds automatic logging without cluttering the validators.
It is the correct tool for this job.

================================================================================
"""
