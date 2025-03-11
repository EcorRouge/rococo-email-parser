from enum import Enum


class CompatibleStrEnum(str, Enum):
    def __str__(self):
        return self.value


class ContentTypes(CompatibleStrEnum):
    """
        https://datatracker.ietf.org/doc/html/rfc822.html
        https://docs.python.org/3.12/library/email.header.html?highlight=822
    """
    forwarding_content_type = 'message/rfc822'
    text_plain = 'text/plain'
    message_delivery_status = 'message/delivery-status'

    @classmethod
    def list(cls):
        return list(map(lambda h: h.value, cls))


class JournalingHeader(CompatibleStrEnum):
    """
        The journaling header is present in both Microsoft Exchange/Office 365 and Google Workspace journaled emails

        X-MS-Journaling-Report: This header when present, is usually empty string
        X-GM-Journal-ID: This header when present, has a unique identifier as it's value
    """
    x_ms_journal_report = 'X-MS-Journal-Report'
    x_gm_journal_id = 'X-GM-Journal-ID'

    @classmethod
    def list(cls):
        return list(map(lambda h: h.value, cls))
