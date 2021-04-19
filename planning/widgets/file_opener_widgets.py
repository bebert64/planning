# -*- coding: utf-8 -*-

"""
Defines :
 The FileOpenerWidget, base class for the Importer and Export versions.

 The ImporterOpenerWidget derived class.

 The ExporterWidget derived class.

"""

from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets
from utils_by_db.my_custom_widget import MyCustomWidget

from planning.excel import Importer, Exporter
from planning.models import Member
import planning.widgets.my_main_window as my_main_window


class FileOpenerWidget(QtWidgets.QWidget, MyCustomWidget):

    """
    Base class for the Importer and Exporter widgets inviting to choose a member.

    Warning
    -------
    This class should not be instantiated directly, but is meant to be subclassed.
    All derived classes must implement a _handle_ok method.

    """

    @classmethod
    def create_opener_widget(cls) -> FileOpenerWidget:
        """Factory method to create a FileOpenerWidget."""
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        opener_widget = cls.create_widget()
        assert isinstance(opener_widget, cls)
        opener_widget._populate_members_combo_box()
        opener_widget._connect_actions()
        return opener_widget

    def _populate_members_combo_box(self) -> None:
        for member in Member.select().order_by(Member.name):
            self.members_combo_box.addItem(member.name)

    def _connect_actions(self) -> None:
        self.cancel_button.clicked.connect(self.close)
        self.ok_button.clicked.connect(self._handle_ok)

    def _get_member(self) -> Member:
        member_name = self.members_combo_box.currentText()
        member: Member = Member.get(name=member_name)
        return member

    def _handle_ok(self) -> None:
        raise NotImplementedError()


class ImporterOpenerWidget(FileOpenerWidget):

    """
    The ImporterOpenerWidget allows to choose a member whose tasks will be imported.

    Warning
    -------
    This widget should not be instantiated directly, but rather through the factory
    method create_importer_opener_widget.

    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._my_main_window: my_main_window.MyMainWindow

    @classmethod
    def create_importer_opener_widget(
        cls, main_window: Optional[my_main_window.MyMainWindow] = None
    ) -> ImporterOpenerWidget:
        """
        Factory method to create an ImporterOpenerWidget.

        Parameters
        ----------
        main_window
            The MyMainWindow widget from the app, onto which the new tickets will be
            drawn after the import.

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        opener_widget = cls.create_opener_widget()
        assert isinstance(opener_widget, cls)
        opener_widget.my_main_window = main_window
        return opener_widget

    def _handle_ok(self) -> None:
        importer = Importer(self._get_member(), self.my_main_window)
        importer.analyse_excel()
        self.close()


class ExporterWidget(FileOpenerWidget):

    """
    The ExporterWidget allows to choose a member whose tasks will be exported to Excel.

    Warning
    -------
    This widget should not be instantiated directly, but rather through the factory
    method create_opener_widget.

    """

    def _handle_ok(self) -> None:
        try:
            exporter = Exporter(self._get_member())
        except PermissionError:
            self.display_msg_box(
                "Problème accès fichier",
                "Le fichier Excel est ouvert par une autre application, "
                "impossible d'exporter la liste des tâches.",
            )
        else:
            exporter.to_excel()
            self.close()
