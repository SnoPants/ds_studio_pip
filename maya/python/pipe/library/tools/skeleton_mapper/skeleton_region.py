import maya.cmds as cmds

from pipe.library.rigging.skeleton_data import JointData
from pipe.library.ui import QtCore, QtWidgets

from pipe.library.rigging.rig_type.guide_registry import REGISTRY


class RigGuideWidget(QtWidgets.QWidget):
    configuration_changed = QtCore.Signal()

    def __init__(self, main_window, region_data, parent=None, registry=None):
        super().__init__(parent)
        self.main_window = main_window
        self.region_data = region_data
        self.registry = registry or REGISTRY
        self.config = region_data.rig_guide
        self.editors = {}

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 4, 4, 8)
        form = QtWidgets.QFormLayout()
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItem('Choose rig type', None)

        for key, label in self.registry.rig_types.items():
            self.type_combo.addItem(label, key)

        self.builder_combo = QtWidgets.QComboBox()
        form.addRow('Rig type', self.type_combo)
        form.addRow('Builder', self.builder_combo)
        layout.addLayout(form)

        self.parameter_form = QtWidgets.QFormLayout()
        layout.addLayout(self.parameter_form)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        type_id = self.config.get('rig_type')
        index = self.type_combo.findData(type_id)
        if index < 0:
            self.type_combo.addItem('Unavailable: ' + str(type_id), type_id)
            index = self.type_combo.count() - 1
            
        self.type_combo.setCurrentIndex(index)
        self._populate_builders(self.config.get('builder_id'))
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self.builder_combo.currentIndexChanged.connect(self._builder_changed)
        self.refresh_validation()

    def _populate_builders(self, selected):
        self.builder_combo.blockSignals(True)
        self.builder_combo.clear()
        self.builder_combo.addItem('Choose builder', None)
        for spec in self.registry.for_type(self.type_combo.currentData()):
            self.builder_combo.addItem(spec.label, spec.id)
        index = self.builder_combo.findData(selected)
        if index < 0 and selected:
            self.builder_combo.addItem('Unavailable: ' + selected, selected)
            index = self.builder_combo.count() - 1
        self.builder_combo.setCurrentIndex(max(0, index))
        self.builder_combo.blockSignals(False)
        self._render_parameters()

    def _type_changed(self, *args):
        self.config['rig_type'] = self.type_combo.currentData()
        self.config['builder_id'] = None
        self._populate_builders(None)
        self.refresh_validation()
        self.configuration_changed.emit()

    def _builder_changed(self, *args):
        self.config['builder_id'] = self.builder_combo.currentData()
        self._render_parameters()
        self.refresh_validation()
        self.configuration_changed.emit()

    def _values(self, spec):
        return self.config.setdefault('parameters', {}).setdefault(spec.id, spec.defaults())

    def _render_parameters(self):
        while self.parameter_form.rowCount():
            self.parameter_form.removeRow(0)
        self.editors.clear()
        spec = self.registry.builders.get(self.builder_combo.currentData())
        if spec is None or spec.rig_type != self.type_combo.currentData():
            return
        values = self._values(spec)
        for parameter in spec.parameters:
            value = values.get(parameter.key, parameter.default)
            if parameter.kind == 'bool':
                editor = QtWidgets.QCheckBox()
                editor.setChecked(value is True)
                signal = editor.toggled
            elif parameter.kind == 'string':
                editor = QtWidgets.QLineEdit(str(value))
                signal = editor.textChanged
            elif parameter.kind == 'choice':
                editor = QtWidgets.QComboBox()
                editor.addItems(list(parameter.choices))
                editor.setCurrentIndex(editor.findText(str(value)))
                signal = editor.currentTextChanged
            elif parameter.kind in ('int', 'float'):
                editor = QtWidgets.QSpinBox() if parameter.kind == 'int' else QtWidgets.QDoubleSpinBox()
                editor.setRange(parameter.minimum, parameter.maximum)
                editor.setValue(value if type(value) in (int, float) else parameter.default)
                signal = editor.valueChanged
            else:
                raise ValueError('Unsupported parameter kind: ' + parameter.kind)
            editor.setToolTip(parameter.help)
            signal.connect(lambda value, key=parameter.key, spec=spec: self._parameter_changed(spec, key, value))
            self.editors[parameter.key] = editor
            self.parameter_form.addRow(parameter.label, editor)

    def _parameter_changed(self, spec, key, value):
        self._values(spec)[key] = value
        self.refresh_validation()
        self.configuration_changed.emit()

    def refresh_validation(self):
        skeleton = self.main_window.skeleton
        skeleton_only = skeleton.build_skeleton_only
        # Visibility is owned by RegionWidget, which also knows the collapsed
        # state. This method only decides what the status label says.
        self.status.setVisible(not skeleton_only)
        if skeleton_only:
            # Clear stale validation labels and skip every builder validator.
            for index in range(1, self.builder_combo.count()):
                spec = self.registry.builders.get(self.builder_combo.itemData(index))
                if spec is not None:
                    self.builder_combo.setItemText(index, spec.label)
                self.builder_combo.setItemData(index, None, QtCore.Qt.ToolTipRole)
            self.status.clear()
            return
        selected = self.builder_combo.currentData()
        result = None
        for index in range(1, self.builder_combo.count()):
            spec = self.registry.builders.get(self.builder_combo.itemData(index))
            if spec is None or spec.rig_type != self.type_combo.currentData():
                continue
            check = spec.validate(self.region_data, skeleton, self._values(spec))
            self.builder_combo.setItemText(index, '{} — {}'.format(spec.label, 'Valid' if check.valid else 'Invalid'))
            self.builder_combo.setItemData(index, '\n'.join(check.errors) or 'Region hierarchy is compatible.', QtCore.Qt.ToolTipRole)
            if spec.id == selected:
                result = check
        if result is None:
            message = ('Saved builder is unavailable.' if selected else
                       'Choose a builder.' if self.registry.for_type(self.type_combo.currentData()) else
                       'No builders registered for this rig type.' if self.type_combo.currentData() else 'Choose a rig type.')
            color = '#c8a020'
        elif result.valid:
            names = {joint.uid: joint.name for joint in self.region_data.joints}
            message = 'Valid hierarchy: ' + ' → '.join(names[uid] for uid in result.joint_uids)
            color = '#70b878'
        else:
            message = 'Invalid: ' + '\n'.join(result.errors)
            color = '#e08080'
        self.status.setText(message)
        self.status.setStyleSheet('color: {};'.format(color))


class JointWidget(QtWidgets.QWidget):

    delete_requested = QtCore.Signal(object)

    # Red because a bad joint name blocks the build, unlike a region name.
    NAME_ERROR_STYLE = "QLineEdit { border: 1px solid red; }"

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
        self.tree_item.setData(0, QtCore.Qt.UserRole, self.joint_data.uid)
        self.tree_item.setText(0, self.joint_data.name)
        self.tree_item.setText(1, self.region_tag)

        # Create the expanded joint settings panel
        self.vertex_panel = QtWidgets.QWidget()
        vertex_layout = QtWidgets.QVBoxLayout(self.vertex_panel)
        vertex_layout.setContentsMargins(28, 8, 8, 12)
        vertex_layout.setSpacing(12)

        self.orientation_group = QtWidgets.QGroupBox("Orientation")
        orientation_form = QtWidgets.QFormLayout(self.orientation_group)
        orientation_form.setContentsMargins(12, 18, 12, 12)
        orientation_form.setHorizontalSpacing(20)
        orientation_form.setVerticalSpacing(10)
        self.primary_axis_combo = QtWidgets.QComboBox()
        self.primary_axis_combo.addItems(list(JointData.AXES))
        self.primary_axis_combo.setCurrentText(self.joint_data.primary_axis)
        self.primary_axis_combo.setToolTip("Local primary axis. Primary and secondary must be different.")
        self.secondary_axis_combo = QtWidgets.QComboBox()
        self.secondary_axis_combo.setToolTip("Choose one of the two remaining local axes.")
        self.refresh_orientation_controls()
        orientation_form.addRow("Primary axis", self.primary_axis_combo)
        orientation_form.addRow("Secondary axis", self.secondary_axis_combo)
        self.primary_axis_combo.setFixedWidth(90)
        self.secondary_axis_combo.setFixedWidth(90)
        vertex_layout.addWidget(self.orientation_group)
        self.primary_axis_combo.currentTextChanged.connect(self.update_primary_axis)
        self.secondary_axis_combo.currentTextChanged.connect(self.update_secondary_axis)

        self.vertices_group = QtWidgets.QGroupBox("Vertex IDs")
        vertices_form = QtWidgets.QVBoxLayout(self.vertices_group)
        vertices_form.setContentsMargins(12, 18, 12, 12)
        self.vertex_text = QtWidgets.QPlainTextEdit()
        self.vertex_text.setReadOnly(True)
        self.vertex_text.setFixedHeight(50)

        vertices_form.addWidget(self.vertex_text)
        vertex_layout.addWidget(self.vertices_group)

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

    def refresh_orientation_controls(self):
        with QtCore.QSignalBlocker(self.primary_axis_combo):
            self.primary_axis_combo.setCurrentText(self.joint_data.primary_axis)
        with QtCore.QSignalBlocker(self.secondary_axis_combo):
            self.secondary_axis_combo.clear()
            self.secondary_axis_combo.addItems([
                axis for axis in JointData.AXES
                if axis != self.joint_data.primary_axis
            ])
            self.secondary_axis_combo.setCurrentText(self.joint_data.secondary_axis)

    def update_primary_axis(self, axis):
        secondary = self.joint_data.secondary_axis
        if secondary == axis:
            # Swap roles when the new primary was the current secondary.
            secondary = self.joint_data.primary_axis
        self.joint_data.set_orientation(axis, secondary)
        self.refresh_orientation_controls()

    def update_secondary_axis(self, axis):
        self.joint_data.set_orientation(self.joint_data.primary_axis, axis)

    def toggle_vertex_panel(self):
        visible = not self.vertex_panel.isVisible()
        self.vertex_panel.setVisible(visible)
        self.expand_button.setText("▼" if visible else "▶")
        self.updateGeometry()

    def existing_joint_names(self):
        return self.main_window.skeleton.all_joint_names(exclude=self.joint_data)

    def name_error(self, name):
        """Ask the model whether a name is usable. Returns "" if it is."""
        return JointData.validate_name(name, self.existing_joint_names())

    def update_joint_name(self, text):
        existing = self.existing_joint_names()
        error = JointData.validate_name(text, existing)

        self.name_field.setStyleSheet(self.NAME_ERROR_STYLE if error else "")
        self.name_field.setToolTip(error)

        # Reject in place while typing; finalize_joint_name reverts on exit.
        if error:
            return

        self.joint_data.rename(text, existing)
        self.tree_item.setText(0, text)
        self.last_valid_name = text
        self.main_window.refresh_rig_guides()

    def finalize_joint_name(self):
        if not self.name_error(self.name_field.text()):
            return

        self.name_field.blockSignals(True)
        self.name_field.setText(self.last_valid_name)
        self.name_field.blockSignals(False)
        self.name_field.setStyleSheet("")
        self.name_field.setToolTip("")

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
        target_mesh = self.main_window.skeleton.mesh

        if not target_mesh:
            cmds.warning(
                "No target mesh set. Set a target mesh before assigning vertices."
            )
            return

        selected_vertices = cmds.ls(selection=True, flatten=True) or []
        selected_vertices = [
            vertex for vertex in selected_vertices
            if ".vtx[" in vertex
        ]

        if not selected_vertices:
            cmds.warning("No vertices selected. Please select mesh vertices.")
            return

        vertex_ids = []

        for vertex in selected_vertices:
            vertex_mesh, vertex_id = vertex.split(".vtx[")

            # Vertex IDs only index the target mesh, so foreign ones are garbage.
            if vertex_mesh != target_mesh:
                cmds.warning(
                    "Vertices must come from the target mesh '{}'. "
                    "Found '{}'.".format(target_mesh, vertex_mesh)
                )
                return

            vertex_ids.append(int(vertex_id.rstrip("]")))

        self.joint_data.set_vertices(vertex_ids)
        self.update_display()

    def select_vertices(self):
        mesh = self.main_window.skeleton.mesh
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

    # Both states carry a border so selection never shifts the layout.
    SELECTED_STYLE = (
        "#regionWidget { border: 1px solid #5285a6; border-radius: 2px;"
        " background-color: rgba(82, 133, 166, 40); }"
    )
    DESELECTED_STYLE = (
        "#regionWidget { border: 1px solid transparent; border-radius: 2px; }"
    )
    NAME_WARNING_STYLE = "QLineEdit { border: 1px solid #c8a020; }"

    def __init__(self, main_window, region_data, parent=None):
        super().__init__(parent)

        # Set up the UI
        self.region_data = region_data
        self.main_window = main_window
        self.joint_widgets = []

        self.setObjectName("regionWidget")
        self.setStyleSheet(self.DESELECTED_STYLE)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum
        )

        # Set up the main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
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

        self.rig_guide_widget = RigGuideWidget(main_window, region_data, parent=self)
        main_layout.addWidget(self.rig_guide_widget)

        # Connect signals
        self.expand_button.clicked.connect(self.toggle_region)
        self.delete_button.clicked.connect(self.request_delete)
        self.add_joint_button.clicked.connect(self.add_joint)

        self.update_rig_guide_visibility()

    def toggle_region(self):
        visible = not self.joint_content.isVisible()
        self.joint_content.setVisible(visible)
        self.update_rig_guide_visibility()
        self.expand_button.setText("▼" if visible else "▶")
        self.updateGeometry()

    def update_rig_guide_visibility(self):
        """Rig settings appear only when expanded and rig config is in scope.

        Hidden rather than disabled so region rows stay compact while the
        skeleton builder is being finished. Settings are retained either way.
        """
        self.rig_guide_widget.setVisible(
            self.joint_content.isVisibleTo(self)
            and not self.main_window.skeleton.build_skeleton_only
        )

    def set_selected(self, selected):
        """Highlight or unhighlight this region."""
        self.setStyleSheet(
            self.SELECTED_STYLE if selected else self.DESELECTED_STYLE
        )

    def is_name_duplicate(self, name):
        existing = self.main_window.skeleton.all_region_names(
            exclude=self.region_data
        )
        return name in existing

    def update_region_name(self, text):
        self.region_data.rename(text)

        if not text.strip():
            warning = "Region name is empty."
        elif self.is_name_duplicate(text):
            warning = "Another region already uses this name."
        else:
            warning = ""

        # Region names are organizational, not Maya node names, so a clash
        # warns instead of blocking the edit the way joint names do.
        self.name_label.setStyleSheet(
            self.NAME_WARNING_STYLE if warning else ""
        )
        self.name_label.setToolTip(warning)

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
        # Working inside a region makes it the selected one.
        self.selected.emit(self)

        joint_name = self.get_next_joint_name()
        joint_data = self.region_data.add_joint(joint_name)

        joint_widget = JointWidget(main_window=self.main_window, joint_data=joint_data, region_tag=self.region_data.name, parent=self.joint_content)

        joint_widget.delete_requested.connect(self.remove_joint)

        self.joint_layout.addWidget(joint_widget)
        self.joint_widgets.append(joint_widget)

        self.joint_content.show()
        self.expand_button.setText("▼")
        self.update_rig_guide_visibility()
        self.main_window.sync_hierarchy_data()
        self.updateGeometry()

    def remove_joint(self, joint_widget):
        self.remove_tree_item(joint_widget.tree_item)

        self.joint_layout.removeWidget(joint_widget)

        if joint_widget in self.joint_widgets:
            self.joint_widgets.remove(joint_widget)

        if joint_widget.joint_data in self.region_data.joints:
            self.region_data.remove_joint(joint_widget.joint_data)

        joint_widget.deleteLater()
        self.main_window.sync_hierarchy_data()

    def remove_tree_item(self, tree_item):
        # Preserve child rows (including joints owned by another region).
        # Their parent IDs are synchronized after the removal completes.
        tree = self.main_window.hierarchy_tree
        for child in tree_item.takeChildren():
            tree.addTopLevelItem(child)
        parent = tree_item.parent()

        if parent:
            parent.removeChild(tree_item)
        else:
            index = self.main_window.hierarchy_tree.indexOfTopLevelItem(tree_item)
            self.main_window.hierarchy_tree.takeTopLevelItem(index)
