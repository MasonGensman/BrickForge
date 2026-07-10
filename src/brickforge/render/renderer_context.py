"""
BrickForge Render Context

Owns OpenGL rendering state and validates that the
rendering system has been initialized correctly.
"""

from OpenGL.GL import (
    GL_VERSION,
    glGetString,
)


class RenderContext:
    """Owns renderer-wide OpenGL state."""

    def __init__(self):

        self.initialized = False
        self.version = None

    def initialize(self):
        """Initialize the rendering context."""

        version = glGetString(GL_VERSION)

        if version is None:
            raise RuntimeError(
                "OpenGL context is not current."
            )

        self.version = version.decode("utf-8")

        self.initialized = True

        print()
        print("=" * 50)
        print("BrickForge Render Context")
        print("=" * 50)
        print(f"OpenGL Version : {self.version}")
        print("=" * 50)
        print()

    def validate(self):
        """Ensure the render context is ready."""

        if not self.initialized:
            raise RuntimeError(
                "RenderContext has not been initialized."
            )