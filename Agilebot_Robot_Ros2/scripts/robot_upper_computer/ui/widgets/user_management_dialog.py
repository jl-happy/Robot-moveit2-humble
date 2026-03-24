from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QAbstractItemView,
)

from core.config_manager import ConfigManager


class UserManagementDialog(QDialog):
    """用户管理（仅超级管理者）"""

    def __init__(self, current_username: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户管理")
        self.resize(700, 420)
        self._config = ConfigManager()
        self._users = []
        self._current_username = current_username.strip()
        self._build_ui()
        self._load_users()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("用户管理（使用者 / 管理者 / 超级管理者）")
        title.setProperty("pageTitle", True)
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["用户名", "角色", "密码(留空则不修改)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.table)

        form_row = QHBoxLayout()
        self.new_user_edit = QLineEdit()
        self.new_user_edit.setPlaceholderText("新用户名")
        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setPlaceholderText("新用户密码")
        self.new_role_combo = QComboBox()
        self.new_role_combo.addItems(["使用者", "管理者", "超级管理者"])

        add_btn = QPushButton("添加用户")
        add_btn.clicked.connect(self._add_user)

        form_row.addWidget(self.new_user_edit)
        form_row.addWidget(self.new_pwd_edit)
        form_row.addWidget(self.new_role_combo)
        form_row.addWidget(add_btn)
        layout.addLayout(form_row)

        btn_row = QHBoxLayout()
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self._delete_selected)
        save_btn = QPushButton("保存修改")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)

        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _load_users(self):
        self._users = self._config.load_users()
        self._refresh_table_from_memory()

    def _refresh_table_from_memory(self):
        self.table.setRowCount(len(self._users))
        for i, user in enumerate(self._users):
            self.table.setItem(i, 0, QTableWidgetItem(str(user.get("username", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(user.get("role", "使用者"))))
            self.table.setItem(i, 2, QTableWidgetItem(""))

    def _add_user(self):
        username = self.new_user_edit.text().strip()
        pwd = self.new_pwd_edit.text().strip()
        role = self.new_role_combo.currentText()

        if not username or not pwd:
            QMessageBox.warning(self, "提示", "用户名和密码不能为空")
            return

        if any(str(u.get("username", "")).strip() == username for u in self._users):
            QMessageBox.warning(self, "提示", "用户名已存在")
            return

        self._users.append({
            "username": username,
            "password": pwd,
            "role": role,
        })
        self.new_user_edit.clear()
        self.new_pwd_edit.clear()
        self._refresh_table_from_memory()

    def _delete_selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._users):
            QMessageBox.information(self, "提示", "请先选择要删除的用户")
            return

        target_username = str(self._users[row].get("username", "")).strip()
        if self._current_username and target_username == self._current_username:
            QMessageBox.warning(self, "禁止操作", "不能删除当前登录用户。")
            return

        del self._users[row]
        self._refresh_table_from_memory()

    def _save(self):
        users_to_save = []
        super_admin_count = 0

        for row in range(self.table.rowCount()):
            username_item = self.table.item(row, 0)
            role_item = self.table.item(row, 1)
            pwd_item = self.table.item(row, 2)

            username = username_item.text().strip() if username_item else ""
            role = role_item.text().strip() if role_item else "使用者"
            new_pwd = pwd_item.text().strip() if pwd_item else ""

            if not username:
                continue

            if role == "超级管理者":
                super_admin_count += 1

            original = next((u for u in self._users if str(u.get("username", "")).strip() == username), None)
            user_data = {
                "username": username,
                "role": role,
            }

            if new_pwd:
                user_data["password"] = new_pwd
            elif original and original.get("password_hash"):
                user_data["password_hash"] = original.get("password_hash")
            elif original and original.get("password"):
                user_data["password"] = original.get("password")
            else:
                QMessageBox.warning(self, "保存失败", f"用户 {username} 缺少密码信息")
                return

            users_to_save.append(user_data)

        if not users_to_save:
            QMessageBox.warning(self, "保存失败", "没有可保存的用户")
            return

        if super_admin_count < 1:
            QMessageBox.warning(self, "保存失败", "至少需要保留一个超级管理者账号。")
            return

        if self._config.save_users(users_to_save):
            QMessageBox.information(self, "成功", "用户配置已保存")
            self.accept()
        else:
            QMessageBox.warning(self, "失败", "用户配置保存失败")
