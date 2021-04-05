# -*- coding: utf-8 -*-

"""
Defines the different models used by the application:

 The PlanningBaseModel class, base class for all the others.

 The FirstRow class.

 The Member class.

 The Status class.

 The ProjectModel class.

 The TicketModel class.

 The CellModel class.

"""

from __future__ import annotations

import datetime
import math
from typing import List, Optional

from peewee import (
    BooleanField,
    Model,
    ForeignKeyField,
    CharField,
    IntegerField,
    AutoField,
    CompositeKey,
    DecimalField,
    DateField,
    DoesNotExist,
)
from utils.config_database import ConfigDatabase
from utils.my_types import Row, Column

from planning.config_planning.config_planning import config
from planning.my_types import Day


class PlanningBaseModel(Model):
    """Base class, only used to set the database."""

    class Meta:  # pylint: disable=missing-class-docstring
        assert isinstance(config, ConfigDatabase)
        database = config.database


class FirstRow(PlanningBaseModel):
    """
    The date of the first row the last time the application was used.

    Used to compute by how many row all cells must be moved up when the application
    is opened.
    Only one row in the table, so there is no real need for a primary key.

    Attributes
    ----------
    date
        The date on the first row the last time the application was used (technically
        used as the primary key).

    """

    date: datetime.date = DateField(primary_key=True)

    class Meta:  # pylint: disable=missing-class-docstring
        table_name = "first_row"


class Member(PlanningBaseModel):

    """
    A member of the team.

    Attributes
    ----------
    name
        This is the primary key.
    free_time_percentage
        The percentage of the time the member dedicates to the tasks in the planning.
        Is equal to 100% minus the percentage of the time spent on tasks not tracked
        via this tool. Compulsory, default is 100.

    Properties
    ----------
    initials

    """

    name: str = CharField(primary_key=True)
    free_time_percentage: int = IntegerField()

    @property
    def initials(self) -> str:
        """The initials of the member, in the order first name / last name."""
        # pylint does not recognize a CharField object as being an instance of a string
        initials_list = [
            name_part[0]
            for name_part in self.name.split(" ")  # pylint: disable=no-member
        ]
        initials = "".join(initials_list)
        return initials

    def _get_last_project_key(self) -> str:
        try:
            last_key = (
                ProjectModel.select()
                .where(ProjectModel.id.startswith(self.initials))
                .order_by(ProjectModel.id.desc())  # type: ignore
                .get()
                .id
            )
        except DoesNotExist:
            last_key = f"{self.initials}00000"
        return last_key

    def get_next_available_key(self) -> str:
        """
        The next available key for a new project.

        More information on how the keys are formed available in the ProjectModel
        documentation.

        """

        last_key = self._get_last_project_key()
        assert last_key.startswith(self.initials)
        key_number = int(last_key[len(self.initials) :])
        key_number += 1
        next_available_key = f"{self.initials}{key_number:05d}"
        return next_available_key


class Status(PlanningBaseModel):

    """
    Fixed list of all available status for a project.

    Parameters
    ----------
    name
    position
        Used to display the status in a specific order.
    is_drawn
        Whether or not a project with this status needs to be displayed on the grid.
    """

    name: str = CharField(primary_key=True)
    position: int = IntegerField()
    is_drawn: bool = BooleanField()


class ProjectModel(PlanningBaseModel):

    """
    A project is a task to be accomplished by a member.

    A project can be represented on the grid by 0, 1 or several tickets.

    Parameters
    ----------
    id
        The key for the project. Formed by the initials of the member followed by an
        incremental number on 5 digits.
    name
        Short name for the project. Compulsory, no default value.
    group
        Used to indicate that the project is part of a group of several. Optional and
        only used for statistical analysis.
    description
        Longer text explaining the project in more details. Optional.
    comments
        Optional.
    origin
        A GLPI ticket number, or the email of the person initially asking for the task.
        Optional.
    site
        The Autajon plant asking for the development. Optional.
    tiers
        The name of an entity external to the Autajon group linked to the project.
        Optional.
    systems
        The systems (CERM, AS400) impacted by the tasks. Optional.
    status
        One of the available Status (foreign key to the "status" table). Compulsory,
        default is "active".
    deadline
        If existing, can be used to check if the estimated end_date is late. Optional.
    charge
        The number of days it would take to complete the task if the member could
        focus on it at 100%. The free_time_percentage of the member is then taken into
        account to calculate a "real" estimated time. Compulsory, default is 0 (in
        which case the project exists in the database, but is not visible on the
        planning grid).
    owner
        The member of the team to whom the task is attributed. Compulsory, no default
        value.
    start_date
        The date at which the work on the task should start.
    end_date
        The estimated end date for the project. If one or more of the tickets
        associated with the project are still in the backlog, the end_date is null.

    Properties
    ----------
    duration

    """

    id: str = CharField(primary_key=True)
    name: str = CharField()
    group: str = CharField()
    description: str = CharField()
    comments: str = CharField()
    origin: str = CharField()
    site: str = CharField()
    tiers: str = CharField()
    systems: str = CharField()
    status: Status = ForeignKeyField(Status, column_name="status")
    deadline: Optional[datetime.date] = DateField()
    charge: float = DecimalField()
    owner: Member = ForeignKeyField(Member, column_name="owner")
    start_date: Optional[datetime.date] = DateField()
    end_date: Optional[datetime.date] = DateField()

    class Meta:  # pylint: disable=missing-class-docstring
        table_name = "project"

    # ==================================================================================
    #
    # Will be used on a future version, when the systems have their own table
    #
    # def get_systems(self) -> List[str]:
    #     return [
    #         project_system.system
    #         for project_system in ProjectSystem.select().where(
    #             ProjectSystem.project == self.name
    #         )
    #     ]
    #
    # ==================================================================================

    @staticmethod
    def get_projects_new() -> List[ProjectModel]:
        """
        A list of the new projects.

        A project is defined as new if :
         - its status indicates it needs to be drawn,
         - its charge is greater than 0,
         - no tickets are linked to it.

        """
        projects_new = []
        for project in (
            ProjectModel.select()
            .join(Status)
            .where(ProjectModel.charge != 0, Status.is_drawn == 1)
        ):
            ticket = TicketModel.get_or_none(project=project.id)
            if ticket is None:
                projects_new.append(project)
        return projects_new

    @property
    def duration(self) -> Day:
        """
        The estimation of the time the project will take to be completed.

        Based on the estimated charge, and the member's free_time_percentage.

        """
        return math.ceil(self.charge / self.owner.free_time_percentage * 100)

    def get_tickets_duration(self) -> Day:
        tickets = (
            TicketModel.select().join(ProjectModel).where(ProjectModel.id == self.id)
        )
        tickets_duration = 0
        for ticket_model in tickets:
            tickets_duration += ticket_model.duration
        return tickets_duration


class TicketModel(PlanningBaseModel):

    """
    A ticket is a "task" that can be scheduled independently.

    A project both "active" and with a charge greater than 0 days will have at least
    one ticket, but can be split into more if we need to schedule different phases
    independently. A ticket can also exists without a project (ex: holidays).

    Parameters
    ----------
    id
        Primary key, incremental number.
    owner
        The team member to whom the ticket is affected. Compulsory, no default value.
    description
        If not null, the description is used to write on the planning grid. If null,
        the project's short name is used instead.
    is_scheduled
        Whether the ticket is scheduled or is still in a "Backlog" column. Compulsory,
        default is False
    duration
        The duration of the ticket in days. Compulsory, default is 0 (in which case the
        project's duration will be used to draw the ticket instead).
    advancement
        The number of days already done on the ticket. Will be removed from the duration
        before drawing the ticket. Compulsory, default is 0.

    Properties
    ----------
    first_cell
    """

    id: int = AutoField()
    owner: Model = ForeignKeyField(Member, column_name="owner")
    description: str = CharField()
    is_scheduled: bool = BooleanField()
    project: ProjectModel = ForeignKeyField(
        ProjectModel, column_name="project", backref="tickets"
    )
    is_fixed: bool = BooleanField()
    duration: int = IntegerField()
    advancement: int = IntegerField()

    class Meta:  # pylint: disable=missing-class-docstring
        table_name = "ticket"

    @staticmethod
    def get_tickets_new() -> List[TicketModel]:
        """The list of tickets with no CellModel associated."""
        new_tickets = []
        for ticket in TicketModel.select():
            first_cell = CellModel.get_or_none(ticket=ticket.id)
            if first_cell is None:
                new_tickets.append(ticket)
        return new_tickets

    @staticmethod
    def create_ticket_new_projects() -> None:
        """Creates TicketModel objects for projects without one."""
        for new_project in ProjectModel.get_projects_new():
            new_ticket_model = TicketModel(
                owner=new_project.owner, description="", project=new_project.id,
            )
            new_ticket_model.save()

    def project_or_none(self) -> Optional[ProjectModel]:
        """Returns the project linked to the ticket or None."""
        try:
            project: Optional[ProjectModel] = self.project
        except DoesNotExist:
            project = None
        return project

    @property
    def first_cell_or_none(self) -> Optional[CellModel]:
        """The cell with the lowest row number on the ticket."""
        try:
            first_cell = (
                CellModel.select()
                .where(CellModel.ticket == self.id)
                .order_by(CellModel.row)
                .get()
            )
        except DoesNotExist:
            first_cell = None
        return first_cell

    @property
    def last_cell_or_none(self) -> Optional[CellModel]:
        """The cell with the highest row number on the ticket."""
        try:
            last_cell = (
                CellModel.select()
                .where(CellModel.ticket == self.id)
                .order_by(CellModel.row.desc())  # type: ignore
                .get()
            )
        except DoesNotExist:
            last_cell = None
        return last_cell

    def get_title(self) -> str:
        """The title to be written on the first cell on the grid."""
        if self.description != "":
            title = self.description
        elif (project := self.project_or_none()) is not None:
            title = project.name
        else:
            title = "N/A"
        return title

    def needs_being_erased(self):
        project_model = self.project_or_none()
        return False if project_model is None else not project_model.status.is_drawn

    @property
    def length(self) -> Day:
        """The number of cells needed to draw the ticket."""
        if self.needs_being_erased():
            length = 0
        else:
            length = self._get_length_from_model()
        return length

    def _get_length_from_model(self) -> int:
        if self.duration != 0:
            duration = self.duration
        else:
            project_model = self.project
            duration_total = project_model.duration
            duration_other_tickets = project_model.get_tickets_duration()
            duration = duration_total - duration_other_tickets
        length = max(duration - self.advancement, 0)
        return length


class CellModel(PlanningBaseModel):

    """
    Represents a cell in the planning grid.

    Parameters
    ----------
    row
    column
    ticket
        The TicketModel to which the cell is linked (foreign key to the "ticket" table).
    is_top_cell
        Whether or not the cell is the first one of a ticket (or a part of a ticket in
        the case of a ticket split in two or more). Used to know whether or not the
        cell will need a top border when drawing the ticket.
    is_bottom_cell
        Whether or not the cell is the last one of a ticket (or a part of a ticket in
        the case of a ticket split in two or more). Used to know whether or not the
        cell will need a bottom border when drawing the ticket.
    """

    row: int = IntegerField()
    column: int = IntegerField()
    ticket: TicketModel = ForeignKeyField(TicketModel, column_name="ticket")
    is_top_cell: bool = BooleanField()
    is_bottom_cell: bool = BooleanField()

    class Meta:  # pylint: disable=missing-class-docstring
        primary_key = CompositeKey("row", "column")
        table_name = "cell"

    def update_model(self) -> None:
        """Updates is_top_cell and is_bottom_cell after moving a ticket on the grid."""
        cell_above = CellModel.get_or_none(
            row=self.row - 1, column=self.column, ticket=self.ticket
        )
        self.is_top_cell = cell_above is None
        cell_under = CellModel.get_or_none(
            row=self.row + 1, column=self.column, ticket=self.ticket
        )
        self.is_bottom_cell = cell_under is None
        self.save()

    def is_fixed(self) -> bool:
        """Whether or not the cell is linked to a fixed ticket."""
        is_fixed = self.ticket.is_fixed
        return is_fixed

    def _is_project_status(self, status: str) -> bool:
        ticket_model = self.ticket
        project_model = ticket_model.project_or_none()
        is_status = (
            False if project_model is None else project_model.status.name == status
        )
        return is_status

    def is_delivered(self) -> bool:
        """Whether or not the cell is linked to a project with status "delivered"."""
        is_delivered = self._is_project_status("delivered")
        return is_delivered

    def is_stand_by(self) -> bool:
        """Whether or not the cell is linked to a project with status "stand-by"."""
        is_stand_by = self._is_project_status("stand-by")
        return is_stand_by

    @staticmethod
    def ticket_or_none(row: Row, column: Column) -> Optional[TicketModel]:
        """Returns the ticket linked to the cell at row and column or None."""
        cell = CellModel.get_or_none(row=row, column=column)
        if cell is None:
            ticket_model = None
        else:
            ticket_id = cell.ticket
            ticket_model = TicketModel.get(id=ticket_id)
        return ticket_model

    @staticmethod
    def project_or_none(row: Row, column: Column) -> Optional[ProjectModel]:
        """Returns the project linked to the cell at row and column or None."""
        ticket_model = CellModel.ticket_or_none(row, column)
        if ticket_model is None:
            project_model = None
        else:
            project_model = ticket_model.project_or_none()
        return project_model


# class ProjectSystem(PlanningBaseModel):
#
#     project: str = ForeignKeyField(ProjectModel)
#     system: str = CharField()
