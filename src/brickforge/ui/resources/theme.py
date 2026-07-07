"""
BrickForge UI Theme

Defines the global application stylesheet.
"""

DARK_THEME = """
QMainWindow {
    background-color: #2b2b2b;
}

QMenuBar {
    background-color: #333333;
    color: white;
}

QMenuBar::item:selected {
    background-color: #4a90e2;
}

QMenu {
    background-color: #333333;
    color: white;
}

QMenu::item:selected {
    background-color: #4a90e2;
}

QDockWidget {
    color: white;
    font-weight: bold;
}

QDockWidget::title {
    background-color: #3c3c3c;
    padding: 6px;
}

QListWidget {
    background-color: #252526;
    color: white;
    border: none;
}

QLabel {
    color: white;
}

QStatusBar {
    background-color: #333333;
    color: white;
}

QToolBar {
    background-color: #333333;
    border: none;
}

QLineEdit {
    background-color: #3c3c3c;
    color: white;
    border: 1px solid #555555;
    padding: 4px;
}
"""