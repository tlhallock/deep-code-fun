
from typing import List, Optional
import ast
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Union
import os
from iawmr.domain.statement import Statement
from iawmr.domain.clazz import Class
from iawmr.domain.method import Method
from iawmr.domain.variable import GlobalVariable


class Module(BaseModel):
    relative_path: str
    dependency_imports: List[str] = []
    # This needs statements too: at the root level...
    project_imports: List[Union["Module", Method, GlobalVariable, Statement]] = []
    classes: List[Class] = []
    methods: List[Method] = []
    variables: List[GlobalVariable] = []

    @classmethod
    def from_ast(cls, relative_path: str, ast_node: ast.Module) -> "Module":
        # could parse the ast here...
        module = cls(relative_path=relative_path)
        for item in ast_node.body:
            # Move to the import class
            if isinstance(item, ast.Import):
                for alias in item.names:
                    import pdb; pdb.set_trace()
                    module.dependency_imports.append(alias.name)
            elif isinstance(item, ast.ImportFrom):
                import pdb; pdb.set_trace()
                for alias in item.names:
                    if alias.name == "*":
                        module.dependency_imports.append(f"{item.module}.{alias.name}")
                    else:
                        module.dependency_imports.append(f"{item.module}.{alias.name}")
                        # This needs to be conditional, probably in a later step.
                        # module.project_imports.append(GlobalVariable(fully_qualified_name=f"{item.module}.{alias.name}"))
            elif isinstance(item, ast.ClassDef):
                # Move to the class class
                # This fully qualified name is not even close to fully qualified
                # Maybe?
                import pdb; pdb.set_trace()
                class_obj = Class(fully_qualified_name=item.name)
                for subitem in item.body:
                    if isinstance(subitem, ast.FunctionDef):
                        import pdb; pdb.set_trace()
                        method = Method(fully_qualified_name=f"{item.name}.{subitem.name}")
                        for stmt in subitem.body:
                            statement = Statement.parse_expression(stmt)
                            if isinstance(statement, Method):
                                method.statements.append(statement)
                            elif isinstance(statement, GlobalVariable):
                                module.project_imports.append(statement)
                                method.statements.append(Statement(statement_type="expr", references_project_variable=statement))
                            else:
                                method.statements.append(Statement(statement_type="expr", references_project_method=statement))
                        class_obj.methods.append(method)
                    elif isinstance(subitem, ast.Assign):
                        import pdb; pdb.set_trace()
                        statement = Statement.parse_expression(subitem.value)
                        if isinstance(statement, GlobalVariable):
                            module.project_imports.append(statement)
                            class_obj.variables.append(statement)
                        else:
                            class_obj.variables.append(GlobalVariable(fully_qualified_name=statement.fully_qualified_name))
                module.classes.append(class_obj)
            elif isinstance(item, ast.FunctionDef):
                import pdb; pdb.set_trace()
                method = Method(fully_qualified_name=item.name)
                for stmt in item.body:
                    statement = Statement.parse_expression(stmt)
                    if isinstance(statement, Method):
                        method.statements.append(statement)
                    elif isinstance(statement, GlobalVariable):
                        module.project_imports.append(statement)
                        method.statements.append(Statement(statement_type="expr", references_project_variable=statement))
                    else:
                        method.statements.append(Statement(statement_type="expr", references_project_method=statement))
                module.methods.append(method)
            elif isinstance(item, ast.Assign):
                import pdb; pdb.set_trace()
                statement = Statement.parse_expression(item.value)
                if isinstance(statement, GlobalVariable):
                    module.project_imports.append(statement)
                    module.variables.append(statement)
                else:
                    module.variables.append(GlobalVariable(fully_qualified_name=statement.fully_qualified_name))
            else:
                import pdb; pdb.set_trace()
        return module
