# -*- coding: utf-8 -*-

"""
Defines :
 The CellMenu class.

"""


from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

import planning.models as models
import planning.widgets.planning_grid as my_planning_grid
from planning.model_drawer import Project, Ticket
from planning.my_types import Row, Column
from planning.widgets.model_modifier_widgets import (
    TicketModifierWidget, ProjectModifierWidget,
)


class CellMenu(QtWidgets.QMenu):
    """
    The context menu that appears when a right-click is done on a cell.

    Parameters
    ----------
    planning_grid
    row, column
        The coordinates of the cell.

    """

    def __init__(
        self, planning_grid: my_planning_grid.PlanningGrid, row: Row, column: Column,
    ):
        super().__init__(planning_grid)
        self.row: Row = row
        self.column: Column = column
        self._add_actions()

    @property
    def ticket_model(self) -> Optional[models.TicketModel]:
        """The TicketModel linked to the cell, or None if the cell is empty."""
        return models.CellModel.ticket_or_none(self.row, self.column)

    @property
    def project_model(self) -> Optional[models.ProjectModel]:
        """The ProjectModel linked to the cell, or None."""
        return models.CellModel.project_or_none(self.row, self.column)

    def _add_actions(self) -> None:
        if self.ticket_model is None:
            self.addAction("Créer un ticket").triggered.connect(self._create_ticket)
            self.addAction("Créer un projet").triggered.connect(self._create_project)
        else:
            self.addAction("Déplacer le ticket").triggered.connect(self._move_ticket)
            self.addAction("Supprimer le ticket").triggered.connect(self._delete_ticket)
            if self.project_model is not None:
                self.addAction("Supprimer le projet").triggered.connect(
                    self._delete_project
                )

    def _create_ticket(self) -> None:
        ticket_creation_widget = TicketModifierWidget.create_widget_new_ticket(
            self.row, self.column, self.parent()
        )
        ticket_creation_widget.show()

    def _create_project(self) -> None:
        project_modifier_widget = ProjectModifierWidget.create_widget_new_project(
            self.row, self.column, self.parent()
        )
        project_modifier_widget.show()

    def _delete_project(self) -> None:
        if (project_model := self.project_model) is not None:
            Project(project_model, self.parent()).delete()

    def _delete_ticket(self) -> None:
        if (ticket_model := self.ticket_model) is not None:
            Ticket(ticket_model, self.parent()).delete()

    def _move_ticket(self) -> None:
        print(self)
        print("_move_ticket")
