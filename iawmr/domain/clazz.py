
from typing import List
import ast
from pydantic import BaseModel
from typing import Dict, Union

from iawmr.domain.variable import GlobalVariable
from iawmr.domain.method import Method


class Class(BaseModel):
    fully_qualified_name: str
    variables: List[GlobalVariable] = []
    methods: List[Method] = []