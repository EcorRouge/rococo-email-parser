import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict
import logging

from pydantic import BaseModel, Field

from rococo.models import EmailAddress, Attachment, TargetedSentiment

logger = logging.getLogger(__name__)


class Email(BaseModel):
    message_id: Optional[str] = Field(
        serialization_alias='MessageID', default=None)
    entity_id: Optional[str] = Field(
        serialization_alias='EntityID', default=None)
    organization_id: Optional[str] = Field(
        serialization_alias='OrganizationID', default=None)

    to: Optional[List[EmailAddress]] = Field(
        serialization_alias='To', default=[])
    from_: Optional[EmailAddress] = Field(
        serialization_alias='From', default=None)
    cc: Optional[List[EmailAddress]] = Field(
        serialization_alias='CC', default=[])
    bcc: Optional[List[EmailAddress]] = Field(
        serialization_alias='BCC', default=[])
    subject: Optional[str] = Field(serialization_alias='Subject', default=None)

    body: Optional[str] = Field(serialization_alias='Body', default=None,
                                deprecated="Use current_body and previous_body fields")
    html: Optional[str] = Field(serialization_alias='BodyHTML', default=None,
                                deprecated="Use current_body_html and previous_body_html fields")

    attachments: Optional[List[Attachment]] = Field(
        serialization_alias='Attachments', default=[])

    current_body: Optional[str] = Field(
        serialization_alias='CurrentBody', default=None)
    current_body_html: Optional[str] = Field(
        serialization_alias='CurrentBodyHTML', default=None)

    previous_body: Optional[str] = Field(
        serialization_alias='PreviousBody', default=None)
    previous_body_html: Optional[str] = Field(
        serialization_alias='PreviousBodyHTML', default=None)

    # (in, out, none to represent whether it was an incoming email, outgoing email, or internal-only, respectively)
    direction: Optional[str] = Field(
        serialization_alias='Direction', default=None)
    # (internal, external to represent who the email was sent to)
    audience: Optional[str] = Field(
        serialization_alias='Audience', default=None)
    # (negative, neutral, positive to represent the overall sentiment of the email)
    sentiment: Optional[str] = Field(
        serialization_alias='Sentiment', default=None)
    # (a list of entities and their related sentiment)
    targeted_sentiment: Optional[List[TargetedSentiment]] = Field(
        serialization_alias='TargetedSentiment', default=[])
    # (the number of minutes between the original email and this reply, aka time-to-reply)
    ttr: Optional[int] = Field(serialization_alias='TTR', default=None)
    # (the number of minutes within business hours between the original email and this reply. This means factoring in the time of day, day of week, and holidays)
    business_hour_ttr: Optional[int] = Field(
        serialization_alias='BusinessHourTTR', default=None)
    # (spam, promotion, social, others)
    category: Optional[str] = Field(
        serialization_alias='Category', default=None)

    date: Optional[str] = Field(serialization_alias='Date', default=None)
    timestamp: Optional[int] = Field(
        serialization_alias='timestamp', default=None)

    # datetime (in ES format) of the previous message
    previous_date: Optional[str] = Field(
        serialization_alias='PreviousDate', default=None)
    # timestamp of the previous message
    previous_timestamp: Optional[int] = Field(
        serialization_alias='PreviousTimestamp', default=None)

    created_date: Optional[str] = Field(
        serialization_alias='CreatedDate', default_factory=lambda: f'{datetime.utcnow().isoformat(timespec="seconds")}Z'
    )
    size_in_bytes: Optional[int] = Field(
        serialization_alias='SizeBytes', default=0)
    s3_storage_zip: Optional[str] = Field(
        serialization_alias='S3StorageZip', default=None)

    def __str__(self) -> str:
        hash = hashlib.sha256(self.message_id.encode()).hexdigest()
        _id = f"{self.organization_id}_{self.timestamp}_{hash}"
        logger.info(f"email _id: {_id}")
        return _id

    def __repr__(self) -> str:
        return json.dumps(self.model_dump())

    def extend(self, field_name: str, addresses: List[EmailAddress]) -> None:
        if field_name == 'to':
            self.to.extend(a for a in addresses if a not in self.to)

        if field_name == 'cc':
            self.cc.extend(a for a in addresses if a not in self.cc)

        if field_name == 'bcc':
            self.bcc.extend(a for a in addresses if a not in self.bcc)

    def update_identifier(self, entity_id: str, s3_key: str):
        self.entity_id = entity_id

        s3_key_parts = s3_key.split("/")
        self.organization_id = s3_key_parts[1]
        self.s3_storage_zip = s3_key
