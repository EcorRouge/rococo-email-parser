import pytest
from rococo.parsers.email.body_parser import _parse_previous_date


def test_forwarded_header():
    date = _parse_previous_date("---------- Forwarded message ----------\nFrom: Elizabeth Vach <elizabeth.vach@emailvault.app>\nDate: Jan 14, 2024 at 3:26\u202fPM -0800\nTo: Elizabeth Hanfman <ehanfman1@gmail.com>\nSubject: Re: Office: Receiving (O365 Account) Threads\n\n> Too cute\n>\n>\n>\n> Elizabeth Vach\n> Email Vault\n> elizabeth.vach@emailvault.app\n> emailvault.app\n>\n> On Jan 14, 2024 at 3:24\u202fPM -0800, Elizabeth Hanfman <ehanfman1@gmail.com>, wrote:")
    assert date == "Jan 14, 2024 3:26 PM -0800"


def test_reply_header():
    date = _parse_previous_date(
        "On Jan 14, 2024 at 3:05\u202fPM -0800, Elizabeth Vach <elizabeth.vach@angstromsable.com>, wrote:\n> Hi there,\n>\n> I hope this message finds you well. I'm just testing a thread ")
    assert date == "Jan 14, 2024 3:05 PM -0800"
