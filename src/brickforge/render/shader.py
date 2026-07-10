"""
BrickForge Shader
Renderer V2
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
    glDeleteProgram,
    glDeleteShader,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetShaderiv,
    glGetUniformLocation,
    glLinkProgram,
    glShaderSource,
    glUniformMatrix4fv,
    glUseProgram,
)

import glm


class Shader:
    """Modern GLSL shader wrapper."""

    def __init__(
        self,
        vertex_file,
        fragment_file,
    ):

        self.program = glCreateProgram()

        self._uniforms = {}

        vertex_source = Path(
            vertex_file
        ).read_text(
            encoding="utf-8"
        )

        fragment_source = Path(
            fragment_file
        ).read_text(
            encoding="utf-8"
        )

        vertex_shader = self._compile(
            GL_VERTEX_SHADER,
            vertex_source,
        )

        fragment_shader = self._compile(
            GL_FRAGMENT_SHADER,
            fragment_source,
        )

        glAttachShader(
            self.program,
            vertex_shader,
        )

        glAttachShader(
            self.program,
            fragment_shader,
        )

        glLinkProgram(
            self.program,
        )

        if not glGetProgramiv(
            self.program,
            GL_LINK_STATUS,
        ):
            raise RuntimeError(
                glGetProgramInfoLog(
                    self.program
                ).decode()
            )

        glDeleteShader(
            vertex_shader
        )

        glDeleteShader(
            fragment_shader
        )

    def use(self):

        glUseProgram(
            self.program
        )

    def uniform_location(
        self,
        name: str,
    ) -> int:

        if name not in self._uniforms:

            location = glGetUniformLocation(
                self.program,
                name,
            )

            if location == -1:
                raise RuntimeError(
                    f"Uniform '{name}' not found."
                )

            self._uniforms[name] = location

        return self._uniforms[name]

    def set_matrix4(
        self,
        name,
        matrix,
    ):

        glUniformMatrix4fv(
            self.uniform_location(name),
            1,
            False,
            glm.value_ptr(matrix),
        )

    def delete(self):

        if self.program:

            glDeleteProgram(
                self.program
            )

            self.program = 0

    @staticmethod
    def _compile(
        shader_type,
        source,
    ):

        shader = glCreateShader(
            shader_type
        )

        glShaderSource(
            shader,
            source,
        )

        glCompileShader(
            shader
        )

        if not glGetShaderiv(
            shader,
            GL_COMPILE_STATUS,
        ):
            raise RuntimeError(
                glGetShaderInfoLog(
                    shader
                ).decode()
            )

        return shader