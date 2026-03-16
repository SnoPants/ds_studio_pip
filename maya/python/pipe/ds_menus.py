import maya.cmds as cmds
import maya.mel as mel
import os

class MayaMenu:
    def __init__(self, name, label, parent, sub_menus):
        self.menu_name = name
        self.menu_label = label
        self.menu_parent = parent
        self.menu_items = sub_menus
        
    def create_menus(self):
        if cmds.menu(self.menu_name, exists=True):
            cmds.deleteUI(self.menu_name)
            
        cmds.menu(self.menu_name, label =self.menu_label, parent=self.menu_parent)
        
        for key, value in self.menu_items.items():
            cmds.menuItem(label= key, command = value)


#--- DEBUG ---#

def create_ds_menu():

    def mod_rigger(debug): print(f"{debug} This will be for rigging!")
    def exporter(debug): print("This will be for exporting!")
    def tools(debug): print("This will be for tools!")
        
    ds_studio_submenu = {
        'MOD Rigger': mod_rigger,
        'Exporter': exporter,
        'Tools': tools
    }
    # ----- #
            
    DS_STUDIO = MayaMenu("DS Studio", 'DS Studio', mel.eval('$temp = $gMainWindow'), ds_studio_submenu)

    print(DS_STUDIO.menu_items)
    DS_STUDIO.create_menus()



def register_icons():
    icon_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(icon_path, "icons")

    current = os.environ.get("XBMLANGPATH", "")
    paths = current.split(";") if current else []

    if icon_path not in paths:
        os.environ["XBMLANGPATH"] = current + (";" if current else "") + icon_path

    print("Registered icon path:", icon_path)
    return icon_path


def create_ds_shelve():
    shelf_name = "DS_Studio"
    icon_path = register_icons()

    maya_default_shelf = mel.eval("global string $gShelfTopLevel; $temp = $gShelfTopLevel;")

    if not cmds.shelfLayout(shelf_name, query=True, exists=True):
        cmds.shelfLayout(shelf_name, parent=maya_default_shelf)
        print(f"Created new shelf: {shelf_name}")
    else:
        print(f"Shelf '{shelf_name}' already exists.")
        cmds.tabLayout(maya_default_shelf, edit=True, selectTab=shelf_name)
        return

    # Add a button to the new shelf
    # The 'cmds.setParent(shelf_name)' ensures new buttons are added to the correct shelf
    cmds.setParent(shelf_name)
    cmds.shelfButton(
        command='from pipe.library.tools.shelves.items import center_joint; center_joint.run()', #C:\Users\andre\Documents\maya\DS_STUDIO\ds_studio_pip\maya\python\pipe\icons\shelf_icons\bozog_icons\Unused.png
        # Warning: Pixmap file C:\Users\andre\Documents\maya\2025\scripts\DS_STUDIO\ds_studio_pip\maya\python\pipe\icons\bozog_icons/Unused.png not found, using default.
        annotation='Create a new sphere',
        label='CTR_JNT',
        image= os.path.join(icon_path, r'shelf_icons\bozog_icons\Unused.png'), # Use a built-in Maya icon, or provide a custom path
        sourceType='python',
        width=32,
        height=32
    )
    
    # Save the shelf layout so it persists across Maya sessions
    # Note: this saves the current configuration to a MEL file in user prefs
    shelf_dir = os.path.dirname(cmds.about(preferences=True)) + "/shelves"
    if not os.path.exists(shelf_dir):
        os.makedirs(shelf_dir)
        
    cmds.saveShelf(shelf_name, os.path.join(shelf_dir, f"shelf_{shelf_name}.mel"))
        
#-----Below this is just reference -----

'''def my_custom_menu():
    # Remove old one if it already exists (prevents duplicates)
    if cmds.menu('MyMenu', exists=True):
        cmds.deleteUI('MyMenu')

    # Create new menu on the main Maya window
    cmds.menu('MyMenu', label='My Tools', parent='MayaWindow', tearOff=True)

    # Add menu items
    cmds.menuItem(label='Say Hello', command=lambda x: print('Hello from My Tools!'))
    cmds.menuItem(divider=True)
    cmds.menuItem(label='Open Scene...', command=lambda x: cmds.FileOpen())
    cmds.menuItem(label='Custom Script', command=lambda x: my_function())

def my_function():
    cmds.confirmDialog(title='My Tool', message='Custom script executed!', button=['OK'])

# Run it
my_custom_menu()'''