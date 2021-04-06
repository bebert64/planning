# -*- coding: utf-8 -*-

"""
Defines :
 The PlanningGrid class.

"""


from __future__ import annotations

from datetime import timedelta, date
from typing import List, Optional, Iterable

from PySide6 import QtWidgets, QtGui, QtCore
from utils.my_custom_widget import MyCustomWidget
from utils.my_types import Pixel, Headers

from planning.config_planning.config_planning import config
from planning.model_drawer import Ticket
from planning.models import (
    Member,
    CellModel,
    FirstRow,
    TicketModel,
)
from planning.my_functions import date_to_string, string_to_date, add_workdays
from planning.my_types import Row, Column, Day
from planning.widgets.context_menus import CellMenu
from planning.widgets.model_modifier_widgets import (
    ProjectModifierWidget,
    TicketModifierWidget,
)


class PlanningGrid(  # pylint: disable=too-many-ancestors
    QtWidgets.QTableWidget, MyCustomWidget
):

    """
    The PlanningGrid is the grid where the tickets are displayed.

    It is the main element of the application and is structured with days as rows and
    members of the team as a group of column.

    Only working days are represented, and how far in the past and the future is
    determined by the parameters days_in_the_past and days_in_the_future. In the case
    where days_in_the_past would be too small to display all tickets (if one ticket
    is scheduled further back), additional rows will be created.

    For one member, we create two columns, one for the scheduled tickets, and one for
    the backlog, plus a third one just to visually separate the different team members.

    Warning
    -------
    This widget should not be instantiated directly, but rather through the factory
    method create_planning_grid.

    """

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.days_displayed: List[date] = []

    @classmethod
    def create_planning_grid(cls, parent: QtWidgets.QWidget) -> PlanningGrid:
        """Factory method to create the main window of the app."""
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        planning_grid = cls.create_widget(parent)
        assert isinstance(planning_grid, cls)
        planning_grid._init_table()
        planning_grid._connect_actions()
        planning_grid.draw_tickets()
        return planning_grid

    def _connect_actions(self) -> None:
        # pylint: disable=no-member
        self.cellClicked.connect(self._handle_cell_clicked)
        self.cellDoubleClicked.connect(self._handle_cell_double_clicked)

    def _init_table(self) -> None:
        grid_initializer = GridInitializer(self)
        grid_initializer.initialize_grid()
        self._scroll_to_today()

    def _scroll_to_today(self) -> None:
        start_row = self.get_today_row() - 4
        empty_item = QtWidgets.QTableWidgetItem()
        self.setItem(start_row, 0, empty_item)
        # Not sure why it's necessary to scroll to bottom first, but it doesn't work
        # without it.
        self.scrollToBottom()
        self.scrollToItem(empty_item, QtWidgets.QAbstractItemView.PositionAtTop)

    def get_today_row(self) -> Row:
        """
        The row corresponding to today or the next working day if today is in a weekend.
        """
        my_date = date.today()
        today_row = self._get_row_from_date(my_date)
        assert today_row is not None
        return today_row

    def _get_row_from_date(self, my_date: date) -> Optional[Row]:
        while my_date.weekday() >= 5:
            my_date = my_date + timedelta(days=1)
        assert len(self.days_displayed) == self.rowCount()
        try:
            row: Optional[Row] = self.days_displayed.index(my_date)
        except IndexError:
            row = None
        return row

    def get_date_from_row(self, row: Row) -> date:
        """The date corresponding to the row's header's label."""
        return string_to_date(self.verticalHeaderItem(row).text())

    def draw_tickets(self) -> None:
        """Draw all tickets on the grid."""
        self.setStyleSheet("QTableView::item {padding: 0px ; }")
        Ticket.draw_all_tickets(self)

    def refresh_grid(self, tickets: Optional[List[TicketModel]] = None) -> None:
        if tickets is None:
            tickets = TicketModel.select()
        total = len(tickets)
        counter = 0
        for ticket_model in tickets:
            ticket = Ticket(ticket_model, self)
            ticket.refresh()
            counter += 1
            print(f"{counter} sur {total}")

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        """
        If the drag & drop started on a cell with a ticket, moves the ticket
        to the dropEvent's location.
        """
        ticket = self._get_ticket_from_cell(self.currentRow(), self.currentColumn())
        if ticket is not None:
            destination = (self.rowAt(event.pos().y()), self.columnAt(event.pos().x()))
            ticket.move_to(*destination)
        self.clearSelection()

    def get_column_from_header(self, header: str) -> Optional[Column]:
        """
        The column's number with the specified header, or None if no column is found.
        """
        result = None
        for column in range(self.columnCount()):
            if self.horizontalHeaderItem(column).text() == header:
                result = column
        return result

    def _handle_cell_clicked(self, row: Row, column: Column) -> None:
        """
        Updates the selection.

        If the cell clicked is linked to a ticket, selects all cells from the ticket.
        If not, unselect all cells.

        """
        ticket = self._get_ticket_from_cell(row, column)
        if ticket is None:
            self.clearSelection()
        else:
            ticket.select_cells()

    def _handle_cell_double_clicked(self, row: Row, column: Column) -> None:
        ticket_model = CellModel.ticket_or_none(row, column)
        project_model = CellModel.project_or_none(row, column)
        if project_model is not None:
            assert ticket_model is not None
            project_widget = ProjectModifierWidget.create_widget_existing_project(
                project_model, ticket_model, self
            )
            project_widget.show()
        elif ticket_model is not None:
            ticket_widget = TicketModifierWidget.create_widget_existing_ticket(
                ticket_model, self
            )
            ticket_widget.show()

    def _get_ticket_from_cell(self, row: Row, column: Column) -> Optional[Ticket]:
        ticket_model = CellModel.ticket_or_none(row, column)
        if ticket_model is None:
            ticket = None
        else:
            ticket = Ticket(ticket_model, self)
        return ticket

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        column = self.currentColumn()
        if column % 3 != 2:
            row = self.currentRow()
            menu = CellMenu(self, row, column)
            menu_position = event.pos()
            self._open_context_menu(menu, menu_position)

    def _open_context_menu(self, menu: CellMenu, menu_position: QtCore.QPoint) -> None:
        menu.exec_(self.mapToGlobal(menu_position))

    def get_member_from_column(self, column: Column) -> Optional[Member]:
        """The member associated to the column, or None for the "separation" columns."""
        header = self.horizontalHeaderItem(column).text()
        if header == "":
            member = None
        else:
            if header == "Backlog":
                header = self.horizontalHeaderItem(column - 1).text()
            member = Member.get(Member.name == header)
        return member


class GridInitializer:

    """
    The GridInitializer is responsible for drawing the grid when the app starts.

    In addition to drawing the columns, it checks if the number of rows in the past is
    sufficient for all tickets to be drawn, and adds some if not.
    After the grid has been initialized, it also populates back the PlanningGrid
    attribute days_displayed, so that the grid itself can access the "real" days
    displayed.
    Finally, the GridInitializer modifies all cells' coordinates in the database, so
    that their row still corresponds to the same date as the last time the application
    was used.

    Parameters
    ----------
    planning_grid

    """

    def __init__(self, planning_grid: PlanningGrid) -> None:
        self._planning_grid: PlanningGrid = planning_grid
        self._days_displayed: List[date] = []
        self._horizontal_headers: Headers = []
        self._first_day: date

    def initialize_grid(self) -> None:
        """Draws all columns and rows, and updates the cells' coordinates."""
        self._create_all_columns()
        self._compute_first_day()
        self._create_rows()
        self._move_all_cells_up()
        self._planning_grid.days_displayed = self._days_displayed

    def _create_all_columns(self) -> None:
        grid = self._planning_grid
        for member in Member.select():
            self._create_member_columns(member)
        grid.removeColumn(0)
        assert grid.columnCount() == len(self._horizontal_headers)
        grid.setHorizontalHeaderLabels(self._horizontal_headers)
        header_view = grid.horizontalHeader()
        header_view.setStyleSheet("QHeaderView::section { color: white }")

    def _create_member_columns(self, member: Member) -> None:
        self._create_column(member.name, config["column_width"])
        self._create_column(config["column_backlog_name"], config["column_width"])
        self._create_column("", config["column_empty_width"])

    def _create_column(self, title: str, width: Pixel) -> None:
        grid = self._planning_grid
        grid.insertColumn(grid.columnCount())
        self._horizontal_headers.append(title)
        grid.setColumnWidth(grid.columnCount() - 1, width)

    def _compute_first_day(self) -> None:
        empty_rows_quantity = CellModel.select().order_by(CellModel.row).get().row
        date_first_row_old = FirstRow.get().date
        date_first_cell_old = add_workdays(date_first_row_old, empty_rows_quantity)
        date_first_row_from_parameters = date.today() - timedelta(
            days=config["days_in_the_past"]
        )
        if date_first_cell_old < date_first_row_from_parameters:
            PlanningGrid.display_msg_box(
                "Attention",
                "Certains tickets étant placés trop haut, des lignes supplémentaires "
                "ont été ajoutées en haut de la grille.",
            )
            self._first_day = date_first_cell_old
        else:
            self._first_day = date_first_row_from_parameters

    def _create_rows(self) -> None:
        grid = self._planning_grid
        self._compute_days_displayed()
        vertical_headers = [date_to_string(day) for day in self._days_displayed]
        for _ in range(1, len(vertical_headers)):
            grid.insertRow(0)
        assert grid.rowCount() == len(vertical_headers)
        grid.setVerticalHeaderLabels(vertical_headers)

    def _compute_days_displayed(self) -> None:
        days_in_the_past = date.today() - self._first_day
        total_days = days_in_the_past.days + config["days_in_the_future"]
        self._days_displayed = [
            self._first_day + timedelta(n)
            for n in range(total_days)
            if (self._first_day + timedelta(n)).weekday() <= 4
        ]

    def _move_all_cells_up(self) -> None:
        grid = self._planning_grid
        first_date_new = grid.get_date_from_row(0)
        delta = self._get_delta_cells(first_date_new)
        cells_ordered = self._get_cells_ordered(delta)
        for cell in cells_ordered:
            cell.delete_instance()
            cell.row = cell.row - delta
            cell.save(force_insert=True)
        FirstRow.get().update(date=first_date_new).execute()

    @staticmethod
    def _get_cells_ordered(delta: Day) -> Iterable[CellModel]:
        if delta > 0:
            cells_ordered = CellModel.select().order_by(CellModel.row)
        elif delta < 0:
            cells_ordered = CellModel.select().order_by(
                CellModel.row.desc()  # type: ignore
            )
        else:
            cells_ordered = []
        return cells_ordered

    @staticmethod
    def _get_delta_cells(first_date_new: date) -> Day:
        first_date_old = FirstRow.get().date
        delta_cells = 0
        step = 1 if first_date_old < first_date_new else -1
        while first_date_old != first_date_new:
            if first_date_old.weekday() <= 4:
                delta_cells += step
            first_date_old = first_date_old + timedelta(days=step)
        return delta_cells
