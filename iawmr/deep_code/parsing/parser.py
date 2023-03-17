


from typing import Any, Iterator, List, Optional, Dict, Set, Tuple, Type, TypeVar, Callable, Generic
import ast
import os
import typing
from contextlib import contextmanager
from abc import ABC, abstractmethod
import json
from enum import Enum, auto

import iawmr.deep_code.model as model
from iawmr.deep_code.parsing.state import ParsingState




O = TypeVar("O", bound=ast.AST)
N = TypeVar("N", bound=model.AstNode)
G = TypeVar("G")
class AstParser(ABC, Generic[O, G, N]):
  state: ParsingState
  node_type: model.AstNodeType
  
  def __init__(self, state: ParsingState, node_type: model.AstNodeType):
    self.state = state
    self.node_type = node_type
  
  def should_push(self, node: ast.AST) -> bool:
    return self.state.parsing_strategy.should_push(node=node)
  
  @abstractmethod
  def begin(self, node: O, id_part: G) -> Optional[N]:
    pass
  
  @abstractmethod
  def end(self, node: O) -> None:
    pass
  
  @contextmanager
  def with_(self, node: O, id_part: G) -> Iterator[Optional[N]]:
    """In hindsight, the arg argument should probably be called name or id_part"""
    """lolz, so then I made the change, and then I realized it doesn't apply to functions"""
    code = self.begin(node=node, id_part=id_part)
    try:
      yield code
    finally:
      self.end(node=node)
  
  def parse_base(self, node: O) -> Dict[str, Any]:
    return dict(
        ast_type=node.__class__.__name__,
        children={},
        references=[],
        node_type=self.node_type,
        project_unique_path=self.state.create_id(),
    )


class ModuleParser(AstParser[ast.Module, str, model.Module]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Module)
  
  def begin(self, node: ast.Module, id_part: str) -> Optional[model.Module]:
    self.state.detailed_paths.push(id_part)
    self.state.referencable_paths.push(id_part)
    scope = self.state.scopes.push(f"module {id_part}")
    if not self.should_push(node=node):
      return None
    ret = model.Module(
      **self.parse_base(node=node),
      scope=scope,
      relative_path=id_part,
      fully_qualified_name=id_part,
    )
    self.state.codes.push(ret)
    return ret
      
  
  def end(self, node: ast.Module) -> None:
    self.state.scopes.pop()
    if self.should_push(node=node):
      self.state.codes.pop()
    self.state.referencable_paths.pop()
    self.state.detailed_paths.pop()


class ClassParser(AstParser[ast.ClassDef, str, model.Class]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Class)
    
  def begin(self, node: ast.ClassDef, id_part: str) -> Optional[model.Class]:
    self.state.detailed_paths.push(id_part)
    self.state.referencable_paths.push(id_part)
    scope = self.state.scopes.push(f"class {id_part}")
    if not self.should_push(node=node):
      return None
    ret = model.Class(
      **self.parse_base(node=node),
      name=id_part,
      scope=scope,
      fully_qualified_name=self.state.fully_qualify(),
    )
    self.state.codes.push(ret)
    return ret
  
  def end(self, node: ast.ClassDef) -> None:
    self.state.scopes.pop()
    if self.should_push(node=node):
      self.state.codes.pop()
    self.state.referencable_paths.pop()
    self.state.detailed_paths.pop()


class FunctionParser(AstParser[ast.AST, Tuple[Optional[str], model.FunctionType], model.Function]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Function)
    
  def begin(self, node: ast.AST, id_part: Tuple[Optional[str], model.FunctionType]) -> Optional[model.Function]:
    name, function_type = id_part[0], id_part[1]
    self.state.detailed_paths.push(name)
    self.state.referencable_paths.push(name)
    scope = self.state.scopes.push(f"function {name}")
    if not self.should_push(node=node):
      return None
    ret = model.Function(
      **self.parse_base(node=node),
      name=name if name is not None else "<anonymous>",
      function_type=function_type,
      scope=scope,
      fully_qualified_name=self.state.fully_qualify(),
    )
    self.state.codes.push(ret)
    return ret
  
  def end(self, node: ast.AST) -> None:
    self.state.scopes.pop()
    if self.should_push(node=node):
      self.state.codes.pop()
    self.state.referencable_paths.pop()
    self.state.detailed_paths.pop()


class StatementParser(AstParser[ast.stmt, str, model.Statement]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Statement)
    
  def begin(self, node: ast.stmt, id_part: str) -> Optional[model.Statement]:
    self.state.detailed_paths.push(id_part)
    self.state.referencable_paths.push(None)
    if not self.should_push(node=node):
      return None
    ret = model.Statement(**self.parse_base(node=node))
    self.state.codes.push(ret)
    return ret
  
  def end(self, node: ast.stmt) -> None:
    if self.should_push(node=node):
      self.state.codes.pop()
    self.state.referencable_paths.pop()
    self.state.detailed_paths.pop()


class ExpressionParser(AstParser[ast.expr, str, model.Expression]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Expression)
    
  def begin(self, node: ast.expr, id_part: str) -> Optional[model.Expression]:
    self.state.detailed_paths.push(id_part)
    self.state.referencable_paths.push(None)
    if not self.should_push(node=node):
      return None
    ret = model.Expression(**self.parse_base(node=node))
    self.state.codes.push(ret)
    return ret
  
  def end(self, node: ast.expr) -> None:
    if self.should_push(node=node):
      self.state.codes.pop()
    self.state.referencable_paths.pop()
    self.state.detailed_paths.pop()


class UnknownParser(AstParser[ast.AST, str, model.AstNode]):
  def __init__(self, state: ParsingState):
    super().__init__(state=state, node_type=model.AstNodeType.Unknown)
    
  def begin(self, node: ast.AST, id_part: str) -> Optional[model.AstNode]:
    self.state.detailed_paths.push(id_part)
    self.state.referencable_paths.push(None)
    if not self.should_push(node=node):
      return None
    ret = model.AstNode(**self.parse_base(node=node))
    self.state.codes.push(ret)
    return ret
  
  def end(self, node: ast.AST) -> None:
    if self.should_push(node=node):
      self.state.codes.pop()
    self.state.referencable_paths.pop()
    self.state.detailed_paths.pop()


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
      state=state,
      modules=ModuleParser(state=state),
      clazz=ClassParser(state=state),
      functions=FunctionParser(state=state),
      statements=StatementParser(state=state),
      expressions=ExpressionParser(state=state),
      unknown=UnknownParser(state=state),
    )