from PySide6 import QtWidgets, QtCore, QtUiTools
from pathlib import Path

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

class MayaUI():

    UI_FILE = None
    OBJECT_NAME = "DSMayaWindow"

    def __init__(self, parent=None):
        self.parent = parent or get_maya_window()
        self.ui = None

        self.close_existing()
        self._validate_ui_file()
        self._load_ui()
        self.connect_signals()

    def _validate_ui_file(self):
        if self.UI_FILE is None:
            raise ValueError("{} must define UI_FILE.".format(self.__class__.__name__))
        self.UI_FILE = Path(self.UI_FILE).resolve()
        if not self.UI_FILE.is_file():
            raise FileNotFoundError("UI file not found: {}".format(self.UI_FILE))

    def _load_ui(self, parent=None):

        ui_file = QtCore.QFile(str(self.UI_FILE))
        if not ui_file.open(QtCore.QFile.ReadOnly):
            raise RuntimeError("Cannot open UI file: {}".format(self.UI_FILE))

        try:
            loader = QtUiTools.QUiLoader()
            self.ui = loader.load(ui_file, parent or self.parent)
        finally:
            ui_file.close()

        if self.ui is None:
            raise RuntimeError("Failed to load UI file: {}".format(self.UI_FILE))

        self.ui.setObjectName(self.OBJECT_NAME)

        try:
            delete_on_close = (QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        except AttributeError:
            delete_on_close = QtCore.Qt.WA_DeleteOnClose

        self.ui.setAttribute(delete_on_close)
        self.ui.destroyed.connect(self.ui_destroyed)

    def connect_signals(self):
        """Connect signals to slots. Override this method in subclasses to connect custom signals."""
        pass

    def find_widget(self, widget_type, object_name):
        if self.ui is None:
            raise RuntimeError("UI is not loaded.")

        widget = self.ui.findChild(widget_type, object_name)

        if widget is None:
            raise ValueError("Could not find {} named '{}' in the UI.".format(widget_type.__name__, object_name, self.UI_FILE))

        return widget

    def show(self):
        """Show and focus the loaded interface."""

        if self.ui is None:
            raise RuntimeError("The UI has already been deleted.")

        self.ui.show()
        self.ui.raise_()
        self.ui.activateWindow()

        return self.ui
    
    def close(self):
        """Close the interface and release its Qt widget."""
        if self.ui is None:
            return

        self.on_close()
        self.ui.close()
        self.ui.deleteLater()
        self.ui = None

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
            if widget.objectName() == self.OBJECT_NAME:
                widget.close()
                widget.deleteLater()