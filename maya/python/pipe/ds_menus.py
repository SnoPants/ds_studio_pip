import maya.cmds as cmds
import maya.mel as mel

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