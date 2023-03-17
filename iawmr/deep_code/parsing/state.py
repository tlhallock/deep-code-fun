


from typing import Any, List, Optional, Dict, Set, Tuple, Type, TypeVar, Callable, Generic
from contextlib import contextmanager
from abc import ABC, abstractmethod

import iawmr.deep_code.model as model
from iawmr.deep_code.parsing.strategy import ParsingStrategy


T = TypeVar("T")
A = TypeVar("A")
class ParsingStack(ABC, Generic[A, T]):
  elements: List[T]
  
  def __init__(self, elements: Optional[List[T]] = None):
    self.elements = elements or []
  
  @abstractmethod
  def create(self, arg: A) -> T:
    pass
  
  def push(self, arg: A) -> T:
    ret = self.create(arg=arg)
    self.elements.append(ret)
    return ret
  
  def peek(self) -> T:
    return self.elements[-1]
  
  def maybe_peek(self) -> Optional[T]:
    if len(self.elements) == 0:
      return None
    return self.peek()
  
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
  # strategy: ParsingStrategy
  # def __init__(self, strategy: ParsingStrategy, elements: Optional[List[model.AstNode]] = None):
  #   super().__init__(elements=elements)
  #   self.strategy = strategy
  
  def create(self, arg: model.AstNode) -> model.AstNode:
    return arg


class ScopeStack(ParsingStack[str, model.Scope]):
  def create(self, arg: str) -> model.Scope:
    return model.Scope(
      name=arg,
      parent=self.maybe_peek(),
      aliases=dict(),
    )


class PathStack(ParsingStack[Optional[str], Optional[str]]):
  def create(self, arg: Optional[str]) -> Optional[str]:
    return arg


class ParsingState:
  module_path: str
  codes: CodeStack
  scopes: ScopeStack
  detailed_paths: PathStack
  referencable_paths: PathStack
  parsing_strategy: ParsingStrategy
  
  def __init__(self, module_path: str, codes: CodeStack, scopes: ScopeStack, detailed_paths: PathStack, referencable_paths: PathStack, parsing_strategy: ParsingStrategy):
    self.module_path = module_path
    self.codes = codes
    self.scopes = scopes
    self.detailed_paths = detailed_paths
    self.referencable_paths = referencable_paths
    self.parsing_strategy = parsing_strategy
  
  # TODO: (maybe) this thing should never have a None in it
  def create_id(self) -> str:
    assert all(s is not None for s in self.detailed_paths.elements)
    return ".".join(s for s in self.detailed_paths.elements if s is not None)
  
  def fully_qualify(self) -> Optional[str]:
    if any(s is None for s in self.referencable_paths.elements):
      return None
    return ".".join(s for s in self.referencable_paths.elements if s is not None)

  def assert_empty(self) -> None:
    assert len(self.codes.elements) == 0
    assert len(self.scopes.elements) == 0
    assert len(self.detailed_paths.elements) == 0
    assert len(self.referencable_paths.elements) == 0
  
  @classmethod
  def create(cls, module_path: str, parsing_strategy: ParsingStrategy) -> "ParsingState":
    return cls(
      module_path=module_path,
      codes=CodeStack(),
      scopes=ScopeStack(),
      detailed_paths=PathStack(),
      referencable_paths=PathStack(),
      parsing_strategy=parsing_strategy,
    )