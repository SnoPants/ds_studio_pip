try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets


# ============================================================
# JOINT ROW
# ============================================================

class JointRowWidget(QtWidgets.QWidget):

    delete_requested = QtCore.Signal(object)
    rename_requested = QtCore.Signal(object)

    move_up_requested = QtCore.Signal(object)
    move_down_requested = QtCore.Signal(object)

    hierarchy_refresh_requested = QtCore.Signal()

    def __init__(self, joint_name="New Joint", parent=None):
        super(JointRowWidget, self).__init__(parent)

        # --------------------------------------------------
        # CURRENT DATA
        # --------------------------------------------------
        #
        # For now, this widget owns its own data.
        #
        # Later, you may want this widget to receive a
        # JointData object instead, for example:
        #
        #     self.joint_data = joint_data
        #
        # Then:
        #
        #     self.joint_name = joint_data.name
        #     self.vertex_ids = joint_data.vertex_ids
        #
        # That would separate UI from data more cleanly.
        # --------------------------------------------------

        self.joint_name = joint_name
        self.vertex_ids = []

        # Keep the whole joint widget vertically compact.
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )

        self._build_ui()
        self._connect_signals()
        self.update_display()

    def _build_ui(self):

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.setAlignment(
            QtCore.Qt.AlignTop
        )

        # --------------------------------------------------
        # MAIN JOINT ROW
        # --------------------------------------------------

        row_widget = QtWidgets.QWidget()

        row_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )

        row_layout = QtWidgets.QHBoxLayout(row_widget)
        row_layout.setContentsMargins(4, 3, 4, 3)
        row_layout.setSpacing(5)

        self.expand_button = QtWidgets.QToolButton()
        self.expand_button.setText("▶")
        self.expand_button.setFixedWidth(20)

        self.name_label = QtWidgets.QLabel(
            self.joint_name
        )

        self.name_label.setMinimumWidth(
            120
        )

        self.count_label = QtWidgets.QLabel(
            "0 verts"
        )

        self.count_label.setMinimumWidth(
            55
        )

        # --------------------------------------------------
        # JOINT ACTION BUTTONS
        # --------------------------------------------------
        #
        # These will eventually call Maya integration logic.
        #
        # Set:
        #     Current Maya vertex selection -> this joint.
        #
        # Select:
        #     Select this joint's stored vertices in Maya.
        #
        # Clear:
        #     Remove stored vertex assignment.
        # --------------------------------------------------

        self.set_button = QtWidgets.QPushButton(
            "Set"
        )

        self.select_button = QtWidgets.QPushButton(
            "Select"
        )

        self.clear_button = QtWidgets.QPushButton(
            "Clear"
        )

        self.set_button.setFixedWidth(52)
        self.select_button.setFixedWidth(52)
        self.clear_button.setFixedWidth(52)

        # --------------------------------------------------
        # JOINT OPTIONS MENU
        # --------------------------------------------------

        self.menu_button = QtWidgets.QToolButton()
        self.menu_button.setText("⋮")

        menu = QtWidgets.QMenu(self)

        rename_action = menu.addAction(
            "Rename"
        )

        menu.addSeparator()

        move_up_action = menu.addAction(
            "Move Up"
        )

        move_down_action = menu.addAction(
            "Move Down"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Delete"
        )

        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self)
        )

        move_up_action.triggered.connect(
            lambda: self.move_up_requested.emit(self)
        )

        move_down_action.triggered.connect(
            lambda: self.move_down_requested.emit(self)
        )

        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self)
        )

        self.menu_button.setMenu(menu)

        self.menu_button.setPopupMode(
            QtWidgets.QToolButton.InstantPopup
        )

        # --------------------------------------------------
        # ROW LAYOUT
        # --------------------------------------------------

        row_layout.addWidget(
            self.expand_button
        )

        row_layout.addWidget(
            self.name_label
        )

        row_layout.addStretch()

        row_layout.addWidget(
            self.count_label
        )

        row_layout.addWidget(
            self.set_button
        )

        row_layout.addWidget(
            self.select_button
        )

        row_layout.addWidget(
            self.clear_button
        )

        row_layout.addWidget(
            self.menu_button
        )

        main_layout.addWidget(
            row_widget
        )

        # --------------------------------------------------
        # EXPANDED VERTEX ID PANEL
        # --------------------------------------------------

        self.vertex_panel = QtWidgets.QWidget()

        self.vertex_panel.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )

        vertex_layout = QtWidgets.QVBoxLayout(
            self.vertex_panel
        )

        vertex_layout.setContentsMargins(
            28,
            3,
            8,
            6
        )

        vertex_layout.setSpacing(4)

        vertex_layout.setAlignment(
            QtCore.Qt.AlignTop
        )

        vertex_label = QtWidgets.QLabel(
            "Vertex IDs"
        )

        vertex_layout.addWidget(
            vertex_label
        )

        self.vertex_text = QtWidgets.QPlainTextEdit()

        self.vertex_text.setReadOnly(
            True
        )

        # Keep this compact.
        self.vertex_text.setFixedHeight(
            50
        )

        self.vertex_text.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )

        vertex_layout.addWidget(
            self.vertex_text
        )

        self.vertex_panel.hide()

        main_layout.addWidget(
            self.vertex_panel
        )

    def _connect_signals(self):

        self.expand_button.clicked.connect(
            self.toggle_vertex_panel
        )

        self.set_button.clicked.connect(
            self.set_vertices
        )

        self.select_button.clicked.connect(
            self.select_vertices
        )

        self.clear_button.clicked.connect(
            self.clear_vertices
        )

    # ======================================================
    # DISPLAY
    # ======================================================

    def toggle_vertex_panel(self):

        visible = not self.vertex_panel.isVisible()

        self.vertex_panel.setVisible(
            visible
        )

        self.expand_button.setText(
            "▼" if visible else "▶"
        )

        # Force Qt to recalculate compact layout sizing.
        self.updateGeometry()

        if self.parentWidget():
            self.parentWidget().updateGeometry()

    def update_display(self):

        self.name_label.setText(
            self.joint_name
        )

        count = len(
            self.vertex_ids
        )

        self.count_label.setText(
            "{} verts".format(count)
        )

        if self.vertex_ids:

            self.vertex_text.setPlainText(
                ", ".join(
                    str(vertex_id)
                    for vertex_id in self.vertex_ids
                )
            )

            self.select_button.setEnabled(
                True
            )

            self.clear_button.setEnabled(
                True
            )

        else:

            self.vertex_text.setPlainText(
                "No vertices assigned."
            )

            self.select_button.setEnabled(
                False
            )

            self.clear_button.setEnabled(
                False
            )

    # ======================================================
    # JOINT NAME
    # ======================================================

    def set_joint_name(self, name):
        """
        INTEGRATION NOTE:

        Right now this simply changes the UI name.

        Later, if you introduce a real JointData/model object,
        update that object here too.

        Example:

            self.joint_data.name = name

        IMPORTANT:
        The hierarchy currently uses joint names as identifiers.

        Long-term, a safer structure would be something like:

            {
                "id": "joint_0012",
                "name": "spine_02_jnt"
            }

        That way a rename does not break parent references.
        """

        self.joint_name = name

        self.update_display()

        self.hierarchy_refresh_requested.emit()

    # ======================================================
    # MAYA INTEGRATION POINT: SET VERTICES
    # ======================================================

    def set_vertices(self):
        """
        MAYA INTEGRATION POINT

        Replace the temporary fake data below.

        Desired future workflow:

            1. Query the current Maya component selection.
            2. Confirm the selection contains vertices.
            3. Confirm they belong to the current target mesh.
            4. Extract vertex IDs.
            5. Store them.
            6. Refresh the UI.

        Prefer putting Maya-specific code in another module:

            maya_utils.py

        For example:

            vertex_ids = maya_utils.get_selected_vertex_ids(
                target_mesh
            )

            self.vertex_ids = vertex_ids
            self.update_display()

        HOW DOES THIS WIDGET GET THE TARGET MESH?

        Recommended options:

            Option A:
                Emit a signal and let the main window handle it.

            Option B:
                Pass a callback into this widget.

            Option C:
                Give this widget access to a central mapping model.

        I would eventually prefer B or C rather than making this
        widget search for the main window directly.
        """

        # --------------------------------------------------
        # TEMPORARY MOCK DATA
        # DELETE THIS WHEN MAYA SELECTION LOGIC IS READY.
        # --------------------------------------------------

        self.vertex_ids = [
            100,
            101,
            102,
            103
        ]

        self.update_display()

    # ======================================================
    # MAYA INTEGRATION POINT: SELECT VERTICES
    # ======================================================

    def select_vertices(self):
        """
        MAYA INTEGRATION POINT

        Future behavior:

            maya_utils.select_vertices(
                target_mesh,
                self.vertex_ids
            )

        Example generated Maya components:

            body_GEO.vtx[100]
            body_GEO.vtx[101]
            body_GEO.vtx[102]

        This lets the artist inspect or modify the stored mapping.
        """

        print(
            "Select vertices:",
            self.joint_name,
            self.vertex_ids
        )

    # ======================================================
    # CLEAR VERTICES
    # ======================================================

    def clear_vertices(self):
        """
        DATA INTEGRATION NOTE

        Once you introduce a mapping model, update the model here
        rather than only changing this widget.

        Example:

            self.joint_data.vertex_ids = []
        """

        self.vertex_ids = []

        self.update_display()


# ============================================================
# REGION WIDGET
# ============================================================

class RegionWidget(QtWidgets.QWidget):

    delete_requested = QtCore.Signal(object)
    rename_requested = QtCore.Signal(object)

    move_up_requested = QtCore.Signal(object)
    move_down_requested = QtCore.Signal(object)

    hierarchy_refresh_requested = QtCore.Signal()

    def __init__(self, region_name="New Region", parent=None):
        super(RegionWidget, self).__init__(parent)

        self.region_name = region_name

        # Currently contains JointRowWidget objects.
        #
        # Eventually you may want:
        #
        #     RegionData
        #         -> contains JointData
        #
        # and have the UI simply display that model.
        self.joints = []

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )

        self._build_ui()

    def _build_ui(self):

        main_layout = QtWidgets.QVBoxLayout(self)

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )

        main_layout.setAlignment(
            QtCore.Qt.AlignTop
        )

        # ==================================================
        # REGION HEADER
        # ==================================================

        header_widget = QtWidgets.QWidget()

        header_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )

        header_layout = QtWidgets.QHBoxLayout(
            header_widget
        )

        header_layout.setContentsMargins(
            4,
            3,
            4,
            3
        )

        header_layout.setSpacing(
            5
        )

        self.expand_button = QtWidgets.QToolButton()

        self.expand_button.setText(
            "▼"
        )

        self.expand_button.setFixedWidth(
            20
        )

        self.name_label = QtWidgets.QLabel(
            self.region_name
        )

        font = self.name_label.font()
        font.setBold(True)

        self.name_label.setFont(
            font
        )

        self.add_joint_button = QtWidgets.QPushButton(
            "+ Joint"
        )

        self.add_joint_button.setFixedWidth(
            60
        )

        # --------------------------------------------------
        # REGION OPTIONS MENU
        # --------------------------------------------------

        self.menu_button = QtWidgets.QToolButton()

        self.menu_button.setText(
            "⋮"
        )

        menu = QtWidgets.QMenu(self)

        rename_action = menu.addAction(
            "Rename Region"
        )

        menu.addSeparator()

        # These only change visual/editor ordering.
        # They DO NOT alter skeleton hierarchy.
        move_up_action = menu.addAction(
            "Move Up"
        )

        move_down_action = menu.addAction(
            "Move Down"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Delete Region"
        )

        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self)
        )

        move_up_action.triggered.connect(
            lambda: self.move_up_requested.emit(self)
        )

        move_down_action.triggered.connect(
            lambda: self.move_down_requested.emit(self)
        )

        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self)
        )

        self.menu_button.setMenu(
            menu
        )

        self.menu_button.setPopupMode(
            QtWidgets.QToolButton.InstantPopup
        )

        header_layout.addWidget(
            self.expand_button
        )

        header_layout.addWidget(
            self.name_label
        )

        header_layout.addStretch()

        header_layout.addWidget(
            self.add_joint_button
        )

        header_layout.addWidget(
            self.menu_button
        )

        main_layout.addWidget(
            header_widget
        )

        # ==================================================
        # JOINT CONTENT
        # ==================================================

        self.content_widget = QtWidgets.QWidget()

        self.content_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )

        self.content_layout = QtWidgets.QVBoxLayout(
            self.content_widget
        )

        self.content_layout.setContentsMargins(
            15,
            0,
            0,
            4
        )

        self.content_layout.setSpacing(
            0
        )

        self.content_layout.setAlignment(
            QtCore.Qt.AlignTop
        )

        main_layout.addWidget(
            self.content_widget
        )

        # ==================================================
        # CONNECTIONS
        # ==================================================

        self.expand_button.clicked.connect(
            self.toggle_region
        )

        self.add_joint_button.clicked.connect(
            self.prompt_add_joint
        )

    # ======================================================
    # REGION DISPLAY
    # ======================================================

    def toggle_region(self):

        visible = not self.content_widget.isVisible()

        self.content_widget.setVisible(
            visible
        )

        self.expand_button.setText(
            "▼" if visible else "▶"
        )

        self.updateGeometry()

    def set_region_name(self, name):
        """
        DATA INTEGRATION NOTE

        Later:

            self.region_data.name = name
        """

        self.region_name = name

        self.name_label.setText(
            name
        )

    # ======================================================
    # JOINT CREATION
    # ======================================================

    def prompt_add_joint(self):

        name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Add Joint",
            "Joint Name:"
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            return

        self.add_joint(
            name
        )

    def add_joint(self, name):
        """
        DATA MODEL INTEGRATION POINT

        Right now:
            Create a Qt widget directly.

        Recommended future behavior:

            joint_data = mapping_model.add_joint(
                region_id,
                name
            )

            joint = JointRowWidget(
                joint_data
            )

        This is where UI and your eventual data model will connect.
        """

        joint = JointRowWidget(
            name
        )

        joint.delete_requested.connect(
            self.delete_joint
        )

        joint.rename_requested.connect(
            self.rename_joint
        )

        joint.move_up_requested.connect(
            self.move_joint_up
        )

        joint.move_down_requested.connect(
            self.move_joint_down
        )

        joint.hierarchy_refresh_requested.connect(
            self.hierarchy_refresh_requested
        )

        self.joints.append(
            joint
        )

        self.content_layout.addWidget(
            joint
        )

        # Refresh right-side skeleton hierarchy because
        # a new skeleton joint definition now exists.
        self.hierarchy_refresh_requested.emit()

        self.updateGeometry()

        return joint

    # ======================================================
    # DELETE JOINT
    # ======================================================

    def delete_joint(self, joint):
        """
        DATA MODEL INTEGRATION POINT

        Later, remove this joint from your mapping model here.

        Also consider whether children in the hierarchy should:
            - become root joints
            - inherit the deleted joint's parent
            - block deletion until hierarchy is fixed

        The current prototype simply removes the joint.
        """

        if joint not in self.joints:
            return

        self.joints.remove(
            joint
        )

        joint.setParent(
            None
        )

        joint.deleteLater()

        self.hierarchy_refresh_requested.emit()

        self.updateGeometry()

    # ======================================================
    # RENAME JOINT
    # ======================================================

    def rename_joint(self, joint):

        name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Rename Joint",
            "Joint Name:",
            text=joint.joint_name
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            return

        joint.set_joint_name(
            name
        )

    # ======================================================
    # VISUAL JOINT REORDERING
    # ======================================================

    def move_joint_up(self, joint):
        """
        IMPORTANT:

        This changes ONLY how joints are displayed in the left panel.

        It does NOT change the skeleton hierarchy.

        The right-hand hierarchy tree is responsible for actual
        parent / child relationships.
        """

        if joint not in self.joints:
            return

        index = self.joints.index(
            joint
        )

        if index <= 0:
            return

        self.joints[index - 1], self.joints[index] = (
            self.joints[index],
            self.joints[index - 1]
        )

        self.content_layout.removeWidget(
            joint
        )

        self.content_layout.insertWidget(
            index - 1,
            joint
        )

    def move_joint_down(self, joint):

        if joint not in self.joints:
            return

        index = self.joints.index(
            joint
        )

        if index >= len(self.joints) - 1:
            return

        self.joints[index + 1], self.joints[index] = (
            self.joints[index],
            self.joints[index + 1]
        )

        self.content_layout.removeWidget(
            joint
        )

        self.content_layout.insertWidget(
            index + 1,
            joint
        )


# ============================================================
# SKELETON HIERARCHY TREE
# ============================================================

class HierarchyTree(QtWidgets.QTreeWidget):
    """
    This panel defines the future skeleton hierarchy.

    Dragging joints here changes intended parent relationships.

    IMPORTANT:
    This does NOT manipulate Maya joints yet.

    It is only editing the skeleton definition that will eventually
    be passed to your skeleton builder.
    """

    hierarchy_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(HierarchyTree, self).__init__(parent)

        self.setHeaderLabels(
            ["Skeleton Hierarchy"]
        )

        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )

        self.setDragEnabled(
            True
        )

        self.setAcceptDrops(
            True
        )

        self.setDropIndicatorShown(
            True
        )

        self.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )

        self.setDefaultDropAction(
            QtCore.Qt.MoveAction
        )

    def dropEvent(self, event):

        super(HierarchyTree, self).dropEvent(
            event
        )

        # Tell main UI to convert the visual tree back into
        # parent relationship data.
        self.hierarchy_changed.emit()


# ============================================================
# MAIN WINDOW
# ============================================================

class JointPlacementMapper(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(JointPlacementMapper, self).__init__(
            parent
        )

        self.setWindowTitle(
            "Joint Placement Mapper"
        )

        self.resize(
            1000,
            650
        )

        # --------------------------------------------------
        # CURRENT EDITOR DATA
        # --------------------------------------------------
        #
        # These are currently stored using UI widgets.
        #
        # Eventually you may want:
        #
        #     self.mapping_model = MappingData()
        #
        # Then the UI becomes purely an editor/view.
        # --------------------------------------------------

        self.regions = []

        # --------------------------------------------------
        # HIERARCHY DATA
        # --------------------------------------------------
        #
        # Example:
        #
        # {
        #     "pelvis_jnt": None,
        #     "spine_01_jnt": "pelvis_jnt",
        #     "spine_02_jnt": "spine_01_jnt"
        # }
        #
        # None = root joint.
        #
        # Long-term, consider storing joint IDs instead of names.
        # --------------------------------------------------

        self.parent_map = {}

        self._build_ui()

    def _build_ui(self):

        main_layout = QtWidgets.QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            8,
            8,
            8,
            8
        )

        main_layout.setSpacing(
            6
        )

        # ==================================================
        # TARGET MESH
        # ==================================================

        mesh_layout = QtWidgets.QHBoxLayout()

        mesh_layout.addWidget(
            QtWidgets.QLabel(
                "Target Mesh:"
            )
        )

        self.mesh_field = QtWidgets.QLineEdit()

        self.mesh_field.setPlaceholderText(
            "body_GEO"
        )

        self.use_selected_button = QtWidgets.QPushButton(
            "Use Selected"
        )

        mesh_layout.addWidget(
            self.mesh_field
        )

        mesh_layout.addWidget(
            self.use_selected_button
        )

        main_layout.addLayout(
            mesh_layout
        )

        # ==================================================
        # MAIN SPLITTER
        # ==================================================

        splitter = QtWidgets.QSplitter(
            QtCore.Qt.Horizontal
        )

        main_layout.addWidget(
            splitter
        )

        # ==================================================
        # LEFT PANEL
        # ==================================================

        left_panel = QtWidgets.QWidget()

        left_layout = QtWidgets.QVBoxLayout(
            left_panel
        )

        left_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        left_layout.setSpacing(
            4
        )

        # --------------------------------------------------
        # LEFT TOOLBAR
        # --------------------------------------------------

        left_toolbar = QtWidgets.QHBoxLayout()

        left_toolbar.addWidget(
            QtWidgets.QLabel(
                "Joint Regions"
            )
        )

        self.add_region_button = QtWidgets.QPushButton(
            "+ Region"
        )

        left_toolbar.addWidget(
            self.add_region_button
        )

        left_toolbar.addStretch()

        self.search_field = QtWidgets.QLineEdit()

        self.search_field.setPlaceholderText(
            "Search..."
        )

        left_toolbar.addWidget(
            self.search_field
        )

        left_layout.addLayout(
            left_toolbar
        )

        # --------------------------------------------------
        # REGION SCROLL AREA
        # --------------------------------------------------

        self.region_scroll = QtWidgets.QScrollArea()

        self.region_scroll.setWidgetResizable(
            True
        )

        self.region_content = QtWidgets.QWidget()

        self.region_layout = QtWidgets.QVBoxLayout(
            self.region_content
        )

        self.region_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.region_layout.setSpacing(
            3
        )

        # Keeps all region content packed at the top.
        self.region_layout.setAlignment(
            QtCore.Qt.AlignTop
        )

        self.region_scroll.setWidget(
            self.region_content
        )

        left_layout.addWidget(
            self.region_scroll
        )

        splitter.addWidget(
            left_panel
        )

        # ==================================================
        # RIGHT PANEL
        # ==================================================

        right_panel = QtWidgets.QWidget()

        right_layout = QtWidgets.QVBoxLayout(
            right_panel
        )

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        right_layout.setSpacing(
            4
        )

        # --------------------------------------------------
        # HIERARCHY HEADER
        # --------------------------------------------------

        hierarchy_header = QtWidgets.QHBoxLayout()

        hierarchy_header.addWidget(
            QtWidgets.QLabel(
                "Skeleton Hierarchy"
            )
        )

        hierarchy_header.addStretch()

        self.unparent_button = QtWidgets.QPushButton(
            "Unparent"
        )

        self.expand_all_button = QtWidgets.QPushButton(
            "Expand All"
        )

        hierarchy_header.addWidget(
            self.unparent_button
        )

        hierarchy_header.addWidget(
            self.expand_all_button
        )

        right_layout.addLayout(
            hierarchy_header
        )

        # --------------------------------------------------
        # HIERARCHY TREE
        # --------------------------------------------------

        self.hierarchy_tree = HierarchyTree()

        right_layout.addWidget(
            self.hierarchy_tree
        )

        # --------------------------------------------------
        # SELECTED JOINT INFO
        # --------------------------------------------------

        selected_group = QtWidgets.QGroupBox(
            "Selected Joint"
        )

        selected_layout = QtWidgets.QFormLayout(
            selected_group
        )

        self.selected_joint_field = QtWidgets.QLineEdit()

        self.selected_joint_field.setReadOnly(
            True
        )

        self.parent_joint_field = QtWidgets.QLineEdit()

        self.parent_joint_field.setReadOnly(
            True
        )

        selected_layout.addRow(
            "Joint:",
            self.selected_joint_field
        )

        selected_layout.addRow(
            "Parent:",
            self.parent_joint_field
        )

        right_layout.addWidget(
            selected_group
        )

        splitter.addWidget(
            right_panel
        )

        splitter.setSizes(
            [600, 400]
        )

        # ==================================================
        # BOTTOM BAR
        # ==================================================

        self.load_button = QtWidgets.QPushButton(
            "Load Mapping"
        )

        self.save_button = QtWidgets.QPushButton(
            "Save Mapping"
        )

        self.build_button = QtWidgets.QPushButton(
            "Build Skeleton"
        )

        bottom_layout = QtWidgets.QHBoxLayout()

        bottom_layout.addWidget(
            self.load_button
        )

        bottom_layout.addWidget(
            self.save_button
        )

        bottom_layout.addStretch()

        bottom_layout.addWidget(
            self.build_button
        )

        main_layout.addLayout(
            bottom_layout
        )

        # ==================================================
        # UI SIGNAL CONNECTIONS
        # ==================================================

        self.add_region_button.clicked.connect(
            self.prompt_add_region
        )

        self.search_field.textChanged.connect(
            self.filter_regions
        )

        self.hierarchy_tree.itemSelectionChanged.connect(
            self.update_selected_joint_info
        )

        self.hierarchy_tree.hierarchy_changed.connect(
            self.read_hierarchy_from_tree
        )

        self.unparent_button.clicked.connect(
            self.unparent_selected
        )

        self.expand_all_button.clicked.connect(
            self.hierarchy_tree.expandAll
        )

        # --------------------------------------------------
        # FUTURE INTEGRATION CONNECTIONS
        # --------------------------------------------------

        self.use_selected_button.clicked.connect(
            self.use_selected_mesh
        )

        self.save_button.clicked.connect(
            self.save_mapping
        )

        self.load_button.clicked.connect(
            self.load_mapping
        )

        self.build_button.clicked.connect(
            self.build_skeleton
        )

    # ======================================================
    # MAYA INTEGRATION POINT: TARGET MESH
    # ======================================================

    def use_selected_mesh(self):
        """
        MAYA INTEGRATION POINT

        Replace this with something like:

            mesh = maya_utils.get_selected_mesh()

            if not mesh:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid Selection",
                    "Please select a mesh."
                )
                return

            self.mesh_field.setText(mesh)

        maya_utils.get_selected_mesh() should probably:
            - inspect Maya selection
            - resolve transform -> mesh shape if needed
            - verify object really has mesh geometry
            - return a stable mesh name/path

        If using a central model:

            self.mapping_model.mesh = mesh
        """

        print("TODO: Get selected Maya mesh.")

    # ======================================================
    # REGION CREATION
    # ======================================================

    def prompt_add_region(self):

        name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Add Region",
            "Region Name:"
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            return

        self.add_region(
            name
        )

    def add_region(self, name):
        """
        DATA MODEL INTEGRATION POINT

        Eventually:

            region_data = self.mapping_model.add_region(name)

            region = RegionWidget(region_data)

        Right now the widget itself stores the data.
        """

        region = RegionWidget(
            name
        )

        region.delete_requested.connect(
            self.delete_region
        )

        region.rename_requested.connect(
            self.rename_region
        )

        region.move_up_requested.connect(
            self.move_region_up
        )

        region.move_down_requested.connect(
            self.move_region_down
        )

        region.hierarchy_refresh_requested.connect(
            self.refresh_hierarchy_tree
        )

        self.regions.append(
            region
        )

        self.region_layout.addWidget(
            region
        )

        return region

    # ======================================================
    # DELETE REGION
    # ======================================================

    def delete_region(self, region):
        """
        DATA MODEL INTEGRATION POINT

        Later:

            self.mapping_model.remove_region(region.id)

        Since deleting a region may also delete joints,
        remember to repair hierarchy relationships afterward.
        """

        if region not in self.regions:
            return

        self.regions.remove(
            region
        )

        region.setParent(
            None
        )

        region.deleteLater()

        self.refresh_hierarchy_tree()

    # ======================================================
    # RENAME REGION
    # ======================================================

    def rename_region(self, region):

        name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Rename Region",
            "Region Name:",
            text=region.region_name
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            return

        region.set_region_name(
            name
        )

    # ======================================================
    # VISUAL REGION REORDERING
    # ======================================================

    def move_region_up(self, region):
        """
        VISUAL/EDITOR ORDER ONLY

        This does not affect skeleton parenting.
        """

        if region not in self.regions:
            return

        index = self.regions.index(
            region
        )

        if index <= 0:
            return

        self.regions[index - 1], self.regions[index] = (
            self.regions[index],
            self.regions[index - 1]
        )

        self.region_layout.removeWidget(
            region
        )

        self.region_layout.insertWidget(
            index - 1,
            region
        )

    def move_region_down(self, region):

        if region not in self.regions:
            return

        index = self.regions.index(
            region
        )

        if index >= len(self.regions) - 1:
            return

        self.regions[index + 1], self.regions[index] = (
            self.regions[index],
            self.regions[index + 1]
        )

        self.region_layout.removeWidget(
            region
        )

        self.region_layout.insertWidget(
            index + 1,
            region
        )

    # ======================================================
    # SEARCH / FILTER
    # ======================================================

    def filter_regions(self, text):

        text = text.lower().strip()

        for region in self.regions:

            region_match = (
                text in region.region_name.lower()
            )

            visible_joint_count = 0

            for joint in region.joints:

                joint_match = (
                    text in joint.joint_name.lower()
                )

                visible = (
                    not text
                    or region_match
                    or joint_match
                )

                joint.setVisible(
                    visible
                )

                if visible:
                    visible_joint_count += 1

            region.setVisible(
                not text
                or region_match
                or visible_joint_count > 0
            )

    # ======================================================
    # JOINT DATA
    # ======================================================

    def get_all_joint_names(self):

        names = []

        for region in self.regions:

            for joint in region.joints:

                names.append(
                    joint.joint_name
                )

        return names

    # ======================================================
    # HIERARCHY REFRESH
    # ======================================================

    def refresh_hierarchy_tree(self):
        """
        Synchronize the right-hand hierarchy editor with the
        current set of defined joints.

        This does NOT create Maya joints.
        """

        joint_names = self.get_all_joint_names()

        # Remove entries for joints that no longer exist.
        self.parent_map = {
            joint: parent
            for joint, parent in self.parent_map.items()
            if joint in joint_names
        }

        # Repair references to deleted parent joints.
        for joint_name in list(
            self.parent_map.keys()
        ):

            parent_name = self.parent_map[
                joint_name
            ]

            if parent_name not in joint_names:

                self.parent_map[
                    joint_name
                ] = None

        # Add newly created joints as roots by default.
        for joint_name in joint_names:

            if joint_name not in self.parent_map:

                self.parent_map[
                    joint_name
                ] = None

        self.build_tree_from_parent_map()

    # ======================================================
    # BUILD VISUAL TREE FROM DATA
    # ======================================================

    def build_tree_from_parent_map(self):
        """
        UI METHOD

        Converts parent_map into the visual QTreeWidget hierarchy.
        """

        self.hierarchy_tree.clear()

        item_map = {}

        for joint_name in self.parent_map:

            item = QtWidgets.QTreeWidgetItem(
                [joint_name]
            )

            item.setData(
                0,
                QtCore.Qt.UserRole,
                joint_name
            )

            item_map[
                joint_name
            ] = item

        for joint_name, parent_name in self.parent_map.items():

            item = item_map[
                joint_name
            ]

            if (
                parent_name
                and parent_name in item_map
                and parent_name != joint_name
            ):

                item_map[
                    parent_name
                ].addChild(
                    item
                )

            else:

                self.hierarchy_tree.addTopLevelItem(
                    item
                )

        self.hierarchy_tree.expandAll()

    # ======================================================
    # READ USER-EDITED HIERARCHY
    # ======================================================

    def read_hierarchy_from_tree(self):
        """
        DATA INTEGRATION POINT

        Whenever the user drag/reparents something in the tree,
        this converts the visual hierarchy back into data.

        Later, instead of only:

            self.parent_map = new_map

        you might use:

            self.mapping_model.set_parent_map(new_map)

        IMPORTANT:
        Do NOT perform Maya parenting here.

        This panel only defines what the eventual skeleton should be.
        """

        new_map = {}

        def walk_item(
            item,
            parent_name=None
        ):

            joint_name = item.data(
                0,
                QtCore.Qt.UserRole
            )

            new_map[
                joint_name
            ] = parent_name

            for index in range(
                item.childCount()
            ):

                child = item.child(
                    index
                )

                walk_item(
                    child,
                    joint_name
                )

        for index in range(
            self.hierarchy_tree.topLevelItemCount()
        ):

            root_item = self.hierarchy_tree.topLevelItem(
                index
            )

            walk_item(
                root_item,
                None
            )

        self.parent_map = new_map

        self.update_selected_joint_info()

    # ======================================================
    # UNPARENT
    # ======================================================

    def unparent_selected(self):
        """
        EDITOR ACTION ONLY

        Makes selected hierarchy item a root joint in the definition.
        It does not call cmds.parent().
        """

        item = self.hierarchy_tree.currentItem()

        if not item:
            return

        parent = item.parent()

        if not parent:
            return

        parent.removeChild(
            item
        )

        self.hierarchy_tree.addTopLevelItem(
            item
        )

        self.read_hierarchy_from_tree()

    # ======================================================
    # SELECTED JOINT INFO
    # ======================================================

    def update_selected_joint_info(self):

        item = self.hierarchy_tree.currentItem()

        if not item:

            self.selected_joint_field.clear()
            self.parent_joint_field.clear()

            return

        joint_name = item.data(
            0,
            QtCore.Qt.UserRole
        )

        parent_item = item.parent()

        parent_name = ""

        if parent_item:

            parent_name = parent_item.data(
                0,
                QtCore.Qt.UserRole
            )

        self.selected_joint_field.setText(
            joint_name
        )

        self.parent_joint_field.setText(
            parent_name
        )

    # ======================================================
    # SERIALIZATION / BUILD DATA
    # ======================================================

    def get_mapping_data(self):
        """
        IMPORTANT INTEGRATION METHOD

        This converts the current UI state into plain Python data.

        Use this as the handoff point between:

            UI
             ↓
            data
             ↓
            JSON / validation / skeleton builder

        Example returned data:

            {
                "mesh": "body_GEO",

                "regions": [
                    {
                        "name": "Spine",
                        "joints": [
                            {
                                "name": "pelvis_jnt",
                                "vertices": [1, 2, 3]
                            }
                        ]
                    }
                ],

                "hierarchy": {
                    "pelvis_jnt": None,
                    "spine_01_jnt": "pelvis_jnt"
                }
            }
        """

        regions_data = []

        for region in self.regions:

            joints_data = []

            for joint in region.joints:

                joints_data.append({
                    "name": joint.joint_name,
                    "vertices": list(
                        joint.vertex_ids
                    )
                })

            regions_data.append({
                "name": region.region_name,
                "joints": joints_data
            })

        return {
            "mesh": self.mesh_field.text(),
            "regions": regions_data,
            "hierarchy": dict(
                self.parent_map
            )
        }

    # ======================================================
    # JSON INTEGRATION POINT: SAVE
    # ======================================================

    def save_mapping(self):
        """
        JSON INTEGRATION POINT

        Future implementation:

            data = self.get_mapping_data()

            path = QFileDialog.getSaveFileName(...)

            mapping_io.save_json(
                path,
                data
            )

        Recommended module:

            io_utils.py

        Example function:

            def save_mapping(path, data):
                with open(path, "w") as file:
                    json.dump(
                        data,
                        file,
                        indent=4
                    )
        """

        data = self.get_mapping_data()

        print(
            "TODO: Save mapping JSON"
        )

        print(
            data
        )

    # ======================================================
    # JSON INTEGRATION POINT: LOAD
    # ======================================================

    def load_mapping(self):
        """
        JSON INTEGRATION POINT

        Recommended future sequence:

            1. Ask user for JSON file.
            2. Read JSON into dict.
            3. Clear existing regions/UI.
            4. Restore target mesh.
            5. Recreate each region.
            6. Recreate each joint.
            7. Restore vertex IDs.
            8. Restore parent_map.
            9. Refresh hierarchy tree.

        Something like:

            data = mapping_io.load_mapping(path)

            self.load_mapping_data(data)

        I would eventually put the UI reconstruction into a separate:

            load_mapping_data(data)

        method.
        """

        print(
            "TODO: Load mapping JSON"
        )

    # ======================================================
    # VALIDATION INTEGRATION
    # ======================================================

    def validate_mapping(self, data):
        """
        VALIDATION INTEGRATION POINT

        Eventually move this to:

            validator.py

        Things worth validating:

            - target mesh exists
            - target mesh is actually a mesh
            - duplicate joint names
            - every vertex ID exists on target mesh
            - empty vertex groups
            - invalid parent names
            - joint parented to itself
            - hierarchy cycles
            - possibly multiple roots, if you do not allow them

        Return errors/warnings rather than building immediately.

        Example future API:

            result = validator.validate(data)

            if not result.valid:
                show errors
                return False
        """

        return True

    # ======================================================
    # SKELETON BUILD INTEGRATION POINT
    # ======================================================

    def build_skeleton(self):
        """
        MAIN BUILD INTEGRATION POINT

        This should eventually be the orchestrator for your
        actual Maya skeleton generation.

        RECOMMENDED BUILD FLOW:

            data = self.get_mapping_data()

            1. Validate mapping.
            2. Calculate joint positions.
            3. Create all Maya joints.
            4. Parent them using hierarchy.
            5. Orient joints if needed.
            6. Return / select finished skeleton.

        Recommended architecture:

            builder.py

            builder.build_skeleton(data)

        Example builder internals:

            for joint:
                position = maya_utils.calculate_vertex_center(
                    mesh,
                    vertex_ids
                )

                cmds.joint(
                    name=joint_name,
                    position=position
                )

            then:

            for child, parent in hierarchy.items():

                if parent:
                    cmds.parent(
                        child,
                        parent
                    )

        Keep as much Maya-specific build logic OUT of the UI
        class as possible.
        """

        data = self.get_mapping_data()

        # --------------------------------------------------
        # VALIDATE FIRST
        # --------------------------------------------------

        if not self.validate_mapping(
            data
        ):
            return

        # --------------------------------------------------
        # FUTURE:
        #
        # skeleton_builder.build_skeleton(data)
        # --------------------------------------------------

        print(
            "TODO: Build skeleton"
        )

        print(
            data
        )


# ============================================================
# MAYA SAFE LAUNCH
# ============================================================
#
# This lets you rerun the script while developing without
# creating a new duplicate window every time.
#
# Maya already owns the Qt application/event loop, so do NOT
# call QApplication.exec() here.
# ============================================================

try:
    joint_mapper_ui.close()
    joint_mapper_ui.deleteLater()
except:
    pass


joint_mapper_ui = JointPlacementMapper()
joint_mapper_ui.show()