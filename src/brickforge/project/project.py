"""
BrickForge Project

Represents a single BrickForge project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Project:
    """Represents a BrickForge project."""

    name: str = "Untitled Project"
    file_path: Path | None = None

    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)

    dirty: bool = False

    version: str = "0.1.0"

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
            return f"{self.name}.bfp"

        return self.file_path.name

    def to_dict(self) -> dict[str, Any]:
        """Convert project to a JSON-serializable dictionary."""

        return {
            "version": self.version,
            "name": self.name,
            "created": self.created.isoformat(),
            "modified": self.modified.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        """Create a Project from a dictionary."""

        project = cls(
            name=data.get("name", "Untitled Project"),
            version=data.get("version", "0.1.0"),
        )

        if "created" in data:
            project.created = datetime.fromisoformat(data["created"])

        if "modified" in data:
            project.modified = datetime.fromisoformat(data["modified"])

        return project