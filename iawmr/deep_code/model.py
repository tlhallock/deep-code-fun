
import ast
from typing import Dict, Generator, Iterator, List, Optional, Tuple
import pydantic
from enum import Enum, auto
from uuid import uuid4


class AstNodeType(Enum):
  Module = "Module"
  Class = "Class"
  Function = "Function"
  Statement = "Statement"
  Expression = "Expression"
  Unknown = "Unknown"
  # Could have a global vs local... 
  # Should be a variable def 
  # Not used yet
  Variable = "Variable"

class FunctionType(Enum):
  Async = "Async"
  Lambda = "Lambda"
  Simple = "Simple"
  
  # TODO: break up Simple into?
  # Method = auto()
  # Global = auto()
  # Static = auto()
  # Class = auto()

class BaseModel(pydantic.BaseModel):
    class Config:  
        use_enum_values = True


class CodeReference(BaseModel):
  local_name: str
  fully_qualified_name: str
  target: Optional["AstNode"] = None
  reference_type: str
  

class Scope(BaseModel):
  name: str
  parent: Optional["Scope"] = None
  aliases: Dict[str, str] = {}


# class ResolvableReference(BaseModel):
#   node: "AstNode"
#   scope: Scope
#   reference: CodeReference


# rename to base or generic?
class AstNode(BaseModel):
  # parent: Optional["AstNode"]
  node_type: AstNodeType
  # This SHOULD be unique, but if they define the same function twice, it won't be.
  project_unique_path: str
  ast_type: str
  children: Dict[str, List["AstNode"]] = {}
  references: List[CodeReference] = []
  
  def node_attributes(self) -> Dict[str, str]:
    return dict(
      node_type=str(self.node_type),
      ast_type=self.ast_type,
    )

  def get_fully_qualified_name(self) -> Optional[str]:
    return None
  
  def get_scope(self, scope: Optional[Scope]):
    return scope
  
  def all_nodes(self, scope: Optional[Scope] = None) -> Iterator[Tuple["AstNode", Scope]]:
    scope = self.get_scope(scope)
    assert scope
    yield (self, scope)
    for group in self.children.values():
      for child in group:
        yield from child.all_nodes(scope=scope)
      
    
#   def all_references(self, scope: Optional[Scope]):
#     scope = self.get_scope(scope)
#     assert scope
#     for reference in self.references:
#       yield ResolvableReference(node=self, scope=scope, reference=reference)
#     for group in self.children.values():
#       for child in group:
#         yield from child.all_references(scope=scope)

# ResolvableReference.update_forward_refs()

class ScopedNode(AstNode):
  scope: Scope
  
  def get_scope(self, scope: Optional[Scope]):
    return self.scope

class Module(ScopedNode):
  relative_path: str
  fully_qualified_name: Optional[str]
  scope: Scope

  def get_fully_qualified_name(self) -> Optional[str]:
    return self.fully_qualified_name
  
class Function(ScopedNode):
  name: str
  function_type: FunctionType
  fully_qualified_name: Optional[str]
  scope: Scope

  def get_fully_qualified_name(self) -> Optional[str]:
    return self.fully_qualified_name

class Class(ScopedNode):
  name: str
  scope: Scope
  fully_qualified_name: Optional[str]

  def get_fully_qualified_name(self) -> Optional[str]:
    return self.fully_qualified_name

class Statement(AstNode): ...

class Expression(AstNode): ...
  
class Variable(AstNode):
  name: str
