from PySide6.QtGui import QAction

from brickforge.project import ProjectManager

project_manager = ProjectManager()


def create_toolbar(window):
    toolbar = window.addToolBar("Main")

    toolbar.setMovable(False)
    toolbar.setFloatable(False)

    new_action = QAction("New", window)
    open_action = QAction("Open", window)
    save_action = QAction("Save", window)
    export_action = QAction("Export", window)

    undo_action = QAction("Undo", window)
    redo_action = QAction("Redo", window)

    #
    # Package_047: setToolTip() alongside setStatusTip() -- a tooltip
    # appears immediately at the cursor, while a status tip only shows
    # in the (easy-to-miss) status bar. Matches the tooltip pattern
    # Package_046 already established on the Generate buttons.
    #
    new_tip = "Create a new project"
    open_tip = "Open a project"
    save_tip = "Save the current project"
    export_tip = "Export the current model to BrickLink Studio (.ldr)"

    new_action.setStatusTip(new_tip)
    new_action.setToolTip(new_tip)
    open_action.setStatusTip(open_tip)
    open_action.setToolTip(open_tip)
    save_action.setStatusTip(save_tip)
    save_action.setToolTip(save_tip)
    export_action.setStatusTip(export_tip)
    export_action.setToolTip(export_tip)

    #
    # Package_046: Undo/Redo have no backend to wire to yet
    # (tracked as known debt since Package_033's roadmap pivot) --
    # disabled rather than left clickable-but-silent, which previously
    # gave no feedback at all when clicked. Package_047 adds their
    # standard shortcuts anyway -- a disabled QAction's shortcut
    # simply never fires, which is correct, unsurprising Qt behavior.
    #
    undo_action.setEnabled(False)
    redo_action.setEnabled(False)
    undo_action.setShortcut("Ctrl+Z")
    redo_action.setShortcut("Ctrl+Y")

    undo_tip = "Undo (not yet available)"
    redo_tip = "Redo (not yet available)"

    undo_action.setStatusTip(undo_tip)
    undo_action.setToolTip(undo_tip)
    redo_action.setStatusTip(redo_tip)
    redo_action.setToolTip(redo_tip)

    #
    # New/Open/Save/Export delegate to MainWindow (Package_026,
    # extended Package_046) so viewport updates and status messages
    # stay in one place, shared with the matching File menu actions --
    # rather than this toolbar module driving project_manager directly
    # with no UI feedback, as "New" alone previously did.
    #
    new_action.triggered.connect(window.on_new_project)
    open_action.triggered.connect(window.on_open_project)
    save_action.triggered.connect(window.on_save_project)
    export_action.triggered.connect(window.on_export_model)

    toolbar.addAction(new_action)
    toolbar.addAction(open_action)
    toolbar.addAction(save_action)
    toolbar.addAction(export_action)

    toolbar.addSeparator()

    toolbar.addAction(undo_action)
    toolbar.addAction(redo_action)

    return toolbar