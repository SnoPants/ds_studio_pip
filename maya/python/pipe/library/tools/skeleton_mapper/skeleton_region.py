import maya.cmds as cmds

from pipe.library.ui import QtCore, QtWidgets

class JointWidget(QtWidgets.QWidget):

    delete_requested = QtCore.Signal(object)

    def __init__(self, main_window, joint_data, region_tag, parent=None):
        super().__init__(parent)

        # Set up the joint data
        self.joint_data = joint_data
        self.main_window = main_window
        self.region_tag = region_tag
        # Keep the joint widget vertically compact
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )

        # Create the main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the joint row
        joint_row = QtWidgets.QWidget()
        joint_layout = QtWidgets.QHBoxLayout(joint_row)
        joint_layout.setContentsMargins(4, 3, 4, 3)
        joint_layout.setSpacing(5)

        self.expand_button = QtWidgets.QToolButton()
        self.expand_button.setText("▶")
        self.expand_button.setFixedWidth(20)

        # Joint names are edited directly instead of using a prompt
        self.name_field = QtWidgets.QLineEdit(self.joint_data.name)
        self.name_field.setPlaceholderText("Joint Name")
        self.name_field.setMinimumWidth(120)

        self.count_label = QtWidgets.QLabel("0 verts")
        self.count_label.setMinimumWidth(55)

        # Create buttons
        self.set_button = QtWidgets.QPushButton("Set")
        self.select_button = QtWidgets.QPushButton("Select")
        self.clear_button = QtWidgets.QPushButton("Clear")
        self.delete_button = QtWidgets.QPushButton("Delete")

        self.set_button.setFixedWidth(52)
        self.select_button.setFixedWidth(52)
        self.clear_button.setFixedWidth(52)
        self.delete_button.setFixedWidth(55)

        joint_layout.addWidget(self.expand_button)
        joint_layout.addWidget(self.name_field, 1)
        joint_layout.addWidget(self.count_label)
        joint_layout.addWidget(self.set_button)
        joint_layout.addWidget(self.select_button)
        joint_layout.addWidget(self.clear_button)
        joint_layout.addWidget(self.delete_button)

        main_layout.addWidget(joint_row)

        self.tree_item = QtWidgets.QTreeWidgetItem(self.main_window.hierarchy_tree)
        self.tree_item.setText(0, self.joint_data.name)
        self.tree_item.setText(1, self.region_tag)

        # Create the expanded vertex ID panel
        self.vertex_panel = QtWidgets.QWidget()
        vertex_layout = QtWidgets.QVBoxLayout(self.vertex_panel)
        vertex_layout.setContentsMargins(28, 3, 8, 6)
        vertex_layout.setSpacing(4)

        vertex_label = QtWidgets.QLabel("Vertex IDs")
        self.vertex_text = QtWidgets.QPlainTextEdit()
        self.vertex_text.setReadOnly(True)
        self.vertex_text.setFixedHeight(50)

        vertex_layout.addWidget(vertex_label)
        vertex_layout.addWidget(self.vertex_text)

        self.vertex_panel.hide()
        main_layout.addWidget(self.vertex_panel)

        self.last_valid_name = self.joint_data.name

        # Connect signals
        self.expand_button.clicked.connect(self.toggle_vertex_panel)
        self.name_field.textChanged.connect(self.update_joint_name)
        self.name_field.editingFinished.connect(self.finalize_joint_name)
        self.set_button.clicked.connect(self.set_vertices)
        self.select_button.clicked.connect(self.select_vertices)
        self.clear_button.clicked.connect(self.clear_vertices)
        self.delete_button.clicked.connect(self.request_delete)

        self.update_display()

    def toggle_vertex_panel(self):
        visible = not self.vertex_panel.isVisible()
        self.vertex_panel.setVisible(visible)
        self.expand_button.setText("▼" if visible else "▶")
        self.updateGeometry()

    def is_name_duplicate(self, name):
        existing = self.main_window.skeleton.all_joint_names(exclude=self.joint_data)
        return name in existing

    def update_joint_name(self, text):
        if self.is_name_duplicate(text):
            self.name_field.setStyleSheet("QLineEdit { border: 1px solid red; }")
        else:
            self.name_field.setStyleSheet("")
            self.joint_data.rename(text)
            self.tree_item.setText(0, text)
            self.last_valid_name = text

    def finalize_joint_name(self):
        if self.is_name_duplicate(self.name_field.text()):
            self.name_field.blockSignals(True)
            self.name_field.setText(self.last_valid_name)
            self.name_field.blockSignals(False)
            self.name_field.setStyleSheet("")

    def update_display(self):
        vertex_ids = self.joint_data.vertex_ids
        self.count_label.setText("{} verts".format(len(vertex_ids)))

        if vertex_ids:
            self.vertex_text.setPlainText(
                ", ".join(str(vertex_id) for vertex_id in vertex_ids)
            )
            self.select_button.setEnabled(True)
            self.clear_button.setEnabled(True)
        else:
            self.vertex_text.setPlainText("No vertices assigned.")
            self.select_button.setEnabled(False)
            self.clear_button.setEnabled(False)

    def set_vertices(self):
        selected_vertices = cmds.ls(selection=True, flatten=True) or []
        selected_vertices = [
            vertex for vertex in selected_vertices
            if ".vtx[" in vertex
        ]

        if not selected_vertices:
            cmds.warning("No vertices selected. Please select mesh vertices.")
            return

        mesh = selected_vertices[0].split(".vtx[")[0]
        vertex_ids = []

        for vertex in selected_vertices:
            vertex_mesh, vertex_id = vertex.split(".vtx[")

            if vertex_mesh != mesh:
                cmds.warning("Please select vertices from one mesh.")
                return

            vertex_ids.append(int(vertex_id.rstrip("]")))

        self.joint_data.set_vertices(mesh, vertex_ids)
        self.update_display()

    def select_vertices(self):
        mesh = self.joint_data.mesh
        vertex_ids = self.joint_data.vertex_ids

        if not mesh or not vertex_ids:
            return

        vertices = [
            "{}.vtx[{}]".format(mesh, vertex_id)
            for vertex_id in vertex_ids
        ]

        cmds.select(vertices, replace=True)

    def clear_vertices(self):
        self.joint_data.clear_vertices()
        self.update_display()

    def request_delete(self):
        self.delete_requested.emit(self)

class RegionWidget(QtWidgets.QFrame):

    delete_requested = QtCore.Signal(object)
    selected = QtCore.Signal(object)

    def __init__(self, main_window, region_data, parent=None):
        super().__init__(parent)

        # Set up the UI
        self.region_data = region_data
        self.main_window = main_window
        self.joint_widgets = []

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )

        # Set up the main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create the region header
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(6)

        self.expand_button = QtWidgets.QToolButton()
        self.expand_button.setText("▼")
        self.expand_button.setFixedWidth(20)

        # Create a line edit for the region name
        self.name_label = QtWidgets.QLineEdit(self.region_data.name)
        self.name_label.setPlaceholderText("Region Name")
        self.name_label.textChanged.connect(self.update_region_name)

        # Create buttons
        self.add_joint_button = QtWidgets.QPushButton("+ Joint")
        self.delete_button = QtWidgets.QPushButton("Delete")

        self.add_joint_button.setFixedWidth(75)
        self.delete_button.setFixedWidth(65)

        header_layout.addWidget(self.expand_button)
        header_layout.addWidget(self.name_label, 1)
        header_layout.addWidget(self.add_joint_button)
        header_layout.addWidget(self.delete_button)

        main_layout.addWidget(header_widget)

        # Create the joint content layout
        self.joint_content = QtWidgets.QWidget()
        self.joint_layout = QtWidgets.QVBoxLayout(self.joint_content)
        self.joint_layout.setContentsMargins(15, 0, 0, 4)
        self.joint_layout.setSpacing(0)
        self.joint_layout.setAlignment(QtCore.Qt.AlignTop)

        main_layout.addWidget(self.joint_content)

        # Connect signals
        self.expand_button.clicked.connect(self.toggle_region)
        self.delete_button.clicked.connect(self.request_delete)
        self.add_joint_button.clicked.connect(self.add_joint)

    def toggle_region(self):
        visible = not self.joint_content.isVisible()
        self.joint_content.setVisible(visible)
        self.expand_button.setText("▼" if visible else "▶")
        self.updateGeometry()

    def update_region_name(self, text):
        self.region_data.rename(text)
        for joint_widget in self.joint_widgets:
            joint_widget.tree_item.setText(1, text)
            joint_widget.region_tag = text

    def request_delete(self):
        for joint_widget in self.joint_widgets:
            self.remove_tree_item(joint_widget.tree_item)
        self.joint_widgets.clear()
        self.region_data.joints.clear()
        self.delete_requested.emit(self)

    #TODO: Implement a reset region functionality here

    def mousePressEvent(self, event):
        self.selected.emit(self)
        super().mousePressEvent(event)

    def get_next_joint_name(self):
        existing_names = self.main_window.skeleton.all_joint_names()

        index = len(self.region_data.joints) + 1
        name = "Joint_{}".format(index)
        while name in existing_names:
            index += 1
            name = "Joint_{}".format(index)
        return name

    def add_joint(self):
        joint_name = self.get_next_joint_name()
        joint_data = self.region_data.add_joint(joint_name)

        joint_widget = JointWidget(main_window=self.main_window, joint_data=joint_data, region_tag=self.region_data.name, parent=self.joint_content)

        joint_widget.delete_requested.connect(self.remove_joint)

        self.joint_layout.addWidget(joint_widget)
        self.joint_widgets.append(joint_widget)

        self.joint_content.show()
        self.expand_button.setText("▼")
        self.updateGeometry()

    def remove_joint(self, joint_widget):
        self.remove_tree_item(joint_widget.tree_item)

        self.joint_layout.removeWidget(joint_widget)

        if joint_widget in self.joint_widgets:
            self.joint_widgets.remove(joint_widget)

        if joint_widget.joint_data in self.region_data.joints:
            self.region_data.remove_joint(joint_widget.joint_data)

        joint_widget.deleteLater()

    def remove_tree_item(self, tree_item):
        parent = tree_item.parent()

        if parent:
            parent.removeChild(tree_item)
        else:
            index = self.main_window.hierarchy_tree.indexOfTopLevelItem(tree_item)
            self.main_window.hierarchy_tree.takeTopLevelItem(index)
