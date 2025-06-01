import tomllib
from pathlib import Path

pyproject_toml = Path(__file__).parent.parent / "pyproject.toml"
with open(pyproject_toml, 'rb') as f:
    project_data = tomllib.load(f)

__version__ = project_data['project']['version']
