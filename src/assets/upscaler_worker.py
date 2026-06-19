"""
src/worker.py  –  TinyImgApp background upscale worker
=======================================================
UpscaleWorker runs Real-ESRGAN in a QThread.

New in this version
-------------------
  • tile_progress(current, total) signal – emitted for every "Tile X/Y" event
  • current_file(filename)         signal – emitted before each image starts
  • _TileLogHandler  – logging.Handler that parses tile lines from log records
  • _StreamWrapper   – wraps sys.stdout **and** sys.stderr to catch tqdm /
                        print-based tile messages
  • _TileCapture     – context manager that installs/uninstalls both above

Public re-exports let main_app.py import all ML symbols from one place.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Callable, List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from src.assets.real_esrGAN_upscaler import (
    IMAGE_EXTENSIONS,
    MODEL_REGISTRY,
    RealESRGANUpscaler,
    UpscalerConfig,
)

_log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
FORMAT_EXT: dict[str, str] = {
    "png":  ".png",
    "jpg":  ".jpg",
    "jpeg": ".jpg",
    "webp": ".webp",
}

_QUALITY_MIN:          int = 10
_QUALITY_MAX:          int = 95
_QUALITY_BISECT_ITERS: int = 12

# Matches:  "Tile 1/12",  "tile 4 / 12",  "TILE  3/8"  (any spacing/case)
_TILE_RE = re.compile(r'\bTile\s+(\d+)\s*/\s*(\d+)\b', re.IGNORECASE)


# ── Tile-progress interceptors ────────────────────────────────────────────────

class _TileLogHandler(logging.Handler):
    """Logging handler that fires *callback(current, total)* on tile records.

    Installed on the **root** logger so it catches every logger that emits
    a record containing the pattern ``Tile X/Y``, regardless of its name
    (basicsr, real_esrgan, src.assets.*, …).
    """

    def __init__(self, callback: Callable[[int, int], None]) -> None:
        super().__init__(logging.DEBUG)
        self._cb = callback

    def emit(self, record: logging.LogRecord) -> None:   # noqa: A003
        try:
            m = _TILE_RE.search(record.getMessage())
            if m:
                self._cb(int(m.group(1)), int(m.group(2)))
        except Exception:  # never let a handler crash the worker
            pass

class _StreamWrapper:
    """Transparent wrapper for sys.stdout / sys.stderr."""

    def __init__(
        self,
        original,
        callback: Callable[[int, int], None],
    ) -> None:
        self._orig = original
        self._cb   = callback

    def write(self, text: str) -> int:
        if self._orig:  # Ensure the original stream is not None
            result = self._orig.write(text)
            m = _TILE_RE.search(text)
            if m:
                self._cb(int(m.group(1)), int(m.group(2)))
            return result
        return 0  # If the original stream is None, do nothing

    def flush(self) -> None:
        if self._orig:  # Ensure the original stream is not None
            self._orig.flush()

    def __getattr__(self, name: str):
        # Transparently forward isatty(), fileno(), encoding, etc.
        return getattr(self._orig, name) if self._orig else None

class _TileCapture:
    """Context manager that installs all tile-progress interceptors.

    On ``__enter__``:
      1. Adds a _TileLogHandler to the root logger.
      2. Wraps sys.stdout with _StreamWrapper.
      3. Wraps sys.stderr with _StreamWrapper (tqdm writes to stderr).

    On ``__exit__``: cleanly removes all three.
    """

    def __init__(self, callback: Callable[[int, int], None]) -> None:
        self._cb       = callback
        self._handler  = _TileLogHandler(callback)
        self._orig_out = None
        self._orig_err = None

    def __enter__(self) -> "_TileCapture":
        logging.root.addHandler(self._handler)
        self._orig_out = sys.stdout
        self._orig_err = sys.stderr
        sys.stdout = _StreamWrapper(sys.stdout, self._cb)
        sys.stderr = _StreamWrapper(sys.stderr, self._cb)
        return self

    def __exit__(self, *_) -> None:
        logging.root.removeHandler(self._handler)
        # Restore originals even if the wrapped object itself raised
        if self._orig_out is not None:
            sys.stdout = self._orig_out
        if self._orig_err is not None:
            sys.stderr = self._orig_err


# ── Worker ────────────────────────────────────────────────────────────────────

class UpscaleWorker(QThread):
    """QThread that upscales a list of images via Real-ESRGAN.

    Signals
    -------
    progress(done, total)          file-level counter  (one per completed file)
    tile_progress(current, total)  tile-level counter  (many per file)
    current_file(filename)         name of the file now starting
    row_done(message)              one-line human-readable status per file
    finished(results)              list[dict] when the full job ends
    error(message)                 fatal setup error (output dir creation, …)

    Result dict keys:  status | filename | size_kb | error
    Status values:     "saved" | "skipped" | "error"
    """

    progress:      pyqtSignal = pyqtSignal(int, int)
    tile_progress: pyqtSignal = pyqtSignal(int, int)
    current_file:  pyqtSignal = pyqtSignal(str)
    row_done:      pyqtSignal = pyqtSignal(str)
    finished:      pyqtSignal = pyqtSignal(list)
    error:         pyqtSignal = pyqtSignal(str)

    def __init__(
        self,
        upscaler:       RealESRGANUpscaler,
        input_paths:    List[str],
        output_dir:     str,
        output_format:  str,
        target_size_kb: Optional[int],
    ) -> None:
        super().__init__()
        self.upscaler       = upscaler
        self.input_paths    = input_paths
        self.output_dir     = Path(output_dir)
        self.output_format  = output_format.lower()
        self.target_size_kb = target_size_kb
        self._total         = len(input_paths)
        self.results: list[dict] = []

    # ── QThread entry point ────────────────────────────────────────────────────
    def run(self) -> None:
        _log.info("Worker started: %d file(s) → %s", self._total, self.output_dir)

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"Cannot create output folder:\n{self.output_dir}\n{exc}"
            _log.error(msg)
            self.error.emit(msg)
            return

        self.progress.emit(0, self._total)

        # Install tile interceptors for the full duration of the job
        with _TileCapture(self._emit_tile):
            for idx, src in enumerate(self.input_paths, start=1):
                src_path = Path(src)
                self.current_file.emit(src_path.name)
                try:
                    result = self._process_one(src_path)
                    self.results.append(result)
                    self.progress.emit(idx, self._total)
                    self.row_done.emit(self._format_row(src_path.name, result))
                except Exception as exc:
                    _log.exception("Unexpected error processing %s", src)
                    self.results.append(
                        {
                            "status":   "error",
                            "filename": src_path.name,
                            "size_kb":  0,
                            "error":    str(exc),
                        }
                    )
                    self.progress.emit(idx, self._total)
                    self.row_done.emit(f"[FAIL]  {src_path.name}  →  {exc}")

        self.finished.emit(self.results)

    def _emit_tile(self, current: int, total: int) -> None:
        """Thread-safe bridge: called from interceptor → emits Qt signal."""
        self.tile_progress.emit(current, total)

    # ── Per-file processing ────────────────────────────────────────────────────
    def _process_one(self, src_path: Path) -> dict:
        """Upscale one image and write it to the output directory."""
        from PIL import Image  # deferred – torch must already be loaded

        ext      = FORMAT_EXT.get(self.output_format, ".jpg")
        out_name = src_path.stem + "_upscaled" + ext
        out_path = self.output_dir / out_name

        if out_path.exists():
            _log.debug("Skipping already-upscaled file: %s", out_name)
            return {
                "status":   "skipped",
                "filename": out_name,
                "size_kb":  out_path.stat().st_size / 1024,
                "error":    "",
            }

        img   = self.upscaler.upscale_pil(Image.open(src_path).convert("RGB"))
        lossy = self.output_format in ("jpg", "jpeg", "webp")

        if self.target_size_kb and lossy:
            quality = self._find_quality(img, out_path, self.target_size_kb)
            if self.output_format in ("jpg", "jpeg"):
                img.save(str(out_path), quality=quality, optimize=True)
            else:
                img.save(str(out_path), quality=quality, method=6)
        elif self.output_format == "png":
            img.save(str(out_path), optimize=True)
        elif self.output_format in ("jpg", "jpeg"):
            img.save(str(out_path), quality=95, optimize=True)
        elif self.output_format == "webp":
            img.save(str(out_path), quality=95, method=6)
        else:
            raise ValueError(f"Unsupported output format: {self.output_format!r}")

        if not out_path.exists():
            raise RuntimeError(f"Output file missing after save: {out_path}")

        size_kb = out_path.stat().st_size / 1024
        _log.debug("Saved %s  (%.0f KB)", out_name, size_kb)
        return {
            "status":   "saved",
            "filename": out_name,
            "size_kb":  size_kb,
            "error":    "",
        }

    def _find_quality(self, img, out_path: Path, target_kb: int) -> int:
        """Binary-search for the highest JPEG/WebP quality that fits *target_kb*."""
        low, high, best = _QUALITY_MIN, _QUALITY_MAX, _QUALITY_MAX
        ext = out_path.suffix.lower()

        for _ in range(_QUALITY_BISECT_ITERS):
            q   = (low + high) // 2
            tmp = out_path.with_suffix(f".tmp_{q}{ext}")
            if ext in (".jpg", ".jpeg"):
                img.save(str(tmp), quality=q, optimize=True)
            else:
                img.save(str(tmp), quality=q, method=6)
            size_kb = tmp.stat().st_size / 1024
            tmp.unlink(missing_ok=True)

            if size_kb <= target_kb:
                best = q
                low  = q + 1
            else:
                high = q - 1

            if high - low <= 2:
                break

        return best

    # ── Static helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _format_row(filename: str, result: dict) -> str:
        status = result["status"]
        if status == "saved":
            return f"[ OK ]  {filename}  →  {result['size_kb']:.0f} KB"
        if status == "skipped":
            return f"[SKIP]  {filename}  (already exists)"
        return f"[FAIL]  {filename}  →  {result['error']}"


# ── Public re-exports ─────────────────────────────────────────────────────────
__all__ = [
    "UpscaleWorker",
    "RealESRGANUpscaler",
    "UpscalerConfig",
    "MODEL_REGISTRY",
    "IMAGE_EXTENSIONS",
]
