from enum import Enum, auto
from typing import Dict, List, Optional
import pydantic
import iawmr.deep_code.model as model


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
  
  def modules(self):
    for source in self.sources:
      for module in source.modules.values():
        yield module


  def resolve_references(self):
    """
    Look at all the references in all the modules, and check if they are in this project.
    If they are, then set the target of the reference to where it points.
    Otherwise, append them to a list of unresolved references
    """
    targets = {}
    for module in self.modules():
      for name, node, scope in module.all_nodes():
        if not name:
          continue
        targets[name] = node
    for module in self.modules():
      for resolvable in module.all_references(scope=None):
        resolvable: model.ResolvableReference = resolvable
        key = resolvable.reference.fully_qualified_name
        if key in targets:
          resolvable.reference.target = targets[key]
        else:
          print("Unresolved reference", key)

