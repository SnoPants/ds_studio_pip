import maya.cmds as cmds

from pipe.library.tools.skeleton_mapper.skeleton_data import SkeletonData
from pipe.library.tools.skeleton_mapper.skeleton_region import RegionWidget
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
        self.skeleton = SkeletonData()
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

        self.selected_region_widget = None

        super().__init__(parent=parent)

    def connect_signals(self):
        """Find the Designer widgets and connect their signals."""

        self.find_widgets()

        self.use_selected_button.clicked.connect(self.use_selected_mesh)
        # editingFinished, not textChanged: setText does not emit it, so
        # use_selected_mesh writing the field cannot feed back into the model.
        self.mesh_field.editingFinished.connect(self.commit_target_mesh)
        self.add_region_button.clicked.connect(self.add_region)
        self.search_field.textChanged.connect(self.filter_regions)
        self.expand_all_button.clicked.connect(self.hierarchy_tree.expandAll)
        self.hierarchy_tree.itemExpanded.connect(self.sync_hierarchy_branch_expansion)
        self.hierarchy_tree.itemCollapsed.connect(self.sync_hierarchy_branch_expansion)
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

        self.region_layout = self.region_content.layout()
        if self.region_layout is None:
            self.region_layout = QtWidgets.QVBoxLayout(self.region_content)
            self.region_layout.setContentsMargins(0, 0, 0, 0)
        self.region_layout.setAlignment(QtCore.Qt.AlignTop)

        self.hierarchy_tree = self.find_widget(QtWidgets.QTreeWidget,"hierarchy_tree")
        self.hierarchy_tree.setHeaderLabels(["Joint", "Region"])
        header = self.hierarchy_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        self.expand_all_button = self.find_widget(QtWidgets.QPushButton,"expand_all_button")
        self.load_mapping_action = self.find_widget(QtCore.QObject,"load_mapping_action")
        self.save_mapping_action = self.find_widget(QtCore.QObject,"save_mapping_action")
        self.mirror_configuration_action = self.find_widget(QtCore.QObject,"mirror_configuration_action")
        self.mirror_region_button = self.find_widget(QtWidgets.QPushButton,"mirror_region_button")
        self.build_button = self.find_widget(QtWidgets.QPushButton,"build_button")

    def sync_hierarchy_branch_expansion(self, item):
        """Apply Shift-expand/collapse to every descendant of the clicked joint."""
        if not QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier:
            return

        expanded = item.isExpanded()
        pending = [item]

        # Descendant updates must not trigger this handler again.
        with QtCore.QSignalBlocker(self.hierarchy_tree):
            while pending:
                current = pending.pop()
                current.setExpanded(expanded)
                pending.extend(
                    current.child(index) for index in range(current.childCount())
                )


    def is_mesh(self, name):
        """Return True if a node exists and has a mesh shape."""
        if not name or not cmds.objExists(name):
            return False
        return bool(cmds.listRelatives(name, shapes=True, type="mesh"))

    def set_target_mesh(self, name):
        """Validate a mesh name and store it on the model. True if accepted."""
        if not self.is_mesh(name):
            cmds.warning(
                "'{}' is not a mesh. Please choose a valid mesh.".format(name)
            )
            return False

        # Vertex IDs are indices into the old mesh, so they do not carry over.
        if self.skeleton.mesh and name != self.skeleton.mesh:
            assigned = sum(1 for joint in self.skeleton.joints() if joint.vertex_ids)
            if assigned:
                cmds.warning(
                    "Target mesh changed to '{}'. {} joint(s) still hold vertex "
                    "IDs from '{}' and should be reassigned.".format(
                        name, assigned, self.skeleton.mesh
                    )
                )

        self.skeleton.mesh = name
        return True

    def use_selected_mesh(self):
        """Use the selected Maya mesh as the target mesh."""
        selection = cmds.ls(sl=True, objectsOnly=True) or None
        if not selection:
            cmds.warning("No mesh selected. Please select a mesh in the scene.")
            return

        if self.set_target_mesh(selection[0]):
            self.mesh_field.setText(selection[0])

    def commit_target_mesh(self):
        """Write a hand-typed mesh name through to the model."""
        name = self.mesh_field.text().strip()

        if name == self.skeleton.mesh:
            return

        if not name:
            self.skeleton.mesh = None
            return

        if not self.set_target_mesh(name):
            self.mesh_field.setText(self.skeleton.mesh or "")

    def get_next_region_name(self):
        existing_names = self.skeleton.all_region_names()

        index = len(self.skeleton.regions) + 1
        name = "Region_{}".format(index)
        while name in existing_names:
            index += 1
            name = "Region_{}".format(index)
        return name

    def remove_region(self, region_widget):
        self.region_layout.removeWidget(region_widget)

        self.skeleton.remove_region(region_widget.region_data)

        if self.selected_region_widget is region_widget:
            self.selected_region_widget = None

        region_widget.deleteLater()

    def set_selected_region(self, region_widget):
        """Highlight one region and clear the previous highlight."""

        if self.selected_region_widget is region_widget:
            return

        if self.selected_region_widget is not None:
            self.selected_region_widget.set_selected(False)

        self.selected_region_widget = region_widget

        if region_widget is not None:
            region_widget.set_selected(True)
    
    def add_region(self):
        """Add a new joint region."""
        region_name = self.get_next_region_name()
        region_data = self.skeleton.add_region(region_name)

        region_widget = RegionWidget(main_window=self, region_data=region_data, parent=self.region_content)
        region_widget.delete_requested.connect(self.remove_region)
        region_widget.selected.connect(self.set_selected_region)
        spacer_index = self.region_layout.count() - 1
        self.region_layout.insertWidget(spacer_index, region_widget)
        self.set_selected_region(region_widget)

    def filter_regions(self, text):
        """Filter the displayed regions."""

        print("TODO: Filter regions using: {}".format(text))



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

        if self.selected_region_widget is None:
            cmds.warning("No region selected. Click a region to select it first.")
            return

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
        self.skeleton = SkeletonData()

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
