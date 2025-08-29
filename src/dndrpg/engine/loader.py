import json
import yaml
import pathlib
from typing import Any

def load_json(path: str | pathlib.Path) -> Any:
    return json.loads(pathlib.Path(path).read_text())

def load_yaml(path: str | pathlib.Path) -> Any:
    return yaml.safe_load(pathlib.Path(path).read_text())
