"""
StudWorks Selection Manager

Tracks which single SceneBrick -- identified by its stable
SceneBrick.id, never a SceneBrick reference, a renderer object, or a
list index -- is currently selected. Deliberately independent of
Scene and Renderer: SelectionManager holds nothing but an
int | None, so it cannot mutate Scene and has no way to reach for
rendering state (see Package_027.md for the full ownership
rationale).

Selection is only ever valid for the currently active Scene. Because
SelectionManager has no Scene reference of its own, it cannot detect
a Scene replacement itself -- MainWindow is responsible for calling
clear() at every point the active Scene is replaced (New Project,
Open Project, Generate LEGO Model), so a selected id can never
silently outlive the Scene it referred to.
"""


class SelectionManager:
    """Owns the single currently-selected SceneBrick.id, or None."""

    def __init__(self):

        self._selected_id: int | None = None

    def select(self, brick_id: int) -> None:
        """
        Select a brick by its stable SceneBrick.id.

        Raises TypeError for anything that isn't a plain int. bool is
        explicitly rejected despite being an int subclass in Python
        (the same recurring gotcha guarded against in
        serialization/schema.py's _is_int), and None is rejected in
        favor of the explicit clear() call, so a caller can never
        confuse "select nothing" with "select id 0".
        """

        if isinstance(brick_id, bool) or not isinstance(brick_id, int):

            raise TypeError(
                f"SelectionManager.select() requires an int id, "
                f"got {brick_id!r} ({type(brick_id).__name__})."
            )

        self._selected_id = brick_id

    def clear(self) -> None:
        """Deselect -- no brick is selected."""

        self._selected_id = None

    def selected_id(self) -> int | None:
        """Return the selected SceneBrick.id, or None if nothing is selected."""

        return self._selected_id

    def has_selection(self) -> bool:

        return self._selected_id is not None
