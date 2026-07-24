"""
BrickForge Catalog Cache

Persists the fully-built PartCatalog (as a list[BrickDefinition]) to a
per-user disk cache, so parsing the LDraw library only has to happen
once per machine per library change, not once per application launch
(measured against the real 24,297-part library: ~29s to rebuild, ~1.4s
to validate a cache, well under a second to load one).

Entirely an implementation detail of PartCatalog.load_best_available()
-- nothing outside services/part_catalog.py should import this module.

Cache validity requires all of:
- CACHE_SCHEMA_VERSION matching (bumped only if BrickDefinition's shape
  or build_catalog_parts()'s logic changes -- deliberately NOT tied to
  the application's own version, so unrelated app/branding changes
  don't force needless rebuilds).
- The resolved library_path matching exactly (so switching which
  library resolves -- env var, install, project-root, bundled --
  naturally invalidates a cache built for a different one).
- A fingerprint (file count, total size, latest mtime across the
  library's top-level .dat files) matching -- cheap to recompute
  relative to the rebuild it's protecting against, and catches
  additions, removals, and modifications without reading any file's
  content.

Any failure to load (missing file, corrupted pickle, schema mismatch,
library mismatch, fingerprint mismatch, unexpected shape) is treated
identically: return None and let the caller rebuild normally. This
cache can never be the reason the application fails to start.
"""

import logging
import os
import pickle
from pathlib import Path

from brickforge._version import APP_VERSION
from brickforge.ldraw.library_layout import resolve_parts_directory
from brickforge.models.part_definition import BrickDefinition

logger = logging.getLogger(__name__)

#
# Bumped to 2 for Package_037: build_catalog_parts()'s logic changed
# (stud_width/stud_length/height_units/category are now independently
# derived where the geometry/header supports it, rather than always
# placeholder), so an on-disk cache built under the old logic must be
# rebuilt rather than silently served as if it reflected the new one.
#
CACHE_SCHEMA_VERSION = 2

_CACHE_APP_DIR_NAME = "StudWorks"
_CACHE_FILE_NAME = "part_catalog.pkl"


def _cache_path() -> Path | None:
    """
    %LOCALAPPDATA%\\StudWorks\\cache\\part_catalog.pkl -- the standard
    per-user Windows cache location (not roaming: this data should
    never sync across machines, and should be safe for the OS or user
    to clear at any time). Returns None if LOCALAPPDATA isn't set, so
    callers can disable caching gracefully rather than guess at a
    fallback location.
    """

    local_app_data = os.environ.get("LOCALAPPDATA")

    if not local_app_data:
        return None

    return (
        Path(local_app_data)
        / _CACHE_APP_DIR_NAME
        / "cache"
        / _CACHE_FILE_NAME
    )


def _compute_fingerprint(parts_path: Path) -> dict:
    """
    A cheap, content-free signal for "has this library's parts
    changed": count, total size, and latest modification time across
    its top-level .dat files.
    """

    count = 0
    total_size = 0
    latest_mtime = 0.0

    for entry in parts_path.iterdir():

        if entry.is_file() and entry.suffix.lower() == ".dat":

            stat = entry.stat()

            count += 1
            total_size += stat.st_size
            latest_mtime = max(latest_mtime, stat.st_mtime)

    return {
        "file_count": count,
        "total_size": total_size,
        "latest_mtime": latest_mtime,
    }


def load_cached_parts(
    library_path: Path,
) -> list[BrickDefinition] | None:
    """
    Return the cached parts list if a valid cache exists for
    `library_path`, otherwise None. Never raises.
    """

    cache_path = _cache_path()

    if cache_path is None or not cache_path.is_file():
        return None

    try:

        with cache_path.open("rb") as file:
            manifest = pickle.load(file)

    except Exception as error:

        #
        # Deliberately broad: pickle can raise a wide range of
        # exception types for corrupted, truncated, or
        # version-incompatible data (UnpicklingError, EOFError,
        # AttributeError, ImportError, and others depending on what
        # the bytes actually contain). Any of them means "not a usable
        # cache" -- the caller must fall through to a normal rebuild
        # regardless of which specific exception occurred.
        #
        logger.warning(
            "Could not read part catalog cache, rebuilding: %s",
            error,
        )

        return None

    if not isinstance(manifest, dict):
        return None

    if manifest.get("cache_schema_version") != CACHE_SCHEMA_VERSION:
        return None

    if manifest.get("library_path") != str(library_path):
        return None

    parts_path = resolve_parts_directory(library_path)

    try:
        current_fingerprint = _compute_fingerprint(parts_path)

    except OSError as error:

        logger.warning(
            "Could not fingerprint LDraw library, rebuilding: %s",
            error,
        )

        return None

    cached_fingerprint = {
        "file_count": manifest.get("file_count"),
        "total_size": manifest.get("total_size"),
        "latest_mtime": manifest.get("latest_mtime"),
    }

    if cached_fingerprint != current_fingerprint:
        return None

    parts = manifest.get("parts")

    if not isinstance(parts, list):
        return None

    return parts


def write_cache(
    library_path: Path,
    parts: list[BrickDefinition],
) -> None:
    """
    Write a fresh cache for `library_path`, unconditionally overwriting
    whatever was there before (a stale or corrupted cache is replaced
    the same way a missing one is filled in). Failures (e.g. an
    unwritable cache directory) are logged and swallowed -- the
    application must never fail just because its cache couldn't be
    written; it simply rebuilds again next launch.
    """

    cache_path = _cache_path()

    if cache_path is None:
        return

    parts_path = resolve_parts_directory(library_path)

    try:
        fingerprint = _compute_fingerprint(parts_path)

    except OSError as error:

        logger.warning(
            "Could not fingerprint LDraw library, skipping cache "
            "write: %s",
            error,
        )

        return

    manifest = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "library_path": str(library_path),
        **fingerprint,
        "parts": parts,
    }

    try:

        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with cache_path.open("wb") as file:
            pickle.dump(
                manifest,
                file,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

    except OSError as error:

        logger.warning(
            "Could not write part catalog cache: %s",
            error,
        )
