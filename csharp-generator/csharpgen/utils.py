import os
from datetime import datetime


def get_root_path():
    """Returns project's root path."""
    path = os.path.split(os.path.abspath(os.path.dirname(__file__)))[0]
    return path


def get_templates_path():
    """Returns the path to the templates folder."""
    return os.path.join(get_root_path(), "csharpgen", "templates")


def create_backup_file(file_path):
    os.rename(file_path, f"{file_path}{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
