# -*- coding: utf-8 -*-

"""
Defines :
 One config instance, to be imported in all modules that might need it.

"""

from utils_by_db.config import Config
from utils_by_db.functions import get_data_folder


_ini_file = get_data_folder() / "config_planning.ini"
config = Config.create(_ini_file)
