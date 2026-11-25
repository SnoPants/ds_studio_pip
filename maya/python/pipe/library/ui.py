from PySide6 import QtWidgets, QtCore, QtGui, QtUiTools
from pathlib import Path
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from shiboken6 import getCppPointer, isValid

PACKAGE_DIR = Path(__file__).resolve().parent

def get_maya_window():

    """Get the Maya main window as a QMainWindow instance."""
    app = QtWidgets.QApplication.instance()
    if not app:
        return None

    for widget in app.topLevelWidgets():
        if widget.objectName() == "MayaWindow":
            return widget

    return None

class CloseEventFilter(QtCore.QObject):
    """Runs a callback when the watched window closes, including the title-bar X."""

    def __init__(self, callback, parent):
        super().__init__(parent)
        self.callback = callback

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Close:
            self.callback()
        return False

class MayaUI():

    UI_FILE = None
    OBJECT_NAME = "DSMayaWindow"
    DOCKABLE = False

    def __init__(self, parent=None):
        self.parent = parent or get_maya_window()
        self.ui = None
        self.closed = False

        self.close_existing()
        self._validate_ui_file()
        self._load_ui()
        self.connect_signals()

    def _validate_ui_file(self):
        if self.UI_FILE is None:
            raise ValueError(f"{self.__class__.__name__} must define UI_FILE.")
        self.UI_FILE = Path(self.UI_FILE).resolve()
        if not self.UI_FILE.is_file():
            raise FileNotFoundError(f"UI file not found: {self.UI_FILE}")

    def _load_ui(self, parent=None):

        ui_file = QtCore.QFile(str(self.UI_FILE))
        if not ui_file.open(QtCore.QFile.ReadOnly):
            raise RuntimeError(f"Cannot open UI file: {self.UI_FILE}")

        try:
            loader = QtUiTools.QUiLoader()
            self.ui = loader.load(ui_file, parent or self.parent)
        finally:
            ui_file.close()

        if self.ui is None:
            raise RuntimeError(f"Failed to load UI file: {self.UI_FILE}")

        self.ui.setObjectName(self.OBJECT_NAME)

        try:
            delete_on_close = (QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        except AttributeError:
            delete_on_close = QtCore.Qt.WA_DeleteOnClose

        self.ui.setAttribute(delete_on_close)
        self.ui.destroyed.connect(self.ui_destroyed)
        self.close_filter = CloseEventFilter(self.handle_close, self.ui)
        self.ui.installEventFilter(self.close_filter)

    def connect_signals(self):
        """Connect signals to slots. Override this method in subclasses to connect custom signals."""
        pass

    def find_widget(self, widget_type, object_name):
        if self.ui is None:
            raise RuntimeError("UI is not loaded.")

        widget = self.ui.findChild(widget_type, object_name)

        if widget is None:
            raise ValueError(f"Could not find {widget_type.__name__} named '{object_name}' in the UI.")

        return widget

    def show(self):
        """Show and focus the loaded interface."""

        if self.ui is None:
            raise RuntimeError("The UI has already been deleted.")

        if self.DOCKABLE:
            self.dock()
            return self.ui

        self.ui.show()
        self.ui.raise_()
        self.ui.activateWindow()

        return self.ui

    def workspace_control_name(self):
        return f"{self.OBJECT_NAME}WorkspaceControl"

    def dock(self):
        """Embed the UI in a Maya workspace control so it can be docked."""
        control = cmds.workspaceControl(
            self.workspace_control_name(),
            label= self.ui.windowTitle(),
            floating= True,
            retain= False,
            initialWidth= self.ui.width(),
            initialHeight= self.ui.height(),
            visibleChangeCommand= self.control_visibility_changed,
        )
        self.ui.setWindowFlags(QtCore.Qt.Widget)
        # Parent in C++: adding through a wrapInstance'd container leaves self.ui
        # a dead Python wrapper once the container wrapper is garbage-collected.
        omui.MQtUtil.addWidgetToMayaLayout(int(getCppPointer(self.ui)[0]), int(omui.MQtUtil.findControl(control)))
        self.ui.show()

    def control_visibility_changed(self, *args):
        # closeCommand never fires in Maya 2025. Closing the panel (X, -close or
        # deleteUI) hides the control while the UI is still alive, so clean up here.
        control = self.workspace_control_name()
        if cmds.workspaceControl(control, exists= True) and not cmds.workspaceControl(control, q= True, visible= True):
            self.handle_close()
    
    def close(self):
        """Close the interface and release its Qt widget."""
        if self.ui is None:
            return

        self.handle_close()
        control = self.workspace_control_name()
        if self.DOCKABLE and cmds.workspaceControl(control, exists= True):
            cmds.deleteUI(control)
        elif isValid(self.ui):
            self.ui.close()
            self.ui.deleteLater()
        self.ui = None

    def handle_close(self):
        # close() and the window's close event both land here; clean up once.
        if self.closed:
            return
        self.closed = True
        self.on_close()

    def on_close(self):
        """Called when the window is closed."""
        pass

    def ui_destroyed(self, *args):
        """Called when the UI is destroyed."""
        self.ui = None

    def close_existing(self):
        """Close any existing instance of the UI."""
        app = QtWidgets.QApplication.instance()

        if app is None:
            return

        for widget in app.allWidgets():
            # Widgets Qt already deleted still show up here; touching them raises.
            if not isValid(widget):
                continue
            if widget.objectName() == self.OBJECT_NAME:
                widget.close()
                widget.deleteLater()

        control = self.workspace_control_name()
        if cmds.workspaceControl(control, exists= True):
            cmds.deleteUI(control)