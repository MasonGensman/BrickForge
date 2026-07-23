"""
BrickForge Image Loader

Decodes PNG/JPEG/BMP files into ImageResource instances, using Qt's image
decoding (PySide6 is already the project's only formal dependency) purely
as the decode mechanism. The stored representation is a plain numpy RGBA
array, independent of Qt.

Uses QImageReader (not the QImage(path) convenience constructor) with
autoTransform enabled, so EXIF orientation is corrected automatically at
decode time -- verified empirically that QImageReader.autoTransform()
defaults to False in this Qt build, and the bare QImage(path) constructor
never applies it, meaning EXIF-rotated photos (routine from phone
cameras) previously decoded in their raw, un-rotated orientation
(Package_034). Always on, not a caller-facing option: there's no
reasonable case for wanting an EXIF-mis-rotated image on purpose.
"""

import hashlib
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage, QImageReader

from brickforge.io.image_resource import ImageResource

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


class ImageLoader:
    """Loads PNG/JPEG/BMP files into ImageResource instances."""

    def load(
        self,
        path: str | Path,
    ) -> ImageResource:
        """
        Load and decode one image file.
        """

        path = Path(path)

        if not path.exists():

            raise FileNotFoundError(
                f"Image not found:\n{path}"
            )

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:

            raise ValueError(
                f"Unsupported image format '{path.suffix}':\n{path}"
            )

        raw_bytes = path.read_bytes()

        content_hash = hashlib.sha256(
            raw_bytes
        ).hexdigest()

        reader = QImageReader(str(path))
        reader.setAutoTransform(True)

        qimage = reader.read()

        if qimage.isNull():

            raise ValueError(
                f"Failed to decode image:\n{path}\n{reader.errorString()}"
            )

        qimage = qimage.convertToFormat(
            QImage.Format_RGBA8888
        )

        width = qimage.width()
        height = qimage.height()
        stride = qimage.bytesPerLine()

        buffer = bytes(qimage.constBits())

        pixels = np.frombuffer(
            buffer,
            dtype=np.uint8,
            count=height * stride,
        ).reshape(
            height,
            stride // 4,
            4,
        )[:, :width, :].copy()

        return ImageResource(
            path=path,
            width=width,
            height=height,
            format=path.suffix.lstrip(".").upper(),
            pixels=pixels,
            content_hash=content_hash,
        )
