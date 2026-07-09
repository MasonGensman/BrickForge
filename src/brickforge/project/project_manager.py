"""
BrickForge Project Manager

Handles creating, loading, and saving projects.
"""

from __future__ import annotations

import json
from pathlib import Path

from brickforge.project.project import Project


class ProjectManager:
    """Handles the active BrickForge project."""

    def __init__(self):
        self.current_project: Project | None = None

    @property
    def has_project(self) -> bool:
        return self.current_project is not None

    def new_project(self, name: str = "Untitled Project") -> Project:
        """Create a new project."""

        self.current_project = Project(name=name)

        return self.current_project

    def save(self, path: str | Path) -> None:
        """Save the current project."""

        if self.current_project is None:
            raise RuntimeError("No project is currently open.")

        path = Path(path)

        self.current_project.file_path = path

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                self.current_project.to_dict(),
                file,
                indent=4,
            )

        self.current_project.mark_saved()

    def load(self, path: str | Path) -> Project:
        """Load an existing project."""

        path = Path(path)

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        project = Project.from_dict(data)
        project.file_path = path
        project.mark_saved()

        self.current_project = project

        return project