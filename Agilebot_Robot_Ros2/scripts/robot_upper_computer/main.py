import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDialog
from ui.main_window import MainWindow
from ui.widgets.login_dialog import LoginDialog


def main():
    app = QApplication(sys.argv)

    # 加载 QSS 样式表
    style_path = Path(__file__).parent / "ui" / "resources" / "styles" / "default.qss"
    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        app.setStyle("Fusion")

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    login_result = login.get_result()
    if login_result is None:
        sys.exit(0)

    window = MainWindow(user_role=login_result.role, username=login_result.username)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
