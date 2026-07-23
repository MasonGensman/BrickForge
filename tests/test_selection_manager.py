"""
StudWorks Selection Manager Tests (Package_027)

Pure unit tests -- no Qt, no OpenGL context, no Scene. SelectionManager
holds nothing but an int | None, so its state transitions can be
verified in complete isolation.
"""

import unittest

from brickforge.selection.selection_manager import SelectionManager


class SelectionManagerTests(unittest.TestCase):

    def test_starts_with_no_selection(self):

        manager = SelectionManager()

        self.assertIsNone(manager.selected_id())
        self.assertFalse(manager.has_selection())

    def test_select_sets_selected_id(self):

        manager = SelectionManager()
        manager.select(5)

        self.assertEqual(manager.selected_id(), 5)
        self.assertTrue(manager.has_selection())

    def test_select_zero_is_a_valid_id(self):
        """0 is a legitimate SceneBrick.id, distinct from "no selection"."""

        manager = SelectionManager()
        manager.select(0)

        self.assertEqual(manager.selected_id(), 0)
        self.assertTrue(manager.has_selection())

    def test_clear_deselects(self):

        manager = SelectionManager()
        manager.select(3)
        manager.clear()

        self.assertIsNone(manager.selected_id())
        self.assertFalse(manager.has_selection())

    def test_select_replaces_previous_selection(self):
        """Only single selection is in scope for this package."""

        manager = SelectionManager()
        manager.select(1)
        manager.select(2)

        self.assertEqual(manager.selected_id(), 2)

    def test_select_rejects_none(self):

        manager = SelectionManager()

        with self.assertRaises(TypeError):
            manager.select(None)

    def test_select_rejects_bool(self):
        """bool is an int subclass in Python -- explicitly excluded."""

        manager = SelectionManager()

        with self.assertRaises(TypeError):
            manager.select(True)

        with self.assertRaises(TypeError):
            manager.select(False)

    def test_select_rejects_non_int_types(self):

        manager = SelectionManager()

        for bad_value in ("3", 3.0, [3], {3}, object()):

            with self.subTest(value=bad_value):

                with self.assertRaises(TypeError):
                    manager.select(bad_value)

    def test_failed_select_does_not_change_state(self):

        manager = SelectionManager()
        manager.select(7)

        with self.assertRaises(TypeError):
            manager.select("bad")

        self.assertEqual(manager.selected_id(), 7)

    def test_deterministic_sequence(self):
        """Same sequence of calls always produces the same resulting state."""

        def run_sequence():

            manager = SelectionManager()
            manager.select(1)
            manager.select(2)
            manager.clear()
            manager.select(9)

            return manager.selected_id()

        self.assertEqual(run_sequence(), run_sequence())
        self.assertEqual(run_sequence(), 9)


if __name__ == "__main__":
    unittest.main()
