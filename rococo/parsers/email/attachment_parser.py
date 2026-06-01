import hashlib
from email.policy import EmailPolicy
from email.message import EmailMessage
from typing import List
import logging

from rococo.models import Attachment

logger = logging.getLogger(__name__)


def _parse_attachments(message_id, email_message: EmailMessage) -> List[Attachment]:
    """
    Parses message attachments.
    Doesn't throw parse exceptions, only logs them.
    Attachments which cannot be parsed will not be included in the resulting list

    :param email_message: Email message
    :return: List of attachments
    """
    attachments: List[Attachment] = []
    for part in email_message.iter_attachments():
        try:
            if part.is_multipart():
                attachment = _parse_multipart_attachment(part, message_id)
            else:
                attachment = _parse_simple_attachment(part)
            
            if attachment:
                attachments.append(attachment)
        except Exception as e:
            logger.error(f"Error parsing message {message_id}: {e}")
            continue

    return attachments


def _parse_multipart_attachment(part: EmailMessage, message_id: str) -> Attachment | None:
    """Parse a multipart attachment"""
    attachment_parts: List[EmailMessage] = part.get_payload()
    filename = part.get_filename()
    
    if not filename and len(attachment_parts) > 0:
        ap = attachment_parts[0]
        content_type = f"{part.get_content_maintype()}-{part.get_content_subtype()}"
        filename = f"{ap.get('subject') or ap.get('message-id') or content_type}.eml"

    try:
        payload = part.as_string(policy=EmailPolicy(verify_generated_headers=False))
        return Attachment(
            name=filename,
            hash=hashlib.sha256(payload.encode()).hexdigest(),
            content_transfer_encoding=part.get('Content-Transfer-Encoding'),
            content_type=part.get_content_type(),
            payload=payload
        )
    except Exception as pe:
        logger.error(f"Error parsing part of message {message_id}: {pe}")
        return None


def _parse_simple_attachment(part: EmailMessage) -> Attachment | None:
    """Parse a simple (non-multipart) attachment"""
    filename = part.get_filename()
    if not filename:
        return None

    return Attachment(
        name=filename,
        hash=hashlib.sha256(part.get_payload().encode()).hexdigest(),
        content_transfer_encoding=part.get('Content-Transfer-Encoding'),
        content_type=part.get_content_type(),
        payload=part.get_payload()
    )
