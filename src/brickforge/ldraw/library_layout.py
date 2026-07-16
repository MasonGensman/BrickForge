"""
BrickForge LDraw Library Layout

Resolves the parts subdirectory name within an LDraw library root.

The official LDraw distribution uses "parts" (plural). Discovered
during Package_020.5: the project-root ldraw/ library already present
in this repository uses "part" (singular) instead -- confirmed to
contain real, standard top-level part files (e.g. 3001.dat, 3005.dat),
just under the alternate directory name. Both LDrawLoader and
build_catalog_parts() need to agree on this, so it is resolved once
here rather than duplicated.
"""

from pathlib import Path

_PARTS_DIRECTORY_NAMES = ("parts", "part")


def resolve_parts_directory(library_path: str | Path) -> Path:
    """
    Return the parts subdirectory for a library root: "parts" (the
    official name) if it exists, otherwise "part" as a fallback.

    Does not verify the directory actually contains any parts -- just
    like the paths this replaces, callers handle a missing/empty
    result gracefully (skip and log, never raise for this alone).
    """

    library_path = Path(library_path)

    for name in _PARTS_DIRECTORY_NAMES:

        candidate = library_path / name

        if candidate.is_dir():
            return candidate

    return library_path / _PARTS_DIRECTORY_NAMES[0]
