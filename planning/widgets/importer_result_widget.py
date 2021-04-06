# -*- coding: utf-8 -*-

"""
Defines :
 The ImporterResultWidget class.

"""

from __future__ import annotations

from typing import Union, Type, List, Optional

from PySide6 import QtWidgets
from utils.my_custom_widget import MyCustomWidget

import planning.excel as importer
from planning.models import ProjectModel, TicketModel


class ImporterResultWidget(QtWidgets.QWidget, MyCustomWidget):

    """
    The ImporterResultWidget presents the results from the Importer's analysis.

    It allows to visualize (and validate) the modification proposed by the Importer's
    analysis (projects' updates and / or creations).

    Warning
    -------
    This widget should not be instantiated directly, but rather through the factory
    method create_importer_result_widget.

    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.importer: importer.Importer
        self.projects_updated: List[ProjectModel] = []

    @classmethod
    def create_importer_result_widget(
        cls, my_importer: importer.Importer
    ) -> ImporterResultWidget:
        """
        Factory method to create an ImporterResultWidget.

        Parameters
        ----------
        my_importer
            The Importer objects whose results are displayed.

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        importer_result_widget = cls.create_widget()
        assert isinstance(importer_result_widget, cls)
        importer_result_widget.importer = my_importer
        importer_result_widget._connect_actions()
        return importer_result_widget

    def _connect_actions(self) -> None:
        self.cancel_button.clicked.connect(self.close)
        self.ok_button.clicked.connect(self._handle_ok)

    def _handle_ok(self) -> None:
        self._accept_modif_auto()
        self._accept_modif_validate()
        self._create_new_projects()
        self._refresh_planning_grid()
        self.close()

    def _accept_modif_auto(self) -> None:
        for widget in self.modif_auto_group_box.children():
            if isinstance(widget, QtWidgets.QLabel):
                project_modification = widget.my_object
                self.projects_updated.append(project_modification.project.id)
                project_modification.accept()

    def _accept_modif_validate(self) -> None:
        for widget in self.modif_validate_group_box.children():
            if isinstance(widget, QtWidgets.QCheckBox) and widget.isChecked():
                project_modification = widget.my_object
                self.projects_updated.append(project_modification.project.id)
                project_modification.accept()

    def _create_new_projects(self) -> None:
        for widget in self.projects_new_group_box.children():
            if isinstance(widget, QtWidgets.QLabel):
                project_model = widget.my_object
                self.projects_updated.append(project_model.id)
                project_model.save(force_insert=True)

    def _refresh_planning_grid(self) -> None:
        my_main_window = self.importer.my_main_window
        planning_grid = my_main_window.centralWidget()
        tickets = (
            TicketModel.select()
            .join(ProjectModel)
            .where(ProjectModel.id << self.projects_updated)  #type: ignore
        )
        planning_grid.refresh_grid(tickets)

    def add_modification_auto(
        self, project_modification: importer.ProjectModification
    ) -> None:
        """
        Adds a ProjectModification that will be automatically accepted if the OK button
        is pressed.
        """
        self._add_to_widget(
            project_modification,
            QtWidgets.QLabel,
            str(project_modification),
            self.modif_auto_layout,
        )

    def add_modification_validate(
        self, project_modification: importer.ProjectModification
    ) -> None:
        """
        Adds a ProjectModification that will be need to be validated to be accepted
        if and when the OK button is pressed.
        """
        self._add_to_widget(
            project_modification,
            QtWidgets.QCheckBox,
            str(project_modification),
            self.modif_validate_layout,
        )

    def add_new_project(self, project: ProjectModel) -> None:
        """Adds a ProjectModel that will be created if the OK button is pressed."""
        self._add_to_widget(
            project,
            QtWidgets.QLabel,
            f"{project.id} : {project.name}",
            self.projects_new_layout,
        )

    def _add_to_widget(
        self,
        my_object: Union[ProjectModel, importer.ProjectModification],
        widget_class: Type[QtWidgets.QWidget],
        description: str,
        layout: QtWidgets.QLayout,
    ) -> None:
        widget = widget_class(self)
        widget.my_object = my_object
        widget.setText(description)
        layout.addWidget(widget)
