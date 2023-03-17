
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
  # This is a circular reference
  parent: Optional["Scope"] = None
  aliases: Dict[str, str] = {}
  
  def resolve(self, name: str) -> Optional[str]:
    resolved, located = self._resolve_inner(name=name, resolved=False)
    return resolved if located else None
  
  def _resolve_inner(self, name: str, resolved: bool) -> Tuple[Optional[str], bool]:
    if name in self.aliases:
      name = self.aliases[name]
      resolved = True
    return self._resolve_from_parent(name, resolved)

  def _resolve_from_parent(self, name: str, resolved: bool) -> Tuple[Optional[str], bool]:
    if self.parent:
      return self.parent._resolve_inner(name=name, resolved=resolved)
    return name, resolved


# class ResolvableReference(BaseModel):
#   node: "AstNode"
#   scope: Scope
#   reference: CodeReference


class FieldInstance(BaseModel):
  name: str
  value: str


class NodeChildren(BaseModel):
  value_fields: Dict[str, List["AstNode"]] = {}
  list_fields: Dict[str, List[List["AstNode"]]] = {}
  # If we are parsing every node type, then fields should be unique.
  single_valued: bool = False
  
  def add_value_field(self, name: str, value: "AstNode"):
    if name not in self.value_fields:
      self.value_fields[name] = []
    elif self.single_valued:
      raise ValueError(f"Field {name} was defined twice.")
    self.value_fields[name].append(value)
  
  def add_list_field(self, name: str, value: List["AstNode"]):
    if name not in self.list_fields:
      self.list_fields[name] = []
    elif self.single_valued:
      raise ValueError(f"Field {name} was defined twice.")
    self.list_fields[name].append(value)
    
  def all_nodes(self, scope: Optional[Scope] = None) -> Iterator[Tuple["AstNode", Scope]]:
    assert scope
    for field_group in self.value_fields.values():
      for child in field_group:
        yield from child.all_nodes(scope=scope)
    for outer_group in self.list_fields.values():
      for inner_group in outer_group:
        for child in inner_group:
          yield from child.all_nodes(scope=scope)
          
  def all_children(self) -> Iterator["AstNode"]:
    for field_group in self.value_fields.values():
      for child in field_group:
        yield from child.all_children()
    for outer_group in self.list_fields.values():
      for inner_group in outer_group:
        for child in inner_group:
          yield from child.all_children()


# rename to base or generic?
class AstNode(BaseModel):
  # parent: Optional["AstNode"]
  node_type: AstNodeType
  # This SHOULD be unique, but if they define the same function twice, it won't be.
  project_unique_path: str
  ast_type: str
  children: NodeChildren = pydantic.Field(default_factory=NodeChildren)
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
    yield from self.children.all_nodes(scope=scope)
  
  def all_children(self) -> Iterator["AstNode"]:
    yield self
    yield from self.children.all_children()
  
  def assert_tree_structure(self):
    for child in self.children.all_children():
      assert child.project_unique_path != self.project_unique_path, f"Node {self.project_unique_path} is a child of itself."
    for child in self.children.all_children():
      child.assert_tree_structure()
    
    
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
