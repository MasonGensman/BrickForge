"""
StudWorks Generation Input Tests (Package_034)

Uses a real, freshly-written test image (via Qt -- no new dependency,
matching image_loader.py's own established approach) rather than a
mock, since GenerationInput.from_source() genuinely needs to decode a
real file. No golden-file byte comparison here: the point of these
tests is behavior (correctness, determinism, error propagation), not
pixel-exact regression tracking.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from brickforge.preparation.generation_input import GenerationInput
from brickforge.preparation.image_preparation import ImagePreparationSettings

_app = QApplication.instance() or QApplication([])


def _write_test_image(directory: Path, width=6, height=4) -> Path:

    image = QImage(width, height, QImage.Format_RGBA8888)

    for y in range(height):
        for x in range(width):
            image.setPixelColor(x, y, QColor((x * 30) % 255, (y * 40) % 255, 100, 255))

    path = directory / "test_input.png"
    image.save(str(path))

    return path


class FromSourceTests(unittest.TestCase):

    def test_builds_correctly_from_a_real_image(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_test_image(Path(tmp_dir))

            generation_input = GenerationInput.from_source(path)

            self.assertEqual(generation_input.source_path, path)
            self.assertEqual(generation_input.prepared_image.width, 6)
            self.assertEqual(generation_input.prepared_image.height, 4)
            self.assertTrue(generation_input.content_hash)

    def test_content_hash_matches_the_underlying_loader(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_test_image(Path(tmp_dir))

            from brickforge.io.image_loader import ImageLoader

            expected = ImageLoader().load(path).content_hash
            generation_input = GenerationInput.from_source(path)

            self.assertEqual(generation_input.content_hash, expected)

    def test_settings_are_applied_to_the_prepared_image(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_test_image(Path(tmp_dir), width=20, height=10)

            generation_input = GenerationInput.from_source(
                path, ImagePreparationSettings(max_dimension=5)
            )

            self.assertLessEqual(generation_input.prepared_image.width, 5)
            self.assertLessEqual(generation_input.prepared_image.height, 5)
            self.assertIs(generation_input.settings.max_dimension, 5)

    def test_default_settings_used_when_none_given(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_test_image(Path(tmp_dir))

            generation_input = GenerationInput.from_source(path)

            self.assertEqual(generation_input.settings.max_dimension, 48)
            self.assertIsNone(generation_input.settings.crop_rect)
            self.assertEqual(generation_input.settings.rotation_degrees, 0)

    def test_missing_source_raises_file_not_found_error(self):

        with self.assertRaises(FileNotFoundError):
            GenerationInput.from_source("this_file_does_not_exist.png")

    def test_unsupported_format_raises_value_error(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            bad_path = Path(tmp_dir) / "not_an_image.txt"
            bad_path.write_text("hello")

            with self.assertRaises(ValueError):
                GenerationInput.from_source(bad_path)

    def test_deterministic_across_two_separate_calls(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_test_image(Path(tmp_dir))
            settings = ImagePreparationSettings(max_dimension=3, rotation_degrees=90)

            first = GenerationInput.from_source(path, settings)
            second = GenerationInput.from_source(path, settings)

            self.assertEqual(first.content_hash, second.content_hash)
            self.assertEqual(
                (first.prepared_image.width, first.prepared_image.height),
                (second.prepared_image.width, second.prepared_image.height),
            )
            self.assertTrue(
                np.array_equal(
                    first.prepared_image.pixels, second.prepared_image.pixels
                )
            )


if __name__ == "__main__":
    unittest.main()
