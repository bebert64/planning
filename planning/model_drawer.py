# -*- coding: utf-8 -*-

"""
Defines:
 The Project, Cell and Ticket class, to handle interaction between the models and the
 grid.

 The TicketMover helper class.

 The Color type.

"""


from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, List, Tuple, Set

import peewee
from PySide6 import QtWidgets, QtGui, QtCore
from utils_by_db.functions import max_with_none, min_with_none

from planning.config_planning.config_planning import config
from planning.models import ProjectModel, TicketModel, CellModel
from planning.my_types import Day, Row, Column, TicketID
from planning.widgets import planning_grid


class Project:

    """
    The Project class handles the interaction between a ProjectModel and the
    PlanningGrid widget.

    Parameters
    ----------
    model
    my_planning_grid

    """

    def __init__(
        self, model: ProjectModel, my_planning_grid: planning_grid.PlanningGrid
    ):
        self.model: ProjectModel = model
        self.planning_grid: planning_grid.PlanningGrid = my_planning_grid

    @property
    def start_date(self) -> Optional[datetime]:
        """
        The date of the first row of any scheduled ticket for the project.

        If no tickets are scheduled, returns None.

        """
        start_date = None
        for ticket in self._get_tickets_scheduled():
            first_cell = ticket.first_cell_or_none
            assert first_cell is not None
            ticket_first_row = ticket.first_cell_or_none.row
            ticket_start_date = self.planning_grid.get_date_from_row(ticket_first_row)
            start_date = min_with_none(start_date, ticket_start_date)
        return start_date

    @property
    def end_date(self) -> Optional[datetime]:
        """
        The date of the last row of all scheduled ticket for the project.

        If there are any unscheduled ticket, it is considered that the project is not
        yet fully scheduled, and the method returns None.

        """
        end_date = None
        if self._is_fully_scheduled():
            for ticket in self._get_tickets_scheduled():
                last_cell = ticket.last_cell_or_none
                assert last_cell is not None
                ticket_last_row = last_cell.row
                ticket_end_date = self.planning_grid.get_date_from_row(ticket_last_row)
                end_date = max_with_none(end_date, ticket_end_date)
        return end_date

    def _is_fully_scheduled(self) -> bool:
        is_fully_scheduled = True
        tickets_backlog = list(
            TicketModel.select().where(
                TicketModel.project == self.model.id, TicketModel.is_scheduled == 0,
            )
        )
        for ticket in tickets_backlog:
            if ticket.length != 0:
                is_fully_scheduled = False
        return is_fully_scheduled

    def _get_tickets_scheduled(self) -> peewee.ModelSelect:
        return TicketModel.select().where(
            TicketModel.project == self.model.id, TicketModel.is_scheduled == 1
        )

    def delete(self) -> None:
        """Deletes the projects and all associated tickets."""
        for ticket in self._tickets:
            ticket.delete()
        self.model.delete_instance()

    @property
    def _tickets(self) -> List[Ticket]:
        return [
            Ticket(ticket_model, self.planning_grid)
            for ticket_model in TicketModel.select().where(
                TicketModel.project == self.model.id
            )
        ]

    def refresh(self) -> None:
        """Refreshes all tickets linked to the project."""
        for ticket in self._tickets:
            ticket.refresh()


Color = str


class Cell:

    """
    The Cell class is responsible for drawing a ticket's cell onto the grid.

    Class Attributes
    ----------------
    default_background_color
    default_border_size
    default_border_color
    fixed_border_color
    delivered_border_color
    stand_by_border_color

    """

    default_background_color = "green"
    default_border_size = "2px"
    default_border_color = "black"
    fixed_border_color = "red"
    delivered_border_color = "orange"
    stand_by_border_color = "blue"

    def __init__(
        self, model: CellModel, my_planning_grid: planning_grid.PlanningGrid
    ):
        self._model: CellModel = model
        self._planning_grid: planning_grid.PlanningGrid = my_planning_grid
        self._item: QtWidgets.QTableWidgetItem = QtWidgets.QTableWidgetItem()
        self._planning_grid.setItem(self._model.row, self._model.column, self._item)
        self._widget: QtWidgets.QLabel = QtWidgets.QLabel()
        self._planning_grid.setCellWidget(
            self._model.row, self._model.column, self._widget
        )

    def draw(self) -> None:
        """Draws the cell on the grid."""
        self._draw_background()
        self._draw_borders()
        self._write_label()

    def _draw_background(self) -> None:
        self._item.setBackground(
            QtGui.QBrush(QtGui.QColor(Cell.default_background_color))
        )

    def _draw_borders(self) -> None:
        border_color: Color = self._get_border_color()
        style_sheet_label = (
            f"border-radius: 0px ; "
            f"border-left: {Cell.default_border_size} solid {border_color}; "
            f"border-right: {Cell.default_border_size} solid {border_color}; "
        )
        if self._model.is_top_cell:
            style_sheet_label += (
                f"border-top: {Cell.default_border_size} solid {border_color}; "
            )
        if self._model.is_bottom_cell:
            style_sheet_label += (
                f"border-bottom: {Cell.default_border_size} solid {border_color}; "
            )
        self._widget.setStyleSheet(style_sheet_label)

    def _get_border_color(self) -> Color:
        if self._model.is_fixed():
            border_color = Cell.fixed_border_color
        elif self._model.is_delivered():
            border_color = Cell.delivered_border_color
        elif self._model.is_stand_by():
            border_color = Cell.stand_by_border_color
        else:
            border_color = Cell.default_border_color
        return border_color

    def _write_label(self) -> None:
        if self._model.is_top_cell:
            cell_label: QtWidgets.QLabel = self._planning_grid.cellWidget(
                self._model.row, self._model.column
            )
            ticket_title = self._model.ticket.get_title()
            cell_label.setText(ticket_title)


class Ticket:
    """
    The Ticket class is responsible for drawing and moving ticket_models on the grid.

    The class also updates the database when needed.

    Parameters
    ----------
    ticket_model
    my_planning_grid

    """

    def __init__(
        self, ticket_model: TicketModel, my_planning_grid: planning_grid.PlanningGrid
    ):
        self.ticket_model: TicketModel = ticket_model
        self.planning_grid: planning_grid.PlanningGrid = my_planning_grid

    @property
    def length(self) -> Day:
        """The number of cells needed to draw the ticket."""
        return self.ticket_model.length

    def refresh(self) -> None:
        """
        Erases or redraw the ticket.

        To be used after a ticket's length has been modified (which includes its length
        being reduced to 0, if the project's status has changed).
        If the cells themselves need to be redrawn (after the border's color has
        changed for example), draw_cells is much faster.

        """
        if self._needs_being_erased():
            self.delete()
        elif self.ticket_model.length == 0:
            self._erase()
            self.ticket_model.is_scheduled = False
            self.ticket_model.save()
        else:
            first_cell = self.ticket_model.first_cell_or_none
            if first_cell is not None:
                row, column = first_cell.row, first_cell.column
            else:
                row, column = (
                    self.planning_grid.get_today_row(),
                    self._get_column_owner_backlog(),
                )
            self.move_to(row, column, force_move=False)

    def delete(self) -> None:
        """Erases all cells and deletes the database instance."""
        self._erase()
        project = self.project_or_none()
        self.ticket_model.delete_instance()
        if project is not None:
            project.refresh()

    def project_or_none(self) -> Optional[Project]:
        """The Project linked to the Ticket if existing, or None."""
        project_model = self.ticket_model.project_or_none()
        if project_model is not None:
            project: Optional[Project] = Project(project_model, self.planning_grid)
        else:
            project = None
        return project

    def draw_cells(self) -> None:
        """
        Redraw the tickets' cells.

        To be used if the cells need to be redrawn (after the border's color has
        changed for example), but the ticket hasn't moved. Otherwise, use the
        refresh method instead.

        """
        for cell_model in self._get_cells():
            Cell(cell_model, self.planning_grid).draw()

    def _needs_being_erased(self) -> bool:
        return self.ticket_model.needs_being_erased()

    def _get_cells(self) -> peewee.ModelSelect:
        ticket_id = self.ticket_model.id
        cells = CellModel.select().where(CellModel.ticket == ticket_id)
        return cells

    def move_to(self, row: Row, column: Column, force_move: bool = True) -> None:
        """
        Moves the ticket to the specified coordinates.

        Parameters
        ----------
        row, column
            Destination coordinates for the first cell of the ticket.
        force_move
            If True, will move non-fixed ticket to take their place. If False, the
            ticket will only be inserted onto free cells.

        """
        self._erase()
        mover = TicketMover(self)
        mover.move_to(row, column, force_move)

    def update_models(self) -> None:
        """
        Updates all models' parameters in the database.
        """
        self._update_cell_models()
        self._update_ticket_model()
        self._update_project_model()

    def _update_cell_models(self) -> None:
        for cell in self._get_cells():
            cell.update_model()

    def _update_ticket_model(self) -> None:
        try:
            cell = CellModel.get(CellModel.ticket == self.ticket_model.id)
        except peewee.DoesNotExist:
            self.ticket_model.is_scheduled = False
        else:
            self.ticket_model.is_scheduled = (
                self.planning_grid.horizontalHeaderItem(cell.column).text()
                != config["column_backlog_name"]
                and self.length != 0
            )
        self.ticket_model.save()

    def _update_project_model(self) -> None:
        project_model = self.ticket_model.project_or_none()
        if project_model is not None:
            project = Project(project_model, self.planning_grid)
            project_model.start_date = project.start_date
            project_model.end_date = project.end_date
            project_model.save()

    def _erase(self) -> None:
        for cell in self._get_cells():
            self.planning_grid.removeCellWidget(cell.row, cell.column)
            self.planning_grid.takeItem(cell.row, cell.column)
            cell.delete_instance()

    def select_cells(self) -> None:
        """Select all cells from the ticket."""
        for cell in self._get_cells():
            model_index = self.planning_grid.model().index(cell.row, cell.column)
            self.planning_grid.selectionModel().select(
                model_index, QtCore.QItemSelectionModel.Select
            )

    def _get_column_owner_backlog(self) -> Column:
        """The number of the backlog column for the ticket's owner."""
        name = self.ticket_model.owner.name
        column_owner = self.planning_grid.get_column_from_header(name)
        assert column_owner is not None
        column_owner_backlog = column_owner + 1
        return column_owner_backlog

    @staticmethod
    def draw_all_tickets(my_planning_grid: planning_grid.PlanningGrid) -> None:
        """
        Draws all existing tickets on the planning grid.

        Parameters
        ----------
        my_planning_grid

        """
        Ticket._create_new_tickets(my_planning_grid)
        for ticket_model in TicketModel.select():
            Ticket(ticket_model, my_planning_grid).draw_cells()

    @staticmethod
    # _create_new_tickets is a factory method, and as such, should be allowed to
    # access protected members of the class.
    def _create_new_tickets(my_planning_grid: planning_grid.PlanningGrid) -> None:
        TicketModel.create_ticket_new_projects()
        for ticket_model in TicketModel.get_tickets_new():
            ticket = Ticket(ticket_model, my_planning_grid)
            today_row = my_planning_grid.get_today_row()
            column = (
                ticket._get_column_owner_backlog()  # pylint: disable=protected-access
            )
            ticket.move_to(today_row, column, force_move=False)


class TicketMover:

    """
    The TicketMover handles moving ticket on the grid.

    Parameters
    ----------
    ticket
        The Ticket to move.

    """

    def __init__(self, ticket: Ticket):
        self.ticket: Ticket = ticket
        self._rows_taken: Dict[Row, CellModel] = {}
        self._rows_fixed: List[Row] = []
        self._ticket_cells_to_create: List[Tuple[Row, Column, TicketID]] = []
        self._ticket_cells_to_insert: List[TicketID] = []
        self._tickets_to_update: Set[TicketID] = set()

    def move_to(self, row: Row, column: Column, force_move: bool) -> None:
        """
        Moves the ticket to the specified coordinates.

        Parameters
        ----------
        row, column
            Destination coordinates for the first cell of the ticket.
        force_move
            If True, will move non-fixed ticket to take their place. If False, the
            ticket will only be inserted onto free cells.

        """
        self._init_values(row, column, force_move)
        current_row = row
        while self._ticket_cells_to_insert:
            while current_row in self._rows_fixed:
                current_row += 1
            self._insert_ticket_cell(current_row, column)
            current_row += 1
        self._create_new_cells()
        self._draw_tickets()

    def _init_values(self, row: Row, column: Column, force_move: bool) -> None:
        self._ticket_cells_to_create = []
        self._ticket_cells_to_insert = [
            self.ticket.ticket_model.id
        ] * self.ticket.length
        self._tickets_to_update.add(self.ticket.ticket_model.id)
        cells_below = CellModel.select(CellModel.row, CellModel.ticket).where(
            CellModel.column == column, CellModel.row >= row
        )
        for cell_model in cells_below:
            self._rows_taken[cell_model.row] = cell_model
            if cell_model.ticket.is_fixed or not force_move:
                self._rows_fixed.append(cell_model.row)

    def _insert_ticket_cell(self, current_row: Row, column: Column) -> None:
        ticket_id = self._ticket_cells_to_insert.pop(0)
        if current_row in self._rows_taken:
            ticket_old = self._rows_taken[current_row].ticket
            cell_to_update = CellModel.get(row=current_row, column=column)
            cell_to_update.ticket = ticket_id
            cell_to_update.save()
            self._ticket_cells_to_insert.append(ticket_old)
            self._tickets_to_update.add(ticket_old)
        else:
            self._ticket_cells_to_create.append((current_row, column, ticket_id))

    def _create_new_cells(self) -> None:
        CellModel.insert_many(  # pylint: disable=no-value-for-parameter
            self._ticket_cells_to_create,
            fields=[CellModel.row, CellModel.column, CellModel.ticket],
        ).execute()

    def _draw_tickets(self) -> None:
        for ticket in self._tickets_to_update:
            Ticket(
                TicketModel.get(id=ticket), self.ticket.planning_grid
            ).update_models()
            Ticket(TicketModel.get(id=ticket), self.ticket.planning_grid).draw_cells()
