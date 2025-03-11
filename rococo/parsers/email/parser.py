import email
import email.utils
import re

from datetime import timezone, datetime
from email import policy
from email.message import EmailMessage

import dateutil.parser

from rococo.models import Email, EmailAddress, ContentTypes, JournalingHeader

from rococo.exceptions import (
    DateNotFoundException, InvalidEmailException
)

from .attachment_parser import _parse_attachments
from .body_parser import _parse_body, _parse_html, _parse_previous_date
from .email_encodings import _decode_content

from .header_parser import (
    _get_header, _parse_message_id, _parse_bcc, _parse_from, _parse_to, _parse_cc, _parse_antispam_report
)

TIMESTAMP_FORMAT = '%d-%m-%Y %H:%M:%S'

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

# for file validation (import)


def quick_parse(email_bytes) -> (EmailMessage, str):
    email_str = _parse_raw(email_bytes=email_bytes)

    # noinspection PyTypeChecker
    email_message: EmailMessage = email.message_from_string(
        email_str, _class=EmailMessage, policy=policy.default)
    return email_message, email_str


def parse(email_bytes: bytes) -> Email:
    email_message, email_str = quick_parse(email_bytes)

    is_valid = _validate_email(email_message)
    if not is_valid:
        raise InvalidEmailException

    utc_date = _parse_date(email_message)
    model = Email(
        size_in_bytes=len(email_bytes),
        message_id=_parse_message_id(email_message),
        date=utc_date.strftime(TIMESTAMP_FORMAT),
        timestamp=int(datetime.timestamp(utc_date))
    )

    if any(header in email_message for header in JournalingHeader.list()):
        try:
            nested_messages = _get_original_messages(email_message)
        except Exception:
            _populate_model(
                model=model, email_message=email_message, raw_message=email_str)
            return model

        for nested_message in nested_messages:
            if nested_message.is_attachment():
                continue

            if nested_message.get_content_type() == ContentTypes.text_plain:
                model.extend('bcc', _parse_bcc(nested_message))
            if nested_message.get_content_type() == ContentTypes.forwarding_content_type:
                _populate_model(
                    model=model, email_message=nested_message.get_content(), raw_message=email_str)
    else:
        _populate_model(model=model, email_message=email_message,
                        raw_message=email_str)

    return model


def _parse_raw(email_bytes: bytes):
    try:
        email_str = email_bytes.decode('utf-8')
    except UnicodeDecodeError:
        email_str = _decode_content(encoding=None, raw_content=email_bytes)

    if "<[" in email_str and "]>" in email_str:
        email_str = email_str.replace("<[", "<")
        email_str = email_str.replace("]>", ">")

    return email_str


def _get_original_messages(email_message: EmailMessage, header_name: str = 'message-id'):
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


def _parse_date(email_message: EmailMessage) -> datetime:
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


def _validate_email(email_message: EmailMessage) -> bool:
    body = _parse_body(email_message)
    date_header = email_message.get_all('date', [])
    received_header = email_message.get_all('received', [])

    return any([body, date_header, received_header])


def _populate_model(model: Email, email_message: EmailMessage, raw_message: str):
    model.from_ = _parse_from(email_message, raw_message)

    model.category = _parse_antispam_report(email_message)

    model.extend('to', _parse_to(email_message))
    model.extend('cc', _parse_cc(email_message))
    model.extend('bcc', _parse_bcc(email_message))

    (body, cur_body, prev_body) = _parse_body(email_message)

    if cur_body is None:
        model.current_body = body
    else:
        model.current_body = cur_body
        model.previous_body = prev_body

    if prev_body:
        prev_date = _parse_previous_date(prev_body)
        if prev_date:
            try:
                date = dateutil.parser.parse(prev_date)
                model.previous_date = date.strftime(TIMESTAMP_FORMAT)
                model.previous_timestamp = int(datetime.timestamp(date))
                model.ttr = int(
                    (model.timestamp - model.previous_timestamp) / 60)
                if model.ttr < 0:
                    model.ttr = 0
            except:
                pass

    (html, cur_html, prev_html) = _parse_html(email_message)

    if cur_html is None:
        model.current_body_html = html
    else:
        model.current_body_html = cur_html
        model.previous_body_html = prev_html

    model.attachments = _parse_attachments(email_message)

    model.subject = email_message.get('subject')

    return model
