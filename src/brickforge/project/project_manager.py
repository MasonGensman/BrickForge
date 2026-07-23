"""
StudWorks Project Manager

Handles creating, loading, and saving StudWorks projects. Owns file
I/O and the "which file is this project" concern; delegates all
format/content validation to Project.from_dict() (project-level) and,
transitively, Package_025's document_to_scene() (scene-level).

save() operates on self.current_project directly -- the current
project owns its own Scene (Package_026 design decision), so a caller
only needs to keep current_project.scene up to date as generation
happens (see MainWindow.on_generate_lego) rather than threading a
Scene through every call site that might eventually save.
"""

from __future__ import annotations

import json
from pathlib import Path

from brickforge.project.project import Project, ProjectFileError


class ProjectManager:
    """Handles the active StudWorks project."""

    def __init__(self):
        self.current_project: Project | None = None

    @property
    def has_project(self) -> bool:
        return self.current_project is not None

    def new_project(self, name: str = "Untitled Project") -> Project:
        """Create a new project with an empty Scene."""

        self.current_project = Project(name=name)

        return self.current_project

    def save(self, path: str | Path) -> None:
        """
        Save the current project, including its Scene, to path.

        Raises RuntimeError if no project is open. Raises OSError
        (unwrapped) if the file can't be written.
        """

        if self.current_project is None:

            raise RuntimeError("No project is currently open.")

        path = Path(path)

        self.current_project.file_path = path

        with path.open("w", encoding="utf-8") as file:

            json.dump(
                self.current_project.to_dict(),
                file,
                indent=2,
            )

        self.current_project.mark_saved()

    def load(self, path: str | Path) -> Project:
        """
        Load an existing project, including its Scene, from path, and
        make it the current project.

        Raises ProjectFileError if the file isn't valid JSON or isn't
        a StudWorks Project file. Raises SceneSerializationError if
        the embedded scene data is invalid. Raises OSError (unwrapped)
        if the file can't be read.
        """

        path = Path(path)

        with path.open("r", encoding="utf-8") as file:

            try:
                data = json.load(file)

            except json.JSONDecodeError as error:

                raise ProjectFileError(
                    f"{path} is not valid JSON: {error}"
                ) from error

        try:
            project = Project.from_dict(data)

        except ProjectFileError as error:

            raise ProjectFileError(f"{path}: {error}") from error

        project.file_path = path
        project.mark_saved()

        self.current_project = project

        return project
