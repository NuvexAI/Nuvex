from typing import Generic, TypeVar, Optional, Union, Dict, Any

from pydantic import BaseModel

T = TypeVar('T')


class RestResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: Optional[Union[T, Dict[str, Any]]] = None
