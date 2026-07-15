"""
BrickForge Flat Mosaic Mode Registration

Registers the existing, unmodified generate_mosaic() as the first
GenerationMode. Does not change generate_mosaic()/GenerationSettings/
OriginMode's behavior, name, or location in mosaic_generator.py -- this
module only describes and wraps them for the registry.

FlatMosaicSettingsPanel intentionally reproduces the same three controls
ImagePreviewWidget already builds inline (Package_014), as a standalone,
independently constructible unit. ImagePreviewWidget itself is untouched
by this package -- nothing calls this factory yet; it exists so a future
package can swap the widget's hardcoded controls for
registry.get_mode("flat_mosaic").create_settings_panel() without
reworking this file.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from brickforge.generation.generation_mode import GenerationMode
from brickforge.generation.mosaic_generator import (
    GenerationSettings,
    OriginMode,
    generate_mosaic,
)
from brickforge.generation.registry import register_mode
from brickforge.services.part_catalog import PartCatalog


class FlatMosaicSettingsPanel:
    """SettingsPanel implementation for the Flat Mosaic mode."""

    def __init__(self):

        self._widget = QWidget()

        layout = QVBoxLayout(self._widget)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Part:"))

        self._part_combo = QComboBox()

        for definition in PartCatalog.from_seed().all():
            self._part_combo.addItem(
                definition.name,
                definition.part_number,
            )

        default_index = self._part_combo.findData("3005")

        if default_index != -1:
            self._part_combo.setCurrentIndex(default_index)

        layout.addWidget(self._part_combo)

        layout.addWidget(QLabel("Transparency:"))

        self._skip_transparent_checkbox = QCheckBox(
            "Skip Transparent Pixels"
        )
        self._skip_transparent_checkbox.setChecked(True)

        layout.addWidget(self._skip_transparent_checkbox)

        layout.addWidget(QLabel("Origin:"))

        self._origin_combo = QComboBox()
        self._origin_combo.addItem("Centered", OriginMode.CENTERED)
        self._origin_combo.addItem("Corner", OriginMode.CORNER)

        layout.addWidget(self._origin_combo)

    @property
    def widget(self) -> QWidget:

        return self._widget

    def get_settings(self) -> GenerationSettings:

        return GenerationSettings(
            default_part_number=self._part_combo.currentData(),
            skip_transparent_pixels=(
                self._skip_transparent_checkbox.isChecked()
            ),
            origin_mode=self._origin_combo.currentData(),
        )


register_mode(
    GenerationMode(
        id="flat_mosaic",
        display_name="Flat Mosaic",
        description=(
            "Converts an image into a flat, one-brick-per-pixel LEGO "
            "mosaic using a single fixed part and mapped LEGO colors."
        ),
        version=1,
        create_settings_panel=FlatMosaicSettingsPanel,
        generate=generate_mosaic,
    )
)
