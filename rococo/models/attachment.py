from typing import Optional, Any

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    name: Optional[str] = Field(serialization_alias='Name', default=None)
    hash: Optional[str] = Field(serialization_alias='Hash', default=None)
    content_transfer_encoding: Optional[str] = Field(serialization_alias='ContentTransferEncoding', default=None)
    content_type: Optional[str] = Field(serialization_alias='ContentType', default=None)
    payload: Optional[str] = Field(exclude=True, default=None)

    def __str__(self):
        return f"name: {self.name}, hash: {self.hash}, content_type: {self.content_type}"
