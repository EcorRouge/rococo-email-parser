import pytest
from rococo.models.enums import (
    CompatibleStrEnum,
    ContentTypes,
    JournalingHeader,
)


class TestCompatibleStrEnum:
    """Tests for CompatibleStrEnum base class"""

    def test_str_method_returns_value(self):
        """Test that __str__ method returns the enum value"""
        assert str(ContentTypes.text_plain) == 'text/plain'
        assert str(ContentTypes.forwarding_content_type) == 'message/rfc822'
        assert str(JournalingHeader.x_ms_journal_report) == 'X-MS-Journal-Report'
        assert str(JournalingHeader.x_gm_journal_id) == 'X-GM-Journal-ID'


class TestContentTypes:
    """Tests for ContentTypes enum"""

    def test_all_enum_values(self):
        """Test that all ContentTypes enum values are accessible"""
        assert ContentTypes.forwarding_content_type == 'message/rfc822'
        assert ContentTypes.text_plain == 'text/plain'
        assert ContentTypes.message_delivery_status == 'message/delivery-status'

    def test_list_method(self):
        """Test the list() classmethod returns all enum values"""
        values = ContentTypes.list()
        assert isinstance(values, list)
        assert 'message/rfc822' in values
        assert 'text/plain' in values
        assert 'message/delivery-status' in values
        assert len(values) == 3

    def test_enum_iteration(self):
        """Test that enum can be iterated"""
        values = [h.value for h in ContentTypes]
        assert len(values) == 3
        assert 'message/rfc822' in values
        assert 'text/plain' in values
        assert 'message/delivery-status' in values


class TestJournalingHeader:
    """Tests for JournalingHeader enum"""

    def test_all_enum_values(self):
        """Test that all JournalingHeader enum values are accessible"""
        assert JournalingHeader.x_ms_journal_report == 'X-MS-Journal-Report'
        assert JournalingHeader.x_gm_journal_id == 'X-GM-Journal-ID'

    def test_list_method(self):
        """Test the list() classmethod returns all enum values"""
        values = JournalingHeader.list()
        assert isinstance(values, list)
        assert 'X-MS-Journal-Report' in values
        assert 'X-GM-Journal-ID' in values
        assert len(values) == 2

    def test_enum_iteration(self):
        """Test that enum can be iterated"""
        values = [h.value for h in JournalingHeader]
        assert len(values) == 2
        assert 'X-MS-Journal-Report' in values
        assert 'X-GM-Journal-ID' in values

