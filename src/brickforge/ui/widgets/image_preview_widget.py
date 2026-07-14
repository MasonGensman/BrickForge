"""
BrickForge Image Preview Widget

Minimal user-visible confirmation that image loading works: an Import
button, a thumbnail, and basic info (dimensions, format, source hash). No
OpenGL texture, no renderer involvement -- self-contained, owns its own
ImageManager.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brickforge.io.image_manager import ImageManager


class ImagePreviewWidget(QDockWidget):
    """Import an image and show a thumbnail + basic info."""

    def __init__(self, parent=None):
        super().__init__("Image Preview", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )

        self.manager = ImageManager()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.import_button = QPushButton("Import Image...")

        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setMinimumHeight(160)
        self.thumbnail.setStyleSheet(
            "border: 1px solid palette(mid);"
        )

        self.info = QLabel("No image loaded.")
        self.info.setWordWrap(True)

        layout.addWidget(self.import_button)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.info)
        layout.addStretch()

        self.setWidget(container)

        self.import_button.clicked.connect(
            self.import_image
        )

    def import_image(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )

        if not path:
            return

        try:
            resource = self.manager.load(path)

        except (OSError, ValueError) as error:

            self.thumbnail.clear()
            self.info.setText(
                f"Failed to load image:\n{error}"
            )
            return

        self.display(resource)

    def display(self, resource):

        qimage = QImage(
            resource.pixels.data,
            resource.width,
            resource.height,
            resource.width * 4,
            QImage.Format_RGBA8888,
        ).copy()

        pixmap = QPixmap.fromImage(qimage).scaled(
            220,
            160,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.thumbnail.setPixmap(pixmap)

        self.info.setText(
            f"{Path(resource.path).name}\n"
            f"{resource.width} x {resource.height}  "
            f"({resource.format})\n"
            f"sha256: {resource.content_hash[:16]}..."
        )
