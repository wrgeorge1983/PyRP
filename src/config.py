from pathlib import Path

import toml
from munch import munchify


class Config:
    def __init__(self):
        self._data = {}
        self.pbasic = {}

    def load(self, path: Path | str):
        if not isinstance(path, Path):
            path = Path(path)

        if not path.suffix == ".toml":
            raise ValueError("Config.load requires a .toml file")

        data = toml.load(path)
        self._data = data
        self.pbasic = data.get("pbasic", {})

    pass
