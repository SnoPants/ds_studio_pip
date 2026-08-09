from pathlib import Path

from pipe.library.ui import MayaUI
from pipe.library.ui import QtWidgets

PACKAGE_DIR = Path(__file__).resolve().parent

UI_FILE = (PACKAGE_DIR / "ui" / "skeleton_mapper.ui")

class SkeletonMapperUI(MayaUI):
    UI_FILE = UI_FILE
    OBJECT_NAME = "DSSkeletonMapperWindow"

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.regions = []
        self.parent_map = {}

    def connect_signals(self):
        """Find the Designer widgets and connect their signals."""

        self.find_widgets()

        self.use_selected_button.clicked.connect(self.use_selected_mesh)
        self.add_region_button.clicked.connect(self.add_region)
        self.search_field.textChanged.connect(self.filter_regions)
        self.hierarchy_tree.itemSelectionChanged.connect(self.update_selected_joint_info)
        self.unparent_button.clicked.connect(self.unparent_selected)
        self.expand_all_button.clicked.connect(self.hierarchy_tree.expandAll)
        self.load_button.clicked.connect(self.load_mapping)
        self.save_button.clicked.connect(self.save_mapping)
        self.build_button.clicked.connect(self.build_skeleton)

    def find_widgets(self):

        """Store references to widgets created in Qt Designer."""

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
        self.load_button = self.find_widget(QtWidgets.QPushButton,"load_button")
        self.save_button = self.find_widget(QtWidgets.QPushButton,"save_button")
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

    def build_skeleton(self):
        """Validate the mapping and build the Maya skeleton."""

        print("TODO: Build skeleton.")

    def on_close(self):
        """
        Perform Skeleton Mapper-specific cleanup.

        Add Maya callback or scriptJob cleanup here later.
        """

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