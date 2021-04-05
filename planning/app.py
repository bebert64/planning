# -*- coding: utf-8 -*-

"""
Launches the app.
"""

import sys
from pathlib import Path

# my import style (adding "planning" everywhere to make it all more explicit) makes
# needed to have the script's parent folder added to system path before importing
# local modules.
# pylint: disable=wrong-import-position

my_package_path = Path(__file__).parent.parent
sys.path.insert(0, str(my_package_path.absolute()))

from PySide6 import QtWidgets, QtCore
from qt_material import apply_stylesheet
from planning.widgets.my_main_window import MyMainWindow


def main() -> None:
    """Creates and launches the app."""
    app = QtWidgets.QApplication(sys.argv)
    my_main_window = MyMainWindow.create_my_main_window()
    apply_stylesheet(app, theme="dark_cyan.xml")
    my_main_window.setWindowState(QtCore.Qt.WindowMaximized)
    my_main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
