from typing import Optional

from pydantic import BaseModel


class EmailAddress(BaseModel):
    """
    Defines an email address
    """

    name: Optional[str] = None
    """
    Person name
    """

    address: Optional[str] = None
    """
    Email address
    """
