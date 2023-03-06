
from typing import List, Optional
import ast
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Union
import os

from iawmr.domain.module import Module


class Project(BaseModel):
  root_path: str
  modules: Dict[str, Module]

  @staticmethod
  def parse_from_root_path(root_path: str) -> "Project":
    modules = {}
    for root, _, files in os.walk(root_path):
      for filename in files:
        if not filename.endswith(".py"):
          continue
        file_path = os.path.join(root, filename)
        with open(file_path, "r") as f:
          source = f.read()
          ast_node = ast.parse(source)
          rel_path = os.path.relpath(file_path, start=root_path)
          module = Module.from_ast(
            relative_path=rel_path,
            ast_node=ast_node,
          )
          modules[rel_path] = module
    return Project(modules=modules)
