"""
StudWorks Image Analysis Tests (Package_034)

Pure unit tests for image_analysis.rotate90() -- crop()/resize()/
to_grayscale()/etc. predate this package and aren't touched by it;
this file covers only the new primitive.
"""

import unittest

import numpy as np

from brickforge.analysis.image_analysis import rotate90


def _asymmetric_pattern():
    """A 2-tall x 3-wide RGBA image with a distinct value per pixel in
    the R channel, so rotation direction is unambiguous."""

    pixels = np.zeros((2, 3, 4), dtype=np.uint8)
    pixels[:, :, 3] = 255

    pixels[0, 0, 0] = 1
    pixels[0, 1, 0] = 2
    pixels[0, 2, 0] = 3
    pixels[1, 0, 0] = 4
    pixels[1, 1, 0] = 5
    pixels[1, 2, 0] = 6

    return pixels


class Rotate90Tests(unittest.TestCase):

    def test_zero_degrees_returns_an_unchanged_copy(self):

        pixels = _asymmetric_pattern()
        result = rotate90(pixels, 0)

        self.assertTrue(np.array_equal(result, pixels))
        self.assertIsNot(result, pixels)

    def test_90_degrees_is_clockwise(self):
        """Top-left corner value must move to top-right after a 90
        degree clockwise rotation, swapping width/height."""

        pixels = _asymmetric_pattern()
        result = rotate90(pixels, 90)

        self.assertEqual(result.shape[:2], (3, 2))
        self.assertEqual(result[0, 1, 0], 1)  # was top-left, now top-right
        self.assertEqual(result[0, 0, 0], 4)

    def test_180_degrees(self):
        """Top-left corner value must move to bottom-right."""

        pixels = _asymmetric_pattern()
        result = rotate90(pixels, 180)

        self.assertEqual(result.shape[:2], (2, 3))
        self.assertEqual(result[1, 2, 0], 1)

    def test_270_degrees(self):
        """Top-left corner value must move to bottom-left."""

        pixels = _asymmetric_pattern()
        result = rotate90(pixels, 270)

        self.assertEqual(result.shape[:2], (3, 2))
        self.assertEqual(result[2, 0, 0], 1)

    def test_four_consecutive_90s_return_to_the_original(self):

        pixels = _asymmetric_pattern()
        result = pixels

        for _ in range(4):
            result = rotate90(result, 90)

        self.assertTrue(np.array_equal(result, pixels))

    def test_invalid_degrees_raises_value_error(self):

        pixels = _asymmetric_pattern()

        for bad_value in (45, 1, -90, 360):

            with self.subTest(degrees=bad_value):

                with self.assertRaises(ValueError):
                    rotate90(pixels, bad_value)

    def test_result_is_always_a_copy(self):

        pixels = _asymmetric_pattern()

        for degrees in (0, 90, 180, 270):

            with self.subTest(degrees=degrees):

                result = rotate90(pixels, degrees)
                self.assertIsNot(
                    result.base if result.base is not None else result,
                    pixels,
                )

    def test_deterministic(self):

        pixels = _asymmetric_pattern()

        first = rotate90(pixels, 90)
        second = rotate90(pixels, 90)

        self.assertTrue(np.array_equal(first, second))


if __name__ == "__main__":
    unittest.main()
