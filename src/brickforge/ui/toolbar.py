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

    new_action.setStatusTip("Create a new project")
    open_action.setStatusTip("Open a project")
    save_action.setStatusTip("Save the current project")
    export_action.setStatusTip(
        "Export the current model to BrickLink Studio (.ldr)"
    )

    #
    # Package_046: Undo/Redo have no backend to wire to yet
    # (tracked as known debt since Package_033's roadmap pivot) --
    # disabled rather than left clickable-but-silent, which previously
    # gave no feedback at all when clicked.
    #
    undo_action.setEnabled(False)
    redo_action.setEnabled(False)
    undo_action.setStatusTip("Undo (not yet available)")
    redo_action.setStatusTip("Redo (not yet available)")

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