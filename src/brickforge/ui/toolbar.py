from PySide6.QtGui import QAction


def create_toolbar(window):
    toolbar = window.addToolBar("Main")

    toolbar.setMovable(False)
    toolbar.setFloatable(False)

    actions = [
        ("New", "Create a new project"),
        ("Open", "Open an existing project"),
        ("Save", "Save the current project"),
        ("Undo", "Undo last action"),
        ("Redo", "Redo last action"),
    ]

    for text, tooltip in actions:
        action = QAction(text, window)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        toolbar.addAction(action)

    return toolbar