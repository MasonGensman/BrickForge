"""
StudWorks Picking

Pure geometry: turning a screen-space click into a world-space ray,
and testing a ray against an axis-aligned bounding box. No OpenGL
calls and no renderer state -- Renderer.pick() is the only caller,
combining these with its own live Camera/BrickManager/Scene state.
Kept separate specifically so this math is unit-testable without a
live GL context, matching how Package_024's LDraw rotation math was
verified independently of any renderer.
"""

import math

import glm


def screen_to_ray(
    screen_x: float,
    screen_y: float,
    width: int,
    height: int,
    view_matrix: glm.mat4,
    projection_matrix: glm.mat4,
) -> tuple[glm.vec3, glm.vec3]:
    """
    Convert a screen-space click (Qt convention: origin top-left, y
    grows downward) into a world-space ray (origin, normalized
    direction), by unprojecting the near and far clip-space points
    under the cursor through the inverse view-projection matrix.
    """

    ndc_x = (2.0 * screen_x / max(width, 1)) - 1.0
    ndc_y = 1.0 - (2.0 * screen_y / max(height, 1))

    inverse_view_projection = glm.inverse(
        projection_matrix * view_matrix
    )

    near = inverse_view_projection * glm.vec4(ndc_x, ndc_y, -1.0, 1.0)
    far = inverse_view_projection * glm.vec4(ndc_x, ndc_y, 1.0, 1.0)

    near = near / near.w
    far = far / far.w

    origin = glm.vec3(near)
    direction = glm.normalize(glm.vec3(far) - origin)

    return origin, direction


def ray_intersects_aabb(
    ray_origin: glm.vec3,
    ray_direction: glm.vec3,
    box_min: glm.vec3,
    box_max: glm.vec3,
) -> float | None:
    """
    Slab-method ray/AABB intersection, in whatever space box_min/
    box_max and the ray are already expressed in (Renderer.pick()
    uses this in each brick's local space). Returns the nearest
    non-negative hit distance t (ray_origin + t * ray_direction), or
    None if the ray misses or the box lies entirely behind the ray
    origin.
    """

    t_near = -math.inf
    t_far = math.inf

    for axis in range(3):

        origin = ray_origin[axis]
        direction = ray_direction[axis]
        lo = box_min[axis]
        hi = box_max[axis]

        if direction == 0.0:

            if origin < lo or origin > hi:
                return None

            continue

        t1 = (lo - origin) / direction
        t2 = (hi - origin) / direction

        if t1 > t2:
            t1, t2 = t2, t1

        t_near = max(t_near, t1)
        t_far = min(t_far, t2)

        if t_near > t_far:
            return None

    if t_far < 0.0:
        return None

    #
    # t_near is the entry point, t_far the exit point. If the ray
    # origin starts inside the box, t_near is negative and t_far is
    # the (irrelevant, further) exit distance -- the nearest point
    # along the ray that's both non-negative and inside the box is
    # the origin itself, t = 0.
    #
    return max(t_near, 0.0)
