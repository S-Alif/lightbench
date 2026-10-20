"""Model architectures, weight registry/downloader and custom-model detection.

Two architectures are supported, which covers the Real-ESRGAN family and most
community models:
  * RRDBNet          (RealESRGAN_x4plus, x2plus, anime_6B, ESRGAN-style "4x-*.pth" files)
  * SRVGGNetCompact  (realesr-general-x4v3, realesr-animevideov3, ...)

Both are small re-implementations of the originals (basicsr / realesrgan, BSD-3),
so those packages are not needed. Parameter names match, so the official .pth
files load with strict=True. The architecture of any file you drop in `models/`
is detected from the tensor shapes in the file itself.
"""

