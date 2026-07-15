"""
BrickForge Image Preview Widget

Minimal user-visible confirmation that image loading works: an Import
button, a thumbnail, and basic info (dimensions, format, source hash). No
OpenGL texture, no renderer involvement -- self-contained, owns its own
ImageManager.

Also hosts Generation Mode selection (Package_017): a mode dropdown
populated entirely from the GenerationMode registry, whichever settings
panel the selected mode provides, and a Generate button. This widget has
no hardcoded knowledge of any specific mode -- only of the
GenerationMode/SettingsPanel contract. It emits generate_requested for
MainWindow to act on, matching how BrickLibraryWidget's brick_selected
signal is already handled.

Runs every imported image through the shared Image Preparation stage
(Package_018) once, immediately after import. The resulting prepared
ImageResource is the single object used for both the thumbnail and
generation -- the preview always shows exactly what the selected mode
will receive, by construction rather than by two call sites happening
to agree.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brickforge.generation.generation_mode import GenerationMode
from brickforge.generation.registry import list_modes
from brickforge.io.image_manager import ImageManager
from brickforge.io.image_resource import ImageResource
from brickforge.preparation.image_preparation import prepare_image


class ImagePreviewWidget(QDockWidget):
    """Import an image, select a generation mode, and request generation."""

    generate_requested = Signal(object, object, object)

    def __init__(self, parent=None):
        super().__init__("Image Preview", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )

        self.manager = ImageManager()

        self._prepared_image: ImageResource | None = None

        self._current_mode: GenerationMode | None = None
        self._current_panel = None

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.import_button = QPushButton("Import Image...")

        self.mode_label = QLabel("Generation Mode:")
        self.mode_combo = QComboBox()

        for mode in list_modes():
            self.mode_combo.addItem(mode.display_name, mode)

        settings_separator_top = QFrame()
        settings_separator_top.setFrameShape(QFrame.HLine)
        settings_separator_top.setFrameShadow(QFrame.Sunken)

        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        self.settings_layout.setContentsMargins(0, 0, 0, 0)

        settings_separator_bottom = QFrame()
        settings_separator_bottom.setFrameShape(QFrame.HLine)
        settings_separator_bottom.setFrameShadow(QFrame.Sunken)

        self.generate_button = QPushButton("Generate LEGO")

        preview_separator = QFrame()
        preview_separator.setFrameShape(QFrame.HLine)
        preview_separator.setFrameShadow(QFrame.Sunken)

        self.thumbnail = QLabel()
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setMinimumHeight(160)
        self.thumbnail.setStyleSheet(
            "border: 1px solid palette(mid);"
        )

        self.info = QLabel("No image loaded.")
        self.info.setWordWrap(True)

        layout.addWidget(self.import_button)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.mode_combo)
        layout.addWidget(settings_separator_top)
        layout.addWidget(self.settings_container)
        layout.addWidget(settings_separator_bottom)
        layout.addWidget(self.generate_button)
        layout.addWidget(preview_separator)
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

        self.mode_combo.currentIndexChanged.connect(
            self._on_mode_changed
        )

        if self.mode_combo.count() > 0:
            self._select_mode(self.mode_combo.itemData(0))

    def _on_mode_changed(self, index):

        if index < 0:
            return

        mode = self.mode_combo.itemData(index)

        if mode is not None:
            self._select_mode(mode)

    def _select_mode(self, mode: GenerationMode):

        self._current_mode = mode
        self._current_panel = mode.create_settings_panel()

        while self.settings_layout.count():

            item = self.settings_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.settings_layout.addWidget(
            self._current_panel.widget
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

        self._prepared_image = prepare_image(resource)

        self.display(self._prepared_image)

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

        if (
            self._current_mode is None
            or self._current_panel is None
        ):

            self.info.setText(
                "No generation mode is available."
            )
            return

        settings = self._current_panel.get_settings()

        self.generate_requested.emit(
            self._prepared_image,
            self._current_mode,
            settings,
        )
