"""
src/uiitems/progress_panel.py  –  TinyImgApp pinned bottom panel
=================================================================
Self-contained widget that owns:
  • QProgressBar  – file progress counter
  • QLabel log    – rolling last-3-lines status
  • "Start Upscaling" QPushButton

The parent window connects to ``start_clicked`` and drives the panel
through its public API (set_progress, append_log, set_log, set_busy).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ── Styles (self-contained; do not depend on main_app styles) ──────────────────
_LOG_STYLE: str = (
    "background-color: #f9f9f9; border: 2px solid #000000;"
    " border-radius: 10px; padding: 8px 12px; margin: 4px 10px;"
    " color: #000000; font-size: 12px; font-family: 'Courier New', monospace;"
)

_START_BTN_STYLE: str = """
QPushButton {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    background-color: #000000;
    border: none;
    border-radius: 14px;
    padding: 16px;
    margin: 8px 10px 10px 10px;
    letter-spacing: 1px;
}
QPushButton:hover    { background-color: #222222; }
QPushButton:disabled { background-color: #cccccc; color: #888888; }
"""

_MAX_LOG_LINES: int = 3


class ProgressPanel(QWidget):
    """Pinned bottom panel: progress bar + rolling log + start button.

    Signals:
        start_clicked – relayed from the "Start Upscaling" button.
    """

    start_clicked: pyqtSignal = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BottomPanel")  # matched by QWidget#BottomPanel QSS
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._build()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(2)

        # Progress bar
        self.bar = QProgressBar()
        self.bar.setValue(0)
        self.bar.setFormat(" %v / %m")
        self.bar.setFixedHeight(28)
        layout.addWidget(self.bar)

        # Rolling log label
        self.log = QLabel("Ready.")
        self.log.setStyleSheet(_LOG_STYLE)
        self.log.setWordWrap(True)
        self.log.setMinimumHeight(52)
        self.log.setMaximumHeight(68)
        self.log.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.log)

        # Start button
        self.start_btn = QPushButton("Start Upscaling")
        self.start_btn.setStyleSheet(_START_BTN_STYLE)
        self.start_btn.clicked.connect(self.start_clicked)
        layout.addWidget(self.start_btn)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_progress(self, done: int, total: int) -> None:
        """Update the progress bar."""
        self.bar.setMaximum(max(total, 1))
        self.bar.setValue(done)

    def reset_progress(self, total: int) -> None:
        """Reset the progress bar to 0 with a new maximum."""
        self.bar.setMaximum(max(total, 1))
        self.bar.setValue(0)

    def set_log(self, text: str) -> None:
        """Replace the log area with *text*."""
        self.log.setText(text)

    def append_log(self, message: str) -> None:
        """Append *message*; keep at most ``_MAX_LOG_LINES`` lines visible."""
        lines = [ln for ln in self.log.text().split("\n") if ln] + [message]
        self.log.setText("\n".join(lines[-_MAX_LOG_LINES:]))

    def set_busy(self, busy: bool) -> None:
        """Enable or disable the start button."""
        self.start_btn.setEnabled(not busy)