"""Video helpers: decode -> process_frame -> encode, one frame at a time.

Frames are streamed through pipes, so no temp PNG sequence is ever written to
disk (a 1-minute 1080p clip upscaled 4x would otherwise be tens of GB).
Audio is taken from the original file.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
from fractions import Fraction
from typing import Callable, Optional

import numpy as np

from ..errors import Cancelled

MP4_COPY_AUDIO = {"aac", "mp3", "ac3", "eac3", "alac", "mp2"}


def ffmpeg_exe() -> str:
    env = os.environ.get("FFMPEG_BINARY")
    if env and os.path.exists(env):
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(
            "FFmpeg not found. Install it (https://ffmpeg.org) or `pip install imageio-ffmpeg`.") from error


def ffmpeg_available() -> bool:
    try:
        ffmpeg_exe()
        return True
    except RuntimeError:
        return False


def _snap_fps(text: str) -> Fraction:
    """ffmpeg prints rounded rates (29.97). Snap to the exact NTSC fraction (30000/1001)
    so audio and video don't drift apart over long clips."""
    rate = float(text)
    ntsc = Fraction(round(rate) * 1000, 1001)
    if abs(float(ntsc) - rate) < 0.006:
        return ntsc
    return Fraction(text).limit_denominator(1001)


def probe(path: str) -> dict:
    """Parse `ffmpeg -i` output (ffprobe isn't bundled with imageio-ffmpeg)."""
    result = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostdin", "-i", path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ffmpeg_output = result.stderr
    video_match = re.search(r"Stream #\S+.*?Video: (.+)", ffmpeg_output)
    if not video_match:
        raise RuntimeError("No video stream found in this file")
    line = video_match.group(1)
    size = re.search(r",\s*(\d{2,5})x(\d{2,5})[\s,\[]", line + " ")
    if not size:
        raise RuntimeError("Could not read the video resolution")
    width, height = int(size.group(1)), int(size.group(2))
    fps_m = re.search(r"([\d.]+) fps", line) or re.search(r"([\d.]+) tbr", line)
    fps = _snap_fps(fps_m.group(1)) if fps_m else Fraction(30)
    rot = re.search(r"rotation of (-?[\d.]+) degrees", ffmpeg_output)
    if rot and round(abs(float(rot.group(1)))) % 180 == 90:
        width, height = height, width                       # ffmpeg auto-rotates while decoding
    duration_match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", ffmpeg_output)
    dur = int(duration_match.group(1)) * 3600 + int(duration_match.group(2)) * 60 + float(duration_match.group(3)) if duration_match else 0.0
    audio_match = re.search(r"Audio: (\w+)", ffmpeg_output)
    return {"w": width, "h": height, "fps": fps, "duration": dur,
            "frames": int(dur * float(fps)) if dur else 0,
            "audio": audio_match.group(1).lower() if audio_match else None}


def _tail(log_file) -> str:
    try:
        log_file.flush()
        log_file.seek(0)
        return log_file.read().decode("utf-8", "replace").strip()[-600:]
    except Exception:  # noqa: BLE001
        return ""


def process_video(src: str, dst: str, process_frame: Callable[[np.ndarray], np.ndarray], *,
                  crf: int = 18, preset: str = "medium", keep_metadata: bool = False,
                  progress: Optional[Callable[[float, str], None]] = None,
                  cancel: Optional[threading.Event] = None) -> None:
    ffmpeg_path = ffmpeg_exe()
    info = probe(src)
    width, height, fps = info["w"], info["h"], info["fps"]
    fbytes = width * height * 3
    dec_err, enc_err = tempfile.TemporaryFile(), tempfile.TemporaryFile()
    dec = subprocess.Popen(
        [ffmpeg_path, "-v", "error", "-nostdin", "-i", src, "-map", "0:v:0",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, stderr=dec_err)
    enc = None
    frames_done = 0
    finished_cleanly = False
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            buf = dec.stdout.read(fbytes)
            if len(buf) < fbytes:
                break
            frame = np.frombuffer(buf, np.uint8).reshape(height, width, 3).copy()
            out = process_frame(frame)
            if enc is None:
                out_height, out_width = out.shape[:2]
                acodec = []
                if info["audio"]:
                    acodec = ["-c:a", "copy"] if info["audio"] in MP4_COPY_AUDIO else ["-c:a", "aac", "-b:a", "192k"]
                cmd = [ffmpeg_path, "-y", "-v", "error", "-nostdin",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{out_width}x{out_height}",
                       "-r", f"{fps.numerator}/{fps.denominator}", "-i", "pipe:0",
                       "-i", src, "-map", "0:v:0", "-map", "1:a:0?",
                       "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2",   # yuv420p needs even sizes
                       "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                       *acodec, "-shortest",
                       "-map_metadata", "1" if keep_metadata else "-1",
                       "-movflags", "+faststart", dst]
                enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=enc_err)
            try:
                enc.stdin.write(np.ascontiguousarray(out).tobytes())
            except (BrokenPipeError, OSError):
                raise RuntimeError(f"FFmpeg encoder stopped: {_tail(enc_err)}")
            frames_done += 1
            if progress:
                total = info["frames"] or max(frames_done + 1, 1)
                progress(min(frames_done / total, 0.99), f"frame {frames_done}" + (f" / {total}" if info["frames"] else ""))
        if frames_done == 0:
            raise RuntimeError(f"Could not decode any frames. {_tail(dec_err)}")
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError(f"FFmpeg encoder failed: {_tail(enc_err)}")
        finished_cleanly = True
    finally:
        for child_process in (dec, enc):
            if child_process is not None and child_process.poll() is None:
                child_process.kill()
        for child_process in (dec, enc):
            if child_process is not None:
                try:
                    child_process.wait(timeout=10)
                except Exception:  # noqa: BLE001
                    pass
        dec_err.close()
        enc_err.close()
        if not finished_cleanly and os.path.exists(dst):
            try:
                os.remove(dst)
            except OSError:
                pass
