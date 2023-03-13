


from typing import Any, List, Optional, Dict, Tuple, TypeVar, Callable, Generic
import ast
import os
import typing
from contextlib import contextmanager
from abc import ABC, abstractmethod
import json

import iawmr.deep_code.model as model
import iawmr.deep_code.project as project


T = TypeVar("T")
A = TypeVar("A")
class ParsingStack(ABC, Generic[A, T]):
  elements: List[T]
  
  def __init__(self, elements: List[T] = []):
    self.elements = elements
  
  @abstractmethod
  def create(self, arg: A) -> T:
    pass
  
  def push(self, arg: A) -> T:
    ret = self.create(arg=arg)
    self.elements.append(ret)
    return ret
  
  def peek(self) -> T:
    return self.elements[-1]
  
  def pop(self) -> T:
    return self.elements.pop()

  @contextmanager
  def with_(self, arg: A):
    self.push(arg=arg)
    try:
      yield self.peek()
    finally:
      self.pop()


class CodeStack(ParsingStack[model.AstNode, model.AstNode]):
  def create(self, arg: model.AstNode) -> model.AstNode:
    return arg


class ScopeStack(ParsingStack[str, model.Scope]):
  def create(self, arg: str) -> model.Scope:
    return model.Scope(
      name=arg,
      parent=self.peek(),
      aliases=dict(),
    )


class PathStack(ParsingStack[Optional[str], Optional[str]]):
  def create(self, arg: Optional[str]) -> Optional[str]:
    return arg


class ParsingState:
  codes: CodeStack
  scopes: ScopeStack
  paths: PathStack
  
  def __init__(self, codes: CodeStack, scopes: ScopeStack, paths: PathStack):
    self.codes = codes
    self.scopes = scopes
    self.paths = paths
  
  def fully_qualify(self, local_name: List[Optional[str]]) -> str:
    return ".".join(s if s is not None else "none" for s in self.paths.elements + local_name)
  
  @classmethod
  def create(cls, base_path) -> "ParsingState":
    return cls(
      # root_path=root_path,
      codes=CodeStack(),
      scopes=ScopeStack(elements=[model.Scope(name="module scope", parent=None, aliases={})]),
      paths=PathStack(elements=[base_path]),
    )


O = TypeVar("O", bound=ast.AST)
N = TypeVar("N", bound=model.AstNode)
G = TypeVar("G")
class AstParser(ABC, Generic[O, G, N]):
  state: ParsingState
  node_type: model.AstNodeType
  
  def __init__(self, state: ParsingState, node_type: model.AstNodeType):
    self.state = state
    self.node_type = node_type
  
  @abstractmethod
  def begin(self, node: O, arg: G):
    pass
  
  @abstractmethod
  def end(self) -> None:
    pass
  
  @contextmanager
  def with_(self, node: O, arg: G):
    self.begin(node=node, arg=arg)
    try:
      yield
    finally:
      self.end()
  
  def parse_base(self, node: O, name: Optional[str]) -> Dict[str, Any]:
    return dict(
        ast_type=node.__class__.__name__,
        children=[],
        references=[],
        node_type=self.node_type,
    )
  

class ModuleParser(AstParser[ast.Module, str, model.Module]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Module)
  
  def begin(self, node: ast.Module, arg: str):
    scope = self.state.scopes.push("module scope")
    self.state.codes.push(
      model.Module(
        **self.parse_base(node=node, name="module"),
        scope=scope,
        relative_path=arg,
        fully_qualified_name=arg,
      ),
    )
    self.state.paths.push(arg)
    
  def end(self):
    self.state.scopes.pop()
    self.state.codes.pop()
    self.state.paths.pop()


class ClassParser(AstParser[ast.ClassDef, str, model.Class]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Class)
    
  def begin(self, node: ast.ClassDef, arg: str):
    scope = self.state.scopes.push(f"class {node.name}")
    self.state.codes.push(
      model.Class(
        **self.parse_base(node=node, name=node.name),
        name=arg,
        scope=scope,
        fully_qualified_name=self.state.fully_qualify([node.name]),
      ),
    )
    self.state.paths.push(node.name)
    
  def end(self):
    self.state.paths.pop()
    self.state.scopes.pop()
    self.state.codes.pop()


class FunctionParser(AstParser[ast.AST, Tuple[str, model.FunctionType], model.Function]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Function)
    
  def begin(self, node: ast.AST, arg: Tuple[str, model.FunctionType]):
    name, function_type = arg[0], arg[1]
    scope = self.state.scopes.push(f"function {name}")
    self.state.codes.push(
      model.Function(
        **self.parse_base(node=node, name=name),
        name=name,
        function_type=function_type,
        scope=scope,
        fully_qualified_name=self.state.fully_qualify([name]),
      )
    )
    self.state.paths.push(name)
    
  def end(self):
    self.state.paths.pop()
    self.state.scopes.pop()
    self.state.codes.pop()


class StatementParser(AstParser[ast.stmt, int, model.Statement]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Statement)
    
  def begin(self, node: ast.stmt, arg: int):
    name = str(arg)
    self.state.codes.push(
      model.Statement(
        **self.parse_base(node=node, name=name)
      )
    )
    self.state.paths.push(None)
    
  def end(self):
    self.state.paths.pop()
    self.state.codes.pop()


class ExpressionParser(AstParser[ast.expr, Any, model.Expression]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Expression)
    
  def begin(self, node: ast.expr, arg: Any):
    self.state.codes.push(
      model.Expression(
        **self.parse_base(node=node, name="expr")
      )
    )
    self.state.paths.push(None)
    
  def end(self):
    self.state.paths.pop()
    self.state.codes.pop()


class UnknownParser(AstParser[ast.AST, Any, model.AstNode]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Unknown)
    
  def begin(self, node: ast.AST, arg: Any):
    self.state.codes.push(
      model.AstNode(
        **self.parse_base(node=node, name="unknown")
      )
    )
    
  def end(self):
    self.state.codes.pop()


class Parsers:
  state: ParsingState
  
  modules: ModuleParser
  clazz: ClassParser
  functions: FunctionParser
  statements: StatementParser
  expressions: ExpressionParser
  unknown: UnknownParser
  
  def __init__(self, modules: ModuleParser, state: ParsingState, clazz: ClassParser, functions: FunctionParser, statements: StatementParser, expressions: ExpressionParser, unknown: UnknownParser):
    self.state = state
    self.modules = modules
    self.clazz = clazz
    self.functions = functions
    self.statements = statements
    self.expressions = expressions
    self.unknown = unknown
  
  def current(self) -> model.AstNode:
    return self.state.codes.peek()
  
  @classmethod
  def create(cls, state: ParsingState) -> "Parsers":
    return Parsers(
      state = state,
      modules=ModuleParser(state=state),
      clazz = ClassParser(state=state),
      functions = FunctionParser(state=state),
      statements = StatementParser(state=state),
      expressions = ExpressionParser(state=state),
      unknown = UnknownParser(state=state),
    )

class Parsing:
  # visit_Constant...
  
  @classmethod
  def collect_import_references(cls, parsers: Parsers, node: ast.Import) -> None:
    for alias in node.names:
      local_name = alias.name if alias.asname is None else alias.asname
      fully_qualifed_name = alias.name
      parsers.state.scopes.peek().aliases[local_name] = fully_qualifed_name
      reference = model.CodeReference(
        local_name=local_name,
        fully_qualified_name=fully_qualifed_name,
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
  
  @classmethod
  def parse_children(cls, parsers: Parsers, node: ast.AST) -> None:
    current = parsers.current()
    if current.ast_type in ["Import", "ImportFrom"]:
      return
    for field, value in ast.iter_fields(node):
      if isinstance(value, ast.AST):
        child = cls.parse_node(parsers=parsers, node=value)
        current.children.update({str(field): [child]})
        continue
      if not isinstance(value, list):
        continue
      children = []
      for item in typing.cast(List[Any], value):
        if not isinstance(item, ast.AST):
          continue
        child = cls.parse_node(parsers=parsers, node=item)
        children.append(child)
      current.children.update({str(field): children})
  
  @classmethod
  def parse_inner(cls, parsers: Parsers, node: ast.AST) -> model.AstNode:
    cls.parse_children(parsers=parsers, node=node)
    cls.collect_references(parsers=parsers, node=node)
    return parsers.current()
  
  @classmethod
  def parse_generic(cls, parsers: Parsers, node: ast.AST) -> model.AstNode:
    with parsers.unknown.with_(node=node, arg=None):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return ret
    
  @classmethod
  def parse_module(cls, parsers: Parsers, node: ast.Module) -> model.Module:
    base_path = arg=parsers.state.paths.peek()
    assert base_path
    with parsers.modules.with_(node=node, arg=base_path):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Module, ret)
    
  @classmethod
  def parse_class_def(cls, parsers: Parsers, node: ast.ClassDef) -> model.Class:
    with parsers.clazz.with_(node=node, arg=node.name):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Class, ret)
  
  @classmethod
  def parse_function_def(cls, parsers: Parsers, node: ast.FunctionDef) -> model.Function:
    with parsers.functions.with_(node=node, arg=(node.name, model.FunctionType.Simple)):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Function, ret)
    
  @classmethod
  def parse_async_function_def(cls, parsers: Parsers, node: ast.AsyncFunctionDef) -> model.Function:
    with parsers.functions.with_(node=node, arg=(node.name, model.FunctionType.Async)):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Function, ret)
  
  @classmethod
  def parse_lambda_def(cls, parsers: Parsers, node: ast.Lambda) -> model.Function:
    with parsers.functions.with_(node=node, arg=("lambda", model.FunctionType.Lambda)):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Function, ret)
  
  @classmethod
  def parse_statement(cls, parsers: Parsers, node: ast.stmt) -> model.Statement:
    with parsers.statements.with_(node=node, arg=0):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Statement, ret)
  
  @classmethod
  def parse_expression(cls, parsers: Parsers, node: ast.expr) -> model.Expression:
    with parsers.expressions.with_(node=node, arg=None):
      ret = cls.parse_inner(parsers=parsers, node=node)
    return typing.cast(model.Expression, ret)
  
  # @classmethod
  # def parse_variable(cls, parsers: Parsers, node: ast.Name) -> model.Variable:
  #   return model.Variable(
  #     node_type=model.AstNodeType.Variable,
  #     **cls.parse_base(node=node, path=path),
  #     name=node.id,
  #   )
    
  @classmethod
  def parse_node(cls, parsers: Parsers, node: ast.AST) -> model.AstNode:
    if isinstance(node, ast.ClassDef):
      return cls.parse_class_def(parsers=parsers, node=node)
    if isinstance(node, ast.AsyncFunctionDef):
      return cls.parse_async_function_def(parsers=parsers, node=node)
    if isinstance(node, ast.FunctionDef):
      return cls.parse_function_def(parsers=parsers, node=node)
    if isinstance(node, ast.Lambda):
      return cls.parse_lambda_def(parsers=parsers, node=node)
    if isinstance(node, ast.stmt):
      return cls.parse_statement(parsers=parsers, node=node)
    if isinstance(node, ast.expr):
      return cls.parse_expression(parsers=parsers, node=node)
    # if isinstance(node, ast.Name):
    #   return cls.parse_variable(parsers=parsers, node=node)
    return cls.parse_generic(parsers=parsers, node=node)
  
  @classmethod
  def fs_path_to_py_path(cls, fs_path: str) -> str:
    return fs_path[:-len(".py")].replace("/", ".")
    
  @classmethod
  def parse_source_directory(
    cls,
    directory_type: project.SourceDirectoryType,
    root_path: str,
    ignores: List[str],
    write_jsons: bool = False
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
          
          base_path = cls.fs_path_to_py_path(relative_path)
          state = ParsingState.create(base_path=base_path)
          parsers = Parsers.create(state=state)
          module = cls.parse_module(
            parsers=parsers,
            node=ast_node,
          )
          modules[base_path] = module
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
        )
      )
    if spec.venv:
      source_directories.append(
        cls.parse_source_directory(
          directory_type=project.SourceDirectoryType.Library,
          root_path=source_directory,
          ignores=spec.ignores,
          write_jsons=write_jsons,
        )
      )
    return project.Project(
      spec=spec,
      sources=source_directories
    )
