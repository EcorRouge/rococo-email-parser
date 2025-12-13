import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from email.message import EmailMessage, MIMEPart

from rococo.exceptions import DateNotFoundException
from rococo.models import ContentTypes
from rococo.parsers.email.message_parser import (
    _decode_bytes,
    _get_original_messages,
    _check_multipart_for_nested_message,
    _check_simple_part_for_nested_message,
    _get_message_date,
)


class TestDecodeBytes:
    """Tests for _decode_bytes function"""

    def test_decode_bytes_utf8(self):
        """Test decoding UTF-8 bytes"""
        email_bytes = b"From: sender@example.com\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "From: sender@example.com" in result
        assert "Subject: Test" in result

    def test_decode_bytes_unicode_decode_error(self):
        """Test decoding bytes with UnicodeDecodeError"""
        email_bytes = b'\xff\xfe\x00\x00'  # Invalid UTF-8
        
        with patch('rococo.parsers.email.message_parser._decode_content') as mock_decode:
            mock_decode.return_value = "decoded content"
            result = _decode_bytes(email_bytes)
            assert result == "decoded content"
            mock_decode.assert_called_once_with(encoding=None, raw_content=email_bytes)

    def test_decode_bytes_with_escape_sequences(self):
        """Test decoding bytes with <[ and ]> escape sequences"""
        email_bytes = b"From: <[sender@example.com]>\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "<[" not in result
        assert "]>" not in result
        assert "sender@example.com" in result

    def test_decode_bytes_empty_message_id(self):
        """Test decoding bytes with empty Message-ID"""
        email_bytes = b"Message-ID: < >\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "Message-ID:" in result
        assert "< >" not in result

    def test_decode_bytes_invalid_domain_to(self):
        """Test decoding bytes with invalid To domain"""
        email_bytes = b"To: user@\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "invalid-domain" in result

    def test_decode_bytes_invalid_domain_from(self):
        """Test decoding bytes with invalid From domain"""
        email_bytes = b"From: user@\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "invalid-domain" in result

    def test_decode_bytes_invalid_domain_cc(self):
        """Test decoding bytes with invalid Cc domain"""
        email_bytes = b"Cc: user@\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "invalid-domain" in result

    def test_decode_bytes_invalid_domain_bcc(self):
        """Test decoding bytes with invalid Bcc domain"""
        email_bytes = b"Bcc: user@\nSubject: Test"
        result = _decode_bytes(email_bytes)
        assert "invalid-domain" in result


class TestGetOriginalMessages:
    """Tests for _get_original_messages function"""

    def test_get_original_messages_with_text_plain(self):
        """Test getting original messages with text/plain content type"""
        email_message = Mock(spec=EmailMessage)
        
        part1 = Mock(spec=MIMEPart)
        part1.get_content_type.return_value = ContentTypes.text_plain
        part1.is_multipart.return_value = False
        
        part2 = Mock(spec=MIMEPart)
        part2.get_content_type.return_value = "text/html"
        part2.is_multipart.return_value = False
        
        email_message.iter_parts.return_value = [part1, part2]
        
        with patch('rococo.parsers.email.message_parser._check_simple_part_for_nested_message') as mock_check:
            mock_check.side_effect = lambda p, h, m: m.append(p) if p.get_content_type() == ContentTypes.text_plain else None
            
            result = _get_original_messages(email_message)
            
            assert len(result) == 1
            assert result[0] == part1

    def test_get_original_messages_with_forwarding_content_type(self):
        """Test getting original messages with message/rfc822 content type"""
        email_message = Mock(spec=EmailMessage)
        
        part = Mock(spec=MIMEPart)
        part.get_content_type.return_value = ContentTypes.forwarding_content_type
        part.is_multipart.return_value = True
        
        email_message.iter_parts.return_value = [part]
        
        with patch('rococo.parsers.email.message_parser._check_multipart_for_nested_message') as mock_check:
            mock_check.side_effect = lambda p, h, m: m.append(p) if p.get_content_type() == ContentTypes.forwarding_content_type else None
            
            result = _get_original_messages(email_message)
            
            assert len(result) == 1
            assert result[0] == part

    def test_get_original_messages_with_multipart(self):
        """Test getting original messages with multipart"""
        email_message = Mock(spec=EmailMessage)
        
        part = Mock(spec=MIMEPart)
        part.get_content_type.return_value = ContentTypes.forwarding_content_type
        part.is_multipart.return_value = True
        
        email_message.iter_parts.return_value = [part]
        
        nested_messages = []
        
        def check_multipart(part, header_name, nested_messages):
            for payload in part.get_payload():
                if payload.get(header_name):
                    nested_messages.append(part)
                    break
        
        with patch('rococo.parsers.email.message_parser._check_multipart_for_nested_message', side_effect=check_multipart):
            payload = Mock()
            payload.get.return_value = "<message-id@example.com>"
            part.get_payload.return_value = [payload]
            
            result = _get_original_messages(email_message)
            
            assert len(result) == 1

    def test_get_original_messages_with_simple_part(self):
        """Test getting original messages with simple part"""
        email_message = Mock(spec=EmailMessage)
        
        part = Mock(spec=MIMEPart)
        part.get_content_type.return_value = ContentTypes.text_plain
        part.is_multipart.return_value = False
        part.get_payload.return_value = "Message-ID: <test@example.com>\nContent: Test"
        
        email_message.iter_parts.return_value = [part]
        
        with patch('rococo.parsers.email.message_parser._get_header') as mock_get_header:
            mock_get_header.return_value = ["<test@example.com>"]
            
            result = _get_original_messages(email_message)
            
            assert len(result) == 1

    def test_get_original_messages_no_matching_content_type(self):
        """Test getting original messages with no matching content type"""
        email_message = Mock(spec=EmailMessage)
        
        part = Mock(spec=MIMEPart)
        part.get_content_type.return_value = "application/pdf"
        part.is_multipart.return_value = False
        
        email_message.iter_parts.return_value = [part]
        
        result = _get_original_messages(email_message)
        
        assert len(result) == 0


class TestCheckMultipartForNestedMessage:
    """Tests for _check_multipart_for_nested_message function"""

    def test_check_multipart_with_message_id(self):
        """Test checking multipart with message-id header"""
        part = Mock(spec=MIMEPart)
        nested_messages = []
        
        payload = Mock()
        payload.get.return_value = "<test@example.com>"
        part.get_payload.return_value = [payload]
        
        _check_multipart_for_nested_message(part, "message-id", nested_messages)
        
        assert len(nested_messages) == 1
        assert nested_messages[0] == part

    def test_check_multipart_without_message_id(self):
        """Test checking multipart without message-id header"""
        part = Mock(spec=MIMEPart)
        nested_messages = []
        
        payload = Mock()
        payload.get.return_value = None
        part.get_payload.return_value = [payload]
        
        _check_multipart_for_nested_message(part, "message-id", nested_messages)
        
        assert len(nested_messages) == 0

    def test_check_multipart_multiple_payloads(self):
        """Test checking multipart with multiple payloads"""
        part = Mock(spec=MIMEPart)
        nested_messages = []
        
        payload1 = Mock()
        payload1.get.return_value = None
        
        payload2 = Mock()
        payload2.get.return_value = "<test@example.com>"
        
        part.get_payload.return_value = [payload1, payload2]
        
        _check_multipart_for_nested_message(part, "message-id", nested_messages)
        
        assert len(nested_messages) == 1


class TestCheckSimplePartForNestedMessage:
    """Tests for _check_simple_part_for_nested_message function"""

    def test_check_simple_part_with_message_id(self):
        """Test checking simple part with message-id header"""
        part = Mock(spec=MIMEPart)
        nested_messages = []
        part.get_payload.return_value = "Message-ID: <test@example.com>\nContent: Test"
        
        with patch('rococo.parsers.email.message_parser._get_header') as mock_get_header:
            mock_get_header.return_value = ["<test@example.com>"]
            
            _check_simple_part_for_nested_message(part, "message-id", nested_messages)
            
            assert len(nested_messages) == 1
            assert nested_messages[0] == part

    def test_check_simple_part_without_message_id(self):
        """Test checking simple part without message-id header"""
        part = Mock(spec=MIMEPart)
        nested_messages = []
        part.get_payload.return_value = "Content: Test"
        
        with patch('rococo.parsers.email.message_parser._get_header') as mock_get_header:
            mock_get_header.return_value = []
            
            _check_simple_part_for_nested_message(part, "message-id", nested_messages)
            
            assert len(nested_messages) == 0

    def test_check_simple_part_empty_header_list(self):
        """Test checking simple part with empty header list"""
        part = Mock(spec=MIMEPart)
        nested_messages = []
        part.get_payload.return_value = "Content: Test"
        
        with patch('rococo.parsers.email.message_parser._get_header') as mock_get_header:
            mock_get_header.return_value = []
            
            _check_simple_part_for_nested_message(part, "message-id", nested_messages)
            
            assert len(nested_messages) == 0


class TestGetMessageDate:
    """Tests for _get_message_date function"""

    def test_get_message_date_from_date_header(self):
        """Test getting date from Date header"""
        email_message = Mock(spec=EmailMessage)
        
        mock_date = Mock()
        mock_date.datetime = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        email_message.get_all.return_value = [mock_date]
        
        result = _get_message_date(email_message)
        
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        email_message.get_all.assert_called_once_with('date', [])

    def test_get_message_date_from_received_header(self):
        """Test getting date from Received header"""
        email_message = Mock(spec=EmailMessage)
        
        email_message.get_all.side_effect = [
            [],  # No date header
            ["by server.example.com (Postfix) with ESMTP id ABC123\n    for <recipient@example.com>; Sat, 5 Jul 2020 18:13:51 +0000"]  # Received header
        ]
        
        with patch('rococo.parsers.email.message_parser.DATE_TIME_RE') as mock_re:
            mock_re.findall.return_value = ["Sat, 5 Jul 2020 18:13:51 +0000"]
            
            result = _get_message_date(email_message)
            
            assert result.year == 2020
            assert result.month == 7
            assert result.day == 5

    def test_get_message_date_no_date_found(self):
        """Test getting date when no date is found"""
        email_message = Mock(spec=EmailMessage)
        
        email_message.get_all.side_effect = [
            [],  # No date header
            []   # No received header
        ]
        
        with patch('rococo.parsers.email.message_parser.DATE_TIME_RE') as mock_re:
            mock_re.findall.return_value = []
            
            with pytest.raises(DateNotFoundException):
                _get_message_date(email_message)

    def test_get_message_date_multiple_date_headers(self):
        """Test getting date when multiple Date headers exist"""
        email_message = Mock(spec=EmailMessage)
        
        mock_date1 = Mock()
        mock_date1.datetime = None
        
        mock_date2 = Mock()
        mock_date2.datetime = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        email_message.get_all.return_value = [mock_date1, mock_date2]
        
        result = _get_message_date(email_message)
        
        assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_get_message_date_received_header_no_match(self):
        """Test getting date when Received header exists but no date match"""
        email_message = Mock(spec=EmailMessage)
        
        email_message.get_all.side_effect = [
            [],  # No date header
            ["by server.example.com (Postfix)"]  # Received header without date
        ]
        
        with patch('rococo.parsers.email.message_parser.DATE_TIME_RE') as mock_re:
            mock_re.findall.return_value = []
            
            with pytest.raises(DateNotFoundException):
                _get_message_date(email_message)

