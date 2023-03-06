
from typing import List, Optional
import ast
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Union
import os

class GlobalVariable(BaseModel):
    fully_qualified_name: str
    variable_type: str = "not implemented"
