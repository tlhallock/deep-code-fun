from enum import Enum, auto
from typing import Dict, Iterator, List, Optional, Set, Generator
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
  # Idk if this needs to be saved...
  unresolved_references: Optional[Set[str]]
  
  def modules(self) -> Iterator[model.Module]:
    for source in self.sources:
      for module in source.modules.values():
        yield module

  def resolve_references(self):
    targets = {}
    unresolved_references = set()
    for module in self.modules():
      for node, _ in module.all_nodes():
        target = node.get_fully_qualified_name()
        if not target:
          continue
        targets[target] = node
    for module in self.modules():
      for node, _ in module.all_nodes():
        for reference in node.references:
          key = reference.fully_qualified_name
          if key in targets:
            reference.target = targets[key]
          else:
            unresolved_references.add(key)
    print("Unresolved references", unresolved_references)
    self.unresolved_references = unresolved_references

