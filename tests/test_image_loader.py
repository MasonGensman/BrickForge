"""
StudWorks Image Loader Tests (Package_018, extended in Package_034)

The EXIF orientation tests hand-construct a minimal JPEG APP1 EXIF
segment and splice it into a Qt-written JPEG -- no Pillow needed (not
available in this environment), and no committed binary fixture
(everything is generated fresh at test time). This is the same
technique used to empirically verify the fix during planning, turned
into a permanent regression test.
"""

import struct
import tempfile
import unittest
from pathlib import Path

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from brickforge.io.image_loader import ImageLoader

_app = QApplication.instance() or QApplication([])


def _write_plain_jpeg(directory: Path, width=6, height=4) -> Path:

    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(0, 0, 0))

    path = directory / "plain.jpg"
    image.save(str(path), "JPEG", 100)

    return path


def _write_exif_tagged_jpeg(
    directory: Path,
    orientation: int,
    width=4,
    height=2,
) -> Path:
    """
    Write a width x height JPEG with a red marker pixel at (0, 0) "as
    stored", then splice in a minimal EXIF APP1 segment declaring the
    given orientation tag.
    """

    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(0, 0, 0))
    image.setPixelColor(0, 0, QColor(255, 0, 0))

    raw_path = directory / "raw.jpg"
    image.save(str(raw_path), "JPEG", 100)

    raw = raw_path.read_bytes()
    assert raw[0:2] == b"\xff\xd8"

    tiff = b"II" + struct.pack("<H", 0x2A) + struct.pack("<I", 8)
    ifd = struct.pack("<H", 1)
    ifd += struct.pack("<HHI", 0x0112, 3, 1) + struct.pack("<HH", orientation, 0)
    ifd += struct.pack("<I", 0)
    exif_payload = b"Exif\x00\x00" + tiff + ifd
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif_payload) + 2) + exif_payload

    spliced = raw[0:2] + app1 + raw[2:]

    exif_path = directory / "exif_tagged.jpg"
    exif_path.write_bytes(spliced)

    return exif_path


class BasicLoadTests(unittest.TestCase):

    def test_loads_a_plain_png_correctly(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            image = QImage(5, 3, QImage.Format_RGBA8888)
            image.setPixelColor(2, 1, QColor(10, 20, 30, 255))

            path = Path(tmp_dir) / "plain.png"
            image.save(str(path))

            resource = ImageLoader().load(path)

            self.assertEqual(resource.width, 5)
            self.assertEqual(resource.height, 3)
            self.assertEqual(list(resource.pixels[1, 2]), [10, 20, 30, 255])

    def test_missing_file_raises_file_not_found_error(self):

        with self.assertRaises(FileNotFoundError):
            ImageLoader().load("does_not_exist.png")

    def test_unsupported_extension_raises_value_error(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = Path(tmp_dir) / "file.txt"
            path.write_text("not an image")

            with self.assertRaises(ValueError):
                ImageLoader().load(path)


class ExifOrientationTests(unittest.TestCase):

    def test_plain_jpeg_with_no_exif_loads_unaffected(self):
        """A JPEG with no EXIF data at all must decode exactly as
        before -- confirms the fix doesn't disturb ordinary images."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_plain_jpeg(Path(tmp_dir), width=6, height=4)

            resource = ImageLoader().load(path)

            self.assertEqual(resource.width, 6)
            self.assertEqual(resource.height, 4)

    def test_orientation_6_rotates_90_clockwise_on_load(self):
        """Orientation=6 means 'rotate 90 clockwise to display
        correctly' -- verified against real EXIF bytes, not just that
        autoTransform is configured."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_exif_tagged_jpeg(
                Path(tmp_dir), orientation=6, width=4, height=2,
            )

            resource = ImageLoader().load(path)

            # Stored as 4 wide x 2 tall; after a 90-degree clockwise
            # correction, dimensions swap to 2 wide x 4 tall.
            self.assertEqual(resource.width, 2)
            self.assertEqual(resource.height, 4)

            # The red marker, stored at top-left, must have moved to
            # top-right after the clockwise correction.
            # JPEG is lossy -- a "black" pixel may decode a shade or
            # two off pure [0,0,0], so check "dark", not exact.
            self.assertLess(max(resource.pixels[0, 0][:3]), 10)
            self.assertGreater(resource.pixels[0, resource.width - 1][0], 200)

    def test_orientation_3_rotates_180_on_load(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = _write_exif_tagged_jpeg(
                Path(tmp_dir), orientation=3, width=4, height=2,
            )

            resource = ImageLoader().load(path)

            # 180 degrees never swaps dimensions.
            self.assertEqual(resource.width, 4)
            self.assertEqual(resource.height, 2)

            # Red marker, stored at top-left, must have moved to
            # bottom-right after a 180-degree correction.
            # JPEG is lossy -- a "black" pixel may decode a shade or
            # two off pure [0,0,0], so check "dark", not exact.
            self.assertLess(max(resource.pixels[0, 0][:3]), 10)
            self.assertGreater(resource.pixels[-1, -1][0], 200)


if __name__ == "__main__":
    unittest.main()
