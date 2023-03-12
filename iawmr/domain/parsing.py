


from typing import Any, List, Optional, Dict, Tuple, TypeVar, Callable, Generic
import ast
import os
import typing
from contextlib import contextmanager
from abc import ABC, abstractmethod
import json

import iawmr.domain.model as model
import iawmr.domain.project as project


T = TypeVar("T")
A = TypeVar("A")
class ParsingStack(ABC, Generic[A, T]):
  elements: List[T]
  
  def __init__(self):
    self.elements = []
  
  @abstractmethod
  def create(self, arg: A) -> T:
    pass
  
  def push(self, arg: A):
    self.elements.append(self.create(arg=arg))
  
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


class ScopeStack(ParsingStack[model.Scope, str]):
  def create(self, arg: str) -> model.Scope:
    return model.Scope(
      name=arg,
      parent=self.peek(),
      aliases=dict(),
    )


class PathStack(ParsingStack[str, str]):
  def create(self, state: "ParsingState", arg: str) -> model.Scope:
    return arg


class ParsingState(model.BaseModel):
  # root_path: str
  codes: CodeStack
  scopes: ScopeStack
  path: PathStack
  
  def fully_qualify(self, local_name: List[str]) -> str:
    return ".".join(self.path.elements + local_name)
  
  @classmethod
  def create(cls, base_path) -> "ParsingState":
    return cls(
      # root_path=root_path,
      code_stack=[],
      scope_stack=[model.Scope(name="module scope", parent=None, aliases={})],
      path_stack=[base_path],
    )


A = TypeVar("A", bound=ast.AST)
B = TypeVar("B", bound=ast.AST)
class AstParser(ABC, Generic[A, B]):
  state: ParsingState
  node_type: model.AstNodeType
  
  def __init__(self, state: ParsingState, node_type: model.AstNodeType):
    self.state = state
    self.node_type = node_type
  
  @abstractmethod
  def begin(self, node: A, arg: Optional[B]) -> T:
    pass
  
  @abstractmethod
  def end(self) -> None:
    pass
  
  @contextmanager
  def with_(self, node: A, arg: Optional[B]):
    self.begin(node=node, arg=arg)
    try:
      yield
    finally:
      self.end()
  
  def parse_base(self, node: A, arg: Optional[str]) -> Dict[str, Any]:
    return dict(
        scope=self.state.scopes.peek(),
        fully_qualified_name=self.state.fully_qualify([arg]),
        ast_type=node.__class__.__name__,
        children=[],
        references=[],
        node_type=self.node_type,
    )
  
  
class ClassParser(AstParser[ast.ClassDef, str]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Class)
    
  def begin(self, node: ast.ClassDef, arg: str):
    self.state.codes.push(
      **model.Class(self.parse_base(node=node, name=node.name))
    )
    self.state.scopes.push(arg)
    self.state.path.push(node.name)
    
  def end(self):
    self.state.path.pop()
    self.state.scopes.pop()
    self.state.codes.pop()


class FunctionParser(AstParser[ast.AST, Tuple[str, model.FunctionType]]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Function)
    
  def begin(self, node: ast.AST, arg: Tuple[str, model.FunctionType]):
    name, function_type = arg[0], arg[1]
    self.state.codes.push(
      model.Function(
        function_type=function_type,
        **self.parse_base(node=node, name=name)
      )
    )
    self.state.scopes.push(name)
    self.state.path.push(name)
    
  def end(self):
    self.state.path.pop()
    self.state.scopes.pop()
    self.state.codes.pop()


class StatementParser(AstParser[ast.stmt, int]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Statement)
    
  def begin(self, node: ast.AST, arg: int):
    name = str(arg)
    self.state.codes.push(
      model.Statement(
        **self.parse_base(node=node, name=name)
      )
    )
    self.state.path.push(f"statements[{arg}]")
    
  def end(self):
    self.state.path.pop()
    self.state.codes.pop()


class ExpressionParser(AstParser[ast.expr, Any]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Expression)
    
  def begin(self, node: ast.AST, arg: Any):
    self.state.codes.push(
      model.Expression(
        **self.parse_base(node=node, name="expr")
      )
    )
    self.state.path.push(f"expr")
    
  def end(self):
    self.state.path.pop()
    self.state.codes.pop()


class UnknownParser(AstParser[ast.AST, Any]):
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
  clazz: ClassParser
  functions: FunctionParser
  statements: StatementParser
  expressions: ExpressionParser
  unknown: UnknownParser
  
  def __init__(self, clazz: ClassParser, functions: FunctionParser, statements: StatementParser, expressions: ExpressionParser, unknown: UnknownParser):
    self.clazz = clazz
    self.functions = functions
    self.statements = statements
    self.expressions = expressions
    self.unknown = unknown
    
  
  @classmethod
  def create(cls, state: ParsingState) -> "Parsers":
    return Parsers(
      clazz = ClassParser(state=state),
      functions = FunctionParser(state=state),
      statements = StatementParser(state=state),
      expressions = ExpressionParser(state=state),
      unknown = UnknownParser(state=state),
    )

class Parsing:
  # visit_Constant...
  
  @classmethod
  def collect_import_references(cls, parsers: Parsers, node: ast.Import) -> List[model.CodeReference]:
    import pdb; pdb.set_trace()
    return [
      model.CodeReference(local_name=[name], reference_type=model.AstNodeType.Unknown)
      for name in node.names
    ]
    
  @classmethod
  def collect_import_from_references(cls, parsers: Parsers, node: ast.ImportFrom) -> List[model.CodeReference]:
    import pdb; pdb.set_trace()
    return [
      model.CodeReference(local_name=local_name, reference_type=model.AstNodeType.Unknown)
      for name in node.names
      for local_name in [
        [name] if node.module is None else [node.module, name]
      ]
    ]
  
  @classmethod
  def collect_name_references(cls, parsers: Parsers, node: ast.Name) -> List[model.CodeReference]:
    import pdb; pdb.set_trace()
    return [
      model.CodeReference(local_name=[node.id], reference_type=model.AstNodeType.Unknown)
    ]
  
  @classmethod
  def collect_references(cls, parsers: Parsers, node: ast.AST) -> List[model.CodeReference]:
    if isinstance(node, ast.Name):
      return cls.collect_name_references(parsers=parsers, node=node)
    
    if isinstance(node, ast.Import):
      return cls.collect_import_references(parsers=parsers, node=node)
    
    if isinstance(node, ast.ImportFrom):
      return cls.collect_import_from_references(parsers=parsers, node=node)
    return []
  
  @classmethod
  def parse_children(cls, parsers: Parsers, node: ast.AST) -> List[model.AstNode]:
    children = []
    for field, value in ast.iter_fields(node):
      if isinstance(value, ast.AST):
        children.append(cls.parse_node(parsers=parsers, node=value))
        continue
      if not isinstance(value, list):
        continue
      for index, item in enumerate(typing.cast(List[Any], value)):
        if not isinstance(item, ast.AST):
          continue
        # with parsers.path_element(path_element=str(index)):
        children.append(cls.parse_node(parsers=parsers, node=item))
    return children
  
  @classmethod
  def parse_inner(cls, parsers: Parsers, node: ast.AST) -> None:
    cls.parse_children(parsers=parsers, node=node)
    cls.collect_references(parsers=parsers, node=node)
  
  @classmethod
  def parse_generic(cls, parsers: Parsers, node: ast.AST) -> model.AstNode:
    with parsers.unknown.with_(node=node, arg=None):
      cls.parse_inner(parsers=parsers, node=node)
    
  @classmethod
  def parse_class_def(cls, parsers: Parsers, node: ast.ClassDef) -> model.Class:
    with parsers.clazz.with_(node=node, name=node.name):
      cls.parse_inner(parsers=parsers, node=node)
  
  @classmethod
  def parse_function_def(cls, parsers: Parsers, node: ast.FunctionDef) -> model.Function:
    with parsers.functions.with_(node=node, arg=[node.name, model.FunctionType.Simple]):
      cls.parse_inner(parsers=parsers, node=node)
    
  @classmethod
  def parse_async_function_def(cls, parsers: Parsers, node: ast.AsyncFunctionDef) -> model.Function:
    with parsers.functions.with_(node=node, arg=[node.name, model.FunctionType.Async]):
      cls.parse_inner(parsers=parsers, node=node)
  
  @classmethod
  def parse_lambda_def(cls, parsers: Parsers, node: ast.Lambda) -> model.Function:
    with parsers.functions.with_(node=node, arg=["lambda", model.FunctionType.Lambda]):
      cls.parse_inner(parsers=parsers, node=node)
  
  @classmethod
  def parse_statement(cls, parsers: Parsers, node: ast.stmt) -> model.Statement:
    with parsers.functions.with_(node=node, index=0):
      cls.parse_inner(parsers=parsers, node=node)
  
  @classmethod
  def parse_expression(cls, parsers: Parsers, node: ast.expr) -> model.Expression:
    with parsers.functions.with_(node=node, arg=None):
      cls.parse_inner(parsers=parsers, node=node)
  
  # @classmethod
  # def parse_variable(cls, parsers: Parsers, node: ast.Name) -> model.Variable:
  #   return model.Variable(
  #     node_type=model.AstNodeType.Variable,
  #     **cls.parse_base(node=node, path=path),
  #     name=node.id,
  #   )
    
  @classmethod
  def parse_node(cls, parsers: Parsers, node: ast.AST) -> model.AstNode:
    """TODO: Don't parse everything, just parse up to the current obj model..."""
    # todo: add ignore directories
    """
    TODO: an expr can also be a statement
    TODO: understand these:
      possible sources of references?
        assign
        augassign
        annassign
        import
        import from
        global
        nonlocal
        Call
        attribute
        Name
      important missing information?
        boolop
        binop
        unaryop
        Constant
    """
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
    if isinstance(node, ast.Expr):
      return cls.parse_expression(parsers=parsers, node=node)
    # if isinstance(node, ast.Name):
    #   return cls.parse_variable(parsers=parsers, node=node)
    return cls.parse_generic(parsers=parsers, node=node)
  
  @classmethod
  def fs_path_to_py_path(cls, fs_path: str) -> str:
    return fs_path[:-len(".py")].replace("/", ".")
    
  @classmethod
  def parse_module(cls, node: ast.Module, relative_path: str) -> model.Module:
    base_path = cls.fs_path_to_py_path(relative_path)
    state = ParsingState.create(base_path=base_path)
    parsers = Parsers.create(state=state)
    
    module = model.Module(
      relative_path=relative_path,
      node_type=model.AstNodeType.Module,
      scope=state.scopes.peek(),
      node_type=model.AstNodeType.Module,
      fully_qualified_name=base_path,
      children=[],
      references=[],
      ast_type="module",
    )
    cls.parse_inner(parsers=parsers, node=node),
    return module

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
          rel_path = os.path.relpath(file_path, start=root_path)
          module = cls.parse_module(
            node=ast_node,
            relative_path=rel_path,
          )
          modules[rel_path] = module
        if write_jsons:
          with open(file_path + ".json", "w") as fp:
            js =json.loads(module.json())
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
        )
      )
    return project.Project(
      spec=spec,
      sources=source_directories
    )
