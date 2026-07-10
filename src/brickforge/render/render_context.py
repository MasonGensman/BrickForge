"""
BrickForge Render Context
"""

from OpenGL.GL import (
    GL_RENDERER,
    GL_VENDOR,
    GL_VERSION,
    glGetString,
)


class RenderContext:
    """Owns renderer-wide OpenGL state."""

    def __init__(self):

        self.initialized = False

        self.vendor = ""
        self.renderer = ""
        self.version = ""

    def initialize(self):

        self.vendor = (
            glGetString(GL_VENDOR)
            .decode("utf-8")
        )

        self.renderer = (
            glGetString(GL_RENDERER)
            .decode("utf-8")
        )

        self.version = (
            glGetString(GL_VERSION)
            .decode("utf-8")
        )

        self.initialized = True

        print()
        print("=" * 60)
        print(" BrickForge Renderer V2")
        print("=" * 60)
        print("Vendor   :", self.vendor)
        print("Renderer :", self.renderer)
        print("Version  :", self.version)
        print("=" * 60)
        print()

    def validate(self):

        if not self.initialized:
            raise RuntimeError(
                "RenderContext has not been initialized."
            )