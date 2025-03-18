from datetime import datetime
from email import policy, message_from_string
from email.message import EmailMessage

import dateutil.parser

from rococo.models import Email, ContentTypes, JournalingHeader

from rococo.exceptions import (
    InvalidEmailException
)

from .attachment_parser import _parse_attachments
from .body_parser import _parse_body, _parse_html, _parse_previous_date
from .message_parser import (
    _decode_bytes,
    _get_message_date,
    _get_original_messages
)

from .header_parser import (
    _parse_message_id, _parse_bcc, _parse_from, _parse_to, _parse_cc, _parse_antispam_report
)


def load_eml_bytes(email_bytes) -> tuple[EmailMessage, str]:
    """
    Load message from bytes in eml format

    :return: EmailMessage and raw string with eml content
    """
    email_str = _decode_bytes(email_bytes=email_bytes)

    # noinspection PyTypeChecker
    email_message: EmailMessage = message_from_string(
        email_str, _class=EmailMessage, policy=policy.default)
    return email_message, email_str


def parse(email_bytes: bytes) -> Email:
    """
    Parse message from bytes in eml format

    :return: parsed Email
    """

    email_message, email_str = load_eml_bytes(email_bytes)

    if not _is_valid_email(email_message):
        raise InvalidEmailException

    utc_date = _get_message_date(email_message)
    model = Email(
        size_in_bytes=len(email_bytes),
        message_id=_parse_message_id(email_message),
        date=utc_date,
        timestamp=int(datetime.timestamp(utc_date))
    )
    model.message_id

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


def _is_valid_email(email_message: EmailMessage) -> bool:
    """
    Message is valid if it contains body or at least one of (Date:|Received:) headers
    """

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
        prev_date_str = _parse_previous_date(prev_body)
        if prev_date_str:
            try:
                model.previous_date = dateutil.parser.parse(prev_date_str)
                model.previous_timestamp = int(
                    datetime.timestamp(model.previous_date))
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

    model.attachments = _parse_attachments(model.message_id, email_message)

    model.subject = email_message.get('subject')

    return model
