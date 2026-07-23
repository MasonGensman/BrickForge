"""
StudWorks Scene Serialization Schema

Defines the on-disk JSON shape for a serialized Scene, and the one
error type deserialize_scene() raises for any structural problem.
Shared by both serializer.py and deserializer.py so the two stay in
sync by construction rather than by convention.

Format (schema_version 1):

{
    "format": "StudWorks Scene",
    "schema_version": 1,
    "bricks": [
        {
            "id": 0,
            "part_name": "3005.dat",
            "position": [x, y, z],
            "rotation": [x, y, z, w],
            "color_code": 4  // or null
        },
        ...
    ]
}

"format" is checked before "schema_version" (Package_025 revision) so
an unrelated JSON file -- not a StudWorks Scene at all -- is rejected
with a clear, specific error rather than a confusing "unknown schema
version" message.

"id" is included (Package_025 revision): a serialized Scene preserves
the complete identity of every SceneBrick, not merely its visible
geometry -- stable ids matter for future editing features (e.g.
Scene.remove_brick already keys off id).

"rotation" is the SceneBrick.rotation quaternion's native [x, y, z, w]
components directly -- not LDraw's 3x3 matrix (that conversion is
Package_024 exporter's concern, not this format's). Serialization
consumes and produces only Scene objects; it has no dependency on
PartCatalog, and part_name is stored as an opaque reference string,
exactly as SceneBrick already treats it -- never resolved or validated
against a catalog here.
"""

import glm

FORMAT_IDENTIFIER = "StudWorks Scene"
SCHEMA_VERSION = 1


class SceneSerializationError(Exception):
    """
    Raised for any structural or content problem in serialized Scene
    data: not the expected format, an unsupported schema version, a
    missing/malformed field, or a non-finite numeric value. Never
    raised for I/O failures -- those propagate as OSError, unwrapped,
    matching Package_024's exporter.
    """


def vec3_to_list(vector: glm.vec3) -> list[float]:

    return [vector.x, vector.y, vector.z]


def list_to_vec3(values: list[float]) -> glm.vec3:

    return glm.vec3(values[0], values[1], values[2])


def quat_to_list(rotation: glm.quat) -> list[float]:

    return [rotation.x, rotation.y, rotation.z, rotation.w]


def list_to_quat(values: list[float]) -> glm.quat:
    """
    glm.quat's constructor takes (w, x, y, z) -- verified empirically
    against glm.angleAxis() during Package_025 planning, since this is
    exactly the kind of convention that's easy to get backwards
    silently. `values` here is [x, y, z, w] (this schema's own storage
    order), so the w component (values[3]) comes first.
    """

    return glm.quat(values[3], values[0], values[1], values[2])
