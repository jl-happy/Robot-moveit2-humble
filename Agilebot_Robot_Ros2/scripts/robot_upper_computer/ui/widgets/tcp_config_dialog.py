"""
TCP配置对话框
用于添加、编辑、删除工具坐标系
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QGroupBox, QFormLayout, QLineEdit,
                               QDoubleSpinBox, QListWidget, QPushButton,
                               QMessageBox, QDialogButtonBox, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from core.data_models import ToolTCP

class TCPConfigDialog(QDialog):
    # 配置变更信号
    config_changed = Signal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.current_tools = []  # 当前工具列表
        self.current_tool = None  # 当前选中的工具

        self.setWindowTitle("TCP/工具坐标系配置")
        self.resize(700, 500)
        self.setup_ui()
        self.load_tools()

    def setup_ui(self):
        main_layout = QHBoxLayout()

        # === 左侧：工具列表 ===
        list_group = QGroupBox("已定义工具")
        list_layout = QVBoxLayout()

        self.tool_list = QListWidget()
        self.tool_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tool_list.currentRowChanged.connect(self.on_tool_selected)
        list_layout.addWidget(self.tool_list)

        # 列表操作按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建")
        self.add_btn.clicked.connect(self.on_add_tool)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.on_delete_tool)
        self.copy_btn = QPushButton("复制")
        self.copy_btn.clicked.connect(self.on_copy_tool)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.delete_btn)
        list_layout.addLayout(btn_layout)

        list_group.setLayout(list_layout)
        main_layout.addWidget(list_group, 1)

        # === 右侧：参数编辑 ===
        edit_group = QGroupBox("TCP参数")
        edit_layout = QFormLayout()

        # 工具名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: gripper_tip")
        edit_layout.addRow("名称:", self.name_edit)

        # 位置 X, Y, Z (米)
        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-10.0, 10.0)
        self.pos_x.setSingleStep(0.01)
        self.pos_x.setDecimals(4)
        self.pos_x.setSuffix(" m")
        edit_layout.addRow("X:", self.pos_x)

        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-10.0, 10.0)
        self.pos_y.setSingleStep(0.01)
        self.pos_y.setDecimals(4)
        self.pos_y.setSuffix(" m")
        edit_layout.addRow("Y:", self.pos_y)

        self.pos_z = QDoubleSpinBox()
        self.pos_z.setRange(-10.0, 10.0)
        self.pos_z.setSingleStep(0.01)
        self.pos_z.setDecimals(4)
        self.pos_z.setSuffix(" m")
        edit_layout.addRow("Z:", self.pos_z)

        # 姿态 R, P, Y (度)
        self.rot_rx = QDoubleSpinBox()
        self.rot_rx.setRange(-180.0, 180.0)
        self.rot_rx.setSingleStep(1.0)
        self.rot_rx.setDecimals(2)
        self.rot_rx.setSuffix(" °")
        edit_layout.addRow("RX:", self.rot_rx)

        self.rot_ry = QDoubleSpinBox()
        self.rot_ry.setRange(-180.0, 180.0)
        self.rot_ry.setSingleStep(1.0)
        self.rot_ry.setDecimals(2)
        self.rot_ry.setSuffix(" °")
        edit_layout.addRow("RY:", self.rot_ry)

        self.rot_rz = QDoubleSpinBox()
        self.rot_rz.setRange(-180.0, 180.0)
        self.rot_rz.setSingleStep(1.0)
        self.rot_rz.setDecimals(2)
        self.rot_rz.setSuffix(" °")
        edit_layout.addRow("RZ:", self.rot_rz)

        # 参考坐标系
        self.frame_edit = QLineEdit()
        self.frame_edit.setPlaceholderText("例如: tool0")
        self.frame_edit.setText("tool0")
        edit_layout.addRow("参考坐标系:", self.frame_edit)

        edit_group.setLayout(edit_layout)
        main_layout.addWidget(edit_group, 1)

        # === 底部按钮 ===
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)

        # 整体布局
        dialog_layout = QVBoxLayout()
        dialog_layout.addLayout(main_layout)
        dialog_layout.addWidget(button_box)

        self.setLayout(dialog_layout)

    def load_tools(self):
        """从配置文件加载工具列表"""
        self.current_tools = self.config_manager.load_tool_config()
        self.tool_list.clear()
        for tool in self.current_tools:
            self.tool_list.addItem(tool.name)

        if self.current_tools:
            self.tool_list.setCurrentRow(0)
        else:
            self.clear_edit_fields()

    def clear_edit_fields(self):
        """清空编辑区域"""
        self.name_edit.clear()
        self.pos_x.setValue(0.0)
        self.pos_y.setValue(0.0)
        self.pos_z.setValue(0.0)
        self.rot_rx.setValue(0.0)
        self.rot_ry.setValue(0.0)
        self.rot_rz.setValue(0.0)
        self.frame_edit.setText("tool0")

    def on_tool_selected(self, row):
        """工具列表选中项变更"""
        if row < 0 or row >= len(self.current_tools):
            return
        self.current_tool = self.current_tools[row]
        # 填充编辑区域
        self.name_edit.setText(self.current_tool.name)
        self.pos_x.setValue(self.current_tool.position[0])
        self.pos_y.setValue(self.current_tool.position[1])
        self.pos_z.setValue(self.current_tool.position[2])

        # 欧拉角（度）
        euler = self.current_tool.to_euler()
        import math
        self.rot_rx.setValue(math.degrees(euler[0]))
        self.rot_ry.setValue(math.degrees(euler[1]))
        self.rot_rz.setValue(math.degrees(euler[2]))

        self.frame_edit.setText(self.current_tool.frame_id)

    def on_add_tool(self):
        """新建工具"""
        # 清空编辑区域，准备输入新工具
        self.clear_edit_fields()
        self.name_edit.setFocus()
        self.current_tool = None
        self.tool_list.clearSelection()

    def on_copy_tool(self):
        """复制当前工具"""
        if self.current_tool is None:
            QMessageBox.warning(self, "提示", "请先选择一个工具")
            return

        # 创建新工具，名称加"_copy"
        import copy
        new_tool = copy.deepcopy(self.current_tool)
        new_tool.name = new_tool.name + "_copy"

        self.current_tools.append(new_tool)
        self.tool_list.addItem(new_tool.name)
        self.tool_list.setCurrentRow(len(self.current_tools)-1)

    def on_delete_tool(self):
        """删除当前工具"""
        if self.current_tool is None:
            QMessageBox.warning(self, "提示", "请先选择一个工具")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除工具 '{self.current_tool.name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.current_tools.remove(self.current_tool)
            self.tool_list.takeItem(self.tool_list.currentRow())
            self.current_tool = None
            self.clear_edit_fields()

    def get_current_tcp_from_ui(self):
        """从UI获取当前编辑的TCP数据"""
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("工具名称不能为空")

        position = [
            self.pos_x.value(),
            self.pos_y.value(),
            self.pos_z.value()
        ]

        import math
        euler_rad = [
            math.radians(self.rot_rx.value()),
            math.radians(self.rot_ry.value()),
            math.radians(self.rot_rz.value())
        ]

        tool = ToolTCP.from_euler(name, position, euler_rad)
        tool.frame_id = self.frame_edit.text().strip() or "tool0"
        return tool

    def on_accept(self):
        """保存并退出"""
        try:
            # 如果当前有选中的工具，则更新；否则新增
            if self.tool_list.currentRow() >= 0 and self.current_tool is not None:
                # 更新现有工具
                updated_tool = self.get_current_tcp_from_ui()
                idx = self.current_tools.index(self.current_tool)
                self.current_tools[idx] = updated_tool
                self.tool_list.currentItem().setText(updated_tool.name)
            else:
                # 新增工具
                new_tool = self.get_current_tcp_from_ui()
                self.current_tools.append(new_tool)

            # 保存到配置文件
            if self.config_manager.save_tool_config(self.current_tools):
                self.config_changed.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "保存配置文件失败")
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生未知错误: {str(e)}")