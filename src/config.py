from enum import Enum
from pathlib import Path

import toml


class ServicePorts(Enum):
    CONTROL_PLANE = 5010
    RIP = 5020
    OSPF = 5021
    BGP = 5022
    SLA = 5023

def control_plane_defaults() -> dict[str, int | list | str]:
    control_plane_config = {
    }

    return control_plane_config

def rp_sla_defaults() -> dict[str, int | list | str]:
    rp_sla_config = {
        "admin_distance": 1,
        "threshold_measure_interval": 60,
        "routes": [],
    }

    return rp_sla_config


class Config:
    def __init__(self):
        self._data = {}
        self.control_plane = control_plane_defaults()
        self.rp_sla = rp_sla_defaults()

    def load(self, path: Path | str):
        if not isinstance(path, Path):
            path = Path(path)

        if not path.suffix == ".toml":
            raise ValueError("Config.load requires a .toml file")

        data = toml.load(path)
        self._data = data
        self.rp_sla.update(data.get("rp_sla", {}))
        self.control_plane.update(data.get("control_plane", {}))
