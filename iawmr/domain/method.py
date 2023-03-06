
from typing import List, Optional
import ast
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Union
import os

from iawmr.domain.statement import Statement



class Method(BaseModel):
    fully_qualified_name: str
    statements: List[Statement] = []

