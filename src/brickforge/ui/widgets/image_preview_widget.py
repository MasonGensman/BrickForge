"""
BrickForge Image Preview Widget

Minimal user-visible confirmation that image loading works: an Import
button, a thumbnail, and basic info (dimensions, format, source hash). No
OpenGL texture, no renderer involvement -- self-contained, owns its own
ImageManager.

Also hosts the Generate LEGO Mosaic controls (Package_014): a button and
the three exposed GenerationSettings fields. This widget only verifies an
image is loaded and builds a GenerationSettings from its own controls --
it has no reference to the renderer or generation machinery itself and
emits generate_requested for MainWindow to act on, matching how
BrickLibraryWidget's brick_selected signal is already handled.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brickforge.generation.mosaic_generator import (
    GenerationSettings,
    OriginMode,
)
from brickforge.io.image_manager import ImageManager
from brickforge.services.part_catalog import PartCatalog


class ImagePreviewWidget(QDockWidget):
    """Import an image, configure mosaic settings, and request generation."""

    generate_requested = Signal(object, object)

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

        self.generate_button = QPushButton("Generate LEGO Mosaic")

        self.part_label = QLabel("Part:")
        self.part_combo = QComboBox()

        for definition in PartCatalog.from_seed().all():
            self.part_combo.addItem(
                definition.name,
                definition.part_number,
            )

        default_index = self.part_combo.findData("3005")

        if default_index != -1:
            self.part_combo.setCurrentIndex(default_index)

        self.transparency_label = QLabel("Transparency:")
        self.skip_transparent_checkbox = QCheckBox(
            "Skip Transparent Pixels"
        )
        self.skip_transparent_checkbox.setChecked(True)

        self.origin_label = QLabel("Origin:")
        self.origin_combo = QComboBox()
        self.origin_combo.addItem("Centered", OriginMode.CENTERED)
        self.origin_combo.addItem("Corner", OriginMode.CORNER)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)

        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setMinimumHeight(160)
        self.thumbnail.setStyleSheet(
            "border: 1px solid palette(mid);"
        )

        self.info = QLabel("No image loaded.")
        self.info.setWordWrap(True)

        layout.addWidget(self.import_button)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.part_label)
        layout.addWidget(self.part_combo)
        layout.addWidget(self.transparency_label)
        layout.addWidget(self.skip_transparent_checkbox)
        layout.addWidget(self.origin_label)
        layout.addWidget(self.origin_combo)
        layout.addWidget(separator)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.info)
        layout.addStretch()

        self.setWidget(container)

        self.import_button.clicked.connect(
            self.import_image
        )

        self.generate_button.clicked.connect(
            self.generate_lego
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

    def generate_lego(self):

        if not self.manager.has_image:

            self.info.setText(
                "Please import an image first."
            )
            return

        settings = GenerationSettings(
            default_part_number=self.part_combo.currentData(),
            skip_transparent_pixels=(
                self.skip_transparent_checkbox.isChecked()
            ),
            origin_mode=self.origin_combo.currentData(),
        )

        self.generate_requested.emit(
            self.manager.current_image,
            settings,
        )
