# Img Upscaler

> AI-powered image upscaling for macOS and Windows.  
> Built with Real-ESRGAN · PyQt5 · Pillow. Frameless Bauhaus UI. Single images or full folders. Target-size compression in one pass.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [How to Use](#how-to-use)
- [Supported Models](#supported-models)
- [Output Formats & Target Size](#output-formats--target-size)
- [Project Structure](#project-structure)
- [Credits & Licenses](#credits--licenses)

---

## What It Does

**Img Upscaler** is a desktop GUI that takes low-resolution images and enlarges them up to 4× using deep-learning super-resolution — without the blurriness of traditional bicubic scaling. It uses [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN), a state-of-the-art blind image restoration model trained on synthetic degradation, which means it handles real-world noise, compression artifacts, and blur without manual tuning.

You pick a file or folder, choose a model and output format, hit **Start Upscaling**, and the app handles the rest — including downloading model weights automatically on first run.

---

## Features

| | |
|---|---|
| **2× and 4× upscaling** | Six Real-ESRGAN models covering photos, anime, illustrations, and general scenes |
| **Single image or batch folder** | Process one file or an entire directory in one run |
| **Auto model download** | Weights fetched automatically on first use; cached locally for reuse |
| **Output format choice** | Save as JPEG, PNG, or WebP |
| **Target file size compression** | Binary-search quality optimisation to hit 500 KB / 700 KB / 1 MB / 2 MB targets |
| **Skip existing files** | Re-runs are safe — already-upscaled files are never overwritten |
| **Tiled inference** | Large images processed in 512 px tiles to stay within VRAM limits |
| **Live progress log** | Per-file status with output size reported in real time |
| **GPU + CPU support** | Runs on CUDA if available; falls back to CPU automatically |
| **Frameless draggable window** | Stays on top; drag anywhere to reposition |

---

## Requirements

| | Minimum version |
|---|---|
| Python | 3.9 |
| PyQt5 | 5.15 |
| Pillow | 9.0 |
| torch | 1.13 |
| basicsr | 1.4.2 |
| realesrgan | 0.3.0 |
| numpy | 1.21 |

> **GPU strongly recommended** for 4× upscaling of large images. CPU is supported but slow — expect several minutes per image at high resolution.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/img-upscaler.git
cd img-upscaler

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
python main_app.py
```

**`requirements.txt`**

```
PyQt5>=5.15
Pillow>=9.0
torch>=1.13
basicsr>=1.4.2
realesrgan>=0.3.0
numpy>=1.21
```

> Model weights are downloaded automatically to `src/models/` on first use.  
> To pre-fetch a specific model, launch the app, select the model, and run any image through it once.

---

## How to Use

### 1 · Select your input

At the top of the window, choose **Single image** or **Image folder**, then click **Browse**.

- **Single image** — opens a file picker. Supported formats: `.png` `.jpg` `.jpeg` `.webp` `.bmp` `.tiff` `.tif`
- **Image folder** — scans all image files in the chosen directory (non-recursive). The count is shown next to the path.

### 2 · Choose an output folder *(optional)*

Click **Select Output Folder**. If you skip this step, a subfolder named `upscaled/` is created automatically next to your source file or folder.

Output files are named:
```
original_filename_upscaled.jpg
```

### 3 · Pick a model

Select from the **Model** dropdown. A short description appears below — use it to confirm the model matches your content type. See [Supported Models](#supported-models) for the full guide.

### 4 · Set output format

Choose **JPEG**, **PNG**, or **WebP** from the **Output Format** dropdown.

> Target size compression applies to JPEG and WebP only. PNG is always lossless.

### 5 · Set a target file size *(optional)*

Choose from **No limit / 500 KB / 700 KB / 1 MB / 2 MB**.

When a target is set, the app runs a binary search across quality values (up to 12 iterations) to find the highest quality setting that fits within your chosen size.

### 6 · Start

Click **Start Upscaling**. The progress bar tracks each file. The log area shows live output:

```
[ OK ]   photo.jpg        →  1,243 KB
[ OK ]   scan_old.png     →  892 KB
[SKIP]   cover_upscaled   (exists)
[FAIL]   corrupt.bmp      → cannot identify image file
```

When the run completes, a summary dialog is shown:

```
Saved    →  14  (18.3 MB)
Skipped  →  1
Errors   →  0

Dir  →  /Users/you/photos/upscaled
```

---

## Supported Models

All weights are sourced from the official [Real-ESRGAN releases](https://github.com/xinntao/Real-ESRGAN/releases) by Xintao Wang et al. (ARC Lab, Tencent PCG). Weights download automatically on first use; the links below are for manual installation — place `.pth` files in `src/models/`.

---

### Overview

| Model | Scale | Architecture | Best for | Size | Download |
|---|---|---|---|---|---|
| `RealESRGAN_x4plus` | ×4 | RRDBNet 23-block | General photos, real-world images | 64 MB | [↓ .pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth) |
| `RealESRGAN_x2plus` | ×2 | RRDBNet 23-block | Photos — modest enlargement | 64 MB | [↓ .pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) |
| `RealESRGAN_x4plus_anime_6B` | ×4 | RRDBNet 6-block | Anime, manga — small fast model | 17 MB | [↓ .pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth) |
| `realesr-animevideov3` | ×4 | SRVGGNetCompact 16-conv | Anime video & illustration | 4 MB | [↓ .pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth) |
| `realesr-general-x4v3` | ×4 | SRVGGNetCompact 32-conv | General scenes, fast | 7 MB | [↓ .pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth) |
| `realesr-general-wdn-x4v3` | ×4 | SRVGGNetCompact 32-conv | General scenes + denoise | 7 MB | [↓ .pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth) |

---

### Per-Model Details

#### `RealESRGAN_x4plus`
**Release:** v0.1.0 · **Scale:** ×4 · **Architecture:** RRDBNet (23 RRDB blocks, 64 features)

The flagship general-purpose model. Trained on a large corpus of real-world degradations — noise, JPEG compression, blur, downscaling — using the full 23-block RRDBNet backbone. Best choice for photographs, scans, and any real-world image content.

- **Download:** https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
- **Source:** [Real-ESRGAN v0.1.0 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.1.0)

---

#### `RealESRGAN_x2plus`
**Release:** v0.2.1 · **Scale:** ×2 · **Architecture:** RRDBNet (23 RRDB blocks, 64 features)

Identical backbone to `x4plus` retrained for 2× upscaling. Use when 4× output would exceed your target resolution, or when source material is already moderate resolution and you only need a modest increase.

- **Download:** https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth
- **Source:** [Real-ESRGAN v0.2.1 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.1)

---

#### `RealESRGAN_x4plus_anime_6B`
**Release:** v0.2.2.4 · **Scale:** ×4 · **Architecture:** RRDBNet (6 RRDB blocks, 64 features)

A compact 6-block variant of the RRDBNet, fine-tuned specifically on anime and illustration content. Significantly smaller (17 MB vs 64 MB) and faster than the 23-block models, with quality optimised for flat colour, clean lines, and cel-shading rather than photographic texture.

- **Download:** https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth
- **Source:** [Real-ESRGAN v0.2.2.4 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.2.4)

---

#### `realesr-animevideov3`
**Release:** v0.2.5.0 · **Scale:** ×4 · **Architecture:** SRVGGNetCompact (16 conv layers)

Version 3 of the anime video super-resolution model using the lightweight SRVGGNetCompact architecture. At only 4 MB, it is the fastest model in the registry and produces notably fewer ringing artifacts on anime-style content than the RRDBNet models. Suitable for both still illustrations and video frame upscaling.

- **Download:** https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth
- **Source:** [Real-ESRGAN v0.2.5.0 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0)

---

#### `realesr-general-x4v3`
**Release:** v0.2.5.0 (v0.3.0 weights) · **Scale:** ×4 · **Architecture:** SRVGGNetCompact (32 conv layers)

General-purpose SRVGGNetCompact model for mixed or unknown content types. The 32-conv configuration offers a better quality/speed tradeoff than the RRDBNet 23-block models on standard hardware, with a much smaller weight file. A good default when content type is mixed or unknown.

- **Download:** https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth
- **Source:** [Real-ESRGAN v0.2.5.0 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0)

---

#### `realesr-general-wdn-x4v3`
**Release:** v0.2.5.0 (v0.3.0 weights) · **Scale:** ×4 · **Architecture:** SRVGGNetCompact (32 conv layers)

The `wdn` (with-denoise) companion to `realesr-general-x4v3`. Trained with explicit noise degradation control, making it better suited for heavily compressed, noisy, or heavily artifacted source images. The denoise strength can be blended with the standard model at inference time for fine-grained control.

- **Download:** https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth
- **Source:** [Real-ESRGAN v0.2.5.0 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0)

---

### Quick-Pick Guide

| Your content | Recommended model |
|---|---|
| 📷 Real photographs, scans | `RealESRGAN_x4plus` |
| 🎨 Anime, manga, flat-colour illustration | `realesr-animevideov3` |
| 🖼 Anime stills, want lighter model | `RealESRGAN_x4plus_anime_6B` |
| 🌐 Mixed or unknown content | `realesr-general-x4v3` |
| 🔊 Heavy noise, strong JPEG compression | `realesr-general-wdn-x4v3` |
| 📐 Only modest upscale needed | `RealESRGAN_x2plus` |

---

## Output Formats & Target Size

| Format | Lossless | Target size support | Notes |
|---|---|---|---|
| JPEG | No | ✅ | Best for photos; smallest output sizes |
| PNG | Yes | ❌ | Lossless; largest files; ideal for graphics and transparency |
| WebP | No (default q=95) | ✅ | Modern format; excellent quality-to-size ratio |

**How target size compression works**

When a target is selected for JPEG or WebP, the app performs a binary search between quality 10 and 95:

1. Tests a midpoint quality value
2. Saves to a temporary file and measures size
3. Narrows the range — up or down — based on whether the file fits
4. Repeats for up to 12 iterations
5. Returns the highest quality setting that fits within the target

PNG output always uses lossless compression (`optimize=True`) regardless of the target size setting.

---

## Project Structure

```
img-upscaler/
├── main_app.py                      ← application entry point
├── requirements.txt
├── static/
│   └── cover.png                    ← banner image shown in the app header
└── src/
    ├── assets/
    │   └── real_esrGAN_upscaler.py  ← RealESRGANUpscaler, UpscalerConfig,
    │                                   MODEL_REGISTRY, IMAGE_EXTENSIONS
    └── uiitems/
        ├── close_button.py          ← custom frameless window close button
        └── dialogs.py               ← AlertDialog, DoneDialog
```

**Key internals**

- `MODEL_REGISTRY` — frozen dataclass registry mapping model names to architecture parameters, scale, description, and download URL. Add new models here.
- `UpscalerConfig` — runtime dataclass (tile size, output scale, half-precision flag, auto-download toggle).
- `RealESRGANUpscaler` — lazy-loading wrapper; model weights are loaded on the first `upscale_pil()` call and cached for the session. Switching models in the UI creates a new instance.
- `UpscaleWorker` — `QThread` subclass that processes files sequentially and emits `progress`, `row_done`, and `finished` signals to the UI.

## License

Application code is released under the [MIT License](LICENSE).  
Model weights remain under their respective upstream licenses as listed above.

---
# TinyImgApp — Real-ESRGAN Upscaler

A desktop image upscaling application built with PyQt5 and [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN). Provides a clean, frameless GUI for batch or single-image super-resolution using multiple pretrained model variants, with optional output format conversion and file-size targeting.

---

## Features

- Single image or batch folder upscaling
- Six bundled model presets (x2 and x4, general and anime)
- Automatic model weight download on first use
- Output format selection: JPEG, PNG, WEBP
- Target file size control with binary-search quality optimization
- Tiled inference for low-VRAM environments
- Background worker thread — UI remains responsive during processing
- Frameless, draggable Bauhaus-style window

---

## Requirements

- Python 3.8 or later
- PyQt5
- PyTorch (CPU or CUDA)
- [basicsr](https://github.com/XPixelGroup/BasicSR)
- [realesrgan](https://github.com/xinntao/Real-ESRGAN)
- Pillow
- NumPy

Install dependencies:

```bash
pip install torch torchvision pillow numpy PyQt5 basicsr realesrgan
```

For GPU acceleration, install the appropriate PyTorch CUDA build from [pytorch.org](https://pytorch.org/get-started/locally/).

---

## Usage

```bash
python main_app.py
```

1. Select **Single image** or **Image folder** as the input source.
2. Browse for the input file or directory.
3. Optionally select an output folder (defaults to an `upscaled/` subdirectory beside the input).
4. Choose a model and output format.
5. Set a target file size if needed (applies lossy compression to meet the limit).
6. Click **Start Upscaling**.

Model weights are downloaded automatically to the `models/` directory on first use. Set `auto_download=False` in `UpscalerConfig` to disable this and manage weights manually.

---

## Supported Input Formats

`.png` `.jpg` `.jpeg` `.webp` `.bmp` `.tiff` `.tif`

---

## Models

Six pretrained models are included in the registry. Weights are downloaded from the official Real-ESRGAN GitHub releases.

| Model | Scale | Architecture | Use Case | Download |
|---|---|---|---|---|
| `RealESRGAN_x4plus` | x4 | RRDBNet (23-block) | General images | [v0.1.0](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth) |
| `RealESRGAN_x2plus` | x2 | RRDBNet (23-block) | General images | [v0.2.1](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) |
| `RealESRGAN_x4plus_anime_6B` | x4 | RRDBNet (6-block) | Anime illustrations | [v0.2.2.4](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth) |
| `realesr-animevideov3` | x4 | SRVGGNetCompact | Anime video frames | [v0.2.5.0](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth) |
| `realesr-general-x4v3` | x4 | SRVGGNetCompact | General scenes, fast | [v0.2.5.0](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth) |
| `realesr-general-wdn-x4v3` | x4 | SRVGGNetCompact | General scenes + denoise | [v0.2.5.0](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth) |

For guidance on choosing between anime-optimized models, refer to the official [Real-ESRGAN anime model documentation](https://github.com/xinntao/Real-ESRGAN/blob/master/docs/anime_model.md).

To download weights manually, place the `.pth` file in the `models/` directory with the filename matching the model name exactly (e.g., `models/RealESRGAN_x4plus_anime_6B.pth`).

---

## Project Structure

```
.
├── main_app.py                        # Application entry point and PyQt5 UI
├── src/
│   └── assets/
│       └── real_esrGAN_upscaler.py    # Upscaler module: model registry, config, worker class
│   └── uiitems/
│       ├── close_button.py            # Custom frameless window close button
│       └── dialogs.py                 # Reusable AlertDialog and DoneDialog
├── static/
│   └── cover.png                      # Title bar cover image
└── models/                            # Downloaded model weights (auto-created)
```

---

## Upscaler API

The upscaler module can be used independently of the GUI:

```python
from src.assets.real_esrGAN_upscaler import RealESRGANUpscaler, UpscalerConfig

cfg = UpscalerConfig(
    model_name="RealESRGAN_x4plus_anime_6B",
    models_dir="models",
    tile=512,          # set > 0 for low-VRAM GPUs; 0 disables tiling
    half=False,        # FP16 inference (CUDA only)
    auto_download=True,
)

upscaler = RealESRGANUpscaler(cfg)

# File-to-file
upscaler.upscale_file("input.png", "output.png")

# PIL Image
from PIL import Image
result: Image.Image = upscaler.upscale_pil(Image.open("input.png"))

# NumPy array (uint8 RGB)
import numpy as np
arr_out: np.ndarray = upscaler.upscale_numpy(arr_in)
```

The upscaler is lazy-loading by default. Call `upscaler.preload()` to load weights eagerly before the first inference call.

---

## Configuration Reference

`UpscalerConfig` fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `model_name` | `str` | `RealESRGAN_x4plus_anime_6B` | Model key from `MODEL_REGISTRY` |
| `models_dir` | `str` | `models` | Directory for cached model weights |
| `tile` | `int` | `0` | Tile size in pixels; `0` disables tiling |
| `tile_pad` | `int` | `10` | Overlap padding between tiles |
| `pre_pad` | `int` | `0` | Padding added before inference |
| `half` | `bool` | `False` | FP16 mode (CUDA only) |
| `outscale` | `float \| None` | `None` | Output scale override; `None` uses the model's native scale |
| `auto_download` | `bool` | `True` | Download missing weights automatically |

---

## Known Compatibility Note

A `torchvision` compatibility shim is applied at module load time to resolve an import conflict between recent versions of `torchvision` and `basicsr`. This is handled automatically and requires no user configuration.

---

## Credits

Super-resolution models and training code are from the **Real-ESRGAN** project by [Xintao Wang](https://github.com/xinntao) and contributors.

- Repository: [https://github.com/xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- Anime model guide: [https://github.com/xinntao/Real-ESRGAN/blob/master/docs/anime_model.md](https://github.com/xinntao/Real-ESRGAN/blob/master/docs/anime_model.md)
- Model releases: [https://github.com/xinntao/Real-ESRGAN/releases](https://github.com/xinntao/Real-ESRGAN/releases)

If you use Real-ESRGAN models in your work, please cite the original paper:

```bibtex
@InProceedings{wang2021realesrgan,
    author    = {Xintao Wang and Liangbin Xie and Chao Dong and Ying Shan},
    title     = {Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data},
    booktitle = {International Conference on Computer Vision Workshops (ICCVW)},
    year      = {2021}
}
```

---

## License

This application is released under the MIT License. Real-ESRGAN model weights are subject to their own license terms; refer to the [Real-ESRGAN repository](https://github.com/xinntao/Real-ESRGAN) for details.