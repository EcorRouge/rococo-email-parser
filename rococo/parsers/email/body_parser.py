import os
import quopri
import re
import sys
import logging
from bs4 import BeautifulSoup


from .email_encodings import _decode_content
from rococo.models import Email

logger = logging.getLogger(__name__)

# Regex pattern to detect lines indicating a forwarded message.
FWD_RE = re.compile(r"^-*\s+Forwarded message")
# Regex pattern to detect lines indicating reply header
REPLY_RE = re.compile(r"On\s+(.*)\s+at\s+([^,]*)\s*,\s*([^,]*)\s*,\s*wrote\:")
# Regex pattern to detect lines that are quoted text (typical in email replies).
QUOTE_RE = re.compile(r"^>(\s>)*\s*")
DATE_HDR_RE = re.compile(r"^>*Date:\s+(.*)\s+at\s+(.*)")

# Function to parse previous message body and extract it's timestamp
# There are 2 possible message types: forwarded message and reply
# Returns extracted date&time as string, expected format is "Jan 14, 2024 3:24 PM -0800"


def _parse_previous_date(previous_body: str) -> str | None:
    # need to go through lines one by one, because we need the first regex match
    lines = previous_body.splitlines()
    for line in lines:
        if reply_match := REPLY_RE.match(line):
            return re.sub('[^0-9a-zA-Z:,+-]+', ' ', reply_match.group(1) + " " + reply_match.group(2))
        elif date_match := DATE_HDR_RE.match(line):
            return re.sub('[^0-9a-zA-Z:,+-]+', ' ', date_match.group(1) + " " + date_match.group(2))

    return None

# Function to parse current message body and all previous messages (in quoted section)
# For plain-text body.
# Takes message plain-text body as an argument
# Returns 3 strings - entire body, current message and previous message


def _is_reply_separator(line: str) -> bool:
    """Check if line marks the start of a previous message section"""
    return bool(FWD_RE.match(line) or REPLY_RE.match(line) or QUOTE_RE.match(line))


def _append_to_body(body: str, line: str) -> str:
    """Append a line to the body with proper newline handling"""
    if len(body) > 0:
        return body + "\n" + line
    return line


def _parse_plain_replies(body: str | None) -> tuple[str | None, str | None, str | None]:
    if body is None or body.strip() == "":
        return (body, body, None)

    current_body = ""
    previous_body = ""
    in_previous_section = False

    lines = body.splitlines()
    for line in lines:
        if in_previous_section:
            previous_body = _append_to_body(previous_body, line)
        elif _is_reply_separator(line):
            in_previous_section = True
            previous_body = line
        else:
            current_body = _append_to_body(current_body, line)

    # Return None for previous_body if it's empty
    return (body, current_body, previous_body if previous_body else None)

# Function to parse current message body and all previous messages (in quoted section)
# For plain-text body.
# Takes EmailMessage object as an argument


def _parse_body(email_message) -> tuple[str, str, str]:
    text_plain = email_message.get_body(preferencelist='plain')
    if not text_plain:
        return (None, None, None)

    body = "".join(_parse_content(text_plain))

    return _parse_plain_replies(body)

# Function to parse current message body and all previous messages (in quoted section)
# For html body.
# Takes BeautifulSopy as an argument


def _parse_html_replies_soup(soup) -> (str, str):
    prev_body_html = None

    # Try Gmail format - quoted text in div with class "gmail_quote"
    prev_body_html = _extract_gmail_quote(soup)
    
    # Try O365 format - cited text in div with name "messageReplySection"
    if not prev_body_html:
        prev_body_html = _extract_o365_quote(soup)
    
    # Try Outlook format - marker div with id='appendonsend'
    if not prev_body_html:
        prev_body_html = _extract_outlook_quote(soup)

    # Get the final HTML after removing previous text
    cur_body_html = str(soup)

    return (cur_body_html, prev_body_html)


def _extract_gmail_quote(soup) -> str | None:
    """Extract Gmail quote format"""
    reply_div = soup.find('div', {'class': 'gmail_quote'})
    if reply_div:
        prev_html = str(reply_div)
        reply_div.decompose()
        return prev_html
    return None


def _extract_o365_quote(soup) -> str | None:
    """Extract O365/messageReplySection quote format"""
    reply_div = soup.find('div', {'name': 'messageReplySection'})
    if reply_div:
        prev_html = str(reply_div)
        reply_div.decompose()
        return prev_html
    return None


def _extract_outlook_quote(soup) -> str | None:
    """Extract Outlook appendonsend quote format"""
    marker_div = soup.find('div', {'id': 'appendonsend'})
    if not marker_div:
        return None
        
    prev_html = str(marker_div)
    siblings = []
    
    for sibling in marker_div.next_siblings:
        prev_html += "\n" + str(sibling)
        siblings.append(sibling)

    for sibling in siblings:
        try:
            sibling.decompose()
        except Exception:
            pass

    marker_div.decompose()
    return prev_html

# Function to parse current message body and all previous messages (in quoted section)
# For html body.
# Takes message html body as an argument


def _parse_html_replies(html: str | None) -> tuple[str | None, str | None, str | None]:
    if html is None or html.strip() == "":
        return (html, html, None)

    soup = BeautifulSoup(html, "html.parser")

    (cur_body_html, prev_body_html) = _parse_html_replies_soup(soup)

    return (html, cur_body_html, prev_body_html)

# Function to parse current message body and all previous messages (in quoted section).
# Also, replaces img tags with "cid:" in url with actual content from attachments.
# For html body.
# Takes EmailMessage object as an argument


def _parse_html(email_message) -> (str, str, str):
    html = ""
    cur_body_html = ""
    prev_body_html = ""

    """
    Replaces cid with image binary string.
    """
    default_recursion_limit = sys.getrecursionlimit()
    try:
        text_html = email_message.get_body(preferencelist='html')
        if not text_html:
            return (None, None, None)

        html = "".join(_parse_content(text_html))
        soup = BeautifulSoup(html, "html.parser")

        # Replace img tags with cid: references with actual base64 data
        _replace_cid_images(soup, email_message)

        # Get the final HTML after replacing the CID references
        html = str(soup)
        (cur_body_html, prev_body_html) = _parse_html_replies_soup(soup)
    except RecursionError:
        logger.info(
            f"Retrying with recursion limit of {default_recursion_limit * 2}")
        sys.setrecursionlimit(default_recursion_limit * 2)
        return _parse_html(email_message)
    finally:
        sys.setrecursionlimit(default_recursion_limit)

    return (html, cur_body_html, prev_body_html)


def _replace_cid_images(soup, email_message):
    """Replace img tags with cid: references with base64-encoded data URLs"""
    img_tags = soup.find_all("img", {"src": re.compile("^cid:")})
    
    for img_tag in img_tags:
        cid = img_tag["src"][4:]  # Remove 'cid:' prefix
        
        for message in email_message.walk():
            if not (message.is_attachment() or message.get('Content-ID')):
                continue
                
            if cid not in message.get('Content-ID', ""):
                continue
                
            # Extract the image type
            if message.get_filename():
                image_type = os.path.splitext(message.get_filename())[1][1:].lower()
            else:
                image_type = message.get_content_subtype()
                
            image_data = message.get_payload()
            img_tag["src"] = f"data:image/{image_type};base64,{image_data}"
            break


def _parse_content(email_message):
    encoding = email_message.get_param('charset', 'utf-8').lower()

    try:
        # Get email content using the latest method
        content = email_message.get_content()
    except LookupError:
        # Get email content using the legacy method if latest method throws exception
        raw_content = email_message.get_payload(decode=True)
        content = _decode_content(encoding, raw_content)

    # Try decoding again to see if content is Quoted Printable, ignore otherwise
    try:
        raw_content = quopri.decodestring(content)
        content = _decode_content(encoding, raw_content)
    except ValueError:
        pass

    return content
