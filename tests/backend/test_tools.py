import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from backend.core.tools import (CollageOptions, ConvertOptions, SplitOptions, convert_image, extract_palette, make_collage,
                                open_image, resolve_folder, split_sheet, write_into_folder)


def encode(picture, fmt="PNG", **extra):
    buffer = io.BytesIO()
    picture.save(buffer, fmt, **extra)
    return buffer.getvalue()


def geotagged_jpeg(orientation=None):
    exif = Image.Exif()
    exif[0x010F] = "TestCam"
    exif.get_ifd(0x8825).update({1: "N", 2: (23.0, 45.0, 0.0), 3: "E", 4: (90.0, 25.0, 0.0)})
    if orientation:
        exif[0x0112] = orientation
    return encode(Image.new("RGB", (200, 100), (10, 120, 200)), "JPEG", exif=exif.tobytes())


def convert(data, **options):
    picture = open_image(data)
    return convert_image(picture, picture.info.get("source_format"), ConvertOptions.from_dict(options))


class ConvertTest(unittest.TestCase):
    def test_formats(self):
        source = encode(Image.new("RGB", (80, 40), (200, 20, 20)))
        self.assertEqual(convert(source).ext, "png")  # keep
        for fmt in ("jpg", "png", "webp"):
            result = convert(source, fmt=fmt)
            self.assertEqual((result.ext, Image.open(io.BytesIO(result.data)).size), (fmt, (80, 40)))

    def test_transparency_becomes_the_background_colour_in_a_jpg(self):
        source = encode(Image.new("RGBA", (20, 20), (0, 0, 0, 0)))
        result = convert(source, fmt="jpg", background="#ff0000")
        pixel = Image.open(io.BytesIO(result.data)).getpixel((10, 10))
        self.assertGreater(pixel[0], 240)
        self.assertLess(pixel[2], 20)
        self.assertEqual(Image.open(io.BytesIO(convert(source, fmt="png").data)).mode, "RGBA")

    def test_resize_modes(self):
        source = encode(Image.new("RGB", (400, 200)))
        self.assertEqual((convert(source, resize="percent", percent=50).width, convert(source, resize="percent", percent=50).height), (200, 100))
        fitted = convert(source, resize="fit", width=100)
        self.assertEqual((fitted.width, fitted.height), (100, 50))
        self.assertEqual(convert(source, resize="fit", width=1000, height=1000).width, 400)  # fit never enlarges
        with self.assertRaises(ValueError):
            ConvertOptions.from_dict({"resize": "fit"})

    def test_metadata_modes(self):
        data = geotagged_jpeg()
        def tags(mode):
            exif = Image.open(io.BytesIO(convert(data, metadata=mode).data)).getexif()
            return exif.get(0x010F), dict(exif.get_ifd(0x8825)).get(1)
        self.assertEqual(tags("remove_all"), (None, None))
        self.assertEqual(tags("remove_location"), ("TestCam", None))
        self.assertEqual(tags("keep"), ("TestCam", "N"))
        picture = open_image(data)
        convert_image(picture, "JPEG", ConvertOptions.from_dict({"metadata": "remove_all"}))
        self.assertEqual(dict(picture.getexif().get_ifd(0x8825)).get(1), "N")  # the loaded picture itself is not changed

    def test_rotation_flag_is_applied_before_it_is_removed(self):
        data = geotagged_jpeg(orientation=6)  # camera says: turn 90 degrees
        result = convert(data, metadata="remove_all")
        self.assertEqual((result.width, result.height), (100, 200))

    def test_target_size(self):
        noise = Image.fromarray(np.random.default_rng(3).integers(0, 255, (300, 300, 3), dtype=np.uint8))
        result = convert(encode(noise), fmt="jpg", target_kb=20)
        self.assertLessEqual(len(result.data), 20_000)
        self.assertEqual(result.note, "")
        self.assertIn("could not", convert(encode(noise), fmt="jpg", target_kb=1).note.lower())
        self.assertIn("jpg and webp", convert(encode(noise), fmt="png", target_kb=20).note.lower())

    def test_colour_and_sharpen_change_pixels(self):
        source = encode(Image.new("RGB", (30, 30), (100, 100, 100)))
        brighter = np.asarray(Image.open(io.BytesIO(convert(source, brightness=50).data)))
        self.assertGreater(int(brighter[5, 5, 0]), 130)
        gray = np.asarray(Image.open(io.BytesIO(convert(encode(Image.new("RGB", (30, 30), (200, 50, 50))), saturation=-100).data)).convert("RGB"))
        self.assertLess(abs(int(gray[5, 5, 0]) - int(gray[5, 5, 2])), 6)
        self.assertEqual(Image.open(io.BytesIO(convert(source, sharpen=60).data)).size, (30, 30))

    def test_bad_options(self):
        for bad in ({"fmt": "gif"}, {"metadata": "x"}, {"background": "red"}, {"resize": "huge"}):
            with self.assertRaises(ValueError):
                ConvertOptions.from_dict(bad)
        self.assertEqual(ConvertOptions.from_dict({"quality": 500, "brightness": -900}).brightness, -100)

    def test_not_an_image(self):
        with self.assertRaises(OSError):
            open_image(b"junk")


class CollageTest(unittest.TestCase):
    def pictures(self, count, colour=(255, 0, 0)):
        return [Image.new("RGB", (300, 200), colour) for _ in range(count)]

    def test_grid_size_and_background(self):
        options = CollageOptions.from_dict({"columns": 2, "cell_width": 100, "ratio": "1:1", "gap": 10, "margin": 5, "background": "#00ff00"})
        sheet = make_collage(self.pictures(3), options)
        self.assertEqual(sheet.size, (2 * 100 + 10 + 10, 2 * 100 + 10 + 10))
        self.assertEqual(sheet.getpixel((5 + 100 + 5, 5 + 100 + 10 + 50)), (0, 255, 0))  # the empty fourth cell and gap show the background
        self.assertEqual(sheet.getpixel((55, 55)), (255, 0, 0))

    def test_transparent_forces_png_and_contain_keeps_whole_picture(self):
        options = CollageOptions.from_dict({"transparent": True, "fmt": "jpg", "fit": "contain", "cell_width": 100, "gap": 0, "margin": 0, "columns": 2})
        self.assertEqual(options.fmt, "png")
        sheet = make_collage(self.pictures(2), options)
        self.assertEqual(sheet.mode, "RGBA")
        self.assertEqual(sheet.getpixel((50, 2))[3], 0)  # letterbox bars are transparent

    def test_limits(self):
        with self.assertRaises(ValueError):
            make_collage(self.pictures(1), CollageOptions())
        with self.assertRaises(ValueError):
            make_collage(self.pictures(61), CollageOptions())
        with self.assertRaises(ValueError):
            CollageOptions.from_dict({"ratio": "5:7"})


class SplitAndPaletteTest(unittest.TestCase):
    def test_split_loses_no_pixel(self):
        picture = Image.new("RGB", (101, 53))
        tiles = split_sheet(picture, SplitOptions.from_dict({"rows": 2, "columns": 3}))
        self.assertEqual([name for name, _ in tiles][:2], ["tile-r1-c1", "tile-r1-c2"])
        self.assertEqual(sum(tile.width * tile.height for _, tile in tiles), 101 * 53)
        with self.assertRaises(ValueError):
            SplitOptions.from_dict({"rows": 1, "columns": 1})

    def test_palette_finds_the_big_colours_first(self):
        picture = Image.new("RGB", (100, 100), (200, 30, 30))
        picture.paste((20, 20, 220), (0, 0, 100, 25))
        colours = extract_palette(picture, 4)
        self.assertEqual(len(colours), 2)
        self.assertGreater(colours[0]["share"], colours[1]["share"])
        self.assertEqual(colours[0]["hex"], "#c81e1e")
        self.assertEqual(extract_palette(Image.new("RGBA", (10, 10), (0, 0, 0, 0))), [])


class SavingTest(unittest.TestCase):
    def test_never_overwrites_and_rejects_bad_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            target = resolve_folder(str(Path(folder) / "new" / "inner"))
            first, second = write_into_folder(target, "a.png", b"1"), write_into_folder(target, "a.png", b"2")
            self.assertEqual((first.name, second.name, first.read_bytes()), ("a.png", "a-2.png", b"1"))
        for bad in ("", "relative/folder"):
            with self.assertRaises(ValueError):
                resolve_folder(bad)


class EndpointTest(unittest.TestCase):
    def setUp(self):
        from starlette.testclient import TestClient
        from backend.main import app
        self.client = TestClient(app)

    def post(self, url, files, options=None):
        return self.client.post(url, files=files, data={"options": json.dumps(options or {})})

    def test_convert_returns_the_file_with_size_headers(self):
        response = self.post("/api/tools/convert", [("file", ("photo.png", encode(Image.new("RGB", (80, 40))), "image/png"))], {"fmt": "webp", "resize": "percent", "percent": 50})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.headers["content-type"], response.headers["x-width"], response.headers["x-ext"]), ("image/webp", "40", "webp"))
        self.assertIn("photo.webp", response.headers["content-disposition"])

    def test_errors(self):
        good = encode(Image.new("RGB", (20, 20)))
        self.assertEqual(self.post("/api/tools/convert", [("file", ("a.png", b"junk", "image/png"))]).status_code, 415)
        self.assertEqual(self.post("/api/tools/convert", [("file", ("a.png", good, "image/png"))], {"fmt": "gif"}).status_code, 400)
        self.assertEqual(self.client.post("/api/tools/convert", data={"options": "{}"}).status_code, 400)
        self.assertEqual(self.post("/api/tools/collage", [("files", ("a.png", good, "image/png"))]).status_code, 400)

    def test_saving_to_a_folder_is_refused_from_other_computers_and_works_locally(self):
        good = encode(Image.new("RGB", (20, 20)))
        with tempfile.TemporaryDirectory() as folder:
            refused = self.post("/api/tools/convert", [("file", ("a.png", good, "image/png"))], {"save_to": folder})
            self.assertEqual(refused.status_code, 403)
            with mock.patch("backend.api.routes.tools.is_local_request", lambda request: True):
                saved = self.post("/api/tools/convert", [("file", ("a.png", good, "image/png"))], {"save_to": folder, "fmt": "jpg"})
            self.assertEqual(saved.status_code, 200)
            self.assertEqual([Path(path).name for path in saved.json()["saved"]], ["a.jpg"])
            self.assertTrue((Path(folder) / "a.jpg").is_file())

    def test_collage_split_palette(self):
        red, blue = encode(Image.new("RGB", (60, 40), (255, 0, 0))), encode(Image.new("RGB", (60, 40), (0, 0, 255)))
        collage = self.post("/api/tools/collage", [("files", ("a.png", red, "image/png")), ("files", ("b.png", blue, "image/png"))], {"columns": 2, "cell_width": 50, "fmt": "png"})
        self.assertEqual((collage.status_code, collage.headers["content-type"]), (200, "image/png"))
        split = self.post("/api/tools/split", [("file", ("sheet.png", encode(Image.new("RGB", (60, 40))), "image/png"))], {"rows": 2, "columns": 2})
        self.assertEqual(sorted(zipfile.ZipFile(io.BytesIO(split.content)).namelist())[0], "sheet-tile-r1-c1.png")
        colours = self.post("/api/tools/palette", [("file", ("a.png", red, "image/png"))], {"count": 3}).json()["colours"]
        self.assertEqual(colours[0]["hex"], "#ff0000")


if __name__ == "__main__":
    unittest.main()
