"""
BrickForge Shader
"""

from pathlib import Path

from OpenGL.GL import (
    GL_COMPILE_STATUS,
    GL_FRAGMENT_SHADER,
    GL_LINK_STATUS,
    GL_VERTEX_SHADER,
    glAttachShader,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteShader,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glLinkProgram,
    glShaderSource,
    glUseProgram,
)


class Shader:
    """GLSL shader program."""

    def __init__(self, vertex_file: str, fragment_file: str):

        self.program = glCreateProgram()

        vertex_source = Path(vertex_file).read_text(encoding="utf-8")
        fragment_source = Path(fragment_file).read_text(encoding="utf-8")

        vertex_shader = self._compile(
            GL_VERTEX_SHADER,
            vertex_source,
        )

        fragment_shader = self._compile(
            GL_FRAGMENT_SHADER,
            fragment_source,
        )

        glAttachShader(self.program, vertex_shader)
        glAttachShader(self.program, fragment_shader)

        glLinkProgram(self.program)

        if not glGetProgramiv(self.program, GL_LINK_STATUS):
            raise RuntimeError(
                glGetProgramInfoLog(self.program).decode()
            )

        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

    def use(self):
        glUseProgram(self.program)

    @staticmethod
    def _compile(shader_type, source):

        shader = glCreateShader(shader_type)

        glShaderSource(shader, source)

        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            raise RuntimeError(
                glGetShaderInfoLog(shader).decode()
            )

        return shader