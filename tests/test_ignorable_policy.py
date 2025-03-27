import pytest

from rococo.exceptions import DateNotFoundException, InvalidEmailException, IgnorableEmailException
import rococo.parsers.email as parser

BAD_EMAIL_NO_DATE = "From: <MAILER-DAEMON>\nSubject: RE: Test Message Subject\n\nTo: Test User\nCc: CC User\nMessage-Id: <>\nMIME-Version: 1.0\n\nIgnore this body"

IGNORABLE_POLICY = {
    "From": r".*mailer-daemon.*",
    "Subject": r"(delivery status notification|undelivered mail|returned mail)",
    "Auto-Submitted": r"auto-.*"
}


def test_throws_proper_date_exception_with_policy():
    """
    We should throw ignorable exception if policy is used and message matches it.

    Test message with missing date
    """
    eml_bytes = BAD_EMAIL_NO_DATE.encode("utf-8")

    with pytest.raises(DateNotFoundException):
        parser.parse(eml_bytes)

    with pytest.raises(IgnorableEmailException):
        parser.parse(eml_bytes, IGNORABLE_POLICY)
