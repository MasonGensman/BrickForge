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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from brickforge._version import APP_VERSION
from brickforge.engine.scene import Scene
from brickforge.serialization.deserializer import document_to_scene
from brickforge.serialization.serializer import scene_to_document

PROJECT_FORMAT_IDENTIFIER = "StudWorks Project"
PROJECT_SCHEMA_VERSION = 1


class ProjectFileError(Exception):
    """
    Raised for any structural or content problem in a project file
    itself: not the expected format, an unsupported schema version, or
    a missing required field. Never raised for a problem in the
    embedded Scene data -- that's SceneSerializationError's job
    (Package_025's document_to_scene()), left uncaught here so callers
    can tell which layer actually failed.
    """


@dataclass
class Project:
    """Represents a StudWorks project: metadata plus its Scene."""

    name: str = "Untitled Project"
    file_path: Path | None = None

    scene: Scene = field(default_factory=Scene)

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

        return {
            "format": PROJECT_FORMAT_IDENTIFIER,
            "schema_version": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
            "app_version": self.app_version,
            "scene": scene_to_document(self.scene),
        }

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

        project = cls(
            name=data.get("name", "Untitled Project"),
            app_version=data.get("app_version", APP_VERSION),
            scene=document_to_scene(data["scene"]),
        )

        if "created" in data:
            project.created = datetime.fromisoformat(data["created"])

        if "modified" in data:
            project.modified = datetime.fromisoformat(data["modified"])

        return project
