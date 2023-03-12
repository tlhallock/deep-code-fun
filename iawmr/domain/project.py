from enum import Enum, auto
from typing import Dict, List, Optional
import pydantic
import iawmr.domain.model as model


class SourceDirectoryType(Enum):
  Application = auto()
  Library = auto()


class SourceDirectory(model.BaseModel):
  root_path: str
  package_type: SourceDirectoryType
  modules: Dict[str, model.Module]


class ProjectSpec(model.BaseModel):
  name: str
  sources: List[str]
  venv: Optional[str]
  ignores: List[str]


class Project(model.BaseModel):
  spec: ProjectSpec
  sources: List[SourceDirectory]


