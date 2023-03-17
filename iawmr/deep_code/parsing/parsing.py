


from typing import Any, List, Optional, Dict, Set, Tuple, Type, TypeVar, Callable, Generic
import ast
import os
import typing
from contextlib import contextmanager
from abc import ABC, abstractmethod
import json
from enum import Enum, auto

import iawmr.deep_code.model as model
from iawmr.deep_code.parsing.parser import Parsers
from iawmr.deep_code.parsing.state import ParsingState
from iawmr.deep_code.parsing.strategy import ParsingStrategy
import iawmr.deep_code.project as project




class Parsing:
  # visit_Constant...
  BUILT_IN_FUNCTIONS: Set[str] = set([
    "print", "len", "range", "enumerate", "zip", "map", "filter", "reduce", "sum",
    "min", "max", "any", "all", "sorted", "reversed", "list", "tuple", "set", "dict",
    "frozenset", "chr", "ord", "bin", "oct", "hex", "abs", "round", "pow", "divmod", 
    "complex", "float", "int", "str", "repr", "ascii", "hash", "id", "type", "dir",
    "isinstance", "issubclass", "issubclass", "hasattr", "getattr", "setattr", "delattr",
    "vars", "locals", "globals", "callable", "compile", "eval", "exec", "open", "input",
    "help", "quit", "exit", "memoryview", "bytearray", "bytes", "format", "ascii", "repr",
    "str", "bool", "int", "float", "complex", "range", "enumerate", "zip", "map", "filter",
    "reduce", "sum", "min", "max", "any", "all", "sorted", "reversed", "list", "tuple",
  ])
  
  @classmethod
  def collect_import_references(cls, parsers: Parsers, node: ast.Import) -> None:
    for alias in node.names:
      local_name = alias.name if alias.asname is None else alias.asname
      fully_qualifed_name = alias.name
      parsers.state.scopes.peek().aliases[local_name] = fully_qualifed_name
      reference = model.CodeReference(
        local_name=local_name,
        fully_qualified_name=fully_qualifed_name,
        reference_type="import",
      )
      parsers.current().references.append(reference)
    
  @classmethod
  def collect_import_from_references(cls, parsers: Parsers, node: ast.ImportFrom) -> None:
    # I don't understand this...
    assert node.level == 0
    base = [] if node.module is None else [node.module]
    for alias in node.names:
      local_name = alias.name if alias.asname is None else alias.asname
      fully_qualified_name = ".".join(base + [alias.name])
      parsers.state.scopes.peek().aliases[local_name] = fully_qualified_name
      reference = model.CodeReference(
        local_name=local_name,
        fully_qualified_name=fully_qualified_name,
        reference_type="import_from",
      )
      parsers.current().references.append(reference)
  
  @classmethod
  def list_references_in_expr(cls) -> None:
    pass
  
  @classmethod
  def resolve_reference_expr(cls, parsers: Parsers, node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Name):
      if node.id in cls.BUILT_IN_FUNCTIONS:
        return f"builtins::{node.id}"
      resolved = parsers.state.scopes.peek().resolve(node.id)
      if not resolved:
        # This can happen if we're in a function and we're referencing a variable
        # import pdb; pdb.set_trace()
        # raise Exception
        return None
      return resolved
    
    if isinstance(node, ast.Attribute):
      parent = cls.resolve_reference_expr(parsers, node.value)
      if not parent:
        return None
      field = node.attr
      return f"{parent}.{field}"
  
    if isinstance(node, ast.Constant):
      # TODO
      return f"Constant({node.value})"
    
    if isinstance(node, ast.Subscript):
      pass
    if isinstance(node, ast.Call):
      pass
    if isinstance(node, ast.Starred):
      pass
    if isinstance(node, ast.Index):
      pass
    
    return None
    # import pdb; pdb.set_trace()
    # raise Exception
  
  @classmethod
  def collect_call_references(cls, parsers: Parsers, node: ast.Call) -> None:
    fully_qualified_name = cls.resolve_reference_expr(parsers, node.func)
    if fully_qualified_name:
      reference = model.CodeReference(
        local_name="<none>",
        fully_qualified_name=fully_qualified_name,
        reference_type="calls",
      )
      parsers.current().references.append(reference)
  
  @classmethod
  def collect_name_references(cls, parsers: Parsers, node: ast.Name) -> None:
    # import pdb; pdb.set_trace()
      # model.CodeReference(local_name=[node.id], reference_type=model.AstNodeType.Unknown)
    # ]
    pass
  
  @classmethod
  def collect_references(cls, parsers: Parsers, node: ast.AST) -> None:
    if isinstance(node, ast.Name):
      cls.collect_name_references(parsers=parsers, node=node)
      return
    
    if isinstance(node, ast.Import):
      cls.collect_import_references(parsers=parsers, node=node)
      return
    
    if isinstance(node, ast.ImportFrom):
      cls.collect_import_from_references(parsers=parsers, node=node)
      return
    
      # return cls.parse_variable(parsers=parsers, node=node)
      # pass
    if isinstance(node, ast.Call):
      cls.collect_call_references(parsers=parsers, node=node)
      return
    if isinstance(node, ast.Attribute):
      pass
    if isinstance(node, ast.Store):
      pass
    if isinstance(node, ast.Load):
      pass
      # return cls.parse_variable(parsers=parsers, node=node)
  
  @classmethod
  def parse_children(cls, parsers: Parsers, node: ast.AST) -> None:
    if not parsers.state.parsing_strategy.should_descend_into(node=node):
      return
    current = parsers.current()
    for field, value in ast.iter_fields(node):
      key = str(field)
      
      if isinstance(value, ast.AST):
        child = cls.parse_node(parsers=parsers, node=value, default_name=str(field))
        if child is None:
          continue
        
        current.children.add_value_field(key, child)
        continue
      if not isinstance(value, list):
        continue
      
      children: List[model.AstNode] = []
      for index, item in enumerate(typing.cast(List[Any], value)):
        if not isinstance(item, ast.AST):
          continue
        child = cls.parse_node(parsers=parsers, node=item, default_name=f"{str(field)}[{index}]")
        if child is None:
          continue
        children.append(child)
      current.children.add_list_field(key, children)
  
  @classmethod
  def parse_inner(cls, parsers: Parsers, node: ast.AST) -> None:
    cls.parse_children(parsers=parsers, node=node)
    cls.collect_references(parsers=parsers, node=node)
  
  @classmethod
  def parse_generic(cls, parsers: Parsers, node: ast.AST, default_name: str) -> Optional[model.AstNode]:
    with parsers.unknown.with_(node=node, id_part=default_name) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    
  @classmethod
  def parse_module(cls, parsers: Parsers, node: ast.Module) -> Optional[model.Module]:
    with parsers.modules.with_(node=node, id_part=parsers.state.module_path) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(Optional[model.Module], ret)
    
  @classmethod
  def parse_class_def(cls, parsers: Parsers, node: ast.ClassDef) -> Optional[model.Class]:
    with parsers.clazz.with_(node=node, id_part=node.name) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(Optional[model.Class], ret)
  
  @classmethod
  def parse_function_def(cls, parsers: Parsers, node: ast.FunctionDef) -> Optional[model.Function]:
    with parsers.functions.with_(node=node, id_part=(node.name, model.FunctionType.Simple)) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(Optional[model.Function], ret)
    
  @classmethod
  def parse_async_function_def(cls, parsers: Parsers, node: ast.AsyncFunctionDef) -> Optional[model.Function]:
    with parsers.functions.with_(node=node, id_part=(node.name, model.FunctionType.Async)) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(Optional[model.Function], ret)
  
  @classmethod
  def parse_lambda_def(cls, parsers: Parsers, node: ast.Lambda) -> Optional[model.Function]:
    with parsers.functions.with_(node=node, id_part=(None, model.FunctionType.Lambda)) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(Optional[model.Function], ret)
  
  @classmethod
  def parse_statement(cls, parsers: Parsers, node: ast.stmt, default_name: str) -> Optional[model.Statement]:
    with parsers.statements.with_(node=node, id_part=default_name) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(model.Statement, ret)
  
  @classmethod
  def parse_expression(cls, parsers: Parsers, node: ast.expr, default_name: str) -> Optional[model.Expression]:
    with parsers.expressions.with_(node=node, id_part=default_name) as ret:
      cls.parse_inner(parsers=parsers, node=node)
    return ret
    # return typing.cast(model.Expression, ret)
  
  # @classmethod
  # def parse_variable(cls, parsers: Parsers, node: ast.Name) -> model.Variable:
  #   return model.Variable(
  #     node_type=model.AstNodeType.Variable,
  #     **cls.parse_base(node=node, path=path),
  #     name=node.id,
  #   )
    
  @classmethod
  def parse_node(cls, parsers: Parsers, node: ast.AST, default_name: str) -> Optional[model.AstNode]:
    if isinstance(node, ast.ClassDef):
      return cls.parse_class_def(parsers=parsers, node=node)
    if isinstance(node, ast.AsyncFunctionDef):
      return cls.parse_async_function_def(parsers=parsers, node=node)
    if isinstance(node, ast.FunctionDef):
      return cls.parse_function_def(parsers=parsers, node=node)
    if isinstance(node, ast.Lambda):
      return cls.parse_lambda_def(parsers=parsers, node=node)
    if isinstance(node, ast.stmt):
      return cls.parse_statement(parsers=parsers, node=node, default_name=default_name)
    if isinstance(node, ast.expr):
      return cls.parse_expression(parsers=parsers, node=node, default_name=default_name)
    # Darn, no way to know when a variable is declared in python.
    # Makes this harder...
    # if isinstance(node, ast.Name):
      # return cls.parse_variable(parsers=parsers, node=node)
      # pass
    return cls.parse_generic(parsers=parsers, node=node, default_name=default_name)
  
  @classmethod
  def fs_path_to_py_path(cls, fs_path: str) -> str:
    return fs_path[:-len(".py")].replace("/", ".")
    
  @classmethod
  def parse_source_directory(
    cls,
    directory_type: project.SourceDirectoryType,
    root_path: str,
    parsing_strategy: ParsingStrategy,
    ignores: List[str],
    write_jsons: bool = False,
  ) -> project.SourceDirectory:
    modules = {}
    for root, _, files in os.walk(root_path):
      if any(ignore in root for ignore in ignores):
        continue
      for filename in files:
        if not filename.endswith(".py"):
          continue
        file_path = os.path.join(root, filename)
        with open(file_path, "r") as f:
          source = f.read()
          ast_node = ast.parse(source)
          relative_path = os.path.relpath(file_path, start=root_path)
          
          module_path = cls.fs_path_to_py_path(relative_path)
          state = ParsingState.create(module_path=module_path, parsing_strategy=parsing_strategy)
          parsers = Parsers.create(state=state)
          module = cls.parse_module(
            parsers=parsers,
            node=ast_node,
          )
          assert module
          state.assert_empty()
          module.assert_tree_structure()
          modules[module_path] = module
        if write_jsons:
          # TODO: This probably won't work with multiple source directories
          file_path = os.path.join("output.dir", relative_path + ".json")
          dir_name = os.path.dirname(file_path)
          os.makedirs(dir_name, exist_ok=True)
          with open(file_path, "w") as fp:
            js = json.loads(module.json())
            json.dump(js, fp, indent=2)
    return project.SourceDirectory(
      root_path=root_path,
      package_type=directory_type,
      modules=modules
    )

  @classmethod
  def parse_project(cls, spec: project.ProjectSpec, write_jsons: bool = False) -> project.Project:
    source_directories = []
    for source_directory in spec.sources:
      source_directories.append(
        cls.parse_source_directory(
          directory_type=project.SourceDirectoryType.Application,
          root_path=source_directory,
          ignores=spec.ignores,
          write_jsons=write_jsons,
          parsing_strategy=spec.parsing_strategy,
        )
      )
    if spec.venv:
      source_directories.append(
        cls.parse_source_directory(
          directory_type=project.SourceDirectoryType.Library,
          root_path=source_directory,
          ignores=spec.ignores,
          write_jsons=write_jsons,
          parsing_strategy=spec.parsing_strategy,
        )
      )
    return project.Project(
      spec=spec,
      sources=source_directories,
    )
