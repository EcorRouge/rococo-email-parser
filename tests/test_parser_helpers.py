import pytest
from unittest.mock import Mock, patch, MagicMock
from email.message import EmailMessage

from rococo.models import Email, ContentTypes, EmailAddress
from rococo.parsers.email.parser import _parse_journaled_email


class TestParseJournaledEmail:
    """Tests for _parse_journaled_email function"""

    def test_with_nested_messages_text_plain(self):
        """Test handling nested message with text/plain content type"""
        model = Email(
            message_id="test-id",
            bcc=[]
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        # Create mock nested message
        nested_message = Mock()
        nested_message.is_attachment.return_value = False
        nested_message.get_content_type.return_value = ContentTypes.text_plain
        
        # Mock BCC addresses
        mock_bcc = [
            EmailAddress(name="BCC User", address="bcc@example.com")
        ]
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._parse_bcc') as mock_parse_bcc:
            
            mock_get_original.return_value = [nested_message]
            mock_parse_bcc.return_value = mock_bcc
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Verify BCC was extended
            assert len(model.bcc) == 1
            assert model.bcc[0].address == "bcc@example.com"
            mock_parse_bcc.assert_called_once_with(nested_message)

    def test_with_nested_messages_forwarding_content_type(self):
        """Test handling nested message with message/rfc822 content type"""
        model = Email(
            message_id="test-id",
            subject="Original Subject"
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        # Create mock nested message
        nested_message = Mock()
        nested_message.is_attachment.return_value = False
        nested_message.get_content_type.return_value = ContentTypes.forwarding_content_type
        
        # Mock the nested email content
        nested_email_content = Mock(spec=EmailMessage)
        nested_message.get_content.return_value = nested_email_content
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            mock_get_original.return_value = [nested_message]
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Verify _populate_model was called with nested content
            mock_populate.assert_called_once_with(
                model=model,
                email_message=nested_email_content,
                raw_message=email_str
            )
            nested_message.get_content.assert_called_once()

    def test_with_multiple_nested_messages(self):
        """Test handling multiple nested messages with different content types"""
        model = Email(
            message_id="test-id",
            bcc=[]
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        # Create multiple mock nested messages
        text_plain_message = Mock()
        text_plain_message.is_attachment.return_value = False
        text_plain_message.get_content_type.return_value = ContentTypes.text_plain
        
        forwarding_message = Mock()
        forwarding_message.is_attachment.return_value = False
        forwarding_message.get_content_type.return_value = ContentTypes.forwarding_content_type
        forwarding_message.get_content.return_value = Mock(spec=EmailMessage)
        
        mock_bcc = [EmailAddress(name="BCC", address="bcc@example.com")]
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._parse_bcc') as mock_parse_bcc, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            mock_get_original.return_value = [text_plain_message, forwarding_message]
            mock_parse_bcc.return_value = mock_bcc
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Verify both were processed
            mock_parse_bcc.assert_called_once_with(text_plain_message)
            mock_populate.assert_called_once()

    def test_skips_attachment_parts(self):
        """Test that attachment parts are skipped"""
        model = Email(
            message_id="test-id",
            bcc=[]
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        # Create mock attachment
        attachment_message = Mock()
        attachment_message.is_attachment.return_value = True
        
        # Create mock regular message
        regular_message = Mock()
        regular_message.is_attachment.return_value = False
        regular_message.get_content_type.return_value = ContentTypes.text_plain
        
        mock_bcc = [EmailAddress(name="BCC", address="bcc@example.com")]
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._parse_bcc') as mock_parse_bcc:
            
            mock_get_original.return_value = [attachment_message, regular_message]
            mock_parse_bcc.return_value = mock_bcc
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Verify only regular message was processed (attachment skipped)
            mock_parse_bcc.assert_called_once_with(regular_message)
            # Attachment's get_content_type should not be called
            attachment_message.get_content_type.assert_not_called()

    def test_fallback_on_exception(self):
        """Test fallback when _get_original_messages raises exception"""
        model = Email(
            message_id="test-id",
            subject="Original Subject"
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            # Make _get_original_messages raise an exception
            mock_get_original.side_effect = Exception("Error getting nested messages")
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Verify fallback to _populate_model was called
            mock_populate.assert_called_once_with(
                model=model,
                email_message=email_message,
                raw_message=email_str
            )

    def test_fallback_on_value_error(self):
        """Test fallback when _get_original_messages raises ValueError"""
        model = Email(message_id="test-id")
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            mock_get_original.side_effect = ValueError("Invalid message format")
            
            _parse_journaled_email(model, email_message, email_str)
            
            mock_populate.assert_called_once_with(
                model=model,
                email_message=email_message,
                raw_message=email_str
            )

    def test_empty_nested_messages_list(self):
        """Test handling when no nested messages are found"""
        model = Email(
            message_id="test-id",
            bcc=[]
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._parse_bcc') as mock_parse_bcc, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            mock_get_original.return_value = []
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Verify nothing was called
            mock_parse_bcc.assert_not_called()
            mock_populate.assert_not_called()
            # Model should remain unchanged
            assert len(model.bcc) == 0

    def test_both_text_plain_and_forwarding(self):
        """Test message with both text/plain and forwarding content types"""
        model = Email(
            message_id="test-id",
            bcc=[]
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        # Create message with text/plain
        text_message = Mock()
        text_message.is_attachment.return_value = False
        text_message.get_content_type.return_value = ContentTypes.text_plain
        
        # Create message with forwarding content type
        forwarding_message = Mock()
        forwarding_message.is_attachment.return_value = False
        forwarding_message.get_content_type.return_value = ContentTypes.forwarding_content_type
        forwarding_message.get_content.return_value = Mock(spec=EmailMessage)
        
        mock_bcc = [EmailAddress(name="BCC", address="bcc@example.com")]
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._parse_bcc') as mock_parse_bcc, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            mock_get_original.return_value = [text_message, forwarding_message]
            mock_parse_bcc.return_value = mock_bcc
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Both should be processed
            assert len(model.bcc) == 1
            mock_parse_bcc.assert_called_once()
            mock_populate.assert_called_once()

    def test_unknown_content_type_skipped(self):
        """Test that messages with unknown content types are skipped"""
        model = Email(
            message_id="test-id",
            bcc=[]
        )
        email_message = Mock(spec=EmailMessage)
        email_str = "raw email string"
        
        # Create message with unknown content type
        unknown_message = Mock()
        unknown_message.is_attachment.return_value = False
        unknown_message.get_content_type.return_value = "application/unknown"
        
        with patch('rococo.parsers.email.parser._get_original_messages') as mock_get_original, \
             patch('rococo.parsers.email.parser._parse_bcc') as mock_parse_bcc, \
             patch('rococo.parsers.email.parser._populate_model') as mock_populate:
            
            mock_get_original.return_value = [unknown_message]
            
            _parse_journaled_email(model, email_message, email_str)
            
            # Nothing should be called for unknown content type
            mock_parse_bcc.assert_not_called()
            mock_populate.assert_not_called()
            assert len(model.bcc) == 0

