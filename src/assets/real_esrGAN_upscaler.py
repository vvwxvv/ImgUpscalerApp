"""
src/assets/real_esrGAN_upscaler.py
------------------------------------
Production Real-ESRGAN upscaler module.

Exports:
    IMAGE_EXTENSIONS  – supported input file suffixes
    MODEL_REGISTRY    – all known model configurations keyed by name
    SCALE_TO_MODELS   – scale (2 or 4) → list of compatible model names
    UpscalerConfig    – runtime settings dataclass
    RealESRGANUpscaler – lazy-loading, cacheable upscaler class
"""

from __future__ import annotations

# ── torchvision compatibility shim ───────────────────────────────────────────
# MUST execute at module-load time, before any basicsr import.
import sys

def _patch_torchvision() -> None:
    key = "torchvision.transforms.functional_tensor"
    if key not in sys.modules:
        from types import ModuleType
        import torchvision.transforms.functional as _F
        _mock = ModuleType(key)
        _mock.rgb_to_grayscale = _F.rgb_to_grayscale
        sys.modules[key] = _mock

_patch_torchvision()
# ─────────────────────────────────────────────────────────────────────────────

import logging
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image

from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

_log = logging.getLogger(__name__)

# ── Supported input extensions ────────────────────────────────────────────────
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
)


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  Architecture enum                                                          │
# └─────────────────────────────────────────────────────────────────────────────┘
class Arch(str, Enum):
    RRDBNET = "RRDBNet"
    SRVGG   = "SRVGGNetCompact"


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  Per-model immutable configuration                                          │
# └─────────────────────────────────────────────────────────────────────────────┘
@dataclass(frozen=True)
class ModelConfig:
    name:         str
    arch:         Arch
    scale:        int
    description:  str
    download_url: str
    # ── RRDBNet params ────────────────────────────────────────────────────────
    num_block:    int = 23
    num_feat:     int = 64
    num_grow_ch:  int = 32
    num_in_ch:    int = 3
    num_out_ch:   int = 3
    # ── SRVGGNetCompact param (ignored for RRDBNet) ───────────────────────────
    num_conv:     int = 16


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  Model registry                                                             │
# │  Source: https://github.com/xinntao/Real-ESRGAN/releases                   │
# └─────────────────────────────────────────────────────────────────────────────┘
MODEL_REGISTRY: dict[str, ModelConfig] = {
    # ── ×4 RRDBNet ────────────────────────────────────────────────────────────
    "RealESRGAN_x4plus": ModelConfig(
        name="RealESRGAN_x4plus",
        arch=Arch.RRDBNET, scale=4, num_block=23,
        description="General images ×4  (23-block RRDBNet)  —  v0.1.0",
        download_url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/"
            "download/v0.1.0/RealESRGAN_x4plus.pth"
        ),
    ),
    # ── ×2 RRDBNet ────────────────────────────────────────────────────────────
    "RealESRGAN_x2plus": ModelConfig(
        name="RealESRGAN_x2plus",
        arch=Arch.RRDBNET, scale=2, num_block=23,
        description="General images ×2  (23-block RRDBNet)  —  v0.2.1",
        download_url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/"
            "download/v0.2.1/RealESRGAN_x2plus.pth"
        ),
    ),
    # ── ×4 Anime lightweight RRDBNet ─────────────────────────────────────────
    "RealESRGAN_x4plus_anime_6B": ModelConfig(
        name="RealESRGAN_x4plus_anime_6B",
        arch=Arch.RRDBNET, scale=4, num_block=6,
        description="Anime images ×4  (6-block RRDBNet, small)  —  v0.2.2.4",
        download_url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/"
            "download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
        ),
    ),
    # ── ×4 SRVGGNetCompact — anime video ─────────────────────────────────────
    "realesr-animevideov3": ModelConfig(
        name="realesr-animevideov3",
        arch=Arch.SRVGG, scale=4, num_conv=16,
        description="Anime video ×4 v3  (fast, fewer artifacts)  —  v0.2.5.0",
        download_url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/"
            "download/v0.2.5.0/realesr-animevideov3.pth"
        ),
    ),
    # ── ×4 SRVGGNetCompact — general v3 ──────────────────────────────────────
    "realesr-general-x4v3": ModelConfig(
        name="realesr-general-x4v3",
        arch=Arch.SRVGG, scale=4, num_conv=32,
        description="General scenes ×4 v3  (tiny, robust)  —  v0.3.0",
        download_url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/"
            "download/v0.2.5.0/realesr-general-x4v3.pth"
        ),
    ),
    # ── ×4 SRVGGNetCompact — general v3 with denoise ─────────────────────────
    "realesr-general-wdn-x4v3": ModelConfig(
        name="realesr-general-wdn-x4v3",
        arch=Arch.SRVGG, scale=4, num_conv=32,
        description="General scenes ×4 v3  (+denoise control)  —  v0.3.0",
        download_url=(
            "https://github.com/xinntao/Real-ESRGAN/releases/"
            "download/v0.2.5.0/realesr-general-wdn-x4v3.pth"
        ),
    ),
}

# Scale factor → models available in that mode
SCALE_TO_MODELS: dict[int, list[str]] = {
    2: [
        "RealESRGAN_x2plus",
    ],
    4: [
        "RealESRGAN_x4plus",
        "RealESRGAN_x4plus_anime_6B",
        "realesr-animevideov3",
        "realesr-general-x4v3",
        "realesr-general-wdn-x4v3",
    ],
}


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  Runtime options dataclass (separate from immutable ModelConfig)            │
# └─────────────────────────────────────────────────────────────────────────────┘
@dataclass
class UpscalerConfig:
    model_name:    str             = "RealESRGAN_x4plus_anime_6B"
    models_dir:    str             = "models"
    tile:          int             = 0        # 0 = no tiling; 512 for low VRAM
    tile_pad:      int             = 10
    pre_pad:       int             = 0
    half:          bool            = False    # FP16 — CUDA only
    outscale:      Optional[float] = None     # None → use model's native scale
    auto_download: bool            = True


# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  Core upscaler — lazy-loading, reusable, cacheable                         │
# └─────────────────────────────────────────────────────────────────────────────┘
class RealESRGANUpscaler:
    """
    Thin, reusable wrapper around RealESRGANer.

    Model weights are loaded lazily on the first upscale call and cached —
    reuse this object across many images to avoid redundant disk / GPU loads.

    Usage
    -----
        cfg      = UpscalerConfig(model_name="RealESRGAN_x4plus_anime_6B")
        upscaler = RealESRGANUpscaler(cfg)
        upscaler.upscale_file("input.png", "output.png")
    """

    def __init__(self, config: UpscalerConfig) -> None:
        self.config    = config
        self.log       = logging.getLogger(f"RealESRGAN.{config.model_name}")
        self.model_cfg = self._resolve_model()
        self.device    = self._select_device()
        self._upsampler: Optional[RealESRGANer] = None   # lazy

    # ── Public API ────────────────────────────────────────────────────────────

    def upscale_file(self, input_path: str, output_path: str) -> Path:
        """Read *input_path*, upscale, save to *output_path*. Returns output Path."""
        src, dst = Path(input_path), Path(output_path)
        if not src.is_file():
            raise FileNotFoundError(f"Input image not found: {src}")
        result = self.upscale_pil(Image.open(src))
        dst.parent.mkdir(parents=True, exist_ok=True)
        result.save(str(dst))
        self.log.info("Saved → %s", dst)
        return dst

    def upscale_pil(self, image: Image.Image) -> Image.Image:
        """PIL Image → upscaled PIL Image."""
        return Image.fromarray(
            self.upscale_numpy(np.array(image.convert("RGB")))
        )

    def upscale_numpy(self, img: np.ndarray) -> np.ndarray:
        """uint8 RGB numpy array → upscaled uint8 numpy array."""
        scale = self.config.outscale or self.model_cfg.scale
        h, w  = img.shape[:2]
        self.log.info(
            "Upscaling %d×%d  →  ×%.0f  [%s]", w, h, scale, self.model_cfg.name
        )
        out, _ = self._get_upsampler().enhance(img, outscale=scale)
        return out

    def preload(self) -> "RealESRGANUpscaler":
        """Eagerly load model weights now rather than on first upscale call."""
        self._get_upsampler()
        return self

    # ── Internals ─────────────────────────────────────────────────────────────

    def _resolve_model(self) -> ModelConfig:
        name = self.config.model_name
        if name not in MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model '{name}'.\nAvailable: {list(MODEL_REGISTRY)}"
            )
        return MODEL_REGISTRY[name]

    def _select_device(self) -> torch.device:
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.log.info("Compute device: %s", dev)
        return dev

    def _get_model_path(self) -> Path:
        models_dir = Path(self.config.models_dir)
        models_dir.mkdir(parents=True, exist_ok=True)
        path = models_dir / f"{self.model_cfg.name}.pth"
        if not path.is_file():
            if self.config.auto_download:
                self._download(path)
            else:
                raise FileNotFoundError(
                    f"Model weights not found: {path}\n"
                    f"Set auto_download=True or download manually:\n"
                    f"{self.model_cfg.download_url}"
                )
        return path

    def _download(self, dest: Path) -> None:
        url = self.model_cfg.download_url
        self.log.info("Downloading model weights: %s", url)
        try:
            urllib.request.urlretrieve(url, str(dest))
            self.log.info(
                "Download complete → %s  (%.1f MB)",
                dest, dest.stat().st_size / 1e6,
            )
        except Exception as exc:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"Download failed: {exc}") from exc

    def _build_net(self) -> torch.nn.Module:
        mc = self.model_cfg
        if mc.arch == Arch.RRDBNET:
            return RRDBNet(
                num_in_ch=mc.num_in_ch,
                num_out_ch=mc.num_out_ch,
                num_feat=mc.num_feat,
                num_block=mc.num_block,
                num_grow_ch=mc.num_grow_ch,
                scale=mc.scale,
            )
        # SRVGGNetCompact — used by animevideov3 and general-x4v3 models
        from basicsr.archs.srvgg_arch import SRVGGNetCompact
        return SRVGGNetCompact(
            num_in_ch=mc.num_in_ch,
            num_out_ch=mc.num_out_ch,
            num_feat=mc.num_feat,
            num_conv=mc.num_conv,
            upscale=mc.scale,
            act_type="prelu",
        )

    def _get_upsampler(self) -> RealESRGANer:
        if self._upsampler is None:
            self._upsampler = self._build_upsampler()
        return self._upsampler

    def _build_upsampler(self) -> RealESRGANer:
        path    = self._get_model_path()
        cfg, mc = self.config, self.model_cfg
        self.log.info(
            "Loading %s  [arch=%s  scale=×%d]",
            mc.name, mc.arch.value, mc.scale,
        )
        return RealESRGANer(
            scale=mc.scale,
            model_path=str(path),
            model=self._build_net(),
            tile=cfg.tile,
            tile_pad=cfg.tile_pad,
            pre_pad=cfg.pre_pad,
            half=(cfg.half and self.device.type == "cuda"),
            device=self.device,
        )