"""
StudWorks Image Preparation Tests (Package_018, extended in Package_034)

Pure unit tests for prepare_image()/ImagePreparationSettings -- no Qt,
no file I/O, no OpenGL. Verifies the crop -> rotate -> resize pipeline
and its determinism/immutability contracts directly.
"""

import unittest
from pathlib import Path

import numpy as np

from brickforge.io.image_resource import ImageResource
from brickforge.preparation.image_preparation import (
    ImagePreparationSettings,
    prepare_image,
)


def _image(width=20, height=10, content_hash="abc123"):

    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    pixels[:, :, 3] = 255

    return ImageResource(
        path=Path("source.png"),
        width=width,
        height=height,
        format="PNG",
        pixels=pixels,
        content_hash=content_hash,
    )


class NoOpTests(unittest.TestCase):

    def test_true_no_op_returns_the_same_object(self):
        """Already within bounds, no crop, no rotation -- Package_018's
        original guarantee, unaffected by Package_034's additions."""

        image = _image(width=10, height=5)

        result = prepare_image(image, ImagePreparationSettings(max_dimension=48))

        self.assertIs(result, image)

    def test_existing_resize_only_behavior_is_unchanged(self):

        image = _image(width=100, height=50)

        result = prepare_image(image, ImagePreparationSettings(max_dimension=10))

        self.assertEqual(result.width, 10)
        self.assertEqual(result.height, 5)


class CropTests(unittest.TestCase):

    def test_crop_only_produces_correct_dimensions(self):

        image = _image(width=20, height=10)

        result = prepare_image(
            image,
            ImagePreparationSettings(max_dimension=48, crop_rect=(2, 3, 8, 4)),
        )

        self.assertIsNot(result, image)
        self.assertEqual(result.width, 8)
        self.assertEqual(result.height, 4)

    def test_crop_extracts_the_correct_region(self):

        image = _image(width=6, height=4)
        image.pixels[1, 2] = [9, 9, 9, 255]  # a marker inside the crop region

        result = prepare_image(
            image,
            ImagePreparationSettings(max_dimension=48, crop_rect=(1, 0, 4, 3)),
        )

        # Marker was at (row=1, col=2) in the source; crop starts at
        # x=1, so it should now be at col=1 in the cropped result.
        self.assertEqual(list(result.pixels[1, 1]), [9, 9, 9, 255])


class RotateTests(unittest.TestCase):

    def test_rotate_90_swaps_dimensions(self):

        image = _image(width=20, height=10)

        result = prepare_image(
            image,
            ImagePreparationSettings(max_dimension=48, rotation_degrees=90),
        )

        self.assertEqual(result.width, 10)
        self.assertEqual(result.height, 20)

    def test_rotate_180_preserves_dimensions(self):

        image = _image(width=20, height=10)

        result = prepare_image(
            image,
            ImagePreparationSettings(max_dimension=48, rotation_degrees=180),
        )

        self.assertEqual(result.width, 20)
        self.assertEqual(result.height, 10)


class CombinedPipelineTests(unittest.TestCase):

    def test_crop_then_rotate_then_resize(self):

        image = _image(width=20, height=10)

        result = prepare_image(
            image,
            ImagePreparationSettings(
                max_dimension=4,
                crop_rect=(0, 0, 10, 8),
                rotation_degrees=90,
            ),
        )

        # crop -> 10x8, rotate90 -> 8x10, fit to max_dimension=4 -> <=4 on both axes.
        self.assertLessEqual(result.width, 4)
        self.assertLessEqual(result.height, 4)

    def test_content_hash_always_preserved_from_source(self):
        """content_hash identifies the source FILE, never the prepared
        pixels -- must survive every stage unchanged."""

        image = _image(content_hash="deadbeef")

        result = prepare_image(
            image,
            ImagePreparationSettings(
                max_dimension=4, crop_rect=(0, 0, 10, 8), rotation_degrees=90,
            ),
        )

        self.assertEqual(result.content_hash, "deadbeef")

    def test_original_image_pixels_never_mutated(self):

        image = _image(width=20, height=10)
        original_pixels = image.pixels.copy()

        prepare_image(
            image,
            ImagePreparationSettings(
                max_dimension=4, crop_rect=(0, 0, 10, 8), rotation_degrees=90,
            ),
        )

        self.assertTrue(np.array_equal(image.pixels, original_pixels))

    def test_deterministic(self):

        def run():
            image = _image(width=20, height=10)
            result = prepare_image(
                image,
                ImagePreparationSettings(
                    max_dimension=4, crop_rect=(0, 0, 10, 8), rotation_degrees=90,
                ),
            )
            return result.width, result.height, result.pixels.tobytes()

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
