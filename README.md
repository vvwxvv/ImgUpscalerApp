# Img Upscaler App — Real-ESRGAN

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
