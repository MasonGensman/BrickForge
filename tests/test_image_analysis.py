"""
StudWorks Image Analysis Tests (Package_034, extended in Package_035)

Pure unit tests for image_analysis.rotate90() (Package_034) and
sobel_edges()/dominant_colors()/occupied_bounds()/analyze_image()
(Package_035) -- crop()/resize()/to_grayscale()/etc. predate both
packages and aren't touched by either; this file covers only the new
primitives, plus analyze_image() as the orchestrator that assembles
them all into one ImageAnalysisResult.
"""

import unittest

import numpy as np

from brickforge.analysis.image_analysis import (
    ImageAnalysisResult,
    analyze_image,
    dominant_colors,
    occupied_bounds,
    rotate90,
    sobel_edges,
)
from brickforge.io.image_resource import ImageResource


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


def _vertical_boundary_pattern():
    """6x6 RGBA: left half luminance-black, right half luminance-white,
    opaque throughout. A sharp vertical edge at the column-2/3 seam and
    nowhere else."""

    pixels = np.zeros((6, 6, 4), dtype=np.uint8)
    pixels[:, 3:, 0] = 255
    pixels[:, :, 3] = 255

    return pixels


def _four_color_pattern():
    """4x4 RGBA in quadrants: red, green, blue (each opaque), and a
    fully-transparent quadrant that must be excluded from color/bounds
    analysis."""

    pixels = np.zeros((4, 4, 4), dtype=np.uint8)
    pixels[0:2, 0:2] = [200, 10, 10, 255]
    pixels[0:2, 2:4] = [10, 200, 10, 255]
    pixels[2:4, 0:2] = [10, 10, 200, 255]
    pixels[2:4, 2:4] = [0, 0, 0, 0]

    return pixels


class SobelEdgesTests(unittest.TestCase):

    def test_detects_a_known_vertical_boundary(self):

        pixels = _vertical_boundary_pattern()
        edges = sobel_edges(pixels)

        for row in range(6):
            self.assertGreater(edges[row, 2], 0)
            self.assertGreater(edges[row, 3], 0)

    def test_zero_away_from_any_boundary(self):

        pixels = _vertical_boundary_pattern()
        edges = sobel_edges(pixels)

        for row in range(6):
            self.assertEqual(edges[row, 0], 0)
            self.assertEqual(edges[row, 5], 0)

    def test_output_shape_matches_input(self):

        pixels = _vertical_boundary_pattern()
        edges = sobel_edges(pixels)

        self.assertEqual(edges.shape, pixels.shape[:2])
        self.assertEqual(edges.dtype, np.uint8)

    def test_flat_color_image_has_no_edges(self):

        pixels = np.full((5, 5, 4), 100, dtype=np.uint8)
        pixels[:, :, 3] = 255

        edges = sobel_edges(pixels)

        self.assertTrue(np.all(edges == 0))

    def test_deterministic(self):

        pixels = _vertical_boundary_pattern()

        first = sobel_edges(pixels)
        second = sobel_edges(pixels)

        self.assertTrue(np.array_equal(first, second))


class DominantColorsTests(unittest.TestCase):

    def test_returns_the_three_opaque_quadrant_colors(self):

        pixels = _four_color_pattern()
        result = dominant_colors(pixels)

        self.assertEqual(len(result), 3)
        self.assertIn((192, 0, 0), result)
        self.assertIn((0, 192, 0), result)
        self.assertIn((0, 0, 192), result)

    def test_fully_transparent_pixels_are_excluded(self):
        """The transparent quadrant's (0,0,0) must not appear -- if it
        did, it would tie for most-frequent alongside the other three."""

        pixels = _four_color_pattern()
        result = dominant_colors(pixels)

        self.assertNotIn((0, 0, 0), result)

    def test_respects_the_count_parameter(self):

        pixels = _four_color_pattern()
        result = dominant_colors(pixels, count=2)

        self.assertEqual(len(result), 2)

    def test_fully_transparent_image_returns_empty_list(self):

        pixels = np.zeros((4, 4, 4), dtype=np.uint8)
        result = dominant_colors(pixels)

        self.assertEqual(result, [])

    def test_deterministic_ordering_across_calls(self):

        pixels = _four_color_pattern()

        first = dominant_colors(pixels)
        second = dominant_colors(pixels)

        self.assertEqual(first, second)


class OccupiedBoundsTests(unittest.TestCase):

    def test_bounds_exclude_the_transparent_quadrant(self):

        pixels = _four_color_pattern()
        bounds = occupied_bounds(pixels)

        # All three opaque quadrants occupy the full 4x4 extent except
        # the bottom-right 2x2, which is fully transparent -- so the
        # bounding box still spans the whole image because red/green/
        # blue quadrants together cover every row and column.
        self.assertEqual(bounds, (0, 0, 3, 3))

    def test_fully_transparent_image_returns_none(self):

        pixels = np.zeros((4, 4, 4), dtype=np.uint8)

        self.assertIsNone(occupied_bounds(pixels))

    def test_partial_content_gives_a_tight_box(self):

        pixels = np.zeros((6, 6, 4), dtype=np.uint8)
        pixels[2:4, 1:3, :] = [255, 255, 255, 255]

        bounds = occupied_bounds(pixels)

        self.assertEqual(bounds, (1, 2, 2, 3))

    def test_deterministic(self):

        pixels = _four_color_pattern()

        first = occupied_bounds(pixels)
        second = occupied_bounds(pixels)

        self.assertEqual(first, second)


def _make_resource(pixels: np.ndarray) -> ImageResource:

    height, width = pixels.shape[:2]

    return ImageResource(
        path="in_memory_test_fixture.png",
        width=width,
        height=height,
        format="png",
        pixels=pixels,
        content_hash="test-hash",
    )


class AnalyzeImageTests(unittest.TestCase):

    def test_assembles_all_fields(self):

        resource = _make_resource(_four_color_pattern())
        result = analyze_image(resource)

        self.assertIsInstance(result, ImageAnalysisResult)
        self.assertEqual(result.width, 4)
        self.assertEqual(result.height, 4)
        self.assertEqual(result.pixel_count, 16)
        self.assertEqual(result.aspect_ratio, 1.0)
        self.assertEqual(result.average_color.shape, (4,))
        self.assertEqual(result.histogram.shape, (4, 256))
        self.assertEqual(len(result.dominant_colors), 3)
        self.assertEqual(result.edges.shape, (4, 4))
        self.assertGreaterEqual(result.edge_density, 0.0)
        self.assertLessEqual(result.edge_density, 1.0)
        self.assertEqual(result.occupied_bounds, (0, 0, 3, 3))

    def test_luminance_stats_unchanged_by_the_rename(self):
        """Existing pre-Package_035 fields keep their original,
        already-verified behavior after the ImageStatistics ->
        ImageAnalysisResult rename."""

        pixels = np.zeros((2, 2, 4), dtype=np.uint8)
        pixels[:, :, :3] = 100
        pixels[:, :, 3] = 255

        resource = _make_resource(pixels)
        result = analyze_image(resource)

        self.assertAlmostEqual(result.mean_luminance, result.min_luminance)
        self.assertAlmostEqual(result.mean_luminance, result.max_luminance)
        self.assertEqual(result.std_luminance, 0.0)

    def test_deterministic(self):

        resource = _make_resource(_four_color_pattern())

        first = analyze_image(resource)
        second = analyze_image(resource)

        self.assertEqual(first.dominant_colors, second.dominant_colors)
        self.assertEqual(first.occupied_bounds, second.occupied_bounds)
        self.assertTrue(np.array_equal(first.edges, second.edges))
        self.assertEqual(first.edge_density, second.edge_density)


if __name__ == "__main__":
    unittest.main()
