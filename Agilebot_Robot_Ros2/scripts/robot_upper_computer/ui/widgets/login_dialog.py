from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QComboBox,
)
from core.config_manager import ConfigManager


@dataclass
class LoginResult:
    username: str
    role: str


class LoginDialog(QDialog):
    """登录对话框：使用者/管理者/超级管理者"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户登录")
        self.setModal(True)
        self.resize(420, 250)
        self._result = None

        self._config_manager = ConfigManager()
        # 启动即迁移旧版明文密码配置
        self._config_manager.migrate_users_to_password_hash()
        self._users = self._config_manager.load_users()

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("协作机械臂上位机登录")
        title.setProperty("pageTitle", True)
        layout.addWidget(title)

        user_row = QHBoxLayout()
        user_row.addWidget(QLabel("账号"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入账号")
        user_row.addWidget(self.username_edit)
        layout.addLayout(user_row)

        pwd_row = QHBoxLayout()
        pwd_row.addWidget(QLabel("密码"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("请输入密码")
        pwd_row.addWidget(self.password_edit)
        layout.addLayout(pwd_row)

        role_row = QHBoxLayout()
        role_row.addWidget(QLabel("角色"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["使用者", "管理者", "超级管理者"])
        role_row.addWidget(self.role_combo)
        layout.addLayout(role_row)

        hint = QLabel("用户来源: configs/users.yaml")
        hint.setProperty("subtleText", True)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        login_btn = QPushButton("登录")
        login_btn.setObjectName("primaryBtn")
        login_btn.clicked.connect(self._try_login)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(login_btn)
        layout.addLayout(btn_row)

        self.username_edit.returnPressed.connect(self._try_login)
        self.password_edit.returnPressed.connect(self._try_login)

    def _find_user(self, username: str):
        for user in self._users:
            if str(user.get("username", "")).strip() == username:
                return user
        return None

    def _try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        selected_role = self.role_combo.currentText()

        if not username or not password:
            QMessageBox.warning(self, "登录失败", "请输入账号和密码。")
            return

        user = self._find_user(username)
        if not user:
            QMessageBox.warning(self, "登录失败", "账号不存在。")
            return

        if not self._config_manager.verify_password(password, user):
            QMessageBox.warning(self, "登录失败", "密码错误。")
            return

        if str(user.get("role", "")) != selected_role:
            QMessageBox.warning(self, "登录失败", "所选角色与账号不匹配。")
            return

        self._result = LoginResult(username=username, role=selected_role)
        self.accept()

    def get_result(self):
        return self._result
