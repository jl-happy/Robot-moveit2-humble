from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QAbstractItemView,
    QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from core.data_models import ProgramStep, CommandType
from typing import List, Tuple, Optional, Dict
import json


class ProgramEditor(QWidget):
    """程序编辑器，支持运行/暂停/停止/单步与当前行高亮。"""
    run_clicked = Signal()
    stop_clicked = Signal()
    pause_clicked = Signal()
    resume_clicked = Signal()
    step_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.program_name_edit: QLineEdit
        self.table: QTableWidget
        self.steps: List[ProgramStep] = []
        self._next_id = 1
        self._current_line = 0
        self._error_line = 0
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(8, 8, 8, 8)

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("程序名称:"))
        self.program_name_edit = QLineEdit()
        self.program_name_edit.setPlaceholderText("例如: demo_program")
        header_layout.addWidget(self.program_name_edit)

        open_btn = QPushButton("打开")
        open_btn.clicked.connect(self._open_program)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_program)
        header_layout.addWidget(open_btn)
        header_layout.addWidget(save_btn)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        group = QGroupBox("程序步骤")
        group_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["行号", "指令", "参数", "注释"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        group_layout.addWidget(self.table)
        group.setLayout(group_layout)
        main_layout.addWidget(group)

        btn_layout = QHBoxLayout()

        add_movej_btn = QPushButton("添加 MoveJ")
        add_movej_btn.clicked.connect(lambda: self._add_step(CommandType.MOVEJ))

        add_movel_btn = QPushButton("添加 MoveL")
        add_movel_btn.clicked.connect(lambda: self._add_step(CommandType.MOVEL))

        add_wait_btn = QPushButton("添加 Wait")
        add_wait_btn.clicked.connect(lambda: self._add_step(CommandType.WAIT))

        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self._delete_selected)

        up_btn = QPushButton("上移")
        up_btn.clicked.connect(lambda: self._move_selected(-1))

        down_btn = QPushButton("下移")
        down_btn.clicked.connect(lambda: self._move_selected(1))

        btn_layout.addWidget(add_movej_btn)
        btn_layout.addWidget(add_movel_btn)
        btn_layout.addWidget(add_wait_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(up_btn)
        btn_layout.addWidget(down_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()

        run_btn = QPushButton("运行")
        run_btn.setObjectName("primaryBtn")
        run_btn.clicked.connect(self.run_clicked.emit)
        stop_btn = QPushButton("停止")
        stop_btn.clicked.connect(self.stop_clicked.emit)
        pause_btn = QPushButton("暂停")
        pause_btn.clicked.connect(self.pause_clicked.emit)
        resume_btn = QPushButton("恢复")
        resume_btn.clicked.connect(self.resume_clicked.emit)
        step_btn = QPushButton("单步")
        step_btn.clicked.connect(self.step_clicked.emit)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(run_btn)
        btn_layout.addWidget(stop_btn)
        btn_layout.addWidget(pause_btn)
        btn_layout.addWidget(resume_btn)
        btn_layout.addWidget(step_btn)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def _add_step(self, cmd_type: CommandType):
        line_number = len(self.steps) + 1

        if cmd_type == CommandType.MOVEJ:
            params = {"target": "0,0,0,0,0,0", "velocity": "0.5"}
        elif cmd_type == CommandType.MOVEL:
            params = {"target": "0,0,0,0,0,0", "velocity": "0.2"}
        elif cmd_type == CommandType.WAIT:
            params = {"time": "1.0"}
        else:
            params = {}

        step = ProgramStep(
            id=self._next_id,
            command=cmd_type.value,
            parameters=params,
            comment="",
            line_number=line_number,
        )
        self._next_id += 1
        self.steps.append(step)
        self._refresh_table()

    def _delete_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.steps):
            QMessageBox.information(self, "提示", "请先选择要删除的步骤")
            return
        del self.steps[row]
        for idx, step in enumerate(self.steps, start=1):
            step.line_number = idx
        self._refresh_table()

    def _move_selected(self, direction: int):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.steps):
            return

        new_row = row + direction
        if new_row < 0 or new_row >= len(self.steps):
            return

        self.steps[row], self.steps[new_row] = self.steps[new_row], self.steps[row]
        for idx, step in enumerate(self.steps, start=1):
            step.line_number = idx
        self._refresh_table()
        self.table.selectRow(new_row)

    def _refresh_table(self):
        self.table.setRowCount(len(self.steps))
        for row, step in enumerate(self.steps):
            line_item = QTableWidgetItem(str(step.line_number))
            line_item.setFlags(line_item.flags() & ~Qt.ItemIsEditable)

            cmd_item = QTableWidgetItem(step.command)
            params_text = ", ".join(f"{k}={v}" for k, v in step.parameters.items())
            params_item = QTableWidgetItem(params_text)
            comment_item = QTableWidgetItem(step.comment)

            self.table.setItem(row, 0, line_item)
            self.table.setItem(row, 1, cmd_item)
            self.table.setItem(row, 2, params_item)
            self.table.setItem(row, 3, comment_item)
            self._highlight_row(row)

    def _parse_params(self, raw: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if not raw:
            return result
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for part in parts:
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
        return result

    def _sync_steps_from_table(self):
        for row, step in enumerate(self.steps):
            cmd_item = self.table.item(row, 1)
            params_item = self.table.item(row, 2)
            comment_item = self.table.item(row, 3)

            if cmd_item:
                step.command = cmd_item.text().strip() or step.command
            if comment_item:
                step.comment = comment_item.text().strip()
            if params_item:
                parsed = self._parse_params(params_item.text().strip())
                if parsed:
                    step.parameters = parsed

    def _save_program(self):
        self._sync_steps_from_table()
        file_path, _ = QFileDialog.getSaveFileName(self, "保存程序", "", "Program Files (*.json)")
        if not file_path:
            return
        data = {
            "name": self.get_program_name(),
            "steps": [
                {
                    "id": s.id,
                    "command": s.command,
                    "parameters": s.parameters,
                    "comment": s.comment,
                    "line_number": s.line_number,
                }
                for s in self.steps
            ],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _open_program(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开程序", "", "Program Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.program_name_edit.setText(data.get("name", ""))
            self.steps = []
            max_id = 0
            for i, raw in enumerate(data.get("steps", []), start=1):
                step = ProgramStep(
                    id=int(raw.get("id", i)),
                    command=str(raw.get("command", "MoveJ")),
                    parameters=dict(raw.get("parameters", {})),
                    comment=str(raw.get("comment", "")),
                    line_number=i,
                )
                max_id = max(max_id, step.id)
                self.steps.append(step)
            self._next_id = max_id + 1
            self.clear_error_line()
            self._refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"程序文件无效：{e}")

    def get_steps(self) -> List[ProgramStep]:
        self._sync_steps_from_table()
        return list(self.steps)

    def validate_program(self) -> Tuple[bool, Optional[str], int]:
        self._sync_steps_from_table()
        if not self.steps:
            return False, "程序为空，请先添加步骤。", 0

        for idx, step in enumerate(self.steps, start=1):
            cmd = (step.command or "").strip()
            if cmd not in {"MoveJ", "MoveL", "Wait"}:
                return False, f"第{idx}行指令无效: {cmd}", idx

            if cmd == "Wait":
                t_raw = step.parameters.get("time")
                if t_raw in (None, ""):
                    return False, f"第{idx}行 Wait 缺少 time 参数", idx
                try:
                    t_val = float(t_raw)
                except (ValueError, TypeError):
                    return False, f"第{idx}行 Wait 的 time 不是数字", idx
                if t_val < 0:
                    return False, f"第{idx}行 Wait 的 time 不能为负数", idx

            if cmd in {"MoveJ", "MoveL"}:
                vel_raw = step.parameters.get("velocity")
                if vel_raw in (None, ""):
                    return False, f"第{idx}行 {cmd} 缺少 velocity 参数", idx
                try:
                    vel_val = float(vel_raw)
                except (ValueError, TypeError):
                    return False, f"第{idx}行 {cmd} 的 velocity 不是数字", idx
                if vel_val <= 0:
                    return False, f"第{idx}行 {cmd} 的 velocity 必须大于0", idx

                target_raw = step.parameters.get("target")
                if target_raw in (None, ""):
                    return False, f"第{idx}行 {cmd} 缺少 target 参数", idx
                values = [v.strip() for v in str(target_raw).split(",") if v.strip()]
                if len(values) != 6:
                    return False, f"第{idx}行 {cmd} 的 target 需要6个数值", idx
                try:
                    [float(v) for v in values]
                except ValueError:
                    return False, f"第{idx}行 {cmd} 的 target 含非法数字", idx

        return True, None, 0

    def get_program_name(self) -> str:
        name = self.program_name_edit.text().strip()
        return name if name else "—"

    def set_current_line(self, line: int):
        if self._current_line == line:
            return
        old_row = self._current_line - 1 if self._current_line >= 1 else -1
        self._current_line = line
        new_row = self._current_line - 1 if self._current_line >= 1 else -1
        if 0 <= old_row < self.table.rowCount():
            self._highlight_row(old_row, on=False)
        if 0 <= new_row < self.table.rowCount():
            self._highlight_row(new_row, on=True)

    def set_error_line(self, line: int):
        self._error_line = line if line > 0 else 0
        self._refresh_table()

    def clear_error_line(self):
        self._error_line = 0
        self._refresh_table()

    def _highlight_row(self, row: int, on: bool = None):
        if row < 0 or row >= self.table.rowCount():
            return
        if on is None:
            on = row == self._current_line - 1

        error_on = row == self._error_line - 1
        if error_on:
            color = QColor(255, 214, 214)
        elif on:
            color = QColor(255, 255, 200)
        else:
            color = QColor(255, 255, 255)

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(color))
