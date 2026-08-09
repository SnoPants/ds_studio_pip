from PySide6 import QtWidgets, QtCore, QtUiTools, QtGui
from PySide6.QtWidgets import QApplication
from pathlib import Path
import sys
import maya.cmds as cmds

PACKAGE_DIR = Path(__file__).resolve().parent
UI_FILE = PACKAGE_DIR / "ui" / "skeleton_mapper.ui"

def GetMayaWindow():
    """Get the Maya main window as a QMainWindow instance."""
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    mayaWindow = next(w for w in app.topLevelWidgets() if w.objectName() == "MayaWindow")
    return mayaWindow

class Window(QtWidgets.QWidget):
    """A window that can be loaded from a Qt .ui file."""

    def __init__(self, filePath):
        """Initialize the window."""
        super().__init__()
        self.filePath = filePath
        self.MainWindow = None
        self.ui = None
        self.loadUIFile()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def loadUIFile(self, parent=None):
        """Load the UI file and return the widget."""
        if parent is None:
            parent = GetMayaWindow()
        loader = QtUiTools.QUiLoader()
        uiFile = QtCore.QFile(self.filePath)
        uiFile.open(QtCore.QFile.ReadOnly)
        ui = loader.load(uiFile, parent)
        uiFile.close()
        
        self.ui = ui
        
        return ui
        
    def show(self):
        """Show the window."""
        self.close()
        self.MainWindow = self.loadUIFile()
        self.MainWindow.show()

    def close(self):
        """Close the window."""
        if self.MainWindow is not None:
            self.MainWindow.close()
            self.MainWindow = None

def showWindow():
    """This is the entry point of the script. Create an instance of the Window class and show it."""
    global win
    win = Window(str(UI_FILE))
    win.show()

    
showWindow()