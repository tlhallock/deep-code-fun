


from typing import Any, List, Optional, Dict, Set, Tuple, Type, TypeVar, Callable, Generic
import ast
import os
import typing
from contextlib import contextmanager
from abc import ABC, abstractmethod
import json
from enum import Enum, auto

import pydantic

import iawmr.deep_code.model as model



class PushRuleType(Enum):
  IsInstance = "IsInstance"
  IsClassName = "IsClassName"
  Any = "Any"


class PushCheckResultType(Enum):
  Push = "Push"
  Descend = "Descend"
  Prune = "Prune"
  Continue = "Continue"


# TODO: model.BaseModel
class PushRule(pydantic.BaseModel):
  rule_type: PushRuleType
  result_type: PushCheckResultType
  values: Optional[Set[str]] = None
  # TODO: Avoid this in serialization!
  classes_cache: Optional[Set[Type]] = None
  
  # TODO: why?
  # class Config:
  #   use_enum_values = False
  
  # def __init__(self, **data: Any):
  #   super().__init__(**data)
  #   self._classes_cache = None
  
  def get_classes_cache(self) -> Set[Type]:
    if self.classes_cache is None:
      assert self.values is not None
      self.classes_cache = set(
        eval(value) for value in self.values
        if value.startswith("ast.") and "." not in value[len("ast."):]
      )
    return self.classes_cache
  
  def apply_rule(self, node: ast.AST) -> PushCheckResultType:
    if self.rule_type == PushRuleType.IsInstance:
      for type_ in self.get_classes_cache():
        if isinstance(node, type_):
          return self.result_type
      return PushCheckResultType.Continue
    elif self.rule_type == PushRuleType.IsClassName:
      assert self.values is not None
      if node.__class__.__name__ in self.values:
        return self.result_type
      return PushCheckResultType.Continue
    elif self.rule_type == PushRuleType.Any:
      return self.result_type
    raise Exception(f"Unknown rule type {self.rule_type}")


class ParsingStrategy(model.BaseModel):
  # TODO: now that parse_node return an Optional, we could have a ignore instead of descend into
  rules: List[PushRule]
  
  def should_push(self, node: ast.AST) -> bool:
    for rule in self.rules:
      result = rule.apply_rule(node)
      if result == PushCheckResultType.Continue:
        continue
      elif result == PushCheckResultType.Prune:
        return False
      elif result == PushCheckResultType.Descend:
        return False
      elif result == PushCheckResultType.Push:
        return True
      else:
        raise Exception(f"Unknown result type {result}")
    raise Exception(f"Could not find a rule for {node}")
  
  def should_descend_into(self, node: ast.AST) -> bool:
    for rule in self.rules:
      result = rule.apply_rule(node)
      if result == PushCheckResultType.Continue:
        continue
      elif result == PushCheckResultType.Prune:
        return False
      elif result == PushCheckResultType.Descend:
        return True
      elif result == PushCheckResultType.Push:
        return True
      else:
        raise Exception(f"Unknown result type {result}")
    raise Exception(f"Could not find a rule for {node}")

  @classmethod
  def create(cls) -> "ParsingStrategy":
    return ParsingStrategy(
      rules=[
        PushRule(
          rule_type=PushRuleType.IsInstance,
          result_type=PushCheckResultType.Push,
          values=set([
            "ast.stmt",
            "ast.mod",
          ]),
          classes_cache=None,
        ),
        PushRule(
          rule_type=PushRuleType.Any,
          result_type=PushCheckResultType.Descend,
          values=None,
          classes_cache=None,
        )
      ]
    )
