import pytest
from unittest.mock import Mock, MagicMock, patch
from email.message import EmailMessage
from email.policy import EmailPolicy

from rococo.parsers.email.attachment_parser import (
    _parse_attachments,
    _parse_multipart_attachment,
    _parse_simple_attachment,
)


class TestParseAttachments:
    """Tests for _parse_attachments function"""

    def test_parse_attachments_with_simple_attachment(self):
        """Test parsing simple attachments"""
        message_id = "test-message-id"
        email_message = Mock(spec=EmailMessage)
        
        # Create a mock simple attachment
        attachment = Mock(spec=EmailMessage)
        attachment.is_multipart.return_value = False
        attachment.get_filename.return_value = "test.txt"
        attachment.get_payload.return_value = "test content"
        attachment.get.return_value = "base64"
        attachment.get_content_type.return_value = "text/plain"
        
        email_message.iter_attachments.return_value = [attachment]
        
        with patch('rococo.parsers.email.attachment_parser._parse_simple_attachment') as mock_parse:
            mock_parse.return_value = Mock(
                name="test.txt",
                hash="abc123",
                content_transfer_encoding="base64",
                content_type="text/plain",
                payload="test content"
            )
            
            result = _parse_attachments(message_id, email_message)
            
            assert len(result) == 1
            mock_parse.assert_called_once_with(attachment)

    def test_parse_attachments_with_multipart_attachment(self):
        """Test parsing multipart attachments"""
        message_id = "test-message-id"
        email_message = Mock(spec=EmailMessage)
        
        # Create a mock multipart attachment
        attachment = Mock(spec=EmailMessage)
        attachment.is_multipart.return_value = True
        attachment.get_filename.return_value = "nested.eml"
        
        email_message.iter_attachments.return_value = [attachment]
        
        with patch('rococo.parsers.email.attachment_parser._parse_multipart_attachment') as mock_parse:
            mock_parse.return_value = Mock(
                name="nested.eml",
                hash="def456",
                content_transfer_encoding="7bit",
                content_type="message/rfc822",
                payload="nested content"
            )
            
            result = _parse_attachments(message_id, email_message)
            
            assert len(result) == 1
            mock_parse.assert_called_once_with(attachment, message_id)

    def test_parse_attachments_with_multiple_attachments(self):
        """Test parsing multiple attachments"""
        message_id = "test-message-id"
        email_message = Mock(spec=EmailMessage)
        
        attachment1 = Mock(spec=EmailMessage)
        attachment1.is_multipart.return_value = False
        attachment1.get_filename.return_value = "file1.txt"
        
        attachment2 = Mock(spec=EmailMessage)
        attachment2.is_multipart.return_value = True
        attachment2.get_filename.return_value = "file2.eml"
        
        email_message.iter_attachments.return_value = [attachment1, attachment2]
        
        with patch('rococo.parsers.email.attachment_parser._parse_simple_attachment') as mock_simple, \
             patch('rococo.parsers.email.attachment_parser._parse_multipart_attachment') as mock_multipart:
            
            mock_simple.return_value = Mock(name="file1.txt")
            mock_multipart.return_value = Mock(name="file2.eml")
            
            result = _parse_attachments(message_id, email_message)
            
            assert len(result) == 2
            mock_simple.assert_called_once_with(attachment1)
            mock_multipart.assert_called_once_with(attachment2, message_id)

    def test_parse_attachments_handles_exceptions(self):
        """Test that exceptions during parsing are logged and skipped"""
        message_id = "test-message-id"
        email_message = Mock(spec=EmailMessage)
        
        attachment = Mock(spec=EmailMessage)
        attachment.is_multipart.side_effect = Exception("Parse error")
        
        email_message.iter_attachments.return_value = [attachment]
        
        with patch('rococo.parsers.email.attachment_parser.logger') as mock_logger:
            result = _parse_attachments(message_id, email_message)
            
            assert len(result) == 0
            mock_logger.error.assert_called_once()

    def test_parse_attachments_skips_none_attachments(self):
        """Test that None attachments are skipped"""
        message_id = "test-message-id"
        email_message = Mock(spec=EmailMessage)
        
        attachment = Mock(spec=EmailMessage)
        attachment.is_multipart.return_value = False
        
        email_message.iter_attachments.return_value = [attachment]
        
        with patch('rococo.parsers.email.attachment_parser._parse_simple_attachment') as mock_parse:
            mock_parse.return_value = None
            
            result = _parse_attachments(message_id, email_message)
            
            assert len(result) == 0


class TestParseMultipartAttachment:
    """Tests for _parse_multipart_attachment function"""

    def test_parse_multipart_with_filename(self):
        """Test parsing multipart attachment with filename"""
        message_id = "test-message-id"
        part = Mock(spec=EmailMessage)
        part.get_payload.return_value = [Mock(spec=EmailMessage)]
        part.get_filename.return_value = "test.eml"
        part.get.return_value = "base64"
        part.get_content_type.return_value = "message/rfc822"
        part.get_content_maintype.return_value = "message"
        part.get_content_subtype.return_value = "rfc822"
        part.as_string.return_value = "email content"
        
        with patch('rococo.parsers.email.attachment_parser.hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "abc123"
            mock_hash.return_value.update = Mock()
            
            result = _parse_multipart_attachment(part, message_id)
            
            assert result is not None
            assert result.name == "test.eml"
            assert result.hash == "abc123"
            # Check that as_string was called (don't check exact policy object)
            part.as_string.assert_called_once()
            call_args = part.as_string.call_args
            assert 'policy' in call_args.kwargs

    def test_parse_multipart_without_filename_uses_subject(self):
        """Test parsing multipart attachment without filename, using subject"""
        message_id = "test-message-id"
        part = Mock(spec=EmailMessage)
        
        attachment_part = Mock(spec=EmailMessage)
        attachment_part.get.return_value = "Test Subject"
        
        part.get_payload.return_value = [attachment_part]
        part.get_filename.return_value = None
        part.get.return_value = "base64"
        part.get_content_type.return_value = "message/rfc822"
        part.get_content_maintype.return_value = "message"
        part.get_content_subtype.return_value = "rfc822"
        part.as_string.return_value = "email content"
        
        with patch('rococo.parsers.email.attachment_parser.hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "def456"
            mock_hash.return_value.update = Mock()
            
            result = _parse_multipart_attachment(part, message_id)
            
            assert result is not None
            assert result.name == "Test Subject.eml"

    def test_parse_multipart_without_filename_uses_message_id(self):
        """Test parsing multipart attachment without filename, using message-id"""
        message_id = "test-message-id"
        part = Mock(spec=EmailMessage)
        
        attachment_part = Mock(spec=EmailMessage)
        attachment_part.get.side_effect = lambda key: None if key == 'subject' else "<msg-id@example.com>"
        
        part.get_payload.return_value = [attachment_part]
        part.get_filename.return_value = None
        part.get.return_value = "base64"
        part.get_content_type.return_value = "message/rfc822"
        part.get_content_maintype.return_value = "message"
        part.get_content_subtype.return_value = "rfc822"
        part.as_string.return_value = "email content"
        
        with patch('rococo.parsers.email.attachment_parser.hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "ghi789"
            mock_hash.return_value.update = Mock()
            
            result = _parse_multipart_attachment(part, message_id)
            
            assert result is not None
            assert "msg-id@example.com" in result.name or "message-rfc822.eml" in result.name

    def test_parse_multipart_handles_exception(self):
        """Test that exceptions during multipart parsing are handled"""
        message_id = "test-message-id"
        part = Mock(spec=EmailMessage)
        part.get_payload.return_value = [Mock(spec=EmailMessage)]
        part.get_filename.return_value = "test.eml"
        part.as_string.side_effect = Exception("Parse error")
        
        with patch('rococo.parsers.email.attachment_parser.logger') as mock_logger:
            result = _parse_multipart_attachment(part, message_id)
            
            assert result is None
            mock_logger.error.assert_called_once()

    def test_parse_multipart_empty_payload(self):
        """Test parsing multipart attachment with empty payload"""
        message_id = "test-message-id"
        part = Mock(spec=EmailMessage)
        part.get_payload.return_value = []
        part.get_filename.return_value = "test.eml"
        part.get.return_value = "base64"  # Need to mock get() for content_transfer_encoding
        part.get_content_type.return_value = "message/rfc822"  # Need to mock get_content_type
        part.get_content_maintype.return_value = "message"
        part.get_content_subtype.return_value = "rfc822"
        part.as_string.return_value = "email content"
        
        with patch('rococo.parsers.email.attachment_parser.hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "jkl012"
            mock_hash.return_value.update = Mock()
            
            result = _parse_multipart_attachment(part, message_id)
            
            # Should still work with empty payload list
            assert result is not None
            assert result.name == "test.eml"


class TestParseSimpleAttachment:
    """Tests for _parse_simple_attachment function"""

    def test_parse_simple_attachment_with_filename(self):
        """Test parsing simple attachment with filename"""
        part = Mock(spec=EmailMessage)
        part.get_filename.return_value = "document.pdf"
        part.get_payload.return_value = "PDF content"
        part.get.return_value = "base64"
        part.get_content_type.return_value = "application/pdf"
        
        with patch('rococo.parsers.email.attachment_parser.hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "sha256hash"
            mock_hash.return_value.update = Mock()
            
            result = _parse_simple_attachment(part)
            
            assert result is not None
            assert result.name == "document.pdf"
            assert result.hash == "sha256hash"
            assert result.content_transfer_encoding == "base64"
            assert result.content_type == "application/pdf"
            assert result.payload == "PDF content"

    def test_parse_simple_attachment_without_filename(self):
        """Test parsing simple attachment without filename returns None"""
        part = Mock(spec=EmailMessage)
        part.get_filename.return_value = None
        
        result = _parse_simple_attachment(part)
        
        assert result is None

    def test_parse_simple_attachment_empty_filename(self):
        """Test parsing simple attachment with empty filename returns None"""
        part = Mock(spec=EmailMessage)
        part.get_filename.return_value = ""
        
        result = _parse_simple_attachment(part)
        
        assert result is None

