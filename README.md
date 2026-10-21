<div align="center">

# Lightbench

**Upscale and watermark images and videos on your own computer.**

A local web app built around [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN).
No accounts, no cloud, nothing leaves your machine.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white)
![PyTorch](https://img.shields.io/badge/pytorch-CUDA%20%7C%20ROCm%20%7C%20MPS%20%7C%20CPU-EE4C2C?logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Hardware](#hardware)
- [Models](#models)
- [Using your own models](#using-your-own-models)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [Privacy and security](#privacy-and-security)
- [Tested on](#tested-on)
- [Roadmap](#roadmap)
- [Credits](#credits)
- [License](#license)

## Features

- **Photo and Art profiles**, or pick any model yourself, including your own `.pth` files
- **2×, 3× and 4× upscaling**, or turn it off to only watermark or convert
- **Basic editor:** crop and rotate each image before upscaling, with a free roam crop and ratio presets (platform names such as Instagram post or YouTube are shown only where the ratio matches their guidance)
- **Text watermark** with nine positions, colour, opacity, and a size that is either a percentage of the image or fixed pixels
- **Life-sized watermark preview** that copies the aspect ratio of your first file, so what you place is what you get
- **Images:** JPG, PNG, WebP. **Videos:** H.264 MP4 with the original audio kept
- **Batch processing** with a live progress overlay: percentage, file counter, elapsed time and ETA
- **History:** every job is stored on disk. Come back later, view the results and download them one by one or as a `.zip`
- **Safe deletes:** removing a job shows the folder it lives in and asks for confirmation
- **One kind per job:** a job is all images or all videos, never mixed
- **Runs anywhere Python and PyTorch run:** NVIDIA, AMD (Linux), Apple Silicon, or plain CPU
- **Automatic out-of-memory recovery:** if the GPU runs out of memory, tiles shrink and the file is retried

## Quick start

You need **Python 3.10 or newer**. On Windows, tick **"Add python.exe to PATH"** in the installer.

```bash
git clone https://github.com/<your-username>/lightbench.git
cd lightbench
python run.py
```

That is all. The first launch sets everything up on its own:

1. creates a private virtual environment in `.venv/`
2. installs the right PyTorch build for your hardware
3. installs the remaining Python packages
4. builds the frontend if it is not built yet (needs [Node.js](https://nodejs.org) only in that case)
5. starts the server and opens your browser

The first run takes a few minutes and downloads PyTorch, which is large. Every launch after that starts in seconds.

### Options

| Flag | What it does |
| --- | --- |
| `--port 8000` | pick a port (the next free one is used if it is taken) |
| `--lan` | also listen on your network, handy for opening it from a phone. **No password**, see [Privacy and security](#privacy-and-security) |
| `--no-browser` | do not open a browser tab |

Other commands:

```bash
python setup.py --cpu       # force the small CPU-only PyTorch
python setup.py --models    # download the built-in models ahead of time
```

### Developing the frontend

```bash
cd frontend
npm install
npm run dev      # hot reload on http://localhost:5173, API proxied to the backend
npm run build    # writes the production build into backend/static
```

## Hardware

| Hardware | Support | Notes |
| --- | --- | --- |
| NVIDIA GPU | CUDA | fastest. Half precision is used automatically |
| AMD GPU on Linux | ROCm | needs a ROCm-supported card |
| AMD / Intel GPU on Windows | CPU only | PyTorch has no official GPU build for these |
| Apple Silicon | MPS | M1 and newer |
| Any other CPU | works | slow for big images, very slow for video |

Some GTX 16xx cards produce black images in half precision. If that happens, turn on **Full precision** under *Advanced*.

Videos also need FFmpeg. A copy is installed for you through `imageio-ffmpeg`, nothing to do.

## Models

Lightbench uses the official **Real-ESRGAN** weights. They are **not stored in this repository**. They download automatically the first time you need them and are saved in the `models/` folder.

| File | Used for | Download |
| --- | --- | --- |
| `RealESRGAN_x2plus.pth` | Photo, 2× | [v0.2.1 release](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) |
| `RealESRGAN_x4plus.pth` | Photo, 3× and 4× | [v0.1.0 release](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth) |
| `RealESRGAN_x4plus_anime_6B.pth` | Art and illustrations, 2× to 4× | [v0.2.2.4 release](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth) |

All three come from the official [Real-ESRGAN GitHub releases](https://github.com/xinntao/Real-ESRGAN/releases). Nothing is downloaded from any other place, and nothing is uploaded anywhere.

Good to know:

- **3× has no native model.** The 4× weights are used and the result is resized to 3× with Lanczos
- Prefer to download them yourself? Save the files above into `models/` and Lightbench will use them without going online
- A download that comes out suspiciously small is rejected, so a broken file never ends up in your models folder

## Using your own models

Drop any compatible Real-ESRGAN style `.pth` or `.pt` file into the `models/` folder, press **Refresh** in the model picker, and it shows up as a custom model.

- Supported architectures: **RRDBNet** (x2plus, x4plus, anime 6B and similar) and **SRVGGNetCompact** (for example `realesr-general-x4v3` and `realesr-animevideov3`)
- The architecture and scale are detected from the file, nothing to configure
- Files load with `torch.load(..., weights_only=True)`, so a malicious pickle cannot run code. Even so, only use weights from sources you trust

## Configuration

The defaults are fine for most people. Two environment variables change where files go:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LIGHTBENCH_DATA` | `./data` | where jobs, results and thumbnails are stored |
| `LIGHTBENCH_MODELS` | `./models` | where model weights are stored |

```bash
# example: keep everything on a bigger drive
LIGHTBENCH_DATA=/mnt/storage/lightbench python run.py
```

On Windows PowerShell: `$env:LIGHTBENCH_DATA = "D:\lightbench"; python run.py`

## Project layout

```text
lightbench/
├── run.py                  start the app
├── setup.py                one-time setup (virtualenv, PyTorch, frontend build)
├── requirements.txt        python packages (PyTorch is installed by setup.py)
├── backend/                python server (Starlette + uvicorn)
│   ├── main.py             builds the app, mounts the api and the built frontend
│   ├── config.py           paths and environment variables
│   ├── api/                http layer: router, shared helpers, routes/
│   ├── services/jobs/      job queue, worker thread and history on disk
│   ├── core/               processing, no web code
│   │   ├── pipeline.py     edit, upscale, watermark, save
│   │   ├── editing/        crop and rotate
│   │   ├── upscaler.py     tiled inference with out-of-memory fallback
│   │   ├── models/         model catalog, architectures, weight loading
│   │   └── media/          video, thumbnails, watermark, file types
│   └── static/             the built frontend
├── frontend/               react app (Vite + Tailwind)
│   └── src/
│       ├── api/            calls to the backend
│       ├── lib/            small pure helpers
│       ├── hooks/          routing and saved settings
│       ├── components/     ui, cards, layout, jobs, icons
│       ├── features/       settings (watermark, output, models), editor (planned)
│       └── pages/          new job, history, job detail
├── docs/                   architecture notes
├── tests/                  backend and frontend tests
├── models/                 model weights, downloaded on first use (not in git)
└── data/                   your jobs and results (not in git)
```

Everything inside `data/` and every downloaded model stays out of git, see [`.gitignore`](.gitignore). More detail in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Privacy and security

- Everything runs locally. Files are processed on your computer and never sent to a third party
- The only network traffic is the model download from GitHub and the one-time package install
- **There is no login.** By default the server only listens on `127.0.0.1`, so only you can reach it. `--lan` opens it to everyone on your network, so only use it on a network you trust
- "Open folder" only works from the computer that runs the app

## Tested on

Created and tested with **Python 3.10.20**.

The code is written to work on Windows, macOS and Linux. The CPU path, the API and the watermark pipeline have been exercised end to end. GPU paths (CUDA, ROCm, MPS) follow the standard PyTorch device APIs but depend on your drivers, so reports from other setups are very welcome.

## Roadmap

- Basic editor: colour adjustments, straighten, metadata clean-up (crop and rotate are done)
- Image watermarks (logos), not only text
- More model families
- Optional password for `--lan`

Ideas and pull requests are welcome.

## Credits

Lightbench is a thin, friendly layer. The hard part, the actual super-resolution, is the work of other people.

### Models

**Real-ESRGAN** by Xintao Wang, Liangbin Xie, Chao Dong and Ying Shan, [Tencent ARC Lab](https://github.com/TencentARC). Released under the BSD 3-Clause license.

- Project: <https://github.com/xinntao/Real-ESRGAN>
- Paper: *Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data*, ICCV Workshops 2021, [arXiv:2107.10833](https://arxiv.org/abs/2107.10833)

```bibtex
@InProceedings{wang2021realesrgan,
    author    = {Xintao Wang and Liangbin Xie and Chao Dong and Ying Shan},
    title     = {Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data},
    booktitle = {International Conference on Computer Vision Workshops (ICCVW)},
    date      = {2021}
}
```

**ESRGAN**, the network behind the RRDB architecture, by Xintao Wang, Ke Yu, Shixiang Wu, Jinjin Gu, Yihao Liu, Chao Dong, Yu Qiao and Chen Change Loy.
*ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks*, ECCV Workshops 2018, [arXiv:1809.00219](https://arxiv.org/abs/1809.00219).

**BasicSR** by Xintao Wang and contributors ([XPixelGroup/BasicSR](https://github.com/XPixelGroup/BasicSR), Apache 2.0). The `RRDBNet` and `SRVGGNetCompact` network definitions in `backend/core/models/architectures.py` follow the architectures published in BasicSR and Real-ESRGAN, so that the official weights load unchanged.

### Libraries

[PyTorch](https://pytorch.org) · [Starlette](https://www.starlette.io) · [Uvicorn](https://www.uvicorn.org) · [Pillow](https://python-pillow.org) · [NumPy](https://numpy.org) · [FFmpeg](https://ffmpeg.org) via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) · [React](https://react.dev) · [Vite](https://vite.dev) · [Tailwind CSS](https://tailwindcss.com)

The watermark uses Noto Sans Bold when it is found on your system or placed in `models/fonts/`. Noto Sans is by Google, licensed under the SIL Open Font License.

Each of these projects is the property of its authors and used under its own license.

## License

Lightbench's source code is released under the [MIT License](LICENSE).

The model weights are **not** part of this repository and keep their original licenses. Please read the [Real-ESRGAN license](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE) before using results commercially.
