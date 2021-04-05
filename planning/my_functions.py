# -*- coding: utf-8 -*-

"""
Defines generic functions used by the different modules:
 date_to_string and its reverse string_to_date

"""


from datetime import date, timedelta, datetime

from planning.config_planning.config_planning import config
from planning.my_types import Day


def date_to_string(my_date: date) -> str:
    """Transforms a date into a string, using the format defined in the config."""
    return my_date.strftime(config["date_format"])


def string_to_date(date_as_string: str) -> date:
    """Transforms a string into a date, using the format defined in the config."""
    return datetime.strptime(date_as_string, config["date_format"]).date()


def add_workdays(my_date: date, workdays: Day) -> date:
    """Adds a specified number of workdays to the date."""
    for _ in range(workdays):
        my_date = my_date + timedelta(days=1)
        while my_date.weekday() >= 5:
            my_date = my_date + timedelta(days=1)
    return my_date
