"""
modules/calculator/view.py

Full calculator module:
  - Live expression display + result, basic and scientific button grids
    (toggle between the two), a collapsible history panel backed by
    calc_history, full keyboard input (typing digits/operators/Enter/
    Backspace/Escape all work without touching the mouse), and a copy
    button that puts the current result on the system clipboard.

All math goes through engine.evaluate(), which never calls bare eval() --
see engine.py for why.

Redesign notes: button grid now distinguishes digits / operators / equals
by objectName (CalcDigit / CalcOperator / CalcEquals -- styled in
ui/theme.py) instead of every button looking identical, which is the
"rich/dashboard, more visual detail" direction. Mode toggle and copy
controls got icons instead of being plain text buttons.
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QFont

from modules.base_module import BaseModule
from modules.calculator.engine import evaluate, CalculatorError
from modules.calculator import storage as calc_storage
from ui.icon_loader import get_icon, icon_size
from ui.theme import PALETTE

ICON_PX = 16

# Each row is (label, object_name) so the grid builder can apply the right
# visual treatment per button without string-matching labels at paint time.
OPERATOR_LABELS = {"C", "⌫", "%", "÷", "×", "−", "+", "^", "(", ")"}
EQUALS_LABEL = "="

BASIC_BUTTONS = [
    ["C", "⌫", "%", "÷"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "−"],
    ["1", "2", "3", "+"],
    ["±", "0", ".", "="],
]

SCIENTIFIC_EXTRA_BUTTONS = [
    ["sin(", "cos(", "tan(", "^"],
    ["log(", "ln(", "sqrt(", "("],
    ["pi", "e", "!", ")"],
]


class CalculatorModule(BaseModule):
    MODULE_KEY = "calculator"
    MODULE_LABEL = "Calculator"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scientific = False
        self._last_result = ""
        self._build_ui()
        self._refresh_history()
        self.setFocusPolicy(Qt.StrongFocus)

    # -- UI construction --------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self.expression_label = QLabel("")
        self.expression_label.setObjectName("MutedLabel")
        self.expression_label.setAlignment(Qt.AlignRight)
        root.addWidget(self.expression_label)

        self.display = QLineEdit()
        self.display.setObjectName("CalcDisplay")
        self.display.setAlignment(Qt.AlignRight)
        self.display.setFont(QFont("Segoe UI", 22))
        self.display.textEdited.connect(self._on_display_edited)
        self.display.returnPressed.connect(self._equals)
        root.addWidget(self.display)

        controls = QHBoxLayout()
        self.mode_btn = QPushButton("  Scientific mode")
        self.mode_btn.setObjectName("SecondaryButton")
        self.mode_btn.setIcon(get_icon("calculator", PALETTE["accent_fg"], ICON_PX))
        self.mode_btn.setIconSize(icon_size(ICON_PX))
        self.mode_btn.clicked.connect(self._toggle_mode)
        controls.addWidget(self.mode_btn)
        controls.addStretch(1)

        copy_btn = QPushButton()
        copy_btn.setObjectName("IconButton")
        copy_btn.setIcon(get_icon("clipboard", PALETTE["text_muted"], ICON_PX))
        copy_btn.setIconSize(icon_size(ICON_PX))
        copy_btn.setFixedSize(36, 36)
        copy_btn.setToolTip("Copy result")
        copy_btn.clicked.connect(self._copy_result)
        controls.addWidget(copy_btn)
        root.addLayout(controls)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        root.addWidget(self.grid_container)
        self._build_button_grid()

        history_header = QHBoxLayout()
        history_label = QLabel("History")
        history_label.setObjectName("MutedLabel")
        history_header.addWidget(history_label)
        history_header.addStretch(1)
        clear_btn = QPushButton()
        clear_btn.setObjectName("IconButton")
        clear_btn.setProperty("danger", "true")
        clear_btn.setIcon(get_icon("trash", PALETTE["danger_fg"], 14))
        clear_btn.setIconSize(icon_size(14))
        clear_btn.setFixedSize(30, 30)
        clear_btn.setToolTip("Clear history")
        clear_btn.clicked.connect(self._clear_history)
        history_header.addWidget(clear_btn)
        root.addLayout(history_header)

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._reuse_history_item)
        self.history_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        root.addWidget(self.history_list, 1)

    def _build_button_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        rows = list(BASIC_BUTTONS)
        if self._scientific:
            rows = SCIENTIFIC_EXTRA_BUTTONS + rows

        for row_idx, row in enumerate(rows):
            for col_idx, label in enumerate(row):
                btn = QPushButton(label)
                btn.setFixedHeight(44)
                if label == EQUALS_LABEL:
                    btn.setObjectName("CalcEquals")
                elif label in OPERATOR_LABELS:
                    btn.setObjectName("CalcOperator")
                else:
                    btn.setObjectName("CalcDigit")
                btn.clicked.connect(lambda checked, l=label: self._on_button(l))
                self.grid_layout.addWidget(btn, row_idx, col_idx)

    def _toggle_mode(self):
        self._scientific = not self._scientific
        self.mode_btn.setText("  Basic mode" if self._scientific else "  Scientific mode")
        self._build_button_grid()

    # -- input handling -----------------------------------------------------

    def _on_button(self, label: str):
        if label == "C":
            self.display.clear()
            self.expression_label.setText("")
        elif label == "⌫":
            self.display.setText(self.display.text()[:-1])
        elif label == "=":
            self._equals()
        elif label == "±":
            text = self.display.text()
            if text.startswith("-"):
                self.display.setText(text[1:])
            elif text:
                self.display.setText("-" + text)
        elif label == "!":
            self.display.insert("factorial(")
        else:
            insert_map = {"−": "-"}
            self.display.insert(insert_map.get(label, label))
        self.display.setFocus()

    def _on_display_edited(self, text: str):
        self.expression_label.setText(text)

    def _equals(self):
        expression = self.display.text()
        if not expression.strip():
            return
        try:
            result = evaluate(expression)
        except CalculatorError as exc:
            self.expression_label.setText(str(exc))
            return

        result_str = self._format_result(result)
        self.expression_label.setText(expression + " =")
        self.display.setText(result_str)
        self._last_result = result_str
        calc_storage.add_entry(expression, result_str)
        self._refresh_history()

    @staticmethod
    def _format_result(value: float) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(round(value, 10))

    def _copy_result(self):
        text = self.display.text() or self._last_result
        if text:
            QGuiApplication.clipboard().setText(text)

    # -- history -----------------------------------------------------

    def _refresh_history(self):
        self.history_list.clear()
        for row in calc_storage.list_entries():
            item = QListWidgetItem(f"{row['expression']} = {row['result']}")
            self.history_list.addItem(item)

    def _clear_history(self):
        calc_storage.clear_history()
        self._refresh_history()

    def _reuse_history_item(self, item: QListWidgetItem):
        expression = item.text().split(" = ")[0]
        self.display.setText(expression)
        self.expression_label.setText(expression)
        self.display.setFocus()

    # -- keyboard input -----------------------------------------------------

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._equals()
        elif key == Qt.Key_Escape:
            self.display.clear()
            self.expression_label.setText("")
        elif key == Qt.Key_Backspace:
            self.display.setText(self.display.text()[:-1])
        elif text and (text.isdigit() or text in "+-*/().%^"):
            self.display.insert(text)
            self.expression_label.setText(self.display.text())
        else:
            super().keyPressEvent(event)

    def on_shown(self):
        self.setFocus()
        self._refresh_history()
