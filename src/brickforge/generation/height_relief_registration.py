"""
BrickForge Height Relief Mode Registration

Registers generate_height_relief() as the second GenerationMode,
proving the registry/UI built in Packages 016-018 needs no changes to
support a mode with a genuinely different Scene shape (a variable
number of bricks per pixel at variable Y, rather than Flat Mosaic's
fixed one-brick-at-Y=0).

HeightReliefSettingsPanel is a real, standalone implementation -- not a
stub -- built the same way FlatMosaicSettingsPanel was in Package_016:
its own widget, its own layout, nothing shared with Flat Mosaic's panel
or with mosaic_generator.py.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from brickforge.generation.generation_mode import GenerationMode
from brickforge.generation.height_relief_generator import (
    HeightReliefSettings,
    generate_height_relief,
)
from brickforge.generation.registry import register_mode
from brickforge.services.part_catalog import PartCatalog


class HeightReliefSettingsPanel:
    """SettingsPanel implementation for the Height Relief mode."""

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

        default_index = self._part_combo.findData("3023")

        if default_index != -1:
            self._part_combo.setCurrentIndex(default_index)

        layout.addWidget(self._part_combo)

        layout.addWidget(QLabel("Maximum Layers:"))

        self._max_layers_spinbox = QSpinBox()
        self._max_layers_spinbox.setRange(1, 10)
        self._max_layers_spinbox.setValue(4)

        layout.addWidget(self._max_layers_spinbox)

        layout.addWidget(QLabel("Transparency:"))

        self._skip_transparent_checkbox = QCheckBox(
            "Skip Transparent Pixels"
        )
        self._skip_transparent_checkbox.setChecked(True)

        layout.addWidget(self._skip_transparent_checkbox)

    @property
    def widget(self) -> QWidget:

        return self._widget

    def get_settings(self) -> HeightReliefSettings:

        return HeightReliefSettings(
            default_part_number=self._part_combo.currentData(),
            max_layers=self._max_layers_spinbox.value(),
            skip_transparent_pixels=(
                self._skip_transparent_checkbox.isChecked()
            ),
        )


register_mode(
    GenerationMode(
        id="height_relief",
        display_name="Height Relief",
        description=(
            "Converts an image into a three-dimensional LEGO relief: "
            "each pixel becomes a vertical stack of one fixed part, "
            "quantized directly from that pixel's luminance."
        ),
        version=1,
        create_settings_panel=HeightReliefSettingsPanel,
        generate=generate_height_relief,
    )
)
