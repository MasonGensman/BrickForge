"""
BrickForge UI Theme

Defines the global application stylesheet.
"""

DARK_THEME = """
QMainWindow {
    background-color: #252526;
}

/* ---------- Menu ---------- */

QMenuBar {
    background-color: #2d2d30;
    color: #f3f3f3;
    border-bottom: 1px solid #3f3f46;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
}

QMenuBar::item:selected {
    background-color: #3e3e42;
}

QMenu {
    background-color: #2d2d30;
    color: #f3f3f3;
    border: 1px solid #3f3f46;
}

QMenu::item {
    padding: 6px 24px;
}

QMenu::item:selected {
    background-color: #007acc;
}

/* ---------- Toolbar ---------- */

QToolBar {
    background-color: #2d2d30;
    border: none;
    spacing: 4px;
    padding: 4px;
}

QToolButton {
    color: #f3f3f3;
    background: transparent;
    border: none;
    padding: 6px 10px;
    border-radius: 4px;
}

QToolButton:hover {
    background-color: #3e3e42;
}

QToolButton:pressed {
    background-color: #007acc;
}

/* ---------- Dock Widgets ---------- */

QDockWidget {
    color: white;
    font-weight: bold;
}

QDockWidget::title {
    background-color: #2d2d30;
    padding: 8px;
    border-bottom: 1px solid #3f3f46;
}

/* ---------- Lists ---------- */

QListWidget {
    background-color: #1e1e1e;
    color: white;
    border: none;
    outline: none;
}

QListWidget::item {
    padding: 4px;
}

QListWidget::item:selected {
    background-color: #007acc;
}

/* ---------- Search ---------- */

QLineEdit {
    background-color: #3c3c3c;
    color: white;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px;
}

QLineEdit:focus {
    border: 1px solid #007acc;
}

/* ---------- Labels ---------- */

QLabel {
    color: white;
}

/* ---------- Status Bar ---------- */

QStatusBar {
    background-color: #2d2d30;
    color: white;
    border-top: 1px solid #3f3f46;
}
"""