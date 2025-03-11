import hashlib
from email.message import EmailMessage
from typing import List
import logging

from rococo.models import Attachment

logger = logging.getLogger(__name__)


def _parse_attachments(email_message: EmailMessage) -> List[Attachment]:
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
                attachment_parts: List[EmailMessage] = part.get_payload()
                filename = part.get_filename()
                if not filename and len(attachment_parts) > 0:
                    ap = attachment_parts[0]
                    content_type = f"{part.get_content_maintype()}-{part.get_content_subtype()}"
                    filename = f"{ap.get('subject') or ap.get('message-id') or content_type}.eml"

                attachment = Attachment(
                    name=filename,
                    hash=hashlib.sha256(
                        part.as_string().encode()).hexdigest(),
                    content_transfer_encoding=part.get(
                        'Content-Transfer-Encoding'),
                    content_type=part.get_content_type(),
                    payload=part.as_string()
                )
                attachments.append(attachment)
            else:
                filename = part.get_filename()
                if not filename:
                    continue

                attachment = Attachment(
                    name=filename,
                    hash=hashlib.sha256(
                        part.get_payload().encode()).hexdigest(),
                    content_transfer_encoding=part.get(
                        'Content-Transfer-Encoding'),
                    content_type=part.get_content_type(),
                    payload=part.get_payload()
                )
                attachments.append(attachment)
        except Exception as e:
            logger.exception(e)
            continue

    return attachments
