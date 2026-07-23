"""
StudWorks Scene Deserializer

deserialize_scene() is the one public entry point: reconstruct a Scene
from a JSON file previously written by serialize_scene() (schema.py).

Validates structure strictly and raises SceneSerializationError for
any problem -- never silently repairs or partially deserializes
invalid data. Raw I/O failures (file not found, permission denied)
propagate as OSError, unwrapped, matching Package_024's exporter.
"""

import json
import math
from pathlib import Path

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.serialization.schema import (
    FORMAT_IDENTIFIER,
    SCHEMA_VERSION,
    SceneSerializationError,
    list_to_quat,
    list_to_vec3,
)

_REQUIRED_BRICK_FIELDS = (
    "id", "part_name", "position", "rotation", "color_code",
)


def _is_int(value) -> bool:
    """
    True int, not bool -- bool is a subclass of int in Python, so a
    plain isinstance(value, int) check would silently accept JSON
    true/false as a valid id or color_code.
    """

    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    """Same bool-exclusion concern as _is_int, for float-or-int fields."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def _require_finite_numbers(values, label: str) -> None:

    for value in values:

        if not _is_number(value):

            raise SceneSerializationError(
                f"{label} contains a non-numeric value: {value!r}"
            )

        if math.isnan(value) or math.isinf(value):

            raise SceneSerializationError(
                f"{label} contains a non-finite value: {value!r}"
            )


def deserialize_scene(path: str | Path) -> Scene:
    """
    Reconstruct a Scene from path. Raises SceneSerializationError for
    any structural or content problem; raises OSError (unwrapped) if
    the file can't be read.
    """

    path = Path(path)

    with path.open("r", encoding="utf-8") as file:

        try:
            document = json.load(file)

        except json.JSONDecodeError as error:

            raise SceneSerializationError(
                f"{path} is not valid JSON: {error}"
            ) from error

    if not isinstance(document, dict):

        raise SceneSerializationError(
            f"{path} does not contain a StudWorks Scene document "
            f"(expected a JSON object at the top level)."
        )

    #
    # "format" is checked before "schema_version" so an unrelated JSON
    # file is rejected with a clear, specific error rather than a
    # confusing "unknown schema version" message.
    #
    file_format = document.get("format")

    if file_format != FORMAT_IDENTIFIER:

        raise SceneSerializationError(
            f'{path} is not a StudWorks Scene file (expected '
            f'"format": {FORMAT_IDENTIFIER!r}, found {file_format!r}).'
        )

    schema_version = document.get("schema_version")

    if schema_version != SCHEMA_VERSION:

        raise SceneSerializationError(
            f"{path} has unsupported schema_version {schema_version!r} "
            f"(this version of StudWorks supports schema_version "
            f"{SCHEMA_VERSION})."
        )

    if "bricks" not in document:

        raise SceneSerializationError(
            f'{path} is missing the required "bricks" field.'
        )

    bricks_data = document["bricks"]

    if not isinstance(bricks_data, list):

        raise SceneSerializationError(
            f'{path}\'s "bricks" field must be a list.'
        )

    scene = Scene()

    for index, brick_data in enumerate(bricks_data):

        if not isinstance(brick_data, dict):

            raise SceneSerializationError(
                f"{path}: brick at index {index} is not a JSON object."
            )

        for required_field in _REQUIRED_BRICK_FIELDS:

            if required_field not in brick_data:

                raise SceneSerializationError(
                    f"{path}: brick at index {index} is missing the "
                    f"required field {required_field!r}."
                )

        brick_id = brick_data["id"]

        if not _is_int(brick_id):

            raise SceneSerializationError(
                f"{path}: brick at index {index} has a non-integer "
                f"id: {brick_id!r}."
            )

        part_name = brick_data["part_name"]

        if not isinstance(part_name, str) or not part_name:

            raise SceneSerializationError(
                f"{path}: brick at index {index} has an invalid "
                f"part_name: {part_name!r}."
            )

        position = brick_data["position"]

        if not isinstance(position, list) or len(position) != 3:

            raise SceneSerializationError(
                f"{path}: brick at index {index} has an invalid "
                f"position (expected a 3-element list): {position!r}."
            )

        _require_finite_numbers(
            position,
            f"{path}: brick at index {index}'s position",
        )

        rotation = brick_data["rotation"]

        if not isinstance(rotation, list) or len(rotation) != 4:

            raise SceneSerializationError(
                f"{path}: brick at index {index} has an invalid "
                f"rotation (expected a 4-element list): {rotation!r}."
            )

        _require_finite_numbers(
            rotation,
            f"{path}: brick at index {index}'s rotation",
        )

        color_code = brick_data["color_code"]

        if color_code is not None and not _is_int(color_code):

            raise SceneSerializationError(
                f"{path}: brick at index {index} has an invalid "
                f"color_code (expected an integer or null): "
                f"{color_code!r}."
            )

        scene.add_brick(
            SceneBrick(
                id=brick_id,
                part_name=part_name,
                position=list_to_vec3(position),
                rotation=list_to_quat(rotation),
                color_code=color_code,
            )
        )

    return scene
