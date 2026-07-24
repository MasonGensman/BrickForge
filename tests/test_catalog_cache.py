"""
StudWorks Catalog Cache Tests (Package_037)

Focused on the one behavior Package_037 depends on: a cache written
under an older CACHE_SCHEMA_VERSION must be treated as invalid and
rebuilt, not silently served as if it reflected the new
build_catalog_parts() logic. Uses a synthetic on-disk library fixture
and a temporarily redirected LOCALAPPDATA (restored automatically by
unittest.mock.patch.dict) rather than touching the real per-user cache
location.
"""

import pickle
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brickforge.models.part_definition import BrickDefinition
from brickforge.services.catalog_cache import (
    CACHE_SCHEMA_VERSION,
    load_cached_parts,
    write_cache,
)


def _build_fixture_library(root: Path) -> Path:

    parts_dir = root / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    (parts_dir / "1111.dat").write_text(
        "0 Test Brick 1 x 1\n"
        "4 16 0 0 0 20 0 0 20 24 20 0 24 20\n",
        encoding="utf-8",
    )

    return root


def _fake_parts() -> list[BrickDefinition]:

    return [
        BrickDefinition(
            part_number="1111",
            name="Test Brick 1x1",
            category="Brick",
            ldraw_filename="1111.dat",
            stud_width=1,
            stud_length=1,
            height_units=24.0,
        )
    ]


class CacheSchemaVersionTests(unittest.TestCase):

    def test_schema_version_was_bumped_for_package_037(self):
        """build_catalog_parts()'s logic changed in Package_037, so
        CACHE_SCHEMA_VERSION must no longer be the pre-Package_037
        value of 1."""

        self.assertEqual(CACHE_SCHEMA_VERSION, 2)


class CacheInvalidationTests(unittest.TestCase):

    def test_cache_written_under_current_schema_loads_back(self):

        with tempfile.TemporaryDirectory() as appdata_dir, \
             tempfile.TemporaryDirectory() as library_dir:

            library_path = _build_fixture_library(Path(library_dir))
            parts = _fake_parts()

            with patch.dict(
                "os.environ", {"LOCALAPPDATA": appdata_dir},
            ):
                write_cache(library_path, parts)
                loaded = load_cached_parts(library_path)

            self.assertIsNotNone(loaded)
            self.assertEqual(
                [p.part_number for p in loaded],
                [p.part_number for p in parts],
            )

    def test_cache_from_an_older_schema_version_is_rejected(self):
        """Simulates a cache written by a pre-Package_037 build: the
        manifest is valid in every other way (library path and
        fingerprint match), but its cache_schema_version is stale."""

        with tempfile.TemporaryDirectory() as appdata_dir, \
             tempfile.TemporaryDirectory() as library_dir:

            library_path = _build_fixture_library(Path(library_dir))
            parts = _fake_parts()

            with patch.dict(
                "os.environ", {"LOCALAPPDATA": appdata_dir},
            ):
                write_cache(library_path, parts)

                cache_file = (
                    Path(appdata_dir)
                    / "StudWorks" / "cache" / "part_catalog.pkl"
                )

                with cache_file.open("rb") as file:
                    manifest = pickle.load(file)

                manifest["cache_schema_version"] = (
                    CACHE_SCHEMA_VERSION - 1
                )

                with cache_file.open("wb") as file:
                    pickle.dump(manifest, file)

                loaded = load_cached_parts(library_path)

            self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()
