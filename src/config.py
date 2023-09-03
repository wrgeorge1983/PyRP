from enum import Enum
from pathlib import Path

import toml


class ServicePorts(Enum):
    CONTROL_PLANE = 5010
    RIP = 5020
    OSPF = 5021
    BGP = 5022
    BASIC = 5023

def control_plane_defaults() -> dict[str, int | list | str]:
    control_plane_config = {
    }

    return control_plane_config

def pbasic_defaults() -> dict[str, int | list | str]:
    pbasic_config = {
        "admin_distance": 1,
        "threshold_measure_interval": 60,
        "routes": [],
    }

    return pbasic_config


class Config:
    def __init__(self):
        self._data = {}
        self.control_plane = control_plane_defaults()
        self.pbasic = pbasic_defaults()

    def load(self, path: Path | str):
        if not isinstance(path, Path):
            path = Path(path)

        if not path.suffix == ".toml":
            raise ValueError("Config.load requires a .toml file")

        data = toml.load(path)
        self._data = data
        self.pbasic.update(data.get("pbasic", {}))
        self.control_plane.update(data.get("control_plane", {}))
