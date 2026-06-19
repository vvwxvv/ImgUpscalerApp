"""
src/uiitems/dialogs.py
----------------------
Reusable, frameless, centered dialogs for Bauhaus‑style apps.
"""

import os
import sys
import subprocess
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class AlertDialog(QDialog):
    """Generic alert with an OK button. Use for warnings, errors, info."""

    def __init__(self, parent, message, is_error=False):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 2px solid #000000;
                border-radius: 14px;
            }
            QLabel {
                color: #000000;
                background: transparent;
                border: none;
                font-size: 14px;
            }
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                border: none;
                border-radius: 10px;
                padding: 11px 36px;
                margin-top: 6px;
            }
            QPushButton:hover { background-color: #222; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignCenter)

        msg_lbl = QLabel(message, self)
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        ok_btn = QPushButton("OK", self)
        ok_btn.setFixedWidth(120)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(360)
        self.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pr = self.parent().geometry()
            self.move(
                pr.x() + (pr.width()  - self.width())  // 2,
                pr.y() + (pr.height() - self.height()) // 2,
            )


class DoneDialog(QDialog):
    """Completion dialog with statistics and an 'Open Folder' button."""

    def __init__(self, parent, saved, skipped, errors, total_mb, out_dir):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 2px solid #000000;
                border-radius: 16px;
            }
            QLabel {
                color: #000000;
                background: transparent;
                border: none;
                font-size: 14px;
            }
            QLabel#title {
                font-size: 17px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#meta {
                color: #444444;
                font-size: 13px;
                font-family: 'Courier New', monospace;
            }
            QPushButton {
                background-color: #000000;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 1px;
                border: none;
                border-radius: 10px;
                padding: 12px 40px;
                margin-top: 8px;
            }
            QPushButton:hover { background-color: #222222; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel("UPSCALE COMPLETE", self)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        divider = QLabel(self)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #000; border: none; margin: 6px 0;")
        root.addWidget(divider)

        stats = QLabel(
            f"  Saved    →  {saved}  ({total_mb:.1f} MB)\n"
            f"  Skipped  →  {skipped}\n"
            f"  Errors   →  {errors}\n\n"
            f"  Output   →  {out_dir}",
            self
        )
        stats.setObjectName("meta")
        stats.setAlignment(Qt.AlignLeft)
        stats.setWordWrap(True)
        root.addWidget(stats)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)

        open_btn = QPushButton("Open Folder", self)
        open_btn.setFixedWidth(120)
        open_btn.clicked.connect(lambda: self._open_folder(out_dir))
        btn_row.addWidget(open_btn)

        ok_btn = QPushButton("OK", self)
        ok_btn.setFixedWidth(120)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        root.addLayout(btn_row)
        self.setFixedWidth(420)
        self.adjustSize()

    def _open_folder(self, path):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            pr = self.parent().geometry()
            self.move(
                pr.x() + (pr.width()  - self.width())  // 2,
                pr.y() + (pr.height() - self.height()) // 2,
            )