"""
modules/chat/view.py

AI Chat module (mocked provider; full chat UI built in its own phase). This is a real, functional placeholder widget for the app-shell
phase -- it renders and is navigable right now. The full feature set is
implemented in this modules dedicated roadmap phase, backed by the
tables/structures already prepared in storage/database.py.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from modules.base_module import BaseModule


class ChatModule(BaseModule):
    MODULE_KEY = "chat"
    MODULE_LABEL = "Chat"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        label = QLabel("Chat module placeholder - full build in its own phase")
        label.setObjectName("MutedLabel")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
