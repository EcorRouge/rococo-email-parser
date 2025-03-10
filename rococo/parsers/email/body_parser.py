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


def _parse_previous_date(previous_body: str) -> str:
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


def _parse_plain_replies(body: str) -> (str, str, str):
    if body is None or body.strip() == "":
        return (body, body, None)

    current_body = ""
    previous_body = None

    current_msg_finished = False

    # Split the email body into lines.
    lines = body.splitlines()
    for line in lines:
        if current_msg_finished:
            previous_body += "\n" + line
        else:
            # If the line matches the forwarded message pattern:
            if FWD_RE.match(line):
                current_msg_finished = True
            elif REPLY_RE.match(line):
                current_msg_finished = True
            elif QUOTE_RE.match(line):
                current_msg_finished = True

            if current_msg_finished:
                if previous_body:
                    previous_body += "\n" + line
                else:
                    previous_body = line
            else:
                if (len(current_body)) > 0:
                    current_body += "\n"
                current_body += line

    return (body, current_body, previous_body)

# Function to parse current message body and all previous messages (in quoted section)
# For plain-text body.
# Takes EmailMessage object as an argument


def _parse_body(email_message) -> (str, str, str):
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

    # This is how gmail adds previous emails (quote format #1) - quoted text is inside first div with class "gmail_quote" - there's a tree of such divs if thread is large
    replyDiv = soup.find('div', {'class': 'gmail_quote'})
    if replyDiv:
        prev_body_html = str(replyDiv)
        replyDiv.decompose()
    else:  # This is o365 format - common for other mail clients - cited text is inside div with name "messageReplySection" - and there's a tree like in gmail format. Actually, this may also present in the gmail format, but not at the top level
        replyDiv = soup.find('div', {'name': 'messageReplySection'})
        if replyDiv:
            prev_body_html = str(replyDiv)
            replyDiv.decompose()

    # This is probably Outlook format - replies/forwarded messages are split using <hr/>, and there's a marker div with id='appendOnSend'. Next level has id ='x_appendOnSend'.
    if not prev_body_html:
        markerDiv = soup.find('div', {'id': 'appendonsend'})
        if markerDiv:
            prev_body_html = str(markerDiv)

            siblings = []
            for sibling in markerDiv.next_siblings:
                prev_body_html += "\n" + str(sibling)
                siblings += sibling

            for sibling in siblings:
                try:
                    sibling.decompose()
                except Exception:
                    pass

            markerDiv.decompose()

    # Get the final HTML after removing previous text
    cur_body_html = str(soup)

    return (cur_body_html, prev_body_html)

# Function to parse current message body and all previous messages (in quoted section)
# For html body.
# Takes message html body as an argument


def _parse_html_replies(html: str) -> (str, str, str):
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
        # If there's img tags with cid, replace it with the actual image
        soup = BeautifulSoup(html, "html.parser")

        # Find all img tags with a src attribute that starts with 'cid:'
        img_tags = soup.find_all("img", {"src": re.compile("^cid:")})

        # For each img tag, replace the src attribute with a URL pointing
        # to the attachment data
        for img_tag in img_tags:
            # Extract the CID without the 'cid:' prefix
            cid = img_tag["src"][4:]

            # Retrieve the attachment data by the CID
            for message in email_message.walk():
                if message.is_attachment() or message.get('Content-ID'):
                    if cid in message.get('Content-ID', ""):
                        # Extract the image type from the CID
                        if message.get_filename():
                            image_type = os.path.splitext(message.get_filename())[
                                1][1:].lower()
                        else:
                            image_type = message.get_content_subtype()
                        image_data = message.get_payload()

                        # Set the src attribute with the base64-encoded data
                        img_tag["src"] = f"data:image/{image_type};base64,{image_data}"

        # Get the final HTML after replacing the CID references with
        # base64-encoded data URLs
        html = str(soup)

        (cur_body_html, prev_body_html) = _parse_html_replies_soup(soup)
    except RecursionError as e:
        logger.info(
            f"Retrying with recursion limit of {default_recursion_limit * 2}")
        sys.setrecursionlimit(default_recursion_limit * 2)

        return _parse_html(email_message)
    finally:
        sys.setrecursionlimit(default_recursion_limit)

    return (html, cur_body_html, prev_body_html)


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
