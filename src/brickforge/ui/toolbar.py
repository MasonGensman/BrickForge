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

    undo_action = QAction("Undo", window)
    redo_action = QAction("Redo", window)

    new_action.setStatusTip("Create a new project")
    open_action.setStatusTip("Open a project")
    save_action.setStatusTip("Save the current project")

    undo_action.setStatusTip("Undo")
    redo_action.setStatusTip("Redo")

    new_action.triggered.connect(
        lambda: project_manager.new_project()
    )

    toolbar.addAction(new_action)
    toolbar.addAction(open_action)
    toolbar.addAction(save_action)

    toolbar.addSeparator()

    toolbar.addAction(undo_action)
    toolbar.addAction(redo_action)

    return toolbar