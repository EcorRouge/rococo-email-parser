from typing import Optional

from pydantic import BaseModel


class EmailAddress(BaseModel):
    name: Optional[str]
    address: Optional[str]
