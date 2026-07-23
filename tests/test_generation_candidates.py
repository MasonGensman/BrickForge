"""
StudWorks Generation Candidate System Tests (Package_036)

A small, hand-built fixture catalog covering every constraint axis in
isolation, plus a "placeholder metadata" part (available_colors=[],
category="Part", family=None) matching what the real, LDraw-library-
derived catalog currently produces for every non-seed part (see
services/ldraw_catalog_builder.py) -- used to verify that incomplete
metadata is excluded strictly, not silently treated as a match.
"""

import unittest

from brickforge.generation.candidates import (
    GenerationConstraints,
    candidates_for,
)
from brickforge.models.part_definition import BrickDefinition
from brickforge.services.part_catalog import PartCatalog

_TECHNIC_BRICK = BrickDefinition(
    part_number="1001",
    name="Technic Brick 1x1",
    category="Brick",
    ldraw_filename="1001.dat",
    stud_width=1,
    stud_length=1,
    height_units=24.0,
    available_colors=[4, 14],
    family="Technic",
)

_PLAIN_PLATE = BrickDefinition(
    part_number="1002",
    name="Plate 2x4",
    category="Plate",
    ldraw_filename="1002.dat",
    stud_width=2,
    stud_length=4,
    height_units=8.0,
    available_colors=[1, 2],
)

_MINIFIG_BRICK = BrickDefinition(
    part_number="1003",
    name="Minifig Brick 4x4",
    category="Brick",
    ldraw_filename="1003.dat",
    stud_width=4,
    stud_length=4,
    height_units=24.0,
    available_colors=[15],
    family="Minifig",
)

_PLACEHOLDER_PART = BrickDefinition(
    part_number="1004",
    name="Unmeasured Real Part",
    category="Part",
    ldraw_filename="1004.dat",
    stud_width=1,
    stud_length=1,
    height_units=24.0,
    available_colors=[],
)

_ALL_PARTS = [_TECHNIC_BRICK, _PLAIN_PLATE, _MINIFIG_BRICK, _PLACEHOLDER_PART]


def _build_catalog() -> PartCatalog:
    return PartCatalog(_ALL_PARTS)


def _part_numbers(definitions) -> list[str]:
    return [d.part_number for d in definitions]


class NoConstraintsTests(unittest.TestCase):

    def test_no_constraints_returns_the_full_catalog_in_order(self):

        catalog = _build_catalog()
        result = candidates_for(catalog)

        self.assertEqual(_part_numbers(result), _part_numbers(_ALL_PARTS))

    def test_default_constraints_object_is_equivalent_to_none(self):

        catalog = _build_catalog()

        self.assertEqual(
            _part_numbers(candidates_for(catalog)),
            _part_numbers(candidates_for(catalog, GenerationConstraints())),
        )


class ColorConstraintTests(unittest.TestCase):

    def test_permitted_colors_matches_by_intersection(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(permitted_colors=[4])
        )

        self.assertEqual(_part_numbers(result), ["1001"])

    def test_explicit_empty_permitted_colors_matches_nothing(self):
        """None means unconstrained; [] means constrained to nothing --
        the two must not behave the same."""

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(permitted_colors=[])
        )

        self.assertEqual(result, [])

    def test_placeholder_metadata_never_satisfies_a_color_constraint(self):
        """A part with available_colors == [] (the real catalog's
        'not yet measured' placeholder) must never match a specific
        color constraint -- strict, not permissive, per Package_036's
        constraint model recommendation."""

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(permitted_colors=[1, 2, 4, 14, 15])
        )

        self.assertNotIn("1004", _part_numbers(result))


class CategoryConstraintTests(unittest.TestCase):

    def test_permitted_categories_filters_correctly(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(permitted_categories=["Brick"])
        )

        self.assertEqual(_part_numbers(result), ["1001", "1003"])


class FamilyConstraintTests(unittest.TestCase):

    def test_permitted_families_filters_correctly(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(permitted_families=["Technic"])
        )

        self.assertEqual(_part_numbers(result), ["1001"])

    def test_unset_family_never_matches_a_family_constraint(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog,
            GenerationConstraints(permitted_families=["Technic", "Minifig"]),
        )

        self.assertNotIn("1002", _part_numbers(result))
        self.assertNotIn("1004", _part_numbers(result))


class DimensionConstraintTests(unittest.TestCase):

    def test_min_stud_width(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(min_stud_width=2)
        )

        self.assertEqual(_part_numbers(result), ["1002", "1003"])

    def test_max_stud_width(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog, GenerationConstraints(max_stud_width=1)
        )

        self.assertEqual(_part_numbers(result), ["1001", "1004"])

    def test_min_and_max_stud_length_together(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog,
            GenerationConstraints(min_stud_length=4, max_stud_length=4),
        )

        self.assertEqual(_part_numbers(result), ["1002", "1003"])


class ExclusionConstraintTests(unittest.TestCase):

    def test_excluded_part_numbers_removes_exact_matches(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog,
            GenerationConstraints(excluded_part_numbers=["1001"]),
        )

        self.assertEqual(
            _part_numbers(result), ["1002", "1003", "1004"]
        )


class CombinedConstraintTests(unittest.TestCase):

    def test_multiple_constraints_are_and_combined(self):

        catalog = _build_catalog()
        result = candidates_for(
            catalog,
            GenerationConstraints(
                permitted_categories=["Brick"], min_stud_width=2,
            ),
        )

        self.assertEqual(_part_numbers(result), ["1003"])


class DeterminismTests(unittest.TestCase):

    def test_repeated_calls_return_identical_results(self):

        catalog = _build_catalog()
        constraints = GenerationConstraints(
            permitted_categories=["Brick", "Plate"], min_stud_width=1,
        )

        first = candidates_for(catalog, constraints)
        second = candidates_for(catalog, constraints)

        self.assertEqual(_part_numbers(first), _part_numbers(second))


if __name__ == "__main__":
    unittest.main()
