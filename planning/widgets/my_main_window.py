# -*- coding: utf-8 -*-

"""
Defines :
 The MyMainWindow class.

"""

from __future__ import annotations

from PySide6 import QtWidgets
from qt_material import QtStyleTools
from utils_by_db.my_custom_widget import MyCustomWidget

from planning.widgets.file_opener_widgets import ImporterOpenerWidget, ExporterWidget
from planning.widgets.planning_grid import PlanningGrid


class MyMainWindow(QtWidgets.QMainWindow, MyCustomWidget, QtStyleTools):

    """
    MainWindow of the app.

    Warning
    -------
    This widget should not be instantiated directly, but rather through the factory
    method create_my_main_window.

    """

    @classmethod
    def create_my_main_window(cls) -> MyMainWindow:
        """Factory method to create the main window of the app."""
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        my_main_window = cls.create_widget()
        assert isinstance(my_main_window, cls)
        my_main_window._add_main_widget()
        my_main_window._connect_actions()
        my_main_window._add_extra_menus()
        return my_main_window

    def _add_main_widget(self) -> None:
        planning_grid = PlanningGrid.create_planning_grid(self)
        self.setCentralWidget(planning_grid)

    def _connect_actions(self) -> None:
        self.action_open_importer.triggered.connect(self._open_importer)
        self.action_open_exporter.triggered.connect(self._open_exporter)

    def _open_importer(self) -> None:
        importer_opener_widget = ImporterOpenerWidget.create_importer_opener_widget(
            self
        )
        importer_opener_widget.show()

    @staticmethod
    def _open_exporter() -> None:
        exporter_widget = ExporterWidget.create_opener_widget()
        exporter_widget.show()

    def _add_extra_menus(self) -> None:
        pass
