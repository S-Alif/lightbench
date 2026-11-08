import tempfile
import unittest
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from backend.core.media.metadata import read_metadata


def jpeg_with_exif(folder: Path) -> Path:
    exif = Image.Exif()
    exif[0x010F] = "TestCam"                 # Make
    exif[0x0110] = "T-1000"                  # Model
    exif.get_ifd(0x8769)[0x9003] = "2026:05:01 10:20:30"      # DateTimeOriginal
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2], gps[3], gps[4] = "N", (23.0, 45.0, 30.0), "W", (90.0, 24.0, 0.0)
    path = folder / "photo.jpg"
    Image.new("RGB", (40, 30), "white").save(path, exif=exif)
    return path


class MetadataTests(unittest.TestCase):
    def test_camera_date_and_gps_are_found(self):
        with tempfile.TemporaryDirectory() as folder:
            result = read_metadata(jpeg_with_exif(Path(folder)))
        labels = {field["label"]: field["value"] for field in result["fields"]}
        self.assertEqual(labels["Camera make"], "TestCam")
        self.assertEqual(labels["Taken"], "2026:05:01 10:20:30")
        self.assertTrue(result["has_gps"])
        latitude, longitude = (float(part) for part in labels["GPS location"].split(","))
        self.assertAlmostEqual(latitude, 23.7583, places=3)
        self.assertAlmostEqual(longitude, -90.4, places=3)         # west is negative
        self.assertTrue(any("GPS" in warning for warning in result["warnings"]))

    def test_ai_prompt_in_png_is_flagged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ai.png"
            info = PngInfo()
            info.add_text("parameters", "a red fox, steps: 20")
            Image.new("RGB", (10, 10)).save(path, pnginfo=info)
            result = read_metadata(path)
        self.assertTrue(result["has_prompt"])
        self.assertIn("a red fox", " ".join(field["value"] for field in result["fields"]))

    def test_clean_file_has_no_warnings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "clean.png"
            Image.new("RGB", (10, 10)).save(path)
            result = read_metadata(path)
        self.assertEqual(result["warnings"], [])
        self.assertFalse(result["has_gps"])
        self.assertEqual(result["fields"][0]["label"], "Format")


if __name__ == "__main__":
    unittest.main()
