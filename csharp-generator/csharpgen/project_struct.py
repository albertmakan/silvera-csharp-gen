"""This module contains code for generating project structure in target language"""
import os


def create_if_missing(dir_path: str):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    return dir_path


def csharp_struct(output_path, app_name):
    """Generates C# project structure"""
    if not os.path.exists(output_path):
        raise Exception("Output path does not exist.")
    return create_if_missing(os.path.join(output_path, app_name))
