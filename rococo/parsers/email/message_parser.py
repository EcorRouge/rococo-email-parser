import re
from datetime import timezone, datetime
from email.message import EmailMessage, MIMEPart

from rococo.exceptions import DateNotFoundException
from rococo.models import ContentTypes

from .email_encodings import _decode_content
from .header_parser import (
    _get_header
)

# Sample date record catered in the pattern: Sat, 5 Jul 2020 18:13:51 +0000
DATE_TIME_RE = re.compile(
    r"\b"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),"  # Day of the week
    r"\s"  # Space
    r"\d{1,2}"  # One or two digits for the day
    r"\s"  # Space
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"  # Month abbreviation
    r"\s"  # Space
    r"\d{4}"  # Four digits for the year
    r"\s"  # Space
    r"\d{2}:\d{2}:\d{2}"  # Time in HH:MM:SS format
    r"\s"  # Space
    r"[+-]\d{4}"  # Time zone offset in +0000 or -0000 format
    r"\b"
)


def _decode_bytes(email_bytes: bytes) -> str:
    """
    Decodes message raw bytes to string, replacing "<[" and "]>" escape sequences
    """
    try:
        email_str = email_bytes.decode('utf-8')
    except UnicodeDecodeError:
        email_str = _decode_content(encoding=None, raw_content=email_bytes)

    if "<[" in email_str and "]>" in email_str:
        email_str = email_str.replace("<[", "<")
        email_str = email_str.replace("]>", ">")

    email_str = re.sub(r'(?i)^Message-ID:\s*<\s*>\s*$', 'Message-ID:', email_str, flags=re.MULTILINE)  # Rollbar error #13028. Python email lib fails with "IndexError: list index out of range"
    email_str = re.sub(r'(?i)^(To:\s*.+@)\s*$', r'\1invalid-domain', email_str, flags=re.MULTILINE)  # Rollbar error #13027. Python email lib fails with "IndexError: string index out of range"
    email_str = re.sub(r'(?i)^(From:\s*.+@)\s*$', r'\1invalid-domain', email_str, flags=re.MULTILINE)  # Rollbar error #13027. Python email lib fails with "IndexError: string index out of range"
    email_str = re.sub(r'(?i)^(Cc:\s*.+@)\s*$', r'\1invalid-domain', email_str, flags=re.MULTILINE)  # Rollbar error #13027. Python email lib fails with "IndexError: string index out of range"
    email_str = re.sub(r'(?i)^(Bcc:\s*.+@)\s*$', r'\1invalid-domain', email_str, flags=re.MULTILINE)  # Rollbar error #13027. Python email lib fails with "IndexError: string index out of range"

    return email_str


def _get_original_messages(email_message: EmailMessage, header_name: str = 'message-id') -> list[MIMEPart]:
    """
    Returns a list of nested messages (in case if it's attached in forwarded or bounced email)

    :param email_message: Email message
    :param header_name: Header which signs that it's a nested message. By default, 'message-id'
    """
    nested_messages = []

    for part in email_message.iter_parts():
        if part.get_content_type() not in ContentTypes.list():
            continue

        if part.is_multipart():
            for payload in part.get_payload():
                header_value = payload.get(header_name, None)

                if header_value:
                    nested_messages.append(part)
        else:
            payload = part.get_payload()
            headers = _get_header(payload, header_name)

            for header_value in headers:
                if header_value:
                    nested_messages.append(part)

    return nested_messages


def _get_message_date(email_message: EmailMessage) -> datetime:
    """
    Extracts and parses date of the message.
    Takes "Date:" header first, if it's not found - uses "Received:" header
    """
    # Get date from Date header
    email_date = email_message.get_all('date', [])
    for date in email_date:
        if date.datetime:
            return date.datetime.astimezone(timezone.utc)

    # If date still not found, try to retrieve it from "Received header"
    received_header = email_message.get_all('received', [])
    for header in received_header:
        if date_match := DATE_TIME_RE.findall(header):
            return datetime.strptime(date_match[0], '%a, %d %b %Y %H:%M:%S %z')

    raise DateNotFoundException
