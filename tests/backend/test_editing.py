"""crop and rotate: sizes, orientation and validation. run with:  python -m unittest discover tests/backend"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.core.editing.operations import apply_edit, validate_edit  # noqa: E402


def sample_image(width=8, height=6):
    # every pixel holds its own column / row so moves are easy to check
    image = np.zeros((height, width, 3), np.uint8)
    image[:, :, 0] = np.arange(width)
    image[:, :, 1] = np.arange(height)[:, None]
    return image


class RotateTests(unittest.TestCase):
    def test_clockwise_turn_moves_top_left_to_top_right(self):
        image = sample_image()
        turned = apply_edit(image, {"rotate": 90})
        self.assertEqual(turned.shape[:2], (8, 6))
        # the old top-left pixel (column 0, row 0) ends up in the top-right corner
        self.assertEqual(tuple(turned[0, -1]), tuple(image[0, 0]))
        # the old bottom-left pixel ends up in the top-left corner
        self.assertEqual(tuple(turned[0, 0]), tuple(image[-1, 0]))

    def test_180_and_270(self):
        image = sample_image()
        self.assertTrue(np.array_equal(apply_edit(image, {"rotate": 180}), image[::-1, ::-1]))
        self.assertEqual(apply_edit(image, {"rotate": 270}).shape[:2], (8, 6))
        self.assertEqual(tuple(apply_edit(image, {"rotate": 270})[-1, 0]), tuple(image[0, 0]))

    def test_four_quarter_turns_give_the_original(self):
        image = sample_image()
        result = image
        for _ in range(4):
            result = apply_edit(result, {"rotate": 90})
        self.assertTrue(np.array_equal(result, image))


class CropTests(unittest.TestCase):
    def test_crop_takes_the_exact_pixels(self):
        image = sample_image()
        cropped = apply_edit(image, {"crop": {"x": 0.25, "y": 0.5, "width": 0.5, "height": 0.5}})
        self.assertEqual(cropped.shape[:2], (3, 4))
        self.assertTrue(np.array_equal(cropped, image[3:6, 2:6]))

    def test_crop_is_applied_after_rotation(self):
        image = sample_image()                      # 8 wide, 6 tall
        edit = {"rotate": 90, "crop": {"x": 0, "y": 0, "width": 1, "height": 0.5}}
        result = apply_edit(image, edit)            # rotated image is 6 wide, 8 tall
        self.assertEqual(result.shape[:2], (4, 6))

    def test_crop_never_returns_an_empty_image(self):
        tiny = apply_edit(sample_image(), {"crop": {"x": 0.99, "y": 0.99, "width": 0.01, "height": 0.01}})
        self.assertGreaterEqual(min(tiny.shape[:2]), 1)


class ValidationTests(unittest.TestCase):
    def test_nothing_to_do_gives_none(self):
        self.assertIsNone(validate_edit(None))
        self.assertIsNone(validate_edit({"rotate": 0, "crop": None}))
        self.assertIsNone(validate_edit({"rotate": 360, "crop": {"x": 0, "y": 0, "width": 1, "height": 1}}))

    def test_rejects_bad_input(self):
        for bad in ({"rotate": 45}, {"crop": {"x": 0, "y": 0, "width": 0, "height": 1}},
                    {"crop": {"x": 0.6, "y": 0, "width": 0.6, "height": 1}}, {"crop": {"x": 0}}, "rotate"):
            with self.assertRaises(ValueError):
                validate_edit(bad)

    def test_untouched_image_is_returned_as_is(self):
        image = sample_image()
        self.assertIs(apply_edit(image, None), image)


if __name__ == "__main__":
    unittest.main()
