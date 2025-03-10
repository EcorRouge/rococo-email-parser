import email
import hashlib
import logging
from email.header import decode_header
from email import utils
from email.headerregistry import Address
from typing import List

from rococo.models import EmailAddress

logger = logging.getLogger(__name__)


def _parse_message_id(email_message) -> str:
    if 'message-id' not in email_message or not email_message.get('message-id'):
        message_id = utils.make_msgid(hashlib.sha256(
            str(email_message).encode()).hexdigest())
        logger.info(
            f'No message id found in email, generated a new one: {message_id}')
        email_message["message-id"] = message_id

    return email_message.get('message-id')

# Parses O365 antispam headers to detect message category
# Takes X-Forefront-Antispam-Report header value as an input


def _parse_antispam_report_o365(report: str) -> str:
    pairs = report.split(';')
    for pair in pairs:
        keyval = pair.split(':')
        if len(keyval) >= 2:
            if keyval[0].lower() == "cat":
                if keyval[1].lower() == "spm" or keyval[1].lower() == "hspm":
                    return "Spam"
            elif keyval[0].lower() == "sfv":
                if keyval[1].lower() == "spm" or keyval[1].lower() == "skb":
                    return "Spam"

    return None

# Parses antispam headers to detect message category
# Takes email message as an input, extracts necessary headers and parses their values
# Returns cateory: "Spam"|None. (To implement - Social, Promotion, others)


def _parse_antispam_report(email_message) -> str:
    if o365 := email_message.get('X-Forefront-Antispam-Report'):
        return _parse_antispam_report_o365(o365)

    return None


def _get_header(text_payload: str, header_name: str):
    header_list = []
    text_payload_lower = text_payload.lower()

    header_start = 0
    while True:
        header_start = text_payload_lower.find(
            f'\n{header_name}:', header_start)
        if header_start == -1:
            break

        header_end = text_payload_lower.find('\n', header_start + 1)
        header_line = text_payload[header_start:header_end].strip(
            f'{header_name}:').strip()

        # Check if the header continues on the next line
        while header_end < len(text_payload) - 1 and text_payload[header_end + 1].isspace():
            next_line_end = text_payload.find('\n', header_end + 1)
            if next_line_end == -1:
                break  # No more lines
            header_line += text_payload[header_end + 1:next_line_end].strip()
            header_end = next_line_end

        header_start = header_end
        header_list.append(header_line)

    return header_list


def _decode_headers(headers):
    formatted_headers = []

    for header in headers:
        decoded_header = email.header.decode_header(header)

        formatted_parts = []
        for part, encoding in decoded_header:
            if isinstance(part, bytes):
                if encoding is not None:
                    part = part.decode(encoding)
                else:
                    part = part.decode()

            part = part.replace("\n", "")
            formatted_parts.append(part)

        formatted_header = email.utils.parseaddr(' '.join(formatted_parts))
        formatted_headers.append(formatted_header)

    return formatted_headers


def _parse_from(email_message, raw_message: str, header_name: str = 'from') -> (EmailAddress, None):
    try:
        if email_message.get(header_name):
            email_from: Address = email_message.get(header_name).addresses[0]
            return EmailAddress(name=email_from.display_name, address=email_from.addr_spec)
    except AttributeError:
        from_header = _get_header(raw_message, header_name)
        if from_header:
            cleaned_from_header = email.utils.getaddresses(
                list(dict.fromkeys(from_header)))
            addresses = [EmailAddress(name=name, address=address)
                         for (name, address) in cleaned_from_header]
            return addresses[0] if addresses else None
    except ValueError:
        from_header = _get_header(raw_message, header_name)
        if from_header:
            cleaned_from_header = _decode_headers(from_header)
            addresses = [EmailAddress(name=name, address=address)
                         for (name, address) in cleaned_from_header]
            return addresses[0] if addresses else None
    return None


def _parse_to(email_message) -> List[EmailAddress]:
    addresses = []
    if email_message.get('to'):
        addresses = [
            EmailAddress(
                name=a.display_name, address=a.addr_spec
            ) for a in email_message.get('to').addresses
        ]
    return _clean_addresses(addresses)


def _parse_cc(email_message) -> List[EmailAddress]:
    addresses = []
    if email_message.get('cc'):
        addresses = [EmailAddress(name=a.display_name, address=a.addr_spec) for a in
                     email_message.get('cc').addresses]
    return addresses


def _parse_bcc(email_message) -> List[EmailAddress]:
    bcc_list: List[EmailAddress] = []

    if email_message.get('bcc'):
        bcc_list.extend([
            EmailAddress(name=a.display_name, address=a.addr_spec) for a in email_message.get('bcc').addresses
        ])
    elif not email_message.is_multipart():
        bcc_header = _get_header(email_message.get_payload(), 'bcc')

        if bcc_header:
            addresses = email.utils.getaddresses(bcc_header)
            bcc_list.extend([EmailAddress(name=name, address=address)
                            for (name, address) in addresses])

    return bcc_list


def _clean_addresses(addresses: List[EmailAddress]) -> List[EmailAddress]:
    """
    This method cleans the passed addresses list of unwanted characters or encodings and returns the results
    """
    cleaned_addresses = []
    for address in addresses:
        _name, _email = address.model_dump().values()
        decoded_name, _ = decode_header(_name.strip('"'))[
            0] if _name else (_name, None)
        decoded_email, _ = decode_header(_email.strip('"'))[
            0] if _email else (_email, None)

        cleaned_addresses.append(EmailAddress(
            name=decoded_name, address=decoded_email))

    return cleaned_addresses
