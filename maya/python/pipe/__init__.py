# pipe/__init__.py

import traceback
import maya.utils

try:
    # Core Maya
    import maya.cmds as cmds

    # DS maya menu
    from pipe import ds_menus
    ds_menus.create_ds_menu()

    # Rigging
    from pipe.library.rigging import ds_rig
    from pipe.library.rigging.rig_type import ds_biped_rig as biped
    from pipe.library.rigging.rig_type.builders import ds_biped_limb_builder as limb
    from pipe.library.rigging.rig_type.builders import ds_controller_builder as ctrl

    # Utilities
    from pipe.library.utilities import ds_maya_math as math
    from pipe.library.utilities import ds_maya_utils as utils

    __all__ = [
        "cmds",
        "ds_rig",
        "biped",
        "limb",
        "ctrl",
        "math",
        "utils",
    ]

    print(f"Successfully imported: {__all__}")

except Exception as e:
    tb = traceback.format_exc()
    try:
        import maya.cmds as cmds
        maya.utils.executeInMainThreadWithResult(cmds.error, f"Failed to load DS Studio tools: {e}\n{tb}")
    except Exception:
        # last resort: print to script editor
        print(f"Failed to load DS Studio tools: {e}\n{tb}")

'''from os.path import dirname, basename, isfile, join
import glob
import importlib
import maya.cmds as cmds

_pack_dir = dirname(__file__)

_files = ['']

__all__ = []
for fil in _files:
    if not isfile(fil) or fil.endswith('__init__.py'):
        continue

    rel = fil[len(_pack_dir)+1:]
    mod = rel[:-3].replace("\\", ".").replace("/", ".")  # "utils.math"
    __all__.append(mod)

print(f'Attempting to import ... {__all__}')

for mod in __all__:
    try:
        importlib.import_module(f".{mod}", package=__name__)
        print(f'Successfully imported: {mod}')
    except Exception as e:
        cmds.warning(f"Failed to load {mod}: {e}")
        continue


    # Left off here.
    # I think instead dynamically importing everything in, we might just want to do this by hand, just for the sake of doing "import.this.module as xyz"
    # or we add a init file to every folder and import them in that way with ....


    from os.path import dirname, basename, isfile, join 
    import glob 
    modules = glob.glob(join(dirname(__file__), "**", "*.py"), recursive= True) 
    print(f'modules...{modules}') 
    __all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')] 
    print(f'importing ... {__all__}')
    '''
