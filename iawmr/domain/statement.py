
from typing import List, Optional
import ast
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Union
import os

from iawmr.domain.variable import GlobalVariable
from iawmr.domain.reference import Reference


class Statement(BaseModel):
  statement_type: str
  
  # We could have broken out a seperate expression object, but these lists
  # contains all the references for subexpressions
  references: List[Reference]
  # I think there needs to be some reference to a local variable here
  substatements: List["Statement"] = []
  
  @classmethod
  def collect_references_from_expr(cls, node: ast.expr) -> List[Reference]:
    ret = []
    if isinstance(node, ast.Name):
        import pdb; pdb.set_trace()
        # return GlobalVariable(local_name=node.id)
    elif isinstance(node, ast.Call):
        import pdb; pdb.set_trace()
        # We should have to parse sub expressions
        method = node.func
        if isinstance(method, ast.Name):
            fully_qualified_name = method.id
        elif isinstance(method, ast.Attribute):
            fully_qualified_name = cls._get_fully_qualified_name(method)
        else:
            fully_qualified_name = None
        statements = [cls.parse_statement(stmt) for stmt in node.args]
    elif isinstance(node, ast.Attribute):
        # return GlobalVariable(local_name=node.attr)
        import pdb; pdb.set_trace()
    return ret
  
  @staticmethod
  def get_fully_qualified_name(node: ast.AST) -> str:
    """Get the fully qualified name of an AST node"""
    parts = []
    while True:
        if isinstance(node, ast.Module):
            break
        elif isinstance(node, ast.ClassDef):
            parts.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            parts.append(node.name)
        node = node.parent
    parts.reverse()
    return ".".join(parts)
  
  @classmethod
  def parse_statement(cls, node: ast.stmt) -> "Statement":
      substatements = []
      if isinstance(node, ast.Expr):
          if isinstance(node.value, ast.Call):
              import pdb; pdb.set_trace()
              method = node.value.func
              if isinstance(method, ast.Name):
                  raise "What is this"
                  calls_method = method.id
              elif isinstance(method, ast.Attribute):
                  calls_method = method.attr
              else:
                  calls_method = None
          else:
              calls_method = None
          statement_type = "expr"
      elif isinstance(node, ast.Assign):
          # If it's an assignment statement, we need to parse each sub-expression
          substatements = [cls._parse_expression(expr) for expr in node.targets]
          statement_type = "assign"
          calls_method = None
      elif isinstance(node, ast.FunctionDef):
          # If it's a function definition, we create a new Method object
          import pdb; pdb.set_trace()
          calls_method = cls._get_fully_qualified_name(node)
          statement_type = "functiondef"
      else:
          # For all other statement types, we just create a new Statement object
          import pdb; pdb.set_trace()
          statement_type = node.__class__.__name__.lower()
          calls_method = None

      # Recursively parse any sub-statements
      import pdb; pdb.set_trace()
      # If they are statements?
      substatements += [cls.parse_statement(stmt) for stmt in ast.iter_child_nodes(node)]
      return Statement(statement_type=statement_type, calls_method=calls_method, substatements=substatements)
