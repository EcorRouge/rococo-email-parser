import json

import pytest

from rococo.models import Attachment, Email
from rococo.parsers.email import parse
import tests.utils as utils

settings.ES_TIMESTAMP_FORMAT = '%d-%m-%Y %H:%M:%S'
DATA_DIR = "data"


@pytest.mark.parametrize("eml_file", utils.list_files(DATA_DIR, ".eml"))
def test_parser(eml_file: str):
    filename = eml_file.replace(".eml", "")

    eml_bytes = utils.read_local_file(f"{DATA_DIR}/{eml_file}")
    expected_str = utils.read_local_file(f"{DATA_DIR}/{filename}.json")

    email = parse(eml_bytes)
    expected = json.loads(expected_str)

    assert email.subject == expected["subject"]
    assert email.subject == expected.get('subject')
    assert email.from_.model_dump() == expected.get('from_')
    assert [to.model_dump() for to in email.to] == expected.get('to')
    assert [cc.model_dump() for cc in email.cc] == expected.get('cc')
    assert [bcc.model_dump() for bcc in email.bcc] == expected.get('bcc')

#    if expected.get('body'):
#        assert email.body == expected.get('body')

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

    assert email.date == expected.get('date')
    assert len(email.attachments) == len(expected.get('attachments'))

    expected_keys = Attachment().model_dump().keys()

    for attachment in email.attachments:
        actual_attachment = attachment.model_dump()
        assert all(k in expected_keys for k in actual_attachment.keys())
        actual_attachment.pop('hash')
        assert actual_attachment in expected.get('attachments')
