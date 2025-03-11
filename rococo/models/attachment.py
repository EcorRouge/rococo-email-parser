from typing import Optional
from pydantic import BaseModel


class Attachment(BaseModel):
    """
    Defines a message attachment
    """

    name: Optional[str] = None
    """
    Attachment name
    """

    hash: Optional[str] = None
    """
    Content hash (SHA-256)
    """

    content_transfer_encoding: Optional[str] = None
    """
    Content transfer encoding
    """

    content_type: Optional[str] = None
    """
    Content type (MIME)
    """

    payload: Optional[str] = None
    """
    Attachment payload
    """

    def __str__(self):
        return f"name: {self.name}, hash: {self.hash}, content_type: {self.content_type}"
