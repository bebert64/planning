# -*- coding: utf-8 -*-

"""
Defines :
 The ModelModifierWidget base class.

 The ProjectModifierWidget and TicketModifierWidget classes, derived from
 ModelModifierWidget

 The TicketInfoWidget class.

"""

from __future__ import annotations

import datetime
from typing import Dict, Tuple, Optional, List

from PySide6 import QtWidgets
from utils.my_custom_widget import MyCustomWidget

import planning.widgets.planning_grid as planning_grid
from planning.model_drawer import Ticket
from planning.models import TicketModel, ProjectModel, Status, CellModel
from planning.my_functions import date_to_string, string_to_date
from planning.my_types import Row, Column


class ModelModifierWidget:

    """
    A ModelModifierWidget is an gui allowing the user to modify information stored in
    the database.

    This is a base class, meant to be subclassed and cannot be used by itself.

    Class Attribute
    ---------------
    field_setter_getter
        A dictionary linking a TicketModel attribute to a tuple with the widget that
        will display this information, and its setter and getter methods.

    """

    field_setter_getter: Dict[str, Tuple[str, str, str]] = {}

    def __init__(self) -> None:
        super().__init__()
        self._model: ProjectModel

    def init_values(self) -> None:
        """
        Displays the information in the appropriate subwidgets.

        The list of information to display with their associated subwidgets is
        defined in the class attribute field_setter_getter.

        """
        for (field, (widget_name, setter, _)) in self.field_setter_getter.items():
            value = getattr(self._model, field)
            widget = getattr(self, widget_name)
            widget_setter = getattr(widget, setter)
            widget_setter(value)

    def save_values(self) -> None:
        """
        Saves the information currently displayed in the database.

        The list of information to save is defined in the class attribute
        field_setter_getter.

        """
        for (field, (widget_name, _, getter),) in self.field_setter_getter.items():
            widget = getattr(self, widget_name)
            widget_getter = getattr(widget, getter)
            value = widget_getter()
            setattr(self._model, field, value)
        self._model.save()


class ProjectModifierWidget(QtWidgets.QWidget, MyCustomWidget, ModelModifierWidget):

    """
    GUI for accessing a project's information stored in the database.

    Warning
    -------
    This widget should not be instantiated directly, but rather through one of the
    factory methods, create_widget_existing_project or create_widget_new_project.

    """

    field_setter_getter = {
        "name": ("title_line_edit", "setText", "text"),
        "group": ("group_line_edit", "setText", "text"),
        "description": ("description_text_edit", "setPlainText", "toPlainText"),
        "comments": ("comments_text_edit", "setPlainText", "toPlainText"),
        "charge": ("charge_spin_box", "setValue", "value"),
        "origin": ("origin_line_edit", "setText", "text"),
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.planning_grid: planning_grid.PlanningGrid
        self.ticket_clicked: TicketModel
        self.first_cell_model: Optional[CellModel] = None

    @classmethod
    def create_widget_existing_project(
        cls,
        project_model: ProjectModel,
        ticket_clicked: TicketModel,
        my_planning_grid: planning_grid.PlanningGrid,
    ) -> ProjectModifierWidget:
        """
        Factory method to create a ProjectModifierWidget for an existing project.

        Parameters
        ----------
        project_model
        ticket_clicked
            The ticket through which the project is accessed (the project themselves are
            not displayed on the grid).
        my_planning_grid
            The planning grid (used to redraw the modified tickets if/when necessary).

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        project_widget = cls.create_widget()
        assert isinstance(project_widget, cls)
        project_widget.project_model = project_model
        project_widget.ticket_clicked = ticket_clicked
        project_widget.planning_grid = my_planning_grid
        project_widget.init_values()
        project_widget._add_ticket_modifier_widgets()
        project_widget._connect_actions()
        project_widget.setWindowTitle(project_model.id)
        return project_widget

    @classmethod
    def create_widget_new_project(
        cls, row: Row, column: Column, my_planning_grid: planning_grid.PlanningGrid,
    ) -> ProjectModifierWidget:
        """
        Factory method to create a ProjectModifierWidget for a new project.

        Parameters
        ----------
        row, column
            The coordinates of the cell where the project will be created.
        my_planning_grid
            The planning grid (used to draw the new tickets).

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        (
            project_model,
            ticket_model,
            first_cell_model,
        ) = ProjectModifierWidget._create_models(row, column, my_planning_grid)
        project_widget = cls.create_widget_existing_project(
            project_model, ticket_model, my_planning_grid
        )
        project_widget.first_cell_model = first_cell_model
        assert isinstance(project_widget, cls)
        return project_widget

    @staticmethod
    def _create_models(
        row: Row, column: Column, my_planning_grid: planning_grid.PlanningGrid
    ) -> Tuple[ProjectModel, TicketModel, CellModel]:
        owner = my_planning_grid.get_member_from_column(column)
        assert owner is not None
        project_model = ProjectModel(
            name="",
            charge=1,
            owner=owner,
            id=owner.get_next_available_key(),
            status="active",
        )
        ticket_model = TicketModel(
            owner=owner,
            description="",
            is_fixed=False,
            duration=0,
            advancement=0,
            project=project_model,
        )
        first_cell_model = CellModel(ticket=ticket_model, row=row, column=column)
        return project_model, ticket_model, first_cell_model

    @property
    def project_model(self) -> ProjectModel:
        """The model which information's are accessed."""
        return self._model

    @project_model.setter
    def project_model(self, project_model: ProjectModel) -> None:
        self._model = project_model

    def init_values(self) -> None:
        """
        Displays the information in the appropriate subwidgets.

        The list of information to display with their associated subwidgets is
        defined in the class attribute field_setter_getter. In addition, the method
        also display the project's status and end date.

        """
        ModelModifierWidget.init_values(self)
        self._init_status()
        self._init_end_date()
        self._init_deadline()

    def _init_status(self) -> None:
        for status in Status.select().order_by(Status.position):
            self.status_combo_box.addItem(status.name)
        self.status_combo_box.setCurrentText(self.project_model.status.name)

    def _init_end_date(self) -> None:
        end_date = self.project_model.end_date
        if end_date is None:
            end_date_str = "Backlog"
        else:
            end_date_str = date_to_string(end_date)
        self.end_date_line_edit.setText(end_date_str)

    def _init_deadline(self) -> None:
        deadline = self.project_model.deadline
        if deadline is None:
            deadline_str = ""
        elif isinstance(deadline, datetime.date):
            deadline_str = date_to_string(deadline)
        else:
            deadline_str = deadline
        self.deadline_line_edit.setText(deadline_str)

    def _add_ticket_modifier_widgets(self) -> None:
        layout = self.scrollAreaWidgetContents.layout()
        ticket_models = self._get_ticket_models()
        ticket_counter = 1
        for ticket_model in ticket_models:
            self._add_empty_space()
            self._add_ticket(ticket_model, ticket_counter, layout)
            ticket_counter += 1

    def _add_ticket(
        self, ticket_model: TicketModel, ticket_counter: int, layout: QtWidgets.QLayout
    ) -> None:
        ticket_widget = TicketInfoWidget.create_ticket_info_widget(self, ticket_model)
        layout.addWidget(ticket_widget)
        ticket_widget.set_title(f"Ticket {ticket_counter}")
        if ticket_model == self.ticket_clicked:
            ticket_widget.highlight()

    def _add_empty_space(self) -> None:
        empty_label = QtWidgets.QLabel(self)
        layout = self.scrollAreaWidgetContents.layout()
        layout.addWidget(empty_label)

    def _connect_actions(self) -> None:
        self.cancel_button.clicked.connect(self.close)
        self.ok_button.clicked.connect(self._handle_ok)
        self.add_ticket_button.clicked.connect(self._create_ticket)

    def _handle_ok(self) -> None:
        self._save_project_values()
        self._save_ticket_values()
        if self.first_cell_model is not None:
            self.first_cell_model.save(force_insert=True)
        self._refresh_tickets()
        self.close()

    def _create_ticket(self) -> None:
        new_ticket = TicketModel(
            owner=self.project_model.owner,
            project=self.project_model,
            duration=1,
            is_fixed=False,
            advancement=0,
        )
        layout = self.scrollAreaWidgetContents.layout()
        ticket_counter = len(self._find_ticket_widgets(self)) + 1
        self._add_empty_space()
        self._add_ticket(new_ticket, ticket_counter, layout)

    def _save_project_values(self) -> None:
        self.save_values()
        self._save_deadline()
        self.project_model.status = self.status_combo_box.currentText()
        if (
            ProjectModel.select()
            .where(ProjectModel.id == self.project_model.id)
            .exists()
        ):
            self.project_model.save()
        else:
            self.project_model.save(force_insert=True)

    def _save_deadline(self) -> None:
        deadline_str = self.deadline_line_edit.text()
        if deadline_str != "":
            deadline = string_to_date(deadline_str)
            self.project_model.deadline = deadline

    def _save_ticket_values(self) -> None:
        for ticket_modifier_widget in self._find_ticket_widgets(self):
            ticket_modifier_widget.save_values()

    def _refresh_tickets(self) -> None:
        ticket_models = self._get_ticket_models()
        for ticket_model in ticket_models:
            ticket = Ticket(ticket_model, self.planning_grid)
            ticket.refresh()

    def _get_ticket_models(self) -> List[TicketModel]:
        ticket_models = list(
            TicketModel.select().where(TicketModel.project == self.project_model.id)
        )
        if len(ticket_models) == 0:
            ticket_models = [self.ticket_clicked]
        return ticket_models

    def _find_ticket_widgets(
        self,
        widget: QtWidgets.QWidget,
        ticket_widgets: Optional[List[TicketInfoWidget]] = None,
    ) -> List[TicketInfoWidget]:
        if ticket_widgets is None:
            ticket_widgets = []
        for child in widget.children():
            if isinstance(child, TicketInfoWidget):
                ticket_widgets.append(child)
            ticket_widgets = self._find_ticket_widgets(child, ticket_widgets)
        return ticket_widgets


class TicketInfoWidget(QtWidgets.QWidget, MyCustomWidget, ModelModifierWidget):

    """
    The TicketInfoWidget can get and set properties of a ticket.

    It is designed to be used inside another widget, either as part of a
    ProjectModifierWidget or in a TicketModifierWidget.

    Warning
    -------
    This widget should not be instantiated directly, but rather through the factory
    method create_ticket_info_widget.

    """

    field_setter_getter: Dict[str, Tuple[str, str, str]] = {
        "description": ("title_line_edit", "setText", "text"),
        "duration": ("duration_spin_box", "setValue", "value"),
        "is_fixed": ("fixed_check_box", "setChecked", "isChecked"),
        "advancement": ("advancement_spin_box", "setValue", "value"),
    }

    @classmethod
    def create_ticket_info_widget(
        cls, parent: Optional[QtWidgets.QWidget], ticket_model: TicketModel
    ) -> TicketInfoWidget:
        """
        Factory method to create a TicketInfoWidget.

        Parameters
        ----------
        parent
        ticket_model

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        ticket_info_widget = cls.create_widget(parent)
        assert isinstance(ticket_info_widget, cls)
        ticket_info_widget.ticket_model = ticket_model
        ticket_info_widget.init_values()
        return ticket_info_widget

    @property
    def ticket_model(self) -> TicketModel:
        """The model which information's are accessed."""
        return self._model

    @ticket_model.setter
    def ticket_model(self, ticket_model) -> None:
        self._model = ticket_model

    def init_values(self) -> None:
        """
        Displays the information in the appropriate subwidgets.

        The list of information to display with their associated subwidgets is
        defined in the class attribute field_setter_getter. In addition, the method
        also display the project's duration after the ticket length (if a project
        is found).

        """
        ModelModifierWidget.init_values(self)
        self._modify_duration_label()

    def _modify_duration_label(self) -> None:
        project = self.ticket_model.project_or_none()
        if project is not None:
            duration_label = self.duration_label.text()
            duration_label += f" ({project.duration})"
            self.duration_label.setText(duration_label)

    def set_title(self, title: str) -> None:
        """Sets the group box title."""
        self.group_box.setTitle(title)

    def highlight(self) -> None:
        """Highlight the widget by putting a green border around its group box."""
        self.group_box.setObjectName("ColoredGroupBox")
        self.group_box.setStyleSheet(
            "QGroupBox#ColoredGroupBox { border: 2px solid green;}"
        )


class TicketModifierWidget(QtWidgets.QWidget, MyCustomWidget):

    """
    GUI for accessing a ticket's information stored in the database.

    This GUI is used when the ticket is not linked to a project.

    Warning
    -------
    This widget should not be instantiated directly, but rather through one of the
    factory methods, create_widget_existing_ticket or create_widget_new_ticket.

    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._planning_grid: planning_grid.PlanningGrid
        self._ticket_model: TicketModel
        self._ticket_info_widget: TicketInfoWidget
        self.first_cell_model: Optional[CellModel] = None

    @classmethod
    def create_widget_new_ticket(
        cls, row: Row, column: Column, my_planning_grid: planning_grid.PlanningGrid
    ) -> TicketModifierWidget:
        """
        Factory method to create a TicketModifierWidget for a new ticket.

        Parameters
        ----------
        row, column
            The coordinates of the cell where the ticket will be created.
        my_planning_grid

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        ticket_model, first_cell_model = TicketModifierWidget._create_ticket_model(
            row, column, my_planning_grid
        )
        ticket_modifier_widget = cls.create_widget_existing_ticket(
            ticket_model, my_planning_grid
        )
        ticket_modifier_widget.first_cell_model = first_cell_model
        assert isinstance(ticket_modifier_widget, cls)
        ticket_modifier_widget.setWindowTitle("Nouveau ticket")
        return ticket_modifier_widget

    @classmethod
    def create_widget_existing_ticket(
        cls, ticket_model: TicketModel, my_planning_grid: planning_grid.PlanningGrid
    ) -> TicketModifierWidget:
        """
        Factory method to create a TicketModifierWidget for an existing ticket.

        Parameters
        ----------
        ticket_model
        my_planning_grid

        """
        # create_tab_widget is a factory method, and should therefore be allowed
        # to access protected members of the class.
        # pylint: disable = protected-access
        ticket_modifier_widget = cls.create_widget(None)
        assert isinstance(ticket_modifier_widget, cls)
        ticket_modifier_widget._planning_grid = my_planning_grid
        ticket_modifier_widget._ticket_model = ticket_model
        ticket_modifier_widget._connect_actions()
        ticket_modifier_widget._add_ticket_info_widget()
        ticket_modifier_widget.setWindowTitle("Edition ticket")
        return ticket_modifier_widget

    def _connect_actions(self) -> None:
        self.cancel_button.clicked.connect(self.close)
        self.ok_button.clicked.connect(self._handle_ok)

    def _handle_ok(self) -> None:
        self._ticket_info_widget.save_values()
        if self.first_cell_model is not None:
            self.first_cell_model.save(force_insert=True)
        ticket = Ticket(self._ticket_model, self._planning_grid)
        ticket.refresh()
        self.close()

    @staticmethod
    def _create_ticket_model(
        row: Row, column: Column, my_planning_grid: planning_grid.PlanningGrid
    ) -> Tuple[TicketModel, CellModel]:
        owner = my_planning_grid.get_member_from_column(column)
        ticket_model = TicketModel(
            owner=owner, description="", is_fixed=False, duration=1, advancement=0
        )
        first_cell_model = CellModel(row=row, column=column, ticket=ticket_model)
        return ticket_model, first_cell_model

    def _add_ticket_info_widget(self) -> None:
        self._ticket_info_widget = TicketInfoWidget.create_ticket_info_widget(
            self, self._ticket_model
        )
        self.ticket_widget_layout.addWidget(self._ticket_info_widget)
