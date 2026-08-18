from pathlib import Path

from pipe.library.ui import MayaUI
from pipe.library.ui import QtCore, QtUiTools, QtWidgets

PACKAGE_DIR = Path(__file__).resolve().parent

UI_FILE = (PACKAGE_DIR / "ui" / "skeleton_mapper.ui")
MIRROR_SETTINGS_UI_FILE = (PACKAGE_DIR / "ui" / "mirror_settings.ui")

class SkeletonMapperUI(MayaUI):
    UI_FILE = UI_FILE
    OBJECT_NAME = "DSSkeletonMapperWindow"

    def __init__(self, parent=None):
        self.regions = []
        self.parent_map = {}
        self.mirror_settings_window = None
        self.mirror_settings = {
            "axis": "X",
            "plane_offset": 0.0,
            "direction": "Left → Right",
            "vertex_match": "Closest Position",
            "tolerance": 0.001,
            "left_token": "_l",
            "right_token": "_r"
        }

        super().__init__(parent=parent)

    def connect_signals(self):
        """Find the Designer widgets and connect their signals."""

        self.find_widgets()

        self.use_selected_button.clicked.connect(self.use_selected_mesh)
        self.add_region_button.clicked.connect(self.add_region)
        self.search_field.textChanged.connect(self.filter_regions)
        self.hierarchy_tree.itemSelectionChanged.connect(self.update_selected_joint_info)
        self.unparent_button.clicked.connect(self.unparent_selected)
        self.expand_all_button.clicked.connect(self.hierarchy_tree.expandAll)
        self.load_mapping_action.triggered.connect(self.load_mapping)
        self.save_mapping_action.triggered.connect(self.save_mapping)
        self.mirror_configuration_action.triggered.connect(self.open_mirror_configuration)
        self.mirror_region_button.clicked.connect(self.mirror_selected_region)
        self.build_button.clicked.connect(self.build_skeleton)

    def find_widgets(self):

        """Store references to widgets created in Qt Designer."""

        self.menu_bar = self.find_widget(QtWidgets.QMenuBar,"menu_bar")
        self.ui.layout().setMenuBar(self.menu_bar)
        self.mesh_field = self.find_widget(QtWidgets.QLineEdit,"mesh_field")
        self.use_selected_button = self.find_widget(QtWidgets.QPushButton,"use_selected_button")
        self.add_region_button = self.find_widget(QtWidgets.QPushButton,"add_region_button")
        self.search_field = self.find_widget(QtWidgets.QLineEdit,"search_field")
        self.region_scroll = self.find_widget(QtWidgets.QScrollArea,"region_scroll")
        self.region_content = self.find_widget(QtWidgets.QWidget,"region_content")
        self.hierarchy_tree = self.find_widget(QtWidgets.QTreeWidget,"hierarchy_tree")
        self.unparent_button = self.find_widget(QtWidgets.QPushButton,"unparent_button")
        self.expand_all_button = self.find_widget(QtWidgets.QPushButton,"expand_all_button")
        self.selected_joint_field = self.find_widget(QtWidgets.QLineEdit,"selected_joint_field")
        self.parent_joint_field = self.find_widget(QtWidgets.QLineEdit,"parent_joint_field")
        self.load_mapping_action = self.find_widget(QtCore.QObject,"load_mapping_action")
        self.save_mapping_action = self.find_widget(QtCore.QObject,"save_mapping_action")
        self.mirror_configuration_action = self.find_widget(QtCore.QObject,"mirror_configuration_action")
        self.mirror_region_button = self.find_widget(QtWidgets.QPushButton,"mirror_region_button")
        self.build_button = self.find_widget(QtWidgets.QPushButton,"build_button")


    def use_selected_mesh(self):
        """Use the selected Maya mesh as the target mesh."""

        print("TODO: Use selected Maya mesh.")

    def add_region(self):
        """Add a new joint region."""

        print("TODO: Add region.")

    def filter_regions(self, text):
        """Filter the displayed regions."""

        print("TODO: Filter regions using: {}".format(text))

    def update_selected_joint_info(self):
        """Display information about the hierarchy selection."""

        selected_items = (self.hierarchy_tree.selectedItems())

        if not selected_items:
            self.selected_joint_field.clear()
            self.parent_joint_field.clear()
            return

        selected_item = selected_items[0]
        joint_name = selected_item.text(0)

        parent_item = selected_item.parent()

        if parent_item is None:
            parent_name = ""
        else:
            parent_name = parent_item.text(0)

        self.selected_joint_field.setText(joint_name)

        self.parent_joint_field.setText(parent_name)

    def unparent_selected(self):
        """Move the selected hierarchy item to the root."""

        selected_items = (self.hierarchy_tree.selectedItems())

        if not selected_items:
            return

        selected_item = selected_items[0]
        parent_item = selected_item.parent()

        if parent_item is None:
            return

        item_index = parent_item.indexOfChild(selected_item)

        selected_item = parent_item.takeChild(item_index)

        self.hierarchy_tree.addTopLevelItem(selected_item)

        self.update_selected_joint_info()

    def load_mapping(self):
        """Load Skeleton Mapper data from JSON."""

        print("TODO: Load mapping.")

    def save_mapping(self):
        """Save Skeleton Mapper data to JSON."""

        print("TODO: Save mapping.")

    def open_mirror_configuration(self):
        """Open the mirror settings dialog."""

        if self.mirror_settings_window is not None:
            self.mirror_settings_window.raise_()
            self.mirror_settings_window.activateWindow()
            return

        ui_file = QtCore.QFile(str(MIRROR_SETTINGS_UI_FILE))

        if not ui_file.open(QtCore.QFile.ReadOnly):
            raise RuntimeError(
                "Cannot open UI file: {}".format(MIRROR_SETTINGS_UI_FILE)
            )

        try:
            loader = QtUiTools.QUiLoader()
            self.mirror_settings_window = loader.load(ui_file, self.ui)
        finally:
            ui_file.close()

        if self.mirror_settings_window is None:
            raise RuntimeError(
                "Failed to load UI file: {}".format(MIRROR_SETTINGS_UI_FILE)
            )

        button_box = self.mirror_settings_window.findChild(
            QtWidgets.QDialogButtonBox,
            "mirror_settings_button_box"
        )

        button_box.accepted.connect(self.save_mirror_configuration)
        button_box.rejected.connect(self.close_mirror_configuration)
        self.mirror_settings_window.destroyed.connect(
            self.mirror_configuration_destroyed
        )

        self.populate_mirror_configuration()
        self.mirror_settings_window.show()

    def populate_mirror_configuration(self):
        """Display the currently stored settings in the dialog."""

        window = self.mirror_settings_window

        window.findChild(QtWidgets.QComboBox, "mirror_axis_combo").setCurrentText(
            self.mirror_settings["axis"]
        )
        window.findChild(QtWidgets.QDoubleSpinBox, "mirror_plane_offset_spinbox").setValue(
            self.mirror_settings["plane_offset"]
        )
        window.findChild(QtWidgets.QComboBox, "mirror_direction_combo").setCurrentText(
            self.mirror_settings["direction"]
        )
        window.findChild(QtWidgets.QComboBox, "vertex_match_combo").setCurrentText(
            self.mirror_settings["vertex_match"]
        )
        window.findChild(QtWidgets.QDoubleSpinBox, "mirror_tolerance_spinbox").setValue(
            self.mirror_settings["tolerance"]
        )
        window.findChild(QtWidgets.QLineEdit, "left_token_field").setText(
            self.mirror_settings["left_token"]
        )
        window.findChild(QtWidgets.QLineEdit, "right_token_field").setText(
            self.mirror_settings["right_token"]
        )

    def save_mirror_configuration(self):
        """Store the current mirror settings for the future backend."""

        window = self.mirror_settings_window

        self.mirror_settings = {
            "axis": window.findChild(QtWidgets.QComboBox, "mirror_axis_combo").currentText(),
            "plane_offset": window.findChild(QtWidgets.QDoubleSpinBox, "mirror_plane_offset_spinbox").value(),
            "direction": window.findChild(QtWidgets.QComboBox, "mirror_direction_combo").currentText(),
            "vertex_match": window.findChild(QtWidgets.QComboBox, "vertex_match_combo").currentText(),
            "tolerance": window.findChild(QtWidgets.QDoubleSpinBox, "mirror_tolerance_spinbox").value(),
            "left_token": window.findChild(QtWidgets.QLineEdit, "left_token_field").text(),
            "right_token": window.findChild(QtWidgets.QLineEdit, "right_token_field").text()
        }

        window.accept()
        window.deleteLater()
        self.mirror_settings_window = None

    def close_mirror_configuration(self):
        """Close the mirror settings without saving changes."""

        if self.mirror_settings_window is not None:
            window = self.mirror_settings_window
            self.mirror_settings_window = None
            window.reject()
            window.deleteLater()

    def mirror_configuration_destroyed(self, *args):
        """Clear the settings-dialog reference after Qt deletes it."""

        self.mirror_settings_window = None

    def mirror_selected_region(self):
        """Mirror the selected region using the stored settings."""

        print("TODO: Mirror selected region using:", self.mirror_settings)

    def build_skeleton(self):
        """Validate the mapping and build the Maya skeleton."""

        print("TODO: Build skeleton.")

    def on_close(self):
        """
        Perform Skeleton Mapper-specific cleanup.

        Add Maya callback or scriptJob cleanup here later.
        """

        self.close_mirror_configuration()
        self.regions = []
        self.parent_map = {}


_window = None


def show():
    """Show a fresh Skeleton Mapper window."""

    global _window

    _window = SkeletonMapperUI()
    _window.show()

    return _window


def close():
    """Close the active Skeleton Mapper window."""

    global _window

    if _window is not None:
        _window.close()
        _window = None
