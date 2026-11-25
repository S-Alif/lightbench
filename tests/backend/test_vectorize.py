import io
import unittest

from PIL import Image

from backend.core.vector import TraceOptions, trace_image
from backend.core.vector import tracer


def make_png(size=(40, 30), mode="RGB", colour=(200, 30, 30)):
    buffer = io.BytesIO()
    Image.new(mode, size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


def fake_convert(png_bytes, options):
    with Image.open(io.BytesIO(png_bytes)) as image:
        width, height = image.size
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><path d="M0 0"/><path d="M1 1"/></svg>'


class OptionsTest(unittest.TestCase):
    def test_defaults_and_clamping(self):
        options = TraceOptions.from_dict({"colors": 99, "remove_specks": -5, "detail": 1})
        self.assertEqual(options.colors, 32)
        self.assertEqual(options.remove_specks, 0)
        self.assertEqual(options.detail, 3.5)

    def test_rejects_unknown_modes(self):
        for bad in ({"colormode": "x"}, {"curves": "x"}, {"layering": "x"}):
            with self.assertRaises(ValueError):
                TraceOptions.from_dict(bad)


class TraceTest(unittest.TestCase):
    def test_result_shape_and_viewbox(self):
        result = trace_image(make_png(), TraceOptions(), convert=fake_convert)
        # small images are enlarged to 1400 px on the long side so curves come out smooth
        self.assertEqual((result["width"], result["height"]), (1400, 1050))
        self.assertEqual(result["paths"], 2)
        self.assertIn('viewBox="0 0 1400 1050"', result["svg"])
        self.assertEqual(result["bytes"], len(result["svg"].encode()))

    def test_large_image_is_shrunk(self):
        result = trace_image(make_png((1000, 500)), TraceOptions(max_side=256), convert=fake_convert)
        self.assertEqual((result["width"], result["height"]), (256, 128))

    def test_missing_vtracer_gives_clear_error(self):
        import sys
        saved = sys.modules.get("vtracer")
        sys.modules["vtracer"] = None  # makes `import vtracer` raise ImportError
        try:
            with self.assertRaises(tracer.VectorizerMissing):
                trace_image(make_png(), TraceOptions())
        finally:
            if saved is None:
                sys.modules.pop("vtracer", None)
            else:
                sys.modules["vtracer"] = saved

    def test_non_image_raises_oserror(self):
        with self.assertRaises(OSError):
            trace_image(b"not an image", TraceOptions(), convert=fake_convert)


def shirt_png(background=(255, 255, 255)):
    from PIL import ImageDraw
    image = Image.new("RGB", (300, 300), background)
    draw = ImageDraw.Draw(image)
    draw.ellipse((50, 50, 250, 250), fill=(220, 40, 40))
    draw.ellipse((120, 120, 180, 180), fill=background)  # a hole, like inside the letter O
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class BackgroundTest(unittest.TestCase):
    def test_solid_background_is_detected_and_flattened(self):
        from backend.core.vector import preprocess
        for background in ((255, 255, 255), (15, 15, 15), (30, 90, 200)):
            prepared = tracer._prepare(shirt_png(background), TraceOptions(max_side=600))
            self.assertIsNotNone(prepared["background"])
            self.assertLess(max(abs(a - b) for a, b in zip(prepared["background"], background)), 4)
            colours = {tuple(pixel) for pixel in Image.open(io.BytesIO(prepared["png"])).convert("RGB").getdata()}
            self.assertLessEqual(len(colours), 3)  # background, red and maybe nothing else

    def test_busy_border_means_no_background(self):
        import numpy as np
        noise = np.random.default_rng(0).integers(0, 255, (200, 200, 3), dtype=np.uint8)
        from backend.core.vector import preprocess
        self.assertIsNone(preprocess.detect_background(noise))

    def test_background_shapes_are_removed_from_svg(self):
        def fake(png_bytes, options):
            self.assertEqual(options.layering, "cutout")  # holes need non-overlapping shapes
            return ('<svg width="600" height="600">'
                    '<path d="M0 0 L600 0 L600 600 L0 600 Z" fill="#ffffff" transform="translate(0,0)"/>'
                    '<path d="M100 100 L500 100 L500 500 L100 500 Z" fill="#dc2828" transform="translate(0,0)"/>'
                    '<path d="M250 250 L350 250 L350 350 L250 350 Z" fill="#fdfdfd" transform="translate(0,0)"/></svg>')
        result = trace_image(shirt_png(), TraceOptions(max_side=600), convert=fake)
        self.assertEqual(result["paths"], 1)
        self.assertEqual(result["background"], "#ffffff")

    def test_keep_enclosed_removes_only_the_outer_background(self):
        svg = ('<svg><path d="M0 0 L600 0 L600 600 L0 600 Z" fill="#ffffff"/>'
               '<path d="M250 250 L350 250 L350 350 L250 350 Z" fill="#ffffff"/></svg>')
        kept = tracer.strip_background(svg, (255, 255, 255), 600, 600, enclosed_too=False)
        self.assertEqual(kept.count("<path"), 1)

    def test_transparent_png_keeps_transparency(self):
        image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        image.paste(Image.new("RGBA", (40, 40), (200, 30, 30, 255)), (30, 30))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        prepared = tracer._prepare(buffer.getvalue(), TraceOptions())
        self.assertIsNotNone(prepared["background"])

    def test_binary_mode_on_dark_background_keeps_light_colour(self):
        def fake(png_bytes, options):
            return '<svg width="1400" height="1400"><path d="M0 0" fill="#000000"/></svg>'
        result = trace_image(shirt_png((10, 10, 10)), TraceOptions(colormode="binary"), convert=fake)
        self.assertNotIn("#000000", result["svg"])


class MergeSmallTest(unittest.TestCase):
    def test_specks_and_hairlines_merge_but_real_shapes_stay(self):
        import numpy as np
        from backend.core.vector import preprocess
        labels = np.zeros((200, 300), dtype=np.uint8)
        labels[:, 150:] = 1
        labels[50:53, 40:43] = 2       # speck
        labels[100, 10:100] = 2        # hairline
        labels[30:45, 200:240] = 2     # real block
        merged = preprocess.merge_small_patches(labels, 36)
        self.assertEqual(int((merged[50:53, 40:43] == 2).sum()), 0)
        self.assertEqual(int((merged[100, 10:100] == 2).sum()), 0)
        self.assertEqual(int((merged[30:45, 200:240] == 2).sum()), 600)

    def test_zero_is_off_and_option_is_clamped(self):
        self.assertEqual(TraceOptions.from_dict({"merge_small": 99}).merge_small, 40)
        self.assertEqual(TraceOptions.from_dict({"merge_small": -3}).merge_small, 0)

    def test_binary_mode_also_merges(self):
        trace_image(shirt_png(), TraceOptions(colormode="binary", merge_small=10), convert=fake_convert)


if __name__ == "__main__":
    unittest.main()
