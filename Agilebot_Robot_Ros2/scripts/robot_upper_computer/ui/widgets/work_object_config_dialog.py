"""
工件坐标系配置对话框
用于添加、编辑、删除工件坐标系（WorkObject）
"""
import copy
import math
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QListWidget,
    QPushButton,
    QMessageBox,
    QDialogButtonBox,
    QAbstractItemView,
    QSpinBox,
)
from PySide6.QtCore import Qt, Signal
from core.data_models import WorkObject


class WorkObjectConfigDialog(QDialog):
    config_changed = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.current_objects: list = []
        self.current_obj = None

        self.setWindowTitle("工件坐标系配置")
        self.resize(650, 480)
        self.setup_ui()
        self.load_objects()

    def setup_ui(self):
        main_layout = QHBoxLayout()

        list_group = QGroupBox("已定义工件坐标系")
        list_layout = QVBoxLayout()
        self.wo_list = QListWidget()
        self.wo_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.wo_list.currentRowChanged.connect(self.on_selection_changed)
        list_layout.addWidget(self.wo_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("新建")
        add_btn.clicked.connect(self.on_add)
        copy_btn = QPushButton("复制")
        copy_btn.clicked.connect(self.on_copy)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.on_delete)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(del_btn)
        list_layout.addLayout(btn_layout)
        list_group.setLayout(list_layout)
        main_layout.addWidget(list_group, 1)

        edit_group = QGroupBox("参数")
        edit_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: table_1")
        edit_layout.addRow("名称:", self.name_edit)

        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-50.0, 50.0)
        self.pos_x.setDecimals(4)
        self.pos_x.setSuffix(" m")
        edit_layout.addRow("X:", self.pos_x)
        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-50.0, 50.0)
        self.pos_y.setDecimals(4)
        self.pos_y.setSuffix(" m")
        edit_layout.addRow("Y:", self.pos_y)
        self.pos_z = QDoubleSpinBox()
        self.pos_z.setRange(-50.0, 50.0)
        self.pos_z.setDecimals(4)
        self.pos_z.setSuffix(" m")
        edit_layout.addRow("Z:", self.pos_z)

        self.rot_rx = QDoubleSpinBox()
        self.rot_rx.setRange(-180.0, 180.0)
        self.rot_rx.setDecimals(2)
        self.rot_rx.setSuffix(" °")
        edit_layout.addRow("RX:", self.rot_rx)
        self.rot_ry = QDoubleSpinBox()
        self.rot_ry.setRange(-180.0, 180.0)
        self.rot_ry.setDecimals(2)
        self.rot_ry.setSuffix(" °")
        edit_layout.addRow("RY:", self.rot_ry)
        self.rot_rz = QDoubleSpinBox()
        self.rot_rz.setRange(-180.0, 180.0)
        self.rot_rz.setDecimals(2)
        self.rot_rz.setSuffix(" °")
        edit_layout.addRow("RZ:", self.rot_rz)

        self.frame_edit = QLineEdit()
        self.frame_edit.setPlaceholderText("例如: world")
        self.frame_edit.setText("world")
        edit_layout.addRow("参考坐标系:", self.frame_edit)

        self.user_frame_id_spin = QSpinBox()
        self.user_frame_id_spin.setRange(0, 99)
        edit_layout.addRow("用户帧 ID:", self.user_frame_id_spin)

        edit_group.setLayout(edit_layout)
        main_layout.addWidget(edit_group, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def load_objects(self):
        self.current_objects = self.config_manager.load_work_object_config()
        self.wo_list.clear()
        for wo in self.current_objects:
            self.wo_list.addItem(wo.name)
        if self.current_objects:
            self.wo_list.setCurrentRow(0)
        else:
            self.clear_edit()

    def clear_edit(self):
        self.name_edit.clear()
        self.pos_x.setValue(0.0)
        self.pos_y.setValue(0.0)
        self.pos_z.setValue(0.0)
        self.rot_rx.setValue(0.0)
        self.rot_ry.setValue(0.0)
        self.rot_rz.setValue(0.0)
        self.frame_edit.setText("world")
        self.user_frame_id_spin.setValue(0)

    def on_selection_changed(self, row):
        if row < 0 or row >= len(self.current_objects):
            return
        self.current_obj = self.current_objects[row]
        self.name_edit.setText(self.current_obj.name)
        self.pos_x.setValue(self.current_obj.position[0])
        self.pos_y.setValue(self.current_obj.position[1])
        self.pos_z.setValue(self.current_obj.position[2])
        euler = self.current_obj.to_euler()
        self.rot_rx.setValue(math.degrees(euler[0]))
        self.rot_ry.setValue(math.degrees(euler[1]))
        self.rot_rz.setValue(math.degrees(euler[2]))
        self.frame_edit.setText(self.current_obj.frame_id)
        self.user_frame_id_spin.setValue(self.current_obj.user_frame_id)

    def on_add(self):
        self.clear_edit()
        self.name_edit.setFocus()
        self.current_obj = None
        self.wo_list.clearSelection()

    def on_copy(self):
        if self.current_obj is None:
            QMessageBox.warning(self, "提示", "请先选择一个工件坐标系")
            return
        new_wo = copy.deepcopy(self.current_obj)
        new_wo.name = new_wo.name + "_copy"
        self.current_objects.append(new_wo)
        self.wo_list.addItem(new_wo.name)
        self.wo_list.setCurrentRow(len(self.current_objects) - 1)

    def on_delete(self):
        if self.current_obj is None:
            QMessageBox.warning(self, "提示", "请先选择一个工件坐标系")
            return
        if QMessageBox.Yes != QMessageBox.question(
            self, "确认删除", f"确定删除 '{self.current_obj.name}' 吗？", QMessageBox.Yes | QMessageBox.No
        ):
            return
        self.current_objects.remove(self.current_obj)
        self.wo_list.takeItem(self.wo_list.currentRow())
        self.current_obj = None
        self.clear_edit()

    def get_current_wo_from_ui(self) -> WorkObject:
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("名称不能为空")
        pos = [self.pos_x.value(), self.pos_y.value(), self.pos_z.value()]
        euler_rad = [
            math.radians(self.rot_rx.value()),
            math.radians(self.rot_ry.value()),
            math.radians(self.rot_rz.value()),
        ]
        return WorkObject.from_euler(
            name=name,
            position=pos,
            euler=euler_rad,
            frame_id=self.frame_edit.text().strip() or "world",
            user_frame_id=self.user_frame_id_spin.value(),
        )

    def on_accept(self):
        try:
            if self.wo_list.currentRow() >= 0 and self.current_obj is not None:
                updated = self.get_current_wo_from_ui()
                idx = self.current_objects.index(self.current_obj)
                self.current_objects[idx] = updated
                self.wo_list.currentItem().setText(updated.name)
            else:
                new_wo = self.get_current_wo_from_ui()
                self.current_objects.append(new_wo)

            if self.config_manager.save_work_object_config(self.current_objects):
                self.config_changed.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "保存配置失败")
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
