"""
main_app.py  –  TinyImgApp  |  Real‑ESRGAN Upscaler
Elegant, Bauhaus‑style UI matching the image downloader app.
Uses reusable dialogs from src/uiitems/dialogs.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox,
    QProgressBar, QRadioButton,
)

# ── DPI awareness ──
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from src.assets.real_esrGAN_upscaler import (
    RealESRGANUpscaler,
    UpscalerConfig,
    MODEL_REGISTRY,
    IMAGE_EXTENSIONS,
)
from src.uiitems.close_button import CloseButton
from src.uiitems.dialogs import AlertDialog, DoneDialog


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ── Styles (identical to downloader) ────────────────────────────────────────

STYLESHEET = """
QWidget#App {
    background-color: #ffffff;
    border: 2px solid #000000;
    border-radius: 20px;
}

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
QPushButton:hover {
    background-color: #f0f0f0;
}
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
QRadioButton:hover {
    background-color: #f5f5f5;
}
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
"""

SECTION_LABEL_STYLE = (
    "color: #888888;"
    "background: transparent;"
    "border: none;"
    "font-size: 11px;"
    "letter-spacing: 1.5px;"
    "margin: 6px 14px 1px 14px;"
)

PATH_LABEL_STYLE = (
    "color: #000000;"
    "background: transparent;"
    "border: none;"
    "font-size: 13px;"
    "font-weight: 500;"
    "margin: 0px 14px 4px 14px;"
)

LOG_STYLE = (
    "background-color: #f9f9f9;"
    "border: 2px solid #000000;"
    "border-radius: 10px;"
    "padding: 8px 12px;"
    "margin: 4px 10px;"
    "color: #000000;"
    "font-size: 12px;"
    "font-family: 'Courier New', monospace;"
)

START_BTN_STYLE = """
QPushButton {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    background-color: #000000;
    border: none;
    border-radius: 14px;
    padding: 18px;
    margin: 10px;
    letter-spacing: 1px;
}
QPushButton:hover {
    background-color: #222222;
}
QPushButton:disabled {
    background-color: #cccccc;
    color: #888888;
}
"""


# ── Worker (unchanged from previous, but we'll keep it here) ──────────────

class UpscaleWorker(QThread):
    progress = pyqtSignal(int, int)
    row_done = pyqtSignal(str)
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, upscaler, input_paths, output_dir, output_format, target_size_kb):
        super().__init__()
        self.upscaler = upscaler
        self.input_paths = input_paths
        self.output_dir = Path(output_dir)
        self.output_format = output_format.lower()
        self.target_size_kb = target_size_kb
        self._total = len(input_paths)
        self._done = 0
        self.results = []

    def run(self):
        self.progress.emit(0, self._total)
        for src in self.input_paths:
            try:
                result = self._process_one(Path(src))
                self.results.append(result)
                self._done += 1
                self.progress.emit(self._done, self._total)
                if result["status"] == "saved":
                    self.row_done.emit(f"[ OK ]  {Path(src).name}  →  {result['size_kb']:.0f} KB")
                elif result["status"] == "skipped":
                    self.row_done.emit(f"[SKIP]  {Path(src).name}  (exists)")
                else:
                    self.row_done.emit(f"[FAIL]  {Path(src).name}  → {result['error']}")
            except Exception as e:
                self.results.append({
                    "status": "error",
                    "filename": Path(src).name,
                    "size_kb": 0,
                    "error": str(e),
                })
                self._done += 1
                self.progress.emit(self._done, self._total)
                self.row_done.emit(f"[FAIL]  {Path(src).name}  → {str(e)}")
        self.finished.emit(self.results)

    def _process_one(self, src_path: Path) -> dict:
        from PIL import Image
        ext_map = {"png": ".png", "jpg": ".jpg", "jpeg": ".jpg", "webp": ".webp"}
        ext = ext_map.get(self.output_format, ".jpg")
        out_name = src_path.stem + "_upscaled" + ext
        out_path = self.output_dir / out_name
        if out_path.exists():
            return {"status": "skipped", "filename": out_name, "size_kb": out_path.stat().st_size / 1024, "error": ""}
        img = self.upscaler.upscale_pil(Image.open(src_path).convert("RGB"))
        if self.target_size_kb and self.output_format in ("jpg", "jpeg", "webp"):
            quality = self._find_quality(img, out_path, self.target_size_kb)
            if self.output_format in ("jpg", "jpeg"):
                img.save(out_path, quality=quality, optimize=True)
            else:
                img.save(out_path, quality=quality, method=6)
            final_size = out_path.stat().st_size / 1024
            return {"status": "saved", "filename": out_name, "size_kb": final_size, "error": ""}
        else:
            if self.output_format == "png":
                img.save(out_path, optimize=True)
            elif self.output_format in ("jpg", "jpeg"):
                img.save(out_path, quality=95, optimize=True)
            elif self.output_format == "webp":
                img.save(out_path, quality=95, method=6)
            else:
                raise ValueError(f"Unsupported format: {self.output_format}")
            size_kb = out_path.stat().st_size / 1024
            return {"status": "saved", "filename": out_name, "size_kb": size_kb, "error": ""}

    def _find_quality(self, img, out_path, target_kb: int) -> int:
        low, high = 10, 95
        best_q = 95
        ext = out_path.suffix.lower()
        for _ in range(12):
            q = (low + high) // 2
            temp_path = out_path.with_suffix(f".tmp_{q}{ext}")
            if ext in (".jpg", ".jpeg"):
                img.save(temp_path, quality=q, optimize=True)
            else:
                img.save(temp_path, quality=q, method=6)
            size_kb = temp_path.stat().st_size / 1024
            temp_path.unlink()
            if size_kb <= target_kb:
                best_q = q
                low = q + 1
            else:
                high = q - 1
            if high - low <= 2:
                break
        return best_q


# ── Main Window ──────────────────────────────────────────────────────────────

class UpscalerApp(QWidget):
    APP_WIDTH  = 540
    APP_HEIGHT = 900          # same as downloader

    def __init__(self):
        super().__init__()
        self._input_paths: List[str] = []
        self._output_dir: Optional[str] = None
        self._upscaler: Optional[RealESRGANUpscaler] = None
        self._worker: Optional[UpscaleWorker] = None
        self.oldPos = self.pos()
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName("App")
        self.setStyleSheet(STYLESHEET)
        self.resize(self.APP_WIDTH, self.APP_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(2)

        # Title bar
        layout.addLayout(self._build_title_bar())

        # Logo (cover) – full width, auto height
        layout.addWidget(self._build_logo())

        # ── INPUT SOURCE ──────────────────────────────────────────────
        layout.addWidget(self._section("INPUT SOURCE"))
        radio_row = QHBoxLayout()
        radio_row.setContentsMargins(10, 0, 10, 0)
        radio_row.setSpacing(0)
        self.rb_single = QRadioButton("Single image")
        self.rb_folder = QRadioButton("Image folder")
        self.rb_single.setChecked(True)
        radio_row.addWidget(self.rb_single)
        radio_row.addWidget(self.rb_folder)
        radio_row.addStretch()
        layout.addLayout(radio_row)

        self.input_button = self._btn("Browse", self._browse_input)
        layout.addWidget(self.input_button)
        self.input_label = self._path_lbl("Nothing selected")
        layout.addWidget(self.input_label)

        # ── OUTPUT FOLDER ──────────────────────────────────────────────
        layout.addWidget(self._section("OUTPUT FOLDER"))
        self.out_button = self._btn("Select Output Folder", self._browse_output)
        layout.addWidget(self.out_button)
        self.output_label = self._path_lbl("Same as input (default)")
        layout.addWidget(self.output_label)

        # ── MODEL ──────────────────────────────────────────────────────
        layout.addWidget(self._section("MODEL"))
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self._refresh_model_desc)
        layout.addWidget(self.model_combo)
        self.model_desc = QLabel("")
        self.model_desc.setStyleSheet("color: #888888; font-size: 11px; margin: 0px 14px 4px 14px;")
        layout.addWidget(self.model_desc)
        self._populate_models()

        # ── OUTPUT FORMAT ──────────────────────────────────────────────
        layout.addWidget(self._section("OUTPUT FORMAT"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "WEBP"])
        self.format_combo.setCurrentIndex(0)
        layout.addWidget(self.format_combo)

        # ── TARGET FILE SIZE ──────────────────────────────────────────
        layout.addWidget(self._section("TARGET FILE SIZE"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["No limit", "500 KB", "700 KB", "1 MB", "2 MB"])
        layout.addWidget(self.size_combo)

        # ── Progress ──────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat(" %v / %m")
        self.progress.setFixedHeight(28)
        layout.addWidget(self.progress)

        # ── Log ────────────────────────────────────────────────────────
        self.log_label = QLabel("Ready.")
        self.log_label.setStyleSheet(LOG_STYLE)
        self.log_label.setWordWrap(True)
        self.log_label.setFixedHeight(66)
        self.log_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.log_label)

        # ── Start button ──────────────────────────────────────────────
        self.start_btn = self._btn("Start Upscaling", self._start_upscale, START_BTN_STYLE)
        layout.addWidget(self.start_btn)

        self.setLayout(layout)

    # ── factories ──────────────────────────────────────────────────────────────

    def _btn(self, text, slot, style=None):
        b = QPushButton(text, self)
        b.clicked.connect(slot)
        if style:
            b.setStyleSheet(style)
        return b

    def _section(self, text):
        lbl = QLabel(text, self)
        lbl.setStyleSheet(SECTION_LABEL_STYLE)
        return lbl

    def _path_lbl(self, text):
        lbl = QLabel(text, self)
        lbl.setStyleSheet(PATH_LABEL_STYLE)
        lbl.setWordWrap(True)
        return lbl

    def _build_title_bar(self):
        bar = QHBoxLayout()
        close_btn = CloseButton(self)
        close_btn.clicked.connect(self.close)
        bar.addWidget(close_btn, alignment=Qt.AlignRight)
        return bar

    def _build_logo(self):
        lbl = QLabel(self)
        cover_path = get_resource_path(os.path.join("static", "cover.png"))
        pixmap = QPixmap(cover_path)
        if not pixmap.isNull():
            # Scale to full width, preserve aspect ratio – height auto
            pixmap = pixmap.scaledToWidth(self.APP_WIDTH, Qt.SmoothTransformation)
        lbl.setPixmap(pixmap)
        lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lbl.setStyleSheet("background: transparent; border: none; margin: 0; padding: 0;")
        lbl.setObjectName("Logo")
        return lbl

    # ── UI logic ─────────────────────────────────────────────────────

    def _populate_models(self):
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        models = sorted(MODEL_REGISTRY.items(), key=lambda x: (x[1].scale, x[0]))
        for name, cfg in models:
            self.model_combo.addItem(f"{name}  (×{cfg.scale})", name)
        self.model_combo.blockSignals(False)
        self._refresh_model_desc()

    def _refresh_model_desc(self):
        idx = self.model_combo.currentIndex()
        if idx >= 0:
            name = self.model_combo.itemData(idx)
            cfg = MODEL_REGISTRY.get(name)
            self.model_desc.setText(cfg.description if cfg else "")
        else:
            self.model_desc.setText("")

    def _browse_input(self):
        if self.rb_single.isChecked():
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Image", "",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif)"
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
                self.input_label.setText(f"▸  {folder}  ({n} image{'s' if n != 1 else ''})")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self._output_dir = folder
            self.output_label.setText(f"▸  {folder}")

    # ── Start upscaling ─────────────────────────────────────────────

    def _start_upscale(self):
        if not self._input_paths:
            AlertDialog(self, "Please select an image or folder.").exec_()
            return

        idx = self.model_combo.currentIndex()
        if idx < 0:
            AlertDialog(self, "Please select a model.").exec_()
            return
        model_name = self.model_combo.itemData(idx)

        fmt = self.format_combo.currentText().lower()
        target_text = self.size_combo.currentText()
        if target_text == "No limit":
            target_kb = None
        else:
            val, unit = target_text.split()
            target_kb = int(val) * (1024 if unit == "MB" else 1)

        if self._output_dir:
            out_dir = self._output_dir
        else:
            base = Path(self._input_paths[0])
            out_dir = str((base.parent if base.is_file() else base) / "upscaled")

        cfg = UpscalerConfig(
            model_name=model_name,
            tile=512,
            outscale=None,
            auto_download=True,
        )

        if (self._upscaler is None or self._upscaler.config.model_name != model_name):
            try:
                self._upscaler = RealESRGANUpscaler(cfg)
            except Exception as e:
                AlertDialog(self, f"Failed to initialise upscaler:\n{e}", is_error=True).exec_()
                return

        self._worker = UpscaleWorker(
            self._upscaler, self._input_paths, out_dir, fmt, target_kb
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.row_done.connect(self._on_row)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_label.setText("[INFO] Starting upscale…")
        self._worker.start()

    # ── Worker callbacks ────────────────────────────────────────────

    def _on_progress(self, done, total):
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(done)

    def _on_row(self, msg):
        lines = [l for l in self.log_label.text().split("\n") if l] + [msg]
        self.log_label.setText("\n".join(lines[-3:]))

    def _on_finished(self, results):
        saved = sum(1 for r in results if r["status"] == "saved")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        errors = sum(1 for r in results if r["status"] == "error")
        total_mb = sum(r["size_kb"] for r in results if r["status"] == "saved") / 1024
        self.start_btn.setEnabled(True)
        self.log_label.setText(f"[DONE] saved={saved} ({total_mb:.1f} MB) skipped={skipped} errors={errors}")
        DoneDialog(self, saved, skipped, errors, total_mb, self._output_dir or "default").exec_()

    def _on_error(self, msg):
        self.start_btn.setEnabled(True)
        self.log_label.setText(f"[ERROR] {msg}")
        AlertDialog(self, f"Upscaling failed:\n{msg}", is_error=True).exec_()

    # ── Window drag ──────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()
        event.accept()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpscalerApp()
    window.show()
    sys.exit(app.exec_())