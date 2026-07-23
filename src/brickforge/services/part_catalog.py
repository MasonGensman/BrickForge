"""
BrickForge Part Catalog

Indexes BrickDefinition entries for lookup by part number. The catalog
itself is agnostic to where its entries came from: today's small
hand-curated seed list and a future loader deriving BrickDefinitions from
the full LDraw parts library both produce a list[BrickDefinition] and are
loaded through the same PartCatalog constructor.
"""

import functools
import logging
from collections.abc import Iterable

from brickforge.models.part_definition import BrickDefinition
from brickforge.services.catalog_cache import load_cached_parts, write_cache
from brickforge.services.ldraw_catalog_builder import build_catalog_parts
from brickforge.services.ldraw_library_locator import find_ldraw_library

logger = logging.getLogger(__name__)

#
# Common LDraw color codes (verified against LDConfig.ldr):
# 0 Black, 1 Blue, 2 Green, 4 Red, 14 Yellow, 15 White.
#
_COMMON_COLORS = [0, 1, 2, 4, 14, 15]


def load_seed_bricks() -> list[BrickDefinition]:
    """
    Today's small, hand-curated seed catalog.

    A future loader (e.g. one deriving BrickDefinitions from the full LDraw
    parts library) returns the same list[BrickDefinition] shape and can be
    passed to PartCatalog exactly like this one -- PartCatalog does not
    assume this is the only source of entries.
    """

    return [
        BrickDefinition(
            part_number="3005",
            name="Brick 1x1",
            category="Brick",
            ldraw_filename="3005.dat",
            stud_width=1,
            stud_length=1,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3004",
            name="Brick 1x2",
            category="Brick",
            ldraw_filename="3004.dat",
            stud_width=1,
            stud_length=2,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3622",
            name="Brick 1x3",
            category="Brick",
            ldraw_filename="3622.dat",
            stud_width=1,
            stud_length=3,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3010",
            name="Brick 1x4",
            category="Brick",
            ldraw_filename="3010.dat",
            stud_width=1,
            stud_length=4,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3003",
            name="Brick 2x2",
            category="Brick",
            ldraw_filename="3003.dat",
            stud_width=2,
            stud_length=2,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3002",
            name="Brick 2x3",
            category="Brick",
            ldraw_filename="3002.dat",
            stud_width=2,
            stud_length=3,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3001",
            name="Brick 2x4",
            category="Brick",
            ldraw_filename="3001.dat",
            stud_width=2,
            stud_length=4,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3023",
            name="Plate 1x2",
            category="Plate",
            ldraw_filename="3023.dat",
            stud_width=1,
            stud_length=2,
            height_units=8.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3022",
            name="Plate 2x2",
            category="Plate",
            ldraw_filename="3022.dat",
            stud_width=2,
            stud_length=2,
            height_units=8.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3068",
            name="Tile 2x2",
            category="Tile",
            ldraw_filename="3068.dat",
            stud_width=2,
            stud_length=2,
            height_units=8.0,
            available_colors=list(_COMMON_COLORS),
        ),
    ]


class PartCatalog:
    """Looks up BrickDefinition entries by part number."""

    def __init__(
        self,
        parts: Iterable[BrickDefinition] = (),
    ):

        self._parts: dict[str, BrickDefinition] = {
            part.part_number: part
            for part in parts
        }

    @classmethod
    def from_seed(cls) -> "PartCatalog":
        """Build a PartCatalog from today's hand-curated seed list."""

        return cls(load_seed_bricks())

    @classmethod
    def load_best_available(cls) -> "PartCatalog":
        """
        Load a real LDraw-derived catalog if an installed library can be
        found (four-tier discovery via find_ldraw_library()); otherwise
        falls back to the permanent seed catalog. Never raises -- the
        seed catalog is always a safe fallback, and the rest of the
        application does not need to know which source produced the
        PartCatalog it received.

        Cached at two layers, both entirely internal to this method --
        callers see no difference in behavior or return type whether
        the catalog was freshly built or served from either cache
        (Package_023):

        - Process-local (functools.lru_cache on the module-level
          helper below): the first call in a running application does
          the real work; every later call in the same process returns
          the same PartCatalog instance instantly. This assumes the
          LDraw library does not change while the application is
          running -- safe today since nothing here watches the
          filesystem or offers a "reload catalog" action. Sharing one
          instance is safe because PartCatalog is architecturally
          immutable in practice: it exposes no mutation methods, and
          no code anywhere mutates a BrickDefinition after
          construction (verified by inspection during Package_023,
          though BrickDefinition is not frozen=True, so this is not
          type-enforced) -- if a future package introduces catalog
          mutation, this sharing needs revisiting.
        - On-disk (services.catalog_cache): survives across separate
          application launches, keyed by the resolved library path
          plus a cheap content fingerprint, so a changed LDraw
          installation is detected and triggers a rebuild
          automatically rather than silently serving stale data.
        """

        return _load_best_available_catalog()

    def all(self) -> list[BrickDefinition]:
        return list(self._parts.values())

    def get(
        self,
        part_number: str,
    ) -> BrickDefinition | None:

        return self._parts.get(part_number)


@functools.lru_cache(maxsize=1)
def _load_best_available_catalog() -> PartCatalog:
    """
    The real work behind PartCatalog.load_best_available(), wrapped in
    a process-local cache -- see that method's docstring for why this
    is safe. A module-level function rather than a method, since
    functools.lru_cache on a classmethod would key its cache on `cls`
    for no benefit here (there is only ever one PartCatalog class).

    maxsize=1 rather than the parameterless functools.cache: there is
    only ever one meaningful call shape (no arguments), so the two
    behave identically today, but lru_cache keeps room for a future
    parameterized variant (e.g. an explicit library override) without
    a cache-strategy change.
    """

    library_path = find_ldraw_library()

    if library_path is not None:

        cached_parts = load_cached_parts(library_path)

        if cached_parts is not None:
            return PartCatalog(cached_parts)

        parts = build_catalog_parts(library_path)

        if parts:

            write_cache(library_path, parts)

            return PartCatalog(parts)

        logger.warning(
            "LDraw library found at %s but no parts could be "
            "loaded; falling back to the seed catalog.",
            library_path,
        )

    return PartCatalog.from_seed()
