import json
import pytest
import dateutil.parser
import datetime

from rococo.models import Attachment
import rococo.parsers.email as parser

from utils import list_files, read_local_file

DATA_DIR = "data"


@pytest.mark.parametrize("eml_file", list_files(DATA_DIR, ".eml"))
def test_parser(eml_file: str):
    filename = eml_file.replace(".eml", "")

    eml_bytes = read_local_file(f"{DATA_DIR}/{eml_file}")
    expected_str = read_local_file(f"{DATA_DIR}/{filename}.json")

    email = parser.parse(eml_bytes)
    expected = json.loads(expected_str)

    assert email.subject == expected.get('subject')
    assert email.from_.model_dump() == expected.get('from_')
    assert [to.model_dump() for to in email.to] == expected.get('to')
    assert [cc.model_dump() for cc in email.cc] == expected.get('cc')
    assert [bcc.model_dump() for bcc in email.bcc] == expected.get('bcc')

    if expected.get('current_body'):
        assert email.current_body == expected.get('current_body')

    if expected.get('current_body_html'):
        assert email.current_body_html == expected.get('current_body_html')

    if expected.get('previous_body'):
        assert email.previous_body == expected.get('previous_body')

    if expected.get('previous_body_html'):
        assert email.previous_body_html == expected.get('previous_body_html')

    if expected.get('previous_date'):
        assert email.previous_date == expected.get('previous_date')

    if expected.get('ttr'):
        assert email.ttr == expected.get('ttr')

    if expected.get('category'):
        assert email.category == expected.get('category')

    if expected.get('message_id'):
        assert email.message_id == expected.get('message_id')
    else:
        assert email.message_id
        assert type(email.message_id) is str
        assert len(email.message_id) > 0

    if expected.get('date'):
        utc_date = dateutil.parser.parse(expected.get('date'))
        assert email.date == utc_date

    assert len(email.attachments) == len(expected.get('attachments'))

    expected_keys = Attachment().model_dump().keys()

    for attachment in email.attachments:
        actual_attachment = attachment.model_dump()
        assert all(k in expected_keys for k in actual_attachment.keys())

        assert {"name": actual_attachment.get("name"), "content_transfer_encoding": actual_attachment.get(
            "content_transfer_encoding"), "content_type": actual_attachment.get("content_type")} in expected.get('attachments')
