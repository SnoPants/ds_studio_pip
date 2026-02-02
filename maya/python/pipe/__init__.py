# Dynamically import every file in the package, TODO: Need to search through the rest of the packages and load it.

from os.path import dirname, basename, isfile, join
import glob
import importlib
import maya.cmds as cmds

_pack_dir = dirname(__file__)

_files = glob.glob(join(_pack_dir, "**", "*.py"), recursive= True)

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

    '''
    from os.path import dirname, basename, isfile, join 
    import glob 
    modules = glob.glob(join(dirname(__file__), "**", "*.py"), recursive= True) 
    print(f'modules...{modules}') 
    __all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')] 
    print(f'importing ... {__all__}')
    '''
