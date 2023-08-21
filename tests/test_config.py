import os

import pytest

from src.config import Config


def get_path_to_config(filename: str):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    path_to_config = os.path.join(current_directory, f"files/configs/{filename}")
    return path_to_config


def test_config_load():
    cfg = Config()
    cfg.load(get_path_to_config("pbasic.toml"))
    print(cfg._data)
