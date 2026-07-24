"""
StudWorks LDraw Catalog Builder Tests (Package_037)

Unit tests for the three independent metadata-derivation helpers
(_derive_stud_footprint, _derive_height_units, _extract_category)
against hand-built BoundingBox/header fixtures -- no dependency on a
real, installed LDraw library, matching this project's established
environment-independence discipline. A separate integration test class
exercises build_catalog_parts() end-to-end against a small, synthetic,
on-disk fixture library (a handful of hand-written .dat files), proving
the orchestrator correctly combines each helper's independent result
without needing the real ~24,000-part library.
"""

import tempfile
import unittest
from pathlib import Path

from brickforge.models.part_definition import BoundingBox
from brickforge.services.ldraw_catalog_builder import (
    DEFAULT_CATEGORY,
    DEFAULT_HEIGHT_UNITS,
    DEFAULT_STUD_LENGTH,
    DEFAULT_STUD_WIDTH,
    _derive_height_units,
    _derive_stud_footprint,
    _extract_category,
    build_catalog_parts,
)


def _box(min_xyz, max_xyz) -> BoundingBox:
    return BoundingBox(min=tuple(min_xyz), max=tuple(max_xyz))


class DeriveStudFootprintTests(unittest.TestCase):

    def test_none_bounding_box_returns_none(self):

        self.assertIsNone(_derive_stud_footprint(None))

    def test_clean_1x1_footprint(self):

        box = _box((0, 0, 0), (20, 24, 20))

        self.assertEqual(_derive_stud_footprint(box), (1, 1))

    def test_clean_2x4_footprint(self):

        box = _box((0, 0, 0), (80, 24, 40))

        self.assertEqual(_derive_stud_footprint(box), (4, 2))

    def test_footprint_outside_tolerance_returns_none(self):
        """27 LDU is 1.35 studs -- too far from a whole number."""

        box = _box((0, 0, 0), (27, 24, 20))

        self.assertIsNone(_derive_stud_footprint(box))

    def test_footprint_within_tolerance_rounds(self):
        """A tiny amount of float noise (well under the tolerance)
        must still resolve to a clean integer footprint."""

        box = _box((0, 0, 0), (20.4, 24, 20))

        self.assertEqual(_derive_stud_footprint(box), (1, 1))

    def test_sub_one_stud_extent_returns_none(self):

        box = _box((0, 0, 0), (10, 24, 20))

        self.assertIsNone(_derive_stud_footprint(box))

    def test_zero_extent_returns_none(self):

        box = _box((0, 0, 0), (0, 24, 20))

        self.assertIsNone(_derive_stud_footprint(box))

    def test_does_not_depend_on_height(self):
        """A wildly irregular height must not affect the footprint
        result -- the two helpers are independent."""

        box = _box((0, 0, 0), (20, 999, 20))

        self.assertEqual(_derive_stud_footprint(box), (1, 1))


class DeriveHeightUnitsTests(unittest.TestCase):

    def test_none_bounding_box_returns_none(self):

        self.assertIsNone(_derive_height_units(None))

    def test_no_stud_offset_matches_directly(self):
        """A stud-less part (e.g. a tile) -- full extent already sits
        exactly on a plate-unit boundary."""

        box = _box((0, 0, 0), (20, 8, 20))

        self.assertEqual(_derive_height_units(box), 8.0)

    def test_one_stud_offset_is_recognized(self):
        """A brick's full envelope (body + stud) measures 4 LDU over
        its correct stacking height -- the exact discrepancy found
        against all 10 seed parts during planning."""

        box = _box((0, -4, 0), (20, 24, 20))

        self.assertEqual(_derive_height_units(box), 24.0)

    def test_unrecognized_remainder_returns_none(self):
        """13 LDU rounds down to 8 with a remainder of 5 -- neither
        'no stud' (~0) nor 'one stud' (~4)."""

        box = _box((0, 0, 0), (20, 13, 20))

        self.assertIsNone(_derive_height_units(box))

    def test_zero_extent_returns_none(self):

        box = _box((0, 0, 0), (20, 0, 20))

        self.assertIsNone(_derive_height_units(box))

    def test_does_not_depend_on_footprint(self):
        """A wildly irregular footprint must not affect the height
        result -- the two helpers are independent."""

        box = _box((0, 0, 0), (999, 24, 777))

        self.assertEqual(_derive_height_units(box), 24.0)


class ExtractCategoryTests(unittest.TestCase):

    def _write(self, directory: Path, lines: list[str]) -> Path:

        path = directory / "test_part.dat"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return path

    def test_category_line_present(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = self._write(
                Path(tmp_dir),
                ["0 Brick  2 x  4", "0 !CATEGORY Brick"],
            )

            self.assertEqual(_extract_category(path), "Brick")

    def test_multi_word_category(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = self._write(
                Path(tmp_dir),
                ["0 Some Sticker Part", "0 !CATEGORY Sticker Shortcut"],
            )

            self.assertEqual(_extract_category(path), "Sticker Shortcut")

    def test_no_category_line_returns_none(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = self._write(
                Path(tmp_dir),
                ["0 Brick  2 x  4", "0 Name: test_part.dat"],
            )

            self.assertIsNone(_extract_category(path))

    def test_category_beyond_scan_limit_is_not_found(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            padding = [f"0 filler line {i}" for i in range(45)]

            path = self._write(
                Path(tmp_dir),
                ["0 Brick  2 x  4", *padding, "0 !CATEGORY Brick"],
            )

            self.assertIsNone(_extract_category(path))

    def test_missing_file_returns_none(self):

        self.assertIsNone(
            _extract_category(Path("does_not_exist_anywhere.dat"))
        )

    def test_does_not_depend_on_geometry(self):
        """A file with no geometry at all, only a category line, must
        still resolve correctly -- this helper never touches
        vertices/bounding_box."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = self._write(
                Path(tmp_dir),
                ["0 Abstract Category-Only Fixture", "0 !CATEGORY Plate"],
            )

            self.assertEqual(_extract_category(path), "Plate")


def _write_dat(directory: Path, filename: str, lines: list[str]) -> None:

    path = directory / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_fixture_library(root: Path) -> Path:
    """
    A tiny, synthetic on-disk LDraw-shaped library: one clean 1x1
    part with no category, one clean 2x1-with-stud part carrying an
    explicit !CATEGORY line, and one geometrically irregular part with
    neither -- covering "valid geometry derives metadata" and "invalid
    geometry preserves placeholders" without touching the real,
    ~24,000-part library.
    """

    parts_dir = root / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    _write_dat(
        parts_dir,
        "1111.dat",
        [
            "0 Test Brick 1 x 1",
            "0 Name: 1111.dat",
            "4 16 0 0 0 20 0 0 20 24 20 0 24 20",
        ],
    )

    _write_dat(
        parts_dir,
        "2222.dat",
        [
            "0 Test Brick 2 x 1",
            "0 Name: 2222.dat",
            "0 !CATEGORY Brick",
            "4 16 0 -4 0 40 -4 0 40 24 20 0 24 20",
        ],
    )

    _write_dat(
        parts_dir,
        "3333.dat",
        [
            "0 Test Irregular Part",
            "0 Name: 3333.dat",
            "4 16 0 0 0 27 0 0 27 13 20 0 13 20",
        ],
    )

    return root


class BuildCatalogPartsIntegrationTests(unittest.TestCase):

    def test_clean_part_with_no_category_gets_derived_footprint_and_height(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            library_root = _build_fixture_library(Path(tmp_dir))
            parts = {
                p.part_number: p
                for p in build_catalog_parts(library_root)
            }

            part = parts["1111"]

            self.assertEqual(part.stud_width, 1)
            self.assertEqual(part.stud_length, 1)
            self.assertEqual(part.height_units, 24.0)
            self.assertEqual(part.category, DEFAULT_CATEGORY)

    def test_clean_part_with_category_gets_everything_derived(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            library_root = _build_fixture_library(Path(tmp_dir))
            parts = {
                p.part_number: p
                for p in build_catalog_parts(library_root)
            }

            part = parts["2222"]

            self.assertEqual(part.stud_width, 2)
            self.assertEqual(part.stud_length, 1)
            self.assertEqual(part.height_units, 24.0)
            self.assertEqual(part.category, "Brick")

    def test_irregular_part_preserves_every_placeholder(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            library_root = _build_fixture_library(Path(tmp_dir))
            parts = {
                p.part_number: p
                for p in build_catalog_parts(library_root)
            }

            part = parts["3333"]

            self.assertEqual(part.stud_width, DEFAULT_STUD_WIDTH)
            self.assertEqual(part.stud_length, DEFAULT_STUD_LENGTH)
            self.assertEqual(part.height_units, DEFAULT_HEIGHT_UNITS)
            self.assertEqual(part.category, DEFAULT_CATEGORY)

    def test_bounding_box_is_still_populated_for_every_part(self):
        """Package_037 must not regress the pre-existing bounding_box
        behavior -- still computed unconditionally, including for the
        irregular part whose other fields stay at placeholders."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            library_root = _build_fixture_library(Path(tmp_dir))
            parts = {
                p.part_number: p
                for p in build_catalog_parts(library_root)
            }

            for part_number in ("1111", "2222", "3333"):
                self.assertIsNotNone(parts[part_number].bounding_box)

    def test_deterministic_across_repeated_builds(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            library_root = _build_fixture_library(Path(tmp_dir))

            first = build_catalog_parts(library_root)
            second = build_catalog_parts(library_root)

            first_signature = [
                (p.part_number, p.stud_width, p.stud_length,
                 p.height_units, p.category)
                for p in first
            ]
            second_signature = [
                (p.part_number, p.stud_width, p.stud_length,
                 p.height_units, p.category)
                for p in second
            ]

            self.assertEqual(first_signature, second_signature)

    def test_placeholder_fraction_drops_after_enrichment(self):
        """A direct 'placeholder detection' check, per Package_037's
        validation strategy: at least one of the two clean fixture
        parts must end up with fewer default-placeholder fields than
        the irregular one."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            library_root = _build_fixture_library(Path(tmp_dir))
            parts = {
                p.part_number: p
                for p in build_catalog_parts(library_root)
            }

            def placeholder_count(part):
                count = 0
                if part.stud_width == DEFAULT_STUD_WIDTH and part.stud_length == DEFAULT_STUD_LENGTH:
                    count += 1
                if part.height_units == DEFAULT_HEIGHT_UNITS:
                    count += 1
                if part.category == DEFAULT_CATEGORY:
                    count += 1
                return count

            self.assertLess(
                placeholder_count(parts["2222"]),
                placeholder_count(parts["3333"]),
            )


if __name__ == "__main__":
    unittest.main()
