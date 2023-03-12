
import ast
from typing import Dict, List, Optional
import pydantic
from enum import Enum, auto


class AstNodeType(Enum):
  Module = auto()
  Class = auto()
  Function = auto()
  Statement = auto()
  Variable = auto()  # Could have a global vs local...
  Expression = auto()
  Unknown = auto()

class FunctionType(Enum):
  Async = auto()
  Lambda = auto()
  Simple = auto()
  
  # TODO: break up Simple into?
  # Method = auto()
  # Global = auto()
  # Static = auto()
  # Class = auto()

class BaseModel(pydantic.BaseModel):
    class Config:  
        use_enum_values = True


class CodeReference(BaseModel):
  reference_type: AstNodeType
  local_name: List[str]
  fully_qualified_name: Optional[str]
  

class Scope(BaseModel):
  name: str
  parent: Optional["Scope"] = None
  aliases: Dict[str, str] = {}
  

# rename to base or generic?
class AstNode(BaseModel):
  # parent: Optional["AstNode"]
  scope: Scope
  node_type: AstNodeType
  fully_qualified_name: str
  ast_type: str
  children: list["AstNode"] = []
  references: list[CodeReference] = []

class Module(AstNode):
  relative_path: str
  
class Function(AstNode):
  name: str
  function_type: FunctionType

class Class(AstNode):
  name: str

class Statement(AstNode): ...

class Expression(AstNode): ...
  
class Variable(AstNode):
  name: str


