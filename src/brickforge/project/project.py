"""
StudWorks Project

Represents a single StudWorks project: a named, timestamped wrapper
around a Scene (Package_026). Project.scene owns the current Scene
directly -- ProjectManager.save() operates on the current project
rather than taking a separate Scene parameter, so the only thing a
caller needs to keep correct is updating current_project.scene when
generation produces a new Scene (see MainWindow.on_generate_lego).

Project persistence is layered on top of Package_025's Scene
serialization rather than reimplementing it: to_dict()/from_dict()
embed a full "StudWorks Scene" document (via
scene_to_document()/document_to_scene(), Package_025's reusable
primitives) inside this project's own "StudWorks Project" document.
The two formats have independent format/schema_version identifiers,
so either can evolve without the other changing.

Package_034 adds generation_input: a Project's reference to the
source image (if any) it was built from. Only the reference --
source_path, content_hash, and ImagePreparationSettings -- is
persisted, never the prepared or original pixel data (keeps the .sws
JSON small and diffable, per Package_025's own reasoning).
prepared_image is regenerated on load via GenerationInput.from_source(),
which is safe because prepare_image() is already deterministic. If
the source file has moved or been deleted since the project was
saved, from_dict() degrades gracefully -- generation_input becomes
None and a warning is logged, rather than blocking the whole project
load, matching this codebase's established "one non-critical
subsystem's failure shouldn't take down the rest of the app" pattern
(BrickManager, ColorResolver).

Package_036 adds generation_constraints: a Project's own
GenerationConstraints (generation/candidates.py), describing which
catalog parts a future generation pass is permitted to use. Unlike
generation_input, this is stored verbatim, not regenerated -- it is
plain user intent (permitted colors/categories/sizes), not derived
from anything, so there is nothing to recompute on load and no
external file it could go missing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from brickforge._version import APP_VERSION
from brickforge.engine.scene import Scene
from brickforge.generation.candidates import GenerationConstraints
from brickforge.preparation.generation_input import GenerationInput
from brickforge.preparation.image_preparation import ImagePreparationSettings
from brickforge.serialization.deserializer import document_to_scene
from brickforge.serialization.serializer import scene_to_document

logger = logging.getLogger(__name__)

PROJECT_FORMAT_IDENTIFIER = "StudWorks Project"
PROJECT_SCHEMA_VERSION = 1


class ProjectFileError(Exception):
    """
    Raised for any structural or content problem in a project file
    itself: not the expected format, an unsupported schema version, or
    a missing required field. Never raised for a problem in the
    embedded Scene data -- that's SceneSerializationError's job
    (Package_025's document_to_scene()), left uncaught here so callers
    can tell which layer actually failed. Also never raised for a
    missing/unreadable generation_input source image -- that degrades
    gracefully instead (see from_dict()).
    """


def _generation_input_to_dict(
    generation_input: GenerationInput,
) -> dict[str, Any]:

    return {
        "source_path": str(generation_input.source_path),
        "content_hash": generation_input.content_hash,
        "settings": {
            "max_dimension": generation_input.settings.max_dimension,
            "crop_rect": (
                list(generation_input.settings.crop_rect)
                if generation_input.settings.crop_rect is not None
                else None
            ),
            "rotation_degrees": generation_input.settings.rotation_degrees,
        },
    }


def _generation_input_from_dict(
    data: dict[str, Any],
) -> GenerationInput | None:

    source_path = data.get("source_path")

    if source_path is None:
        return None

    settings_data = data.get("settings", {})

    crop_rect = settings_data.get("crop_rect")

    settings = ImagePreparationSettings(
        max_dimension=settings_data.get("max_dimension", 48),
        crop_rect=tuple(crop_rect) if crop_rect is not None else None,
        rotation_degrees=settings_data.get("rotation_degrees", 0),
    )

    try:

        return GenerationInput.from_source(source_path, settings)

    except (OSError, ValueError) as error:

        logger.warning(
            "Project's generation_input source image could not be "
            "reloaded, continuing without it: %s",
            error,
        )

        return None


def _generation_constraints_to_dict(
    constraints: GenerationConstraints,
) -> dict[str, Any]:

    return {
        "permitted_colors": constraints.permitted_colors,
        "permitted_categories": constraints.permitted_categories,
        "permitted_families": constraints.permitted_families,
        "min_stud_width": constraints.min_stud_width,
        "max_stud_width": constraints.max_stud_width,
        "min_stud_length": constraints.min_stud_length,
        "max_stud_length": constraints.max_stud_length,
        "excluded_part_numbers": constraints.excluded_part_numbers,
    }


def _generation_constraints_from_dict(
    data: dict[str, Any],
) -> GenerationConstraints:

    return GenerationConstraints(
        permitted_colors=data.get("permitted_colors"),
        permitted_categories=data.get("permitted_categories"),
        permitted_families=data.get("permitted_families"),
        min_stud_width=data.get("min_stud_width"),
        max_stud_width=data.get("max_stud_width"),
        min_stud_length=data.get("min_stud_length"),
        max_stud_length=data.get("max_stud_length"),
        excluded_part_numbers=data.get("excluded_part_numbers", []),
    )


@dataclass
class Project:
    """Represents a StudWorks project: metadata plus its Scene."""

    name: str = "Untitled Project"
    file_path: Path | None = None

    scene: Scene = field(default_factory=Scene)

    generation_input: GenerationInput | None = None
    generation_constraints: GenerationConstraints | None = None

    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)

    dirty: bool = False

    app_version: str = field(default_factory=lambda: APP_VERSION)

    def mark_dirty(self) -> None:
        """Mark the project as modified."""
        self.dirty = True
        self.modified = datetime.now()

    def mark_saved(self) -> None:
        """Mark the project as saved."""
        self.dirty = False
        self.modified = datetime.now()

    @property
    def filename(self) -> str:
        """Return the project filename."""
        if self.file_path is None:
            return f"{self.name}.sws"

        return self.file_path.name

    def to_dict(self) -> dict[str, Any]:
        """Convert project (including its Scene) to a JSON-serializable dictionary."""

        data = {
            "format": PROJECT_FORMAT_IDENTIFIER,
            "schema_version": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
            "app_version": self.app_version,
            "scene": scene_to_document(self.scene),
        }

        if self.generation_input is not None:

            data["generation_input"] = _generation_input_to_dict(
                self.generation_input
            )

        if self.generation_constraints is not None:

            data["generation_constraints"] = (
                _generation_constraints_to_dict(
                    self.generation_constraints
                )
            )

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        """
        Create a Project (including its Scene) from a dictionary.

        Raises ProjectFileError for any problem with the project
        document itself (wrong format, unsupported schema version,
        missing required fields). Raises SceneSerializationError
        (uncaught, propagated as-is) if the embedded scene data is
        invalid -- validated entirely by Package_025's
        document_to_scene(), not re-implemented here.
        """

        if not isinstance(data, dict):

            raise ProjectFileError(
                "Project data is not a JSON object."
            )

        file_format = data.get("format")

        if file_format != PROJECT_FORMAT_IDENTIFIER:

            raise ProjectFileError(
                f'Not a StudWorks Project file (expected "format": '
                f'{PROJECT_FORMAT_IDENTIFIER!r}, found {file_format!r}).'
            )

        schema_version = data.get("schema_version")

        if schema_version != PROJECT_SCHEMA_VERSION:

            raise ProjectFileError(
                f"Unsupported project schema_version {schema_version!r} "
                f"(this version of StudWorks supports schema_version "
                f"{PROJECT_SCHEMA_VERSION})."
            )

        if "scene" not in data:

            raise ProjectFileError(
                'Project data is missing the required "scene" field.'
            )

        generation_input = None

        if "generation_input" in data:
            generation_input = _generation_input_from_dict(
                data["generation_input"]
            )

        generation_constraints = None

        if "generation_constraints" in data:
            generation_constraints = _generation_constraints_from_dict(
                data["generation_constraints"]
            )

        project = cls(
            name=data.get("name", "Untitled Project"),
            app_version=data.get("app_version", APP_VERSION),
            scene=document_to_scene(data["scene"]),
            generation_input=generation_input,
            generation_constraints=generation_constraints,
        )

        if "created" in data:
            project.created = datetime.fromisoformat(data["created"])

        if "modified" in data:
            project.modified = datetime.fromisoformat(data["modified"])

        return project
