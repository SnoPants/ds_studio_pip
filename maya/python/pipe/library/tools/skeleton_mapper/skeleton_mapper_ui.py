import maya.cmds as cmds

from pipe.library.rigging.ds_skeleton import Skeleton
from pipe.library.rigging.skeleton_data import SkeletonData
from pipe.library.tools.skeleton_mapper.skeleton_region import RegionWidget
from pipe.library.utilities.ds_maya_utils import create_preview_joint_link, create_preview_aimconstraint, node_uuid, node_path, world_rotation
from pathlib import Path

from pipe.library.ui import MayaUI
from pipe.library.ui import QtCore, QtUiTools, QtWidgets

PACKAGE_DIR = Path(__file__).resolve().parent

UI_FILE = (PACKAGE_DIR / "ui" / "skeleton_mapper.ui")
MIRROR_SETTINGS_UI_FILE = (PACKAGE_DIR / "ui" / "mirror_settings.ui")

class SkeletonMapperUI(MayaUI):
    UI_FILE = UI_FILE
    OBJECT_NAME = "DSSkeletonMapperWindow"
    DOCKABLE = True

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
        # Sync trigger: any tree change (drag, add, remove) resyncs the hierarchy.
        # QTreeWidget internal moves may emit remove/insert rather than move.
        self._hierarchy_sync_pending = False
        for signal in (self.hierarchy_tree.model().rowsMoved,
                       self.hierarchy_tree.model().rowsInserted,
                       self.hierarchy_tree.model().rowsRemoved):
            signal.connect(self.schedule_hierarchy_sync)
        self.load_mapping_action.triggered.connect(self.load_mapping)
        self.save_mapping_action.triggered.connect(self.save_mapping)
        self.mirror_configuration_action.triggered.connect(self.open_mirror_configuration)
        self.mirror_region_button.clicked.connect(self.mirror_selected_region)
        self.build_button.clicked.connect(self.build_skeleton)
        self.build_skeleton_only_checkbox.toggled.connect(self.set_build_skeleton_only)

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
        self.build_skeleton_only_checkbox = self.find_widget(QtWidgets.QCheckBox, "build_skeleton_only_checkbox")
        self.build_skeleton_only_checkbox.setChecked(self.skeleton.build_skeleton_only)

    # --- Preview sync system ---------------------------------------------------
    # Keeps the Maya preview objects matching the UI. Anything that changes the
    # hierarchy calls sync_hierarchy_data() (tree signals, add/remove joint,
    # remove region). It walks the Skeleton Hierarchy tree into tree_parents
    # {child_uid: parent_uid}, then hands that to each sync_preview_* function.
    # Each one compares what should exist with what its JointWidget built last
    # time, and only deletes/rebuilds where they differ, so syncing often is
    # safe. Uids connect the tree, the data, and the widgets; the Maya nodes are
    # stored on the JointWidget and never looked up by name.

    # uid -> JointWidget, so a uid from the tree can reach its preview nodes.
    def joint_widgets_by_uid(self):
        joint_widgets = {}
        for index in range(self.region_layout.count()):
            widget = self.region_layout.itemAt(index).widget()
            if isinstance(widget, RegionWidget):
                for joint_widget in widget.joint_widgets:
                    joint_widgets[joint_widget.joint_data.uid] = joint_widget
        return joint_widgets

    # Child owns a link curve to its tree parent. preview_link_parent records
    # which parent it was built for, so unchanged links are skipped.
    def sync_preview_links(self, tree_parents):
        joint_widgets = self.joint_widgets_by_uid()
        for joint_widget in joint_widgets.values():
            parent_uid = tree_parents.get(joint_widget.joint_data.uid)
            if node_path(joint_widget.preview_link) and joint_widget.preview_link_parent == parent_uid:
                continue
            joint_widget.delete_preview_link()
            parent_widget = joint_widgets.get(parent_uid)
            if parent_widget is None or not parent_widget.preview_path() or not joint_widget.preview_path():
                continue
            joint_widget.preview_link = node_uuid(create_preview_joint_link(
                parent_widget.preview_path(), joint_widget.preview_path()))
            joint_widget.preview_link_parent = parent_uid

    # Parent owns an aim constraint at its tree child when Orient Joint is on.
    def sync_preview_orients(self, tree_parents):
        # TODO(planarize): Planarize design, to be written by hand.
        #   - A run of consecutive Planarize-ticked joints in a region, following the
        #     first child as the aim chain, shares one plane built from the ticked
        #     joints only.
        #   - Normal with sign alignment: for each consecutive triplet a, b, c,
        #     n = (b - a) ^ (c - b). Flip n if its dot with the running total is
        #     negative, then sum and normalize.
        #   - Each ticked joint aims at its child with worldUpType "vector" and
        #     worldUpVector = n. A ticked end joint with no child copies its
        #     parent's orientation.
        #   - Warn through RegionWidget.set_planarize_warning, falling back to scene up:
        #       fewer than 3 in a run: "Planarize needs 3+ connected ticked joints."
        #       |n| about 0: "Planarize joints are in a straight line. Add a slight bend."
        #   - Add the planarize flag and the run to preview_orient_key so the
        #     constraints rebuild.
        joint_widgets = self.joint_widgets_by_uid()
        tree_children = {}
        for child_uid, parent_uid  in tree_parents.items():
            tree_children.setdefault(parent_uid, []).append(child_uid)
        for uid, joint_widget in joint_widgets.items():
            joint_data = joint_widget.joint_data
            children = tree_children.get(uid, [])
            child_uid = children[0] if children else None
            key = None
            if joint_data.orient_to_child and child_uid:
                key = (child_uid, joint_data.primary_axis, joint_data.secondary_axis)
            if joint_widget.preview_orient_key == key:
                continue
            joint_widget.delete_preview_orient()
            child_widget = joint_widgets.get(child_uid)
            if key is None or child_widget is None or not joint_widget.preview_path() or not child_widget.preview_path():
                continue
            joint_widget.preview_orient = node_uuid(create_preview_aimconstraint(joint_widget.preview_path(), child_widget.preview_path(), joint_data.primary_axis, joint_data.secondary_axis))
            joint_widget.preview_orient_key = key

    def schedule_hierarchy_sync(self, *args):
        # Wait until a drop has completed before reading parent relationships.
        if not self._hierarchy_sync_pending:
            self._hierarchy_sync_pending = True
            QtCore.QTimer.singleShot(0, self.sync_hierarchy_data)

    # Sync entry point. Reads the tree, updates JointData.parent, then runs
    # each sync_preview_* step with the same tree_parents.
    def sync_hierarchy_data(self):
        self._hierarchy_sync_pending = False                                         # 1. Clear flag; stop if window is closing.
        if self.closed or (hasattr(self, 'ui') and self.ui is None):
            return
        joints = {joint.uid: joint for joint in self.skeleton.joints()}              # 2. uid -> JointData.
        root = self.hierarchy_tree.invisibleRootItem()                               # 3. Walk the tree.
        pending = [(root.child(index), None) for index in range(root.childCount())]  # (item, parent_uid); None at top.
        tree_parents = {}                                                            # Built here: {child_uid: parent_uid}, used by 5 and 6.
        while pending:
            item, parent_uid = pending.pop()
            uid = item.data(0, QtCore.Qt.UserRole)
            if uid in joints:
                joints[uid].parent = parent_uid
                tree_parents[uid] = parent_uid                                       # One entry per joint in the tree.
            pending.extend((item.child(index), uid) for index in range(item.childCount()))
        self.refresh_rig_guides()                                                    # 4. Rig guide UI.
        self.sync_preview_links(tree_parents)                                        # 5. Link curves.
        self.sync_preview_orients(tree_parents)                                      # 6. Aim constraints.

    def set_build_skeleton_only(self, checked):
        self.skeleton.build_skeleton_only = checked
        self.refresh_rig_guides()

    def refresh_rig_guides(self):
        for index in range(self.region_layout.count()):
            widget = self.region_layout.itemAt(index).widget()
            if isinstance(widget, RegionWidget):
                widget.rig_guide_widget.refresh_validation()
                widget.update_rig_guide_visibility()

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
                f"'{name}' is not a mesh. Please choose a valid mesh."
            )
            return False

        # Positions were placed on the old mesh, so they may not fit the new one.
        if self.skeleton.mesh and name != self.skeleton.mesh:
            assigned = sum(1 for joint in self.skeleton.joints() if joint.position is not None)
            if assigned:
                cmds.warning(
                    f"Target mesh changed to '{name}'. {assigned} joint(s) were placed on "
                    f"'{self.skeleton.mesh}' and may need repositioning."
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
        name = f"Region_{index}"
        while name in existing_names:
            index += 1
            name = f"Region_{index}"
        return name

    def remove_region(self, region_widget):
        self.region_layout.removeWidget(region_widget)

        self.skeleton.remove_region(region_widget.region_data)

        if self.selected_region_widget is region_widget:
            self.selected_region_widget = None

        region_widget.deleteLater()
        # Sync trigger: the region's joints left the hierarchy.
        self.sync_hierarchy_data()

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

        print(f"TODO: Filter regions using: {text}")


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
                f"Cannot open UI file: {MIRROR_SETTINGS_UI_FILE}"
            )

        try:
            loader = QtUiTools.QUiLoader()
            self.mirror_settings_window = loader.load(ui_file, self.ui)
        finally:
            ui_file.close()

        if self.mirror_settings_window is None:
            raise RuntimeError(f"Failed to Load UI file: {MIRROR_SETTINGS_UI_FILE}")

        self.mirror_settings_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        button_box = self.mirror_settings_window.findChild(QtWidgets.QDialogButtonBox, "mirror_settings_button_box")

        button_box.accepted.connect(self.save_mirror_configuration)
        button_box.rejected.connect(self.close_mirror_configuration)
        self.mirror_settings_window.destroyed.connect(
        self.mirror_configuration_destroyed)

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

        if not self.skeleton.mesh:
            cmds.warning("Set a target mesh before building.")
            return

        if not list(self.skeleton.joints()):
            cmds.warning("Add at leas one joint before building.")
            return

        # Build where the previews are, even if a move slipped past the callback.
        for joint_widget in self.joint_widgets_by_uid().values():
            path = joint_widget.preview_path()
            if path:
                joint_widget.joint_data.set_position(cmds.xform(path, query=True, worldSpace=True, translation=True))
                joint_widget.joint_data.set_rotation(world_rotation(path))

        skel = Skeleton(self.skeleton.mesh)
        built = skel.build_skeleton(self.skeleton)
        print(f"Built joints. {built}" )

    def on_close(self):
        """
        Perform Skeleton Mapper-specific cleanup.

        Previews and their move callbacks belong to this window, so none are
        left in the scene once it closes.
        """

        self.close_mirror_configuration()
        for joint_widget in self.joint_widgets_by_uid().values():
            joint_widget.delete_previews()
        for group in ("|PreviewGroup|PreviewJoints", "|PreviewGroup|PreviewLinks"):
            if cmds.objExists(group) and not cmds.listRelatives(group, children=True):
                cmds.delete(group)
        if cmds.objExists("|PreviewGroup") and not cmds.listRelatives("|PreviewGroup", children=True):
            cmds.delete("|PreviewGroup")
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
