"""
main_app.py  –  TinyImgApp | Real-ESRGAN Upscaler
==================================================
Single UI entry point.  All bootstrap utilities, path helpers, resize
logic, styles, and window code live here.

Only two external project splits are imported:
  src/worker.py                   – UpscaleWorker + ML re-exports
  src/uiitems/progress_panel.py   – pinned bottom panel widget
  src/uiitems/close_button.py     – frameless close button
  src/uiitems/dialogs.py          – AlertDialog / DoneDialog

Window features
  • Frameless with manual 8-direction edge resize (GRIP_PX border)
  • QScrollArea body  +  ProgressPanel pinned at the bottom
  • Max height = 90 % of screen; initial size ≈ 80 %
"""

from __future__ import annotations

# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  Windows DLL pre-registration                                               │
# │  MUST execute before any import that can transitively load torch.           │
# │  Fixes OSError WinError 1114 – c10.dll / CUDA DLL init failure.            │
# └─────────────────────────────────────────────────────────────────────────────┘
import os
import sys


def _register_torch_dll_dirs() -> None:
    """Add torch/lib and CUDA bin dirs to the Windows DLL search path."""
    if sys.platform != "win32":
        return
    candidates: list[str] = []
    try:
        import site
        import sysconfig
        for sp in site.getsitepackages():
            candidates.append(os.path.join(sp, "torch", "lib"))
        purelib = sysconfig.get_path("purelib")
        if purelib:
            candidates.append(os.path.join(purelib, "torch", "lib"))
    except Exception:
        pass
    for path in candidates:
        if os.path.isdir(path):
            try:
                os.add_dll_directory(path)
            except Exception:
                pass
    for env_var in ("CUDA_PATH", "CUDA_HOME"):
        cuda_root = os.environ.get(env_var, "")
        if cuda_root:
            for sub in ("bin", "libnvvp"):
                dll_path = os.path.join(cuda_root, sub)
                if os.path.isdir(dll_path):
                    try:
                        os.add_dll_directory(dll_path)
                    except Exception:
                        pass
            break


def _apply_torchvision_shim() -> None:
    """Shim back the removed torchvision.transforms.functional_tensor module."""
    key = "torchvision.transforms.functional_tensor"
    if key in sys.modules:
        return
    try:
        from types import ModuleType
        import torchvision.transforms.functional as _F
        mock = ModuleType(key)
        mock.rgb_to_grayscale = _F.rgb_to_grayscale  # type: ignore[attr-defined]
        sys.modules[key] = mock
    except Exception:
        pass


# Run both side-effects immediately – before any other import.
_register_torch_dll_dirs()
_apply_torchvision_shim()

# ── Standard library ──────────────────────────────────────────────────────────
import logging
from pathlib import Path
from typing import List, Optional

# ── Qt ────────────────────────────────────────────────────────────────────────
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# ── Project imports ───────────────────────────────────────────────────────────
from src.uiitems.close_button import CloseButton
from src.uiitems.dialogs import AlertDialog, DoneDialog
from src.uiitems.progress_panel import ProgressPanel
from src.assets.upscaler_worker import (
    IMAGE_EXTENSIONS,
    MODEL_REGISTRY,
    RealESRGANUpscaler,
    UpscalerConfig,
    UpscaleWorker,
)


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap helpers (logging + paths)
# ─────────────────────────────────────────────────────────────────────────────

def _setup_logging() -> Path:
    """Configure root logger (file + console).  Returns the log file path."""
    log_path: Path = (
        Path(sys.executable).parent / "upscaler.log"
        if getattr(sys, "frozen", False)
        else Path("upscaler.log")
    )
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


def _get_resource_path(relative_path: str) -> str:
    """Resolve *relative_path* against the bundle root (PyInstaller or CWD)."""
    try:
        base = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


def _get_models_dir() -> str:
    """Return the absolute models directory, creating it when absent."""
    base: Path = (
        Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(".")
    )
    d = base / "models"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _get_cover_path() -> Optional[str]:
    """Return the path to ``static/cover.png``, or ``None`` if not found."""
    path = _get_resource_path(os.path.join("static", "cover.png"))
    if os.path.isfile(path):
        return path
    logging.getLogger(__name__).warning("Cover image not found: %s", path)
    return None


# Initialise logging once at module level.
_LOG_PATH = _setup_logging()
_log      = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# UI option data
# ─────────────────────────────────────────────────────────────────────────────
_FORMAT_OPTIONS: tuple[str, ...] = ("JPEG", "PNG", "WEBP")
_SIZE_OPTIONS:   tuple[str, ...] = ("No limit", "500 KB", "700 KB", "1 MB", "2 MB")


def _parse_target_kb(text: str) -> Optional[int]:
    """Convert a size-option label to kilobytes, or ``None`` for *No limit*."""
    if text == "No limit":
        return None
    value, unit = text.split()
    return int(value) * (1024 if "MB" in unit else 1)


# ─────────────────────────────────────────────────────────────────────────────
# Edge-resize direction bitmasks  (module-level constants)
# ─────────────────────────────────────────────────────────────────────────────
_RNONE  = 0
_RLEFT  = 1
_RRIGHT = 2
_RTOP   = 4
_RBOT   = 8

_CURSOR_MAP: dict[int, Qt.CursorShape] = {
    _RLEFT:             Qt.SizeHorCursor,
    _RRIGHT:            Qt.SizeHorCursor,
    _RTOP:              Qt.SizeVerCursor,
    _RBOT:              Qt.SizeVerCursor,
    _RTOP | _RLEFT:     Qt.SizeFDiagCursor,
    _RBOT | _RRIGHT:    Qt.SizeFDiagCursor,
    _RTOP | _RRIGHT:    Qt.SizeBDiagCursor,
    _RBOT | _RLEFT:     Qt.SizeBDiagCursor,
}

GRIP_PX: int = 8   # invisible resize border width in pixels


# ─────────────────────────────────────────────────────────────────────────────
# Stylesheet & inline styles
# ─────────────────────────────────────────────────────────────────────────────
STYLESHEET = """
QWidget#App {
    background-color: #ffffff;
    border: 2px solid #000000;
    border-radius: 20px;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QScrollBar:vertical {
    background: #f0f0f0;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #aaaaaa;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover { background: #555555; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical     { height: 0; }
QLabel {
    color: #000000;
    background-color: transparent;
    border: none;
    font-size: 14px;
}
QPushButton {
    background-color: #ffffff;
    color: #000000;
    font-weight: 600;
    font-size: 14px;
    border: 2px solid #000000;
    border-radius: 10px;
    padding: 11px 16px;
    margin: 5px 10px;
}
QPushButton:hover    { background-color: #f0f0f0; }
QPushButton:disabled {
    background-color: #f5f5f5;
    color: #aaaaaa;
    border-color: #cccccc;
}
QComboBox {
    background-color: #ffffff;
    color: #000000;
    font-size: 14px;
    border: 2px solid #000000;
    border-radius: 10px;
    padding: 9px 12px;
    margin: 4px 10px;
}
QComboBox:disabled {
    background-color: #f5f5f5;
    color: #bbbbbb;
    border-color: #dddddd;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 2px solid #000000;
    selection-background-color: #000000;
    selection-color: #ffffff;
}
QRadioButton {
    background-color: #ffffff;
    color: #000000;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 14px;
    margin: 4px 5px;
    border-radius: 10px;
    border: 2px solid #000000;
}
QRadioButton:hover    { background-color: #f5f5f5; }
QRadioButton:disabled {
    background-color: #f5f5f5;
    color: #aaaaaa;
    border-color: #dddddd;
}
QRadioButton::indicator {
    background-color: #ffffff;
    border: 2px solid #000000;
    width: 16px;
    height: 16px;
    border-radius: 3px;
}
QRadioButton::indicator:checked {
    background-color: #000000;
    border-color: #000000;
}
QProgressBar {
    background-color: #f5f5f5;
    border: 2px solid #000000;
    border-radius: 8px;
    margin: 4px 10px;
    text-align: center;
    color: #000000;
    font-size: 13px;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #000000;
    border-radius: 5px;
}
QWidget#BottomPanel {
    background-color: #ffffff;
    border-top: 2px solid #eeeeee;
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
}
"""

_SECTION_STYLE: str = (
    "color: #888888; background: transparent; border: none;"
    " font-size: 11px; letter-spacing: 1.5px; margin: 8px 14px 2px 14px;"
)
_PATH_STYLE: str = (
    "color: #000000; background: transparent; border: none;"
    " font-size: 13px; font-weight: 500; margin: 0px 14px 4px 14px;"
)
_MODEL_DESC_STYLE: str = (
    "color: #888888; font-size: 11px; margin: 0px 14px 4px 14px;"
)
_FALLBACK_LOGO_STYLE: str = (
    "font-size: 22px; font-weight: bold; color: #000000;"
    " background: transparent; border: none; padding: 18px; margin: 0;"
)


# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────
class UpscalerApp(QWidget):
    """Frameless main window for TinyImgApp.

    Responsibilities:
      • Render complete interface: cover image, controls, pinned panel.
      • Handle window dragging and 8-direction edge resizing directly.
      • Create and supervise UpscaleWorker; relay signals to ProgressPanel.
      • No ML or file-IO code lives here.
    """

    MIN_W: int = 420
    MIN_H: int = 480

    def __init__(self) -> None:
        super().__init__()

        # Application state
        self._input_paths: List[str]                    = []
        self._output_dir:  Optional[str]                = None
        self._upscaler:    Optional[RealESRGANUpscaler] = None
        self._worker:      Optional[UpscaleWorker]      = None

        # Window drag state
        self._drag_pos: Optional[QPoint] = None

        # Edge-resize state
        self._resize_dir:    int              = _RNONE
        self._resize_origin: Optional[QPoint] = None
        self._resize_rect:   Optional[QRect]  = None

        self._init_ui()
        _log.info("UpscalerApp ready  (log → %s)", _LOG_PATH)

    # =========================================================================
    # UI construction
    # =========================================================================

    def _init_ui(self) -> None:
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setObjectName("App")
        self.setStyleSheet(STYLESHEET)
        self.setMouseTracking(True)

        screen  = QApplication.primaryScreen().availableGeometry()
        max_h   = int(screen.height() * 0.90)
        start_w = min(540, screen.width() - 40)
        start_h = min(int(screen.height() * 0.80), max_h)

        self.setMinimumSize(self.MIN_W, self.MIN_H)
        self.setMaximumSize(screen.width(), max_h)
        self.resize(start_w, start_h)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(self._build_title_bar())
        root.addWidget(self._build_scroll_body(), stretch=1)
        root.addWidget(self._build_bottom_panel())
        self.setLayout(root)

    # ── Title bar ─────────────────────────────────────────────────────────────
    def _build_title_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 4, 4, 0)
        close_btn = CloseButton(self)
        close_btn.clicked.connect(self.close)
        bar.addStretch()
        bar.addWidget(close_btn)
        return bar

    # ── Scrollable body ───────────────────────────────────────────────────────
    def _build_scroll_body(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setMouseTracking(True)

        body = QWidget()
        body.setObjectName("ScrollContent")
        body.setMouseTracking(True)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 8)
        bl.setSpacing(2)

        # Cover / logo
        self._logo_label = self._build_logo()
        bl.addWidget(self._logo_label)

        # INPUT SOURCE
        bl.addWidget(self._mk_section("INPUT SOURCE"))
        radio_row = QHBoxLayout()
        radio_row.setContentsMargins(10, 0, 10, 0)
        self.rb_single = QRadioButton("Single image")
        self.rb_folder = QRadioButton("Image folder")
        self.rb_single.setChecked(True)
        radio_row.addWidget(self.rb_single)
        radio_row.addWidget(self.rb_folder)
        radio_row.addStretch()
        bl.addLayout(radio_row)
        self.input_btn = self._mk_btn("Browse", self._browse_input)
        bl.addWidget(self.input_btn)
        self.input_label = self._mk_path_lbl("Nothing selected")
        bl.addWidget(self.input_label)

        # OUTPUT FOLDER
        bl.addWidget(self._mk_section("OUTPUT FOLDER"))
        self.out_btn = self._mk_btn("Select Output Folder", self._browse_output)
        bl.addWidget(self.out_btn)
        self.output_label = self._mk_path_lbl("Same as input (default)")
        bl.addWidget(self.output_label)

        # MODEL
        bl.addWidget(self._mk_section("MODEL"))
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self._refresh_model_desc)
        bl.addWidget(self.model_combo)
        self.model_desc = QLabel()
        self.model_desc.setStyleSheet(_MODEL_DESC_STYLE)
        self.model_desc.setWordWrap(True)
        bl.addWidget(self.model_desc)
        self._populate_models()

        # OUTPUT FORMAT
        bl.addWidget(self._mk_section("OUTPUT FORMAT"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(_FORMAT_OPTIONS)
        bl.addWidget(self.format_combo)

        # TARGET FILE SIZE
        bl.addWidget(self._mk_section("TARGET FILE SIZE"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(_SIZE_OPTIONS)
        bl.addWidget(self.size_combo)

        bl.addStretch(1)
        scroll.setWidget(body)
        return scroll

    # ── Pinned bottom panel ───────────────────────────────────────────────────
    def _build_bottom_panel(self) -> ProgressPanel:
        self._panel = ProgressPanel(self)
        self._panel.start_clicked.connect(self._start_upscale)
        return self._panel

    # ── Cover / logo image ────────────────────────────────────────────────────
    def _build_logo(self) -> QLabel:
        lbl = QLabel(self)
        lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lbl.setStyleSheet(
            "background: transparent; border: none; margin: 0; padding: 0;"
        )
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        cover = _get_cover_path()
        self._raw_pixmap = QPixmap(cover) if cover else QPixmap()

        if not self._raw_pixmap.isNull():
            lbl.setPixmap(
                self._raw_pixmap.scaledToWidth(self.width(), Qt.SmoothTransformation)
            )
        else:
            lbl.setText("TinyImgApp")
            lbl.setStyleSheet(_FALLBACK_LOGO_STYLE)

        return lbl

    # =========================================================================
    # Widget micro-factories
    # =========================================================================

    def _mk_btn(self, text: str, slot, style: Optional[str] = None) -> QPushButton:
        btn = QPushButton(text, self)
        btn.clicked.connect(slot)
        if style:
            btn.setStyleSheet(style)
        return btn

    def _mk_section(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setStyleSheet(_SECTION_STYLE)
        return lbl

    def _mk_path_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setStyleSheet(_PATH_STYLE)
        lbl.setWordWrap(True)
        return lbl

    # =========================================================================
    # Qt event overrides
    # =========================================================================

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not getattr(self, "_raw_pixmap", QPixmap()).isNull():
            self._logo_label.setPixmap(
                self._raw_pixmap.scaledToWidth(self.width(), Qt.SmoothTransformation)
            )

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        d = self._hit_test(event.pos())
        if d != _RNONE:
            self._resize_dir    = d
            self._resize_origin = event.globalPos()
            self._resize_rect   = self.geometry()
            self._drag_pos      = None
        else:
            self._resize_dir = _RNONE
            self._drag_pos   = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton:
            if self._resize_dir != _RNONE and self._resize_origin is not None:
                self._do_resize(event.globalPos())
            elif self._drag_pos is not None:
                self.move(event.globalPos() - self._drag_pos)
        else:
            self._apply_resize_cursor(self._hit_test(event.pos()))

    def mouseReleaseEvent(self, event) -> None:
        self._resize_dir    = _RNONE
        self._resize_origin = None
        self._resize_rect   = None
        self._drag_pos      = None
        self.unsetCursor()

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            _log.info("Terminating running worker on close.")
            self._worker.terminate()
            self._worker.wait()
        event.accept()

    # =========================================================================
    # Edge-resize helpers
    # =========================================================================

    def _hit_test(self, pos: QPoint) -> int:
        """Return a bitmask for the window edges under *pos* (widget-local)."""
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        d = _RNONE
        if x <= GRIP_PX:       d |= _RLEFT
        if x >= w - GRIP_PX:   d |= _RRIGHT
        if y <= GRIP_PX:       d |= _RTOP
        if y >= h - GRIP_PX:   d |= _RBOT
        return d

    def _apply_resize_cursor(self, direction: int) -> None:
        if direction == _RNONE:
            self.unsetCursor()
        else:
            self.setCursor(_CURSOR_MAP.get(direction, Qt.ArrowCursor))

    def _do_resize(self, global_pos: QPoint) -> None:
        delta      = global_pos - self._resize_origin
        r          = QRect(self._resize_rect)
        mn_w, mn_h = self.minimumWidth(), self.minimumHeight()
        mx_w, mx_h = self.maximumWidth(), self.maximumHeight()
        d          = self._resize_dir

        if d & _RRIGHT:
            r.setRight(max(r.left() + mn_w, min(r.left() + mx_w, r.right() + delta.x())))
        if d & _RLEFT:
            r.setLeft(min(r.right() - mn_w, r.left() + delta.x()))
        if d & _RBOT:
            r.setBottom(max(r.top() + mn_h, min(r.top() + mx_h, r.bottom() + delta.y())))
        if d & _RTOP:
            r.setTop(min(r.bottom() - mn_h, r.top() + delta.y()))

        self.setGeometry(r)

    # =========================================================================
    # Model combo
    # =========================================================================

    def _populate_models(self) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for name, cfg in sorted(
            MODEL_REGISTRY.items(), key=lambda kv: (kv[1].scale, kv[0])
        ):
            self.model_combo.addItem(f"{name}  (×{cfg.scale})", name)
        self.model_combo.blockSignals(False)
        self._refresh_model_desc()

    def _refresh_model_desc(self) -> None:
        idx  = self.model_combo.currentIndex()
        name = self.model_combo.itemData(idx) if idx >= 0 else None
        cfg  = MODEL_REGISTRY.get(name) if name else None
        self.model_desc.setText(cfg.description if cfg else "")

    # =========================================================================
    # File / folder browsers
    # =========================================================================

    def _browse_input(self) -> None:
        if self.rb_single.isChecked():
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif)",
            )
            if path:
                self._input_paths = [path]
                self.input_label.setText(f"▸  {Path(path).name}")
        else:
            folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
            if folder:
                paths = [
                    str(p) for p in Path(folder).iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                ]
                self._input_paths = paths
                n = len(paths)
                self.input_label.setText(
                    f"▸  {folder}  ({n} image{'s' if n != 1 else ''})"
                )

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self._output_dir = folder
            self.output_label.setText(f"▸  {folder}")

    # =========================================================================
    # Upscale job
    # =========================================================================

    def _validate(self) -> Optional[str]:
        """Return a human-readable error string, or ``None`` when inputs are valid."""
        if not self._input_paths:
            return "Please select an image or folder."
        if self.model_combo.currentIndex() < 0:
            return "Please select a model."
        if self._worker and self._worker.isRunning():
            return "An upscale job is already in progress."
        return None

    def _start_upscale(self) -> None:
        err = self._validate()
        if err:
            AlertDialog(self, err).exec_()
            return

        model_name = self.model_combo.itemData(self.model_combo.currentIndex())
        fmt        = self.format_combo.currentText().lower()
        target_kb  = _parse_target_kb(self.size_combo.currentText())

        if self._output_dir:
            out_dir = self._output_dir
        else:
            base    = Path(self._input_paths[0])
            out_dir = str((base.parent if base.is_file() else base) / "upscaled")

        # Re-initialise only when the selected model changes.
        if self._upscaler is None or self._upscaler.config.model_name != model_name:
            try:
                self._upscaler = RealESRGANUpscaler(
                    UpscalerConfig(
                        model_name=model_name,
                        models_dir=_get_models_dir(),
                        tile=512,
                        outscale=None,
                        auto_download=True,
                    )
                )
            except Exception as exc:
                _log.exception("Failed to initialise upscaler")
                AlertDialog(
                    self, f"Failed to initialise upscaler:\n{exc}", is_error=True
                ).exec_()
                return

        self._worker = UpscaleWorker(
            self._upscaler, self._input_paths, out_dir, fmt, target_kb
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.row_done.connect(self._panel.append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_worker_error)

        self._set_busy(True)
        self._panel.reset_progress(len(self._input_paths))
        self._panel.set_log("[INFO] Starting upscale…")
        self._worker.start()
        _log.info(
            "Job started: model=%s  fmt=%s  target_kb=%s  files=%d",
            model_name, fmt, target_kb, len(self._input_paths),
        )

    # =========================================================================
    # Worker signal callbacks
    # =========================================================================

    def _on_progress(self, done: int, total: int) -> None:
        self._panel.set_progress(done, total)

    def _on_finished(self, results: list) -> None:
        saved    = sum(1 for r in results if r["status"] == "saved")
        skipped  = sum(1 for r in results if r["status"] == "skipped")
        errors   = sum(1 for r in results if r["status"] == "error")
        total_mb = sum(r["size_kb"] for r in results if r["status"] == "saved") / 1024

        self._set_busy(False)
        self._panel.set_log(
            f"[DONE] saved={saved} ({total_mb:.1f} MB)  "
            f"skipped={skipped}  errors={errors}"
        )
        _log.info(
            "Job finished: saved=%d  skipped=%d  errors=%d", saved, skipped, errors
        )
        DoneDialog(
            self, saved, skipped, errors, total_mb,
            self._output_dir or "default",
        ).exec_()

    def _on_worker_error(self, message: str) -> None:
        _log.error("Worker error: %s", message)
        self._set_busy(False)
        self._panel.set_log(f"[ERROR] {message}")
        AlertDialog(self, f"Upscaling failed:\n{message}", is_error=True).exec_()

    # =========================================================================
    # UI state helpers
    # =========================================================================

    def _set_busy(self, busy: bool) -> None:
        """Toggle all interactive controls as a single unit."""
        for widget in (
            self.rb_single,
            self.rb_folder,
            self.input_btn,
            self.out_btn,
            self.model_combo,
            self.format_combo,
            self.size_combo,
        ):
            widget.setEnabled(not busy)
        self._panel.set_busy(busy)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    app = QApplication(sys.argv)
    window = UpscalerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
