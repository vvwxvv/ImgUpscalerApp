"""
src/assets/real_esrGAN_upscaler.py  –  TinyImgApp
==================================================
Production wrapper around Real-ESRGAN (xinntao/Real-ESRGAN).

Required packages: torch, basicsr, realesrgan, Pillow, numpy

Public API
----------
    IMAGE_EXTENSIONS   frozenset[str]
    ModelConfig        frozen dataclass  – per-model metadata
    MODEL_REGISTRY     dict[str, ModelConfig]
    UpscalerConfig     dataclass         – constructor arguments
    RealESRGANUpscaler                   – main upscaler class

Supported architectures
-----------------------
    "rrdbnet"   RRDBNet (basicsr)             – all x4plus / x2plus models
    "srvgg"     SRVGGNetCompact (realesrgan)  – realesr-general-x4v3
"""

from __future__ import annotations

import logging
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from PIL import Image

_log = logging.getLogger(__name__)

# ── Supported input file extensions ───────────────────────────────────────────
IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif",
})

# ── Architecture type alias ────────────────────────────────────────────────────
ArchType = Literal["rrdbnet", "srvgg"]


# ── Torchvision compatibility shim ────────────────────────────────────────────
def _apply_torchvision_shim() -> None:
    """Restore the removed torchvision.transforms.functional_tensor submodule.

    Newer torchvision merged functional_tensor into functional; basicsr still
    imports the old name.  Re-applied inside worker threads so the shim is
    guaranteed to be in place before the first model load regardless of which
    thread triggers it.
    """
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


# ── Model metadata ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ModelConfig:
    """Immutable descriptor for one Real-ESRGAN model preset.

    Attributes:
        scale       Native upscale factor of the model.
        filename    Weight file name (stored under models_dir).
        url         GitHub releases download URL for the .pth file.
        description Human-readable summary shown in the UI.
        arch        Neural network architecture: "rrdbnet" or "srvgg".
        num_block   RRDBNet: number of Residual-in-Residual Dense Blocks.
        num_feat    Both archs: intermediate feature channels.
        num_grow_ch RRDBNet: growth channel count inside each dense block.
        num_conv    SRVGGNetCompact: total number of conv layers.
    """

    scale:       int
    filename:    str
    url:         str
    description: str
    arch:        ArchType = "rrdbnet"
    num_block:   int      = 23
    num_feat:    int      = 64
    num_grow_ch: int      = 32
    num_conv:    int      = 32   # used only when arch == "srvgg"


MODEL_REGISTRY: dict[str, ModelConfig] = {
    # ── General-purpose models ─────────────────────────────────────────────────
    "RealESRGAN_x4plus": ModelConfig(
        scale=4,
        arch="rrdbnet",
        filename="RealESRGAN_x4plus.pth",
        url=(
            "https://github.com/xinntao/Real-ESRGAN/"
            "releases/download/v0.1.0/RealESRGAN_x4plus.pth"
        ),
        description=(
            "General-purpose 4× upscaler trained on diverse real-world images. "
            "Best for photos, textures, and mixed content."
        ),
        num_block=23,
    ),
    "RealESRGAN_x2plus": ModelConfig(
        scale=2,
        arch="rrdbnet",
        filename="RealESRGAN_x2plus.pth",
        url=(
            "https://github.com/xinntao/Real-ESRGAN/"
            "releases/download/v0.2.1/RealESRGAN_x2plus.pth"
        ),
        description=(
            "General-purpose 2× upscaler. "
            "Faster and lighter; ideal when moderate enlargement is enough."
        ),
        num_block=23,
    ),
    # ── Anime / illustration model ─────────────────────────────────────────────
    "RealESRGAN_x4plus_anime_6B": ModelConfig(
        scale=4,
        arch="rrdbnet",
        filename="RealESRGAN_x4plus_anime_6B.pth",
        url=(
            "https://github.com/xinntao/Real-ESRGAN/"
            "releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
        ),
        description=(
            "Anime / illustration 4× upscaler (6 RRDB blocks). "
            "Optimised for flat colours, clean lines, and cartoon art. "
            "Much smaller model than x4plus."
        ),
        num_block=6,
    ),
    # ── No-GAN baseline ────────────────────────────────────────────────────────
    "RealESRNet_x4plus": ModelConfig(
        scale=4,
        arch="rrdbnet",
        filename="RealESRNet_x4plus.pth",
        url=(
            "https://github.com/xinntao/Real-ESRGAN/"
            "releases/download/v0.1.1/RealESRNet_x4plus.pth"
        ),
        description=(
            "ESRNET (no GAN discriminator) 4× upscaler. "
            "Produces smoother, artifact-free output. "
            "Good baseline for already-clean source images."
        ),
        num_block=23,
    ),
    # ── Tiny fast model (SRVGGNetCompact) ─────────────────────────────────────
    # Added in Real-ESRGAN v0.2.5 – https://github.com/xinntao/Real-ESRGAN
    # Uses the lightweight SRVGGNetCompact architecture instead of RRDBNet,
    # resulting in significantly faster inference and lower VRAM usage.
    "realesr-general-x4v3": ModelConfig(
        scale=4,
        arch="srvgg",          # ← only once; duplicate removed (was the bug)
        filename="realesr-general-x4v3.pth",
        url=(
            "https://github.com/xinntao/Real-ESRGAN/"
            "releases/download/v0.2.5.0/realesr-general-x4v3.pth"
        ),
        description=(
            "Tiny 4× model for general scenes (SRVGGNetCompact). "
            "Fastest inference with lowest VRAM footprint. "
            "Supports denoising-strength balancing to avoid over-smoothing."
        ),
        num_feat=64,
        num_conv=32,
    ),
}


# ── Runtime configuration ─────────────────────────────────────────────────────
@dataclass
class UpscalerConfig:
    """Runtime options forwarded to RealESRGANUpscaler.

    Attributes:
        model_name      Key in MODEL_REGISTRY.
        models_dir      Directory where .pth weight files are stored / cached.
        tile            Tile size for tiled inference (0 = no tiling).
                        Smaller values reduce VRAM at the cost of speed.
        tile_pad        Overlap (px) between tiles to suppress seam artefacts.
        pre_pad         Extra border padding added before inference.
        outscale        Final output scale factor.
                        None → use the model's native scale.
        half_precision  Use FP16 on CUDA for ~2× speedup (Ampere / Turing).
                        Disable if you observe NaN or black pixels.
        auto_download   Fetch missing weights from GitHub automatically.
        gpu_id          CUDA device index.  None → let PyTorch choose.
    """

    model_name:     str
    models_dir:     str
    tile:           int             = 512
    tile_pad:       int             = 10
    pre_pad:        int             = 0
    outscale:       Optional[float] = None
    half_precision: bool            = False
    auto_download:  bool            = True
    gpu_id:         Optional[int]   = None


# ── Main upscaler class ───────────────────────────────────────────────────────
class RealESRGANUpscaler:
    """Thin wrapper around RealESRGANer with lazy loading and auto-download.

    The underlying RealESRGANer is constructed on the **first** call to
    :meth:`upscale_pil` so creating the instance itself is cheap and does
    not import torch.

    Example::

        cfg = UpscalerConfig(model_name="RealESRGAN_x4plus", models_dir="./models")
        upscaler = RealESRGANUpscaler(cfg)
        out: Image.Image = upscaler.upscale_pil(img)
    """

    def __init__(self, config: UpscalerConfig) -> None:
        if config.model_name not in MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model {config.model_name!r}. "
                f"Available: {sorted(MODEL_REGISTRY)}"
            )
        self.config     = config
        self._upsampler = None   # lazily initialised on first upscale call

    # ── Public API ────────────────────────────────────────────────────────────
    def upscale_pil(self, img: Image.Image) -> Image.Image:
        """Upscale a PIL RGB image and return the result as a PIL RGB image.

        Args:
            img: Source image in RGB mode.  Call ``Image.open(...).convert("RGB")``
                 before passing here.

        Returns:
            Upscaled image in RGB mode.

        Raises:
            RuntimeError:       CUDA OOM or corrupt model weights.
            FileNotFoundError:  Weights missing and auto_download=False.
        """
        import numpy as np  # deferred – avoids numpy at module import time

        if self._upsampler is None:
            self._build_upsampler()

        # RealESRGANer expects BGR (OpenCV convention)
        img_bgr = np.array(img)[:, :, ::-1]

        try:
            output_bgr, _ = self._upsampler.enhance(
                img_bgr,
                outscale=self.config.outscale,
            )
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                _log.error(
                    "CUDA OOM – reduce tile size (current: %d px). "
                    "Try tile=256 or tile=128.",
                    self.config.tile,
                )
            raise

        return Image.fromarray(output_bgr[:, :, ::-1])  # BGR → RGB

    # ── Internal ──────────────────────────────────────────────────────────────
    def _build_upsampler(self) -> None:
        """Construct and cache the RealESRGANer; called once on first inference."""
        _apply_torchvision_shim()   # must also run inside the worker thread

        from realesrgan import RealESRGANer  # noqa: PLC0415

        model_cfg  = MODEL_REGISTRY[self.config.model_name]
        model_path = Path(self.config.models_dir) / model_cfg.filename

        if not model_path.exists():
            if not self.config.auto_download:
                raise FileNotFoundError(
                    f"Model weights not found: {model_path}\n"
                    "Set auto_download=True or place the .pth file manually."
                )
            self._download_weights(model_cfg.url, model_path)

        backbone = self._build_backbone(model_cfg)

        self._upsampler = RealESRGANer(
            scale=model_cfg.scale,
            model_path=str(model_path),
            model=backbone,
            tile=self.config.tile,
            tile_pad=self.config.tile_pad,
            pre_pad=self.config.pre_pad,
            half=self.config.half_precision,
            gpu_id=self.config.gpu_id,
        )
        _log.info(
            "Loaded model %s  (arch=%s  scale=×%d  tile=%d  fp16=%s)",
            self.config.model_name,
            model_cfg.arch,
            model_cfg.scale,
            self.config.tile,
            self.config.half_precision,
        )

    @staticmethod
    def _build_backbone(cfg: ModelConfig):
        """Instantiate the correct neural network backbone for *cfg*."""
        if cfg.arch == "rrdbnet":
            from basicsr.archs.rrdbnet_arch import RRDBNet  # noqa: PLC0415
            return RRDBNet(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=cfg.num_feat,
                num_block=cfg.num_block,
                num_grow_ch=cfg.num_grow_ch,
                scale=cfg.scale,
            )
        elif cfg.arch == "srvgg":
            from realesrgan.archs.srvgg_arch import SRVGGNetCompact  # noqa: PLC0415
            return SRVGGNetCompact(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=cfg.num_feat,
                num_conv=cfg.num_conv,
                upscale=cfg.scale,
                act_type="prelu",
            )
        else:
            raise ValueError(
                f"Unknown architecture {cfg.arch!r}. "
                "Expected 'rrdbnet' or 'srvgg'."
            )

    @staticmethod
    def _download_weights(url: str, dest: Path) -> None:
        """Download *url* → *dest* via a .part temp file.

        The partial file is removed on any error so a subsequent retry always
        starts clean.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        _log.info("Downloading  %s  →  %s", url, dest.name)

        def _progress(block: int, block_size: int, total: int) -> None:
            if total > 0:
                pct = min(block * block_size * 100 / total, 100.0)
                _log.debug("  … %.0f %%", pct)

        try:
            urllib.request.urlretrieve(url, str(tmp), reporthook=_progress)
            tmp.rename(dest)
            _log.info(
                "Download complete: %s  (%.1f MB)",
                dest.name,
                dest.stat().st_size / 1_048_576,
            )
        except Exception:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise