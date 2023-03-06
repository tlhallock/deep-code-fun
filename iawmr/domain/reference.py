
import pydantic
from enum import Enum, auto

class ReferenceType(Enum):
  Method = auto()
  GlobalVariable = auto()
  Class = auto()
  Module = auto()
  # Should we have a reference type for a local variable?
  # Should we have a reference type for a function?


class Reference(pydantic.BaseModel):
  reference_type: ReferenceType
  fully_qualified_name: str
