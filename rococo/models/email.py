import json
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from rococo.models import EmailAddress, Attachment


class Email(BaseModel):
    """
    Defines a message
    """

    message_id: Optional[str] = None
    """
    Unique message id
    """

    to: Optional[List[EmailAddress]] = []
    """
    List of recepients
    """

    from_: Optional[EmailAddress] = []
    """
    Sender address
    """

    cc: Optional[List[EmailAddress]] = []
    """
    List of copy(CC) recepients
    """

    bcc: Optional[List[EmailAddress]] = []
    """
    List of shadow copy(BCC) recepients
    """

    subject: Optional[str] = None
    """
    Message subject
    """

    attachments: Optional[List[Attachment]] = []
    """
    Message attachment
    """

    current_body: Optional[str] = None
    """
    Current plain-text body (without original message, if it's a reply or forwarded message)
    """

    current_body_html: Optional[str] = None
    """
    Current html body (without original message, if it's a reply or forwarded message)
    """

    previous_body: Optional[str] = None
    """
    Previous plain-text bodies (concatenated)
    """

    previous_body_html: Optional[str] = None
    """
    Previous html bodies (concatenated)
    """

    ttr: Optional[int] = 0
    """
    The number of minutes between the original email and this reply, aka time-to-reply
    """

    business_hour_ttr: Optional[int] = 0
    """
    The number of minutes within business hours between the original email and this reply. This means factoring in the time of day, day of week, and holidays
    """

    category: Optional[str] = None
    """
    Message category - Spam, Promotion, Social, Others
    """

    date: Optional[datetime] = None
    """
    Message date
    """

    previous_date: Optional[datetime] = None
    """
    Previous message date
    """

    size_in_bytes: Optional[int] = 0
    """
    Message size in bytes
    """

    def __str__(self) -> str:
        return self.message_id

    def __repr__(self) -> str:
        return json.dumps(self.model_dump())

    def extend(self, field_name: str, addresses: List[EmailAddress]) -> None:
        if field_name == 'to':
            self.to.extend(a for a in addresses if a not in self.to)

        if field_name == 'cc':
            self.cc.extend(a for a in addresses if a not in self.cc)

        if field_name == 'bcc':
            self.bcc.extend(a for a in addresses if a not in self.bcc)
