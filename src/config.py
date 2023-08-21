from pathlib import Path

import toml


class Config:
    def __init__(self):
        self._data = {}

    def load(self, path: Path | str):
        if not isinstance(path, Path):
            path = Path(path)

        if not path.suffix == ".toml":
            raise ValueError("Config.load requires a .toml file")

        data = toml.load(path)
        self._data = data

    pass
