"""
BrickForge Generation Candidate System

Defines the searchable LEGO design space available to future generation
algorithms (Package_036). GenerationConstraints describes what a
generation pass is permitted to use -- colors, categories, families,
stud-size bounds, explicit exclusions. candidates_for() is the one public
query entry point: every constraint field is AND-combined, so a future
Generation Engine never needs to write its own filtering logic.

No LEGO model generation occurs here, and no specific generator is
modified -- this module only defines the query layer over the existing
PartCatalog/BrickDefinition data already used throughout generation/.

Empty-list vs. None matters: None on a list-type constraint means "not
constrained by this field"; an explicit [] means "constrained to
nothing" and matches no part. Matching is deliberately strict, not
permissive, about incomplete catalog metadata -- a part with
available_colors == [] (the real, LDraw-library-derived catalog's
placeholder for "not yet measured", see services/ldraw_catalog_builder.py)
never satisfies a permitted_colors constraint. This is an honest
reflection of a real, pre-existing metadata-completeness gap (confirmed
by inspection: build_catalog_parts() currently leaves
stud_width/stud_length/height_units/category/available_colors/family at
uniform placeholder values for every real, non-seed part), not something
this module works around silently.

Independent of engine/, render/, OpenGL, and ui/ -- depends only on
dataclasses and the existing models/part_definition.py and
services/part_catalog.py.
"""

from dataclasses import dataclass, field

from brickforge.models.part_definition import BrickDefinition
from brickforge.services.part_catalog import PartCatalog


@dataclass(slots=True)
class GenerationConstraints:
    """What a generation pass is permitted to use. Every field defaults
    to unconstrained."""

    permitted_colors: list[int] | None = None
    permitted_categories: list[str] | None = None
    permitted_families: list[str] | None = None

    min_stud_width: int | None = None
    max_stud_width: int | None = None
    min_stud_length: int | None = None
    max_stud_length: int | None = None

    excluded_part_numbers: list[str] = field(default_factory=list)


def _matches(
    definition: BrickDefinition,
    constraints: GenerationConstraints,
) -> bool:

    if constraints.permitted_colors is not None:

        if not any(
            code in definition.available_colors
            for code in constraints.permitted_colors
        ):
            return False

    if constraints.permitted_categories is not None:

        if definition.category not in constraints.permitted_categories:
            return False

    if constraints.permitted_families is not None:

        if definition.family not in constraints.permitted_families:
            return False

    if (
        constraints.min_stud_width is not None
        and definition.stud_width < constraints.min_stud_width
    ):
        return False

    if (
        constraints.max_stud_width is not None
        and definition.stud_width > constraints.max_stud_width
    ):
        return False

    if (
        constraints.min_stud_length is not None
        and definition.stud_length < constraints.min_stud_length
    ):
        return False

    if (
        constraints.max_stud_length is not None
        and definition.stud_length > constraints.max_stud_length
    ):
        return False

    if definition.part_number in constraints.excluded_part_numbers:
        return False

    return True


def candidates_for(
    catalog: PartCatalog,
    constraints: GenerationConstraints | None = None,
) -> list[BrickDefinition]:
    """
    Every catalog part satisfying every active constraint (AND-combined).
    Deterministic: preserves catalog.all()'s own order, and returns
    identical results for identical (catalog, constraints) inputs.
    constraints=None (or the all-defaults GenerationConstraints()) means
    unconstrained -- returns the full catalog.
    """

    constraints = constraints or GenerationConstraints()

    return [
        definition
        for definition in catalog.all()
        if _matches(definition, constraints)
    ]
