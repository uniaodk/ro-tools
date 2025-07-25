from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon
from PySide6.QtCore import QEvent

from config.app import APP_NAME, APP_ICON
from events.game_event import GAME_EVENT
from gui.app_controller import APP_CONTROLLER
from gui.central_widget import CentralWidget
from gui.widget.tray_menu import TrayMenu


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._config_layout()

    def closeEvent(self, event: QEvent) -> None:
        GAME_EVENT.stop()
        event.accept()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self.hide()
        super().changeEvent(event)

    def _config_layout(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(1000)
        self.setWindowIcon(QIcon(APP_ICON))
        self.setCentralWidget(CentralWidget(self))
        APP_CONTROLLER.tray_menu = TrayMenu(self)
