# -*- coding: utf-8 -*-

"""
Defines :
 The ExcelInterface base class.

 The Importer and Exporter derived classes.

 The ProjectModification class.

 Two dictionaries for translating the headers' names from the Excel files to the
 database in both directions.

"""


from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Dict

import pandas
import xlsxwriter

import planning.widgets.my_main_window as main_window
from planning.config_planning.config_planning import config
from planning.models import ProjectModel, Member
from planning.widgets.importer_result_widget import ImporterResultWidget


class ExcelInterface:

    """
    Base class for the Importer and the Exporter.

    Parameters
    ----------
    member
        The member of the team's whose projects we need to import.

    """

    def __init__(self, member: Member):
        self.member: Member = member

    @property
    def _excel_file_name(self) -> str:
        initials = self.member.initials
        excel_file_name = f"Taches {initials}.xlsx"
        return excel_file_name


class Importer(ExcelInterface):

    """
    Class responsible for importing a member's list of projects from an Excel file.

    Parameters
    ----------
    member
        The member of the team's whose projects we need to import.
    my_main_window
        The MyMainWindow object onto which the tickets associated with the new projects
        will be drawn.

    """

    def __init__(
        self, member: Member, my_main_window: main_window.MyMainWindow
    ) -> None:
        super().__init__(member)
        self.my_main_window: main_window.MyMainWindow = my_main_window
        self._excel_file_path: Path = config[
            "excel_folder_path"
        ] / self._excel_file_name
        self._result_widget: ImporterResultWidget

    def _add_new_project(self, data: pandas.Series) -> None:
        project = ProjectModel(owner=self.member)
        for header, value in data.items():
            if not pandas.isnull(value):
                setattr(project, header, value)
        self._result_widget.add_new_project(project)

    def _update_project(self, project: ProjectModel, data: pandas.Series) -> None:
        for field_name in config["fields_update_auto"]:
            project_modification = self._create_project_modification(
                data, field_name, project
            )
            if project_modification is not None:
                self._result_widget.add_modification_auto(project_modification)
        for field_name in config["fields_update_manual"]:
            project_modification = self._create_project_modification(
                data, field_name, project
            )
            if project_modification is not None:
                self._result_widget.add_modification_validate(project_modification)

    @staticmethod
    def _create_project_modification(
        data: pandas.Series, field_name: str, project: ProjectModel
    ) -> Optional[ProjectModification]:
        value_old = getattr(project, field_name)
        value_new = data[field_name] if not pandas.isnull(data[field_name]) else None
        if field_name == "status" and value_new is None:
            value_new = "active"
        if Importer._are_different(value_old, value_new):
            project_modification: Optional[ProjectModification] = ProjectModification(
                project, field_name, value_new
            )
        else:
            project_modification = None
        return project_modification

    @staticmethod
    def _are_different(value_old: Any, value_new: Any) -> bool:
        if str(value_old) == str(value_new):
            are_different = False
        elif not (value_old or value_new):
            are_different = False
        else:
            try:
                are_different = float(value_old) != float(value_new)
            except (ValueError, TypeError):
                are_different = True
        return are_different

    def analyse_excel(self) -> None:
        """
        Loads the data from the Excel file and updates the database.

        The path to the folder of the file is defined in the parameters
        (excel_folder_path), and the name of the file itself is "Taches " followed by
        the initials of the team member (in .xlsx format).
        The method will then updates projects already existing in the database and
        creates new ones.

        Depending on the field which have been modified, the update will either be done
        automatically or will need to be validated. Which field is linked to which
        behaviour is editable directly in the database, through the parameters
        "fields_update_auto" and "fields_update_manual"

        """
        data_frame = pandas.read_excel(self._excel_file_path, engine="openpyxl")
        data_frame.rename(columns=excel_to_database, inplace=True)
        self._result_widget = ImporterResultWidget.create_importer_result_widget(self)
        self._result_widget.show()
        for _, data in data_frame.iterrows():
            project = ProjectModel.get_or_none(id=data.id)
            if project is None:
                self._add_new_project(data)
            else:
                self._update_project(project, data)


class ProjectModification:

    """
    A proposed modification, which can be accepted or not.

    Parameters
    ----------
    project
        The project to update.
    field
        The field to update.
    value_new
        The proposed new value.

    Attributes
    ----------
    value_database

    """

    def __init__(self, project: ProjectModel, field: str, value_new: Any) -> None:
        self.project: ProjectModel = project
        self.field: str = field
        self.value_new: Any = value_new

    @property
    def value_database(self) -> Any:
        """The value currently stored in the database."""
        return getattr(self.project, self.field)

    def accept(self) -> None:
        """Updates the project's field value with value_new."""
        setattr(self.project, self.field, self.value_new)
        self.project.save()

    def __str__(self) -> str:
        if self.field == "name":
            string = (
                f"{self.project.id}'s {self.field} : "
                f"{self.value_database} => {self.value_new}"
            )
        else:
            string = (
                f"{self.project.id}'s ({self.project.name}) {self.field} : "
                f"{self.value_database} => {self.value_new}"
            )
        return string


class Exporter(ExcelInterface):

    """
    Class responsible for exporting a member's list of projects to an Excel file.

    Parameters
    ----------
    member
        The member of the team's whose projects we need to export.

    """

    def __init__(self, member: Member) -> None:
        super().__init__(member)
        self._excel_file_path: Path = config[
            "excel_folder_path"
        ] / self._excel_file_name
        self._writer: pandas.ExcelWriter = pandas.ExcelWriter(  # pylint: disable=abstract-class-instantiated
            self._excel_file_path, engine="xlsxwriter"
        )
        self._data_frame: pandas.DataFrame
        self._workbook: xlsxwriter.workbook.Workbook
        self._worksheet: xlsxwriter.workbook.Worksheet

    def to_excel(self) -> None:
        """
        Dumps the data into an Excel file and formats it as an Excel table.

        The path to the folder of the file is defined in the parameters
        (excel_folder_path), and the name of the file itself is "Taches " followed by
        the initials of the team member (in .xlsx format).

        """
        self._init_member_data_frame()
        self._data_frame.to_excel(
            self._writer, sheet_name="Sheet1", index=False, header=False, startrow=1
        )
        self._workbook = self._writer.book  # pylint: disable=no-member
        self._worksheet = self._workbook.worksheets()[0]
        self._add_table()
        self._format_column()
        self._writer.save()

    def _add_table(self) -> None:
        (max_row, max_col) = self._data_frame.shape
        column_settings = [{"header": column} for column in self._data_frame.columns]
        self._worksheet.add_table(
            0, 0, max_row, max_col - 1, {"columns": column_settings}
        )
        self._worksheet.set_column(0, max_col - 1, 12)

    def _init_member_data_frame(self) -> None:
        projects = ProjectModel.select().join(Member).where(Member.name == self.member)
        data_frame = pandas.DataFrame(list(projects.dicts()))
        data_frame.rename(columns=database_to_excel, inplace=True)
        del data_frame["owner"]
        self._data_frame = data_frame

    def _format_column(self) -> None:
        length_list = [
            max([len(str(s)) for s in self._data_frame[col].values] + [len(col) + 2])
            for col in self._data_frame.columns
        ]
        column_format = self._workbook.add_format({"text_wrap": True, "valign": "top"})
        for i, width in enumerate(length_list):
            width = min(width, 50)
            width = max(width, 10)
            self._worksheet.set_column(i, i, width, column_format)


database_to_excel: Dict[str, str] = {
    "id": "Id",
    "name": "Nom",
    "group": "Groupe",
    "description": "Description",
    "comments": "Commentaires",
    "origin": "Origine",
    "site": "Site",
    "tiers": "Tiers",
    "systems": "Systemes / ERP",
    "status": "Statut",
    "deadline": "Deadline",
    "charge": "Charge",
    "start_date": "Date de début",
    "end_date": "Date de fin prévue",
}


def _invert_dictionary(dictionary: Dict[str, str]) -> Dict[str, str]:
    dictionary_inverted = {}
    for key, value in dictionary.items():
        dictionary_inverted[value] = key
    return dictionary_inverted


excel_to_database: Dict[str, str] = _invert_dictionary(database_to_excel)
