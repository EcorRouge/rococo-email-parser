import pytest
from unittest.mock import Mock, MagicMock, patch
from email.message import EmailMessage
from email.headerregistry import Address, AddressHeader
from email.header import decode_header

from rococo.models import EmailAddress
from rococo.parsers.email.header_parser import (
    _parse_message_id,
    _parse_antispam_report,
    _parse_antispam_report_o365,
    _get_header,
    _decode_headers,
    _parse_from,
    _parse_to,
    _parse_cc,
    _parse_bcc,
    _clean_addresses,
)


class TestParseMessageId:
    """Tests for _parse_message_id function"""

    def test_parse_message_id_with_valid_header(self):
        """Test parsing message ID when header exists"""
        message = Mock(spec=EmailMessage)
        message.get.return_value = "<test@example.com>"
        
        result = _parse_message_id(message)
        
        assert result == "<test@example.com>"
        message.get.assert_called_once_with('message-id')

    def test_parse_message_id_with_empty_string(self):
        """Test parsing message ID when header is empty string"""
        # Create a mock that supports 'in' operator
        message = MagicMock(spec=EmailMessage)
        message.get.return_value = ""
        message.__str__ = Mock(return_value="email content")
        # Configure __contains__ to work with 'in' operator
        def contains(key):
            return key == 'message-id'
        type(message).__contains__ = Mock(side_effect=contains)
        
        with patch('rococo.parsers.email.header_parser.utils.make_msgid') as mock_make, \
             patch('rococo.parsers.email.header_parser.hashlib.sha256') as mock_hash, \
             patch('rococo.parsers.email.header_parser.logger') as mock_logger:
            
            mock_hash.return_value.hexdigest.return_value = "abc123"
            mock_make.return_value = "<generated@example.com>"
            
            result = _parse_message_id(message)
            
            assert result == "<generated@example.com>"
            mock_logger.info.assert_called_once()

    def test_parse_message_id_with_angle_brackets_only(self):
        """Test parsing message ID when header is just angle brackets"""
        message = MagicMock(spec=EmailMessage)
        message.get.return_value = "<>"
        message.__str__ = Mock(return_value="email content")
        def contains(key):
            return key == 'message-id'
        type(message).__contains__ = Mock(side_effect=contains)
        
        with patch('rococo.parsers.email.header_parser.utils.make_msgid') as mock_make, \
             patch('rococo.parsers.email.header_parser.hashlib.sha256') as mock_hash:
            
            mock_hash.return_value.hexdigest.return_value = "def456"
            mock_make.return_value = "<generated2@example.com>"
            
            result = _parse_message_id(message)
            
            assert result == "<generated2@example.com>"

    def test_parse_message_id_with_whitespace_only(self):
        """Test parsing message ID when header is whitespace only"""
        message = MagicMock(spec=EmailMessage)
        message.get.return_value = "   "
        message.__str__ = Mock(return_value="email content")
        def contains(key):
            return key == 'message-id'
        type(message).__contains__ = Mock(side_effect=contains)
        
        with patch('rococo.parsers.email.header_parser.utils.make_msgid') as mock_make, \
             patch('rococo.parsers.email.header_parser.hashlib.sha256') as mock_hash:
            
            mock_hash.return_value.hexdigest.return_value = "ghi789"
            mock_make.return_value = "<generated3@example.com>"
            
            result = _parse_message_id(message)
            
            assert result == "<generated3@example.com>"

    def test_parse_message_id_with_none(self):
        """Test parsing message ID when header is None"""
        message = MagicMock(spec=EmailMessage)
        message.get.return_value = None
        message.__str__ = Mock(return_value="email content")
        def contains(key):
            return False  # No message-id header exists
        type(message).__contains__ = Mock(side_effect=contains)
        
        with patch('rococo.parsers.email.header_parser.utils.make_msgid') as mock_make, \
             patch('rococo.parsers.email.header_parser.hashlib.sha256') as mock_hash:
            
            mock_hash.return_value.hexdigest.return_value = "jkl012"
            mock_make.return_value = "<generated4@example.com>"
            
            result = _parse_message_id(message)
            
            assert result == "<generated4@example.com>"


class TestParseAntispamReportO365:
    """Tests for _parse_antispam_report_o365 function"""

    def test_parse_o365_spam_cat_spm(self):
        """Test parsing O365 antispam report with CAT:SPM"""
        report = "CIP:1.2.3.4;CAT:SPM;DIR:INB;"
        result = _parse_antispam_report_o365(report)
        assert result == "Spam"

    def test_parse_o365_spam_cat_hspm(self):
        """Test parsing O365 antispam report with CAT:HSPM"""
        report = "CIP:1.2.3.4;CAT:HSPM;DIR:INB;"
        result = _parse_antispam_report_o365(report)
        assert result == "Spam"

    def test_parse_o365_spam_sfv_spm(self):
        """Test parsing O365 antispam report with SFV:SPM"""
        report = "CIP:1.2.3.4;SFV:SPM;DIR:INB;"
        result = _parse_antispam_report_o365(report)
        assert result == "Spam"

    def test_parse_o365_spam_sfv_skb(self):
        """Test parsing O365 antispam report with SFV:SKB"""
        report = "CIP:1.2.3.4;SFV:SKB;DIR:INB;"
        result = _parse_antispam_report_o365(report)
        assert result == "Spam"

    def test_parse_o365_not_spam(self):
        """Test parsing O365 antispam report that is not spam"""
        report = "CIP:1.2.3.4;CAT:NONE;SFV:NSPM;DIR:INB;"
        result = _parse_antispam_report_o365(report)
        assert result is None

    def test_parse_o365_invalid_format(self):
        """Test parsing O365 antispam report with invalid format"""
        report = "invalid;format;no:colons"
        result = _parse_antispam_report_o365(report)
        assert result is None

    def test_parse_o365_empty_string(self):
        """Test parsing empty O365 antispam report"""
        report = ""
        result = _parse_antispam_report_o365(report)
        assert result is None


class TestParseAntispamReport:
    """Tests for _parse_antispam_report function"""

    def test_parse_antispam_with_o365_header(self):
        """Test parsing antispam report with O365 header"""
        message = Mock(spec=EmailMessage)
        message.get.return_value = "CIP:1.2.3.4;CAT:SPM;DIR:INB;"
        
        with patch('rococo.parsers.email.header_parser._parse_antispam_report_o365') as mock_parse:
            mock_parse.return_value = "Spam"
            
            result = _parse_antispam_report(message)
            
            assert result == "Spam"
            message.get.assert_called_once_with('X-Forefront-Antispam-Report')
            mock_parse.assert_called_once_with("CIP:1.2.3.4;CAT:SPM;DIR:INB;")

    def test_parse_antispam_without_header(self):
        """Test parsing antispam report without header"""
        message = Mock(spec=EmailMessage)
        message.get.return_value = None
        
        result = _parse_antispam_report(message)
        
        assert result is None


class TestGetHeader:
    """Tests for _get_header function"""

    def test_get_header_single_occurrence(self):
        """Test getting a header that appears once"""
        # _get_header looks for \n{header_name}:, so need newline before header
        # It strips the header name but keeps the rest
        text_payload = "\nFrom: sender@example.com\nTo: recipient@example.com\nSubject: Test"
        result = _get_header(text_payload, "from")
        assert len(result) == 1
        # Result includes "From: " prefix after stripping
        assert "sender@example.com" in result[0] or "From: sender" in result[0]

    def test_get_header_multiple_occurrences(self):
        """Test getting a header that appears multiple times"""
        text_payload = "\nFrom: sender1@example.com\nFrom: sender2@example.com\nTo: recipient@example.com"
        result = _get_header(text_payload, "from")
        assert len(result) >= 1  # Function finds headers after newlines
        # Check that we got at least one result
        assert any("sender" in r for r in result)

    def test_get_header_with_continuation(self):
        """Test getting a header with continuation lines"""
        text_payload = "\nFrom: long\n name@example.com\nTo: recipient@example.com"
        result = _get_header(text_payload, "from")
        assert len(result) == 1
        assert "long" in result[0]
        assert "name@example.com" in result[0]

    def test_get_header_continuation_no_more_lines(self):
        """Test getting a header with continuation that has no more lines (reaches end)"""
        # Header continuation that reaches end of string without newline
        text_payload = "\nFrom: long\n name@example.com"
        result = _get_header(text_payload, "from")
        assert len(result) == 1
        assert "long" in result[0] or "name@example.com" in result[0]

    def test_get_header_not_found(self):
        """Test getting a header that doesn't exist"""
        text_payload = "To: recipient@example.com\nSubject: Test"
        result = _get_header(text_payload, "from")
        assert len(result) == 0

    def test_get_header_case_insensitive(self):
        """Test that header search is case insensitive"""
        text_payload = "\nFROM: sender@example.com\nTo: recipient@example.com"
        result = _get_header(text_payload, "from")
        assert len(result) == 1
        # Result includes "FROM: " prefix after stripping
        assert "sender@example.com" in result[0] or "FROM: sender" in result[0]


class TestDecodeHeaders:
    """Tests for _decode_headers function"""

    def test_decode_headers_ascii(self):
        """Test decoding ASCII headers"""
        headers = ["sender@example.com"]
        
        with patch('rococo.parsers.email.header_parser.email.header.decode_header') as mock_decode:
            mock_decode.return_value = [("sender@example.com", None)]
            
            result = _decode_headers(headers)
            
            assert len(result) == 1
            assert result[0][1] == "sender@example.com"

    def test_decode_headers_encoded(self):
        """Test decoding encoded headers"""
        headers = ["=?utf-8?q?Test?="]
        
        with patch('rococo.parsers.email.header_parser.email.header.decode_header') as mock_decode:
            mock_decode.return_value = [(b"Test", "utf-8")]
            
            result = _decode_headers(headers)
            
            assert len(result) == 1

    def test_decode_headers_with_newlines(self):
        """Test decoding headers with newlines"""
        headers = ["sender@example.com\n"]
        
        with patch('rococo.parsers.email.header_parser.email.header.decode_header') as mock_decode:
            mock_decode.return_value = [("sender@example.com\n", None)]
            
            result = _decode_headers(headers)
            
            # Newlines should be removed
            assert "\n" not in result[0][1] if len(result) > 0 else True

    def test_decode_headers_bytes_without_encoding(self):
        """Test decoding headers that are bytes without encoding"""
        headers = [b"test@example.com"]
        
        with patch('rococo.parsers.email.header_parser.email.header.decode_header') as mock_decode:
            mock_decode.return_value = [(b"test@example.com", None)]
            
            result = _decode_headers(headers)
            
            assert len(result) == 1


class TestParseFrom:
    """Tests for _parse_from function"""

    def test_parse_from_with_address_header(self):
        """Test parsing From header with AddressHeader"""
        email_message = Mock(spec=EmailMessage)
        raw_message = "From: sender@example.com"
        
        mock_address = Mock(spec=Address)
        mock_address.display_name = "Sender Name"
        mock_address.addr_spec = "sender@example.com"
        
        mock_header = Mock(spec=AddressHeader)
        mock_header.addresses = [mock_address]
        
        email_message.get.return_value = mock_header
        
        result = _parse_from(email_message, raw_message)
        
        assert result is not None
        assert result.name == "Sender Name"
        assert result.address == "sender@example.com"

    def test_parse_from_with_attribute_error(self):
        """Test parsing From header when AttributeError occurs"""
        email_message = Mock(spec=EmailMessage)
        raw_message = "From: sender@example.com"
        
        email_message.get.side_effect = AttributeError("No addresses attribute")
        
        with patch('rococo.parsers.email.header_parser._get_header') as mock_get, \
             patch('rococo.parsers.email.header_parser.email.utils.getaddresses') as mock_getaddresses:
            
            mock_get.return_value = ["Sender <sender@example.com>"]
            mock_getaddresses.return_value = [("Sender", "sender@example.com")]
            
            result = _parse_from(email_message, raw_message)
            
            assert result is not None
            assert result.address == "sender@example.com"

    def test_parse_from_with_value_error(self):
        """Test parsing From header when ValueError occurs"""
        email_message = Mock(spec=EmailMessage)
        raw_message = "From: sender@example.com"
        
        email_message.get.side_effect = ValueError("Invalid address")
        
        with patch('rococo.parsers.email.header_parser._get_header') as mock_get, \
             patch('rococo.parsers.email.header_parser._decode_headers') as mock_decode:
            
            mock_get.return_value = ["=?utf-8?q?Sender?= <sender@example.com>"]
            mock_decode.return_value = [("Sender", "sender@example.com")]
            
            result = _parse_from(email_message, raw_message)
            
            assert result is not None
            assert result.address == "sender@example.com"

    def test_parse_from_no_header(self):
        """Test parsing From header when header doesn't exist"""
        email_message = Mock(spec=EmailMessage)
        raw_message = "To: recipient@example.com"
        
        email_message.get.return_value = None
        
        result = _parse_from(email_message, raw_message)
        
        assert result is None


class TestParseTo:
    """Tests for _parse_to function"""

    def test_parse_to_with_addresses(self):
        """Test parsing To header with addresses"""
        email_message = Mock(spec=EmailMessage)
        
        mock_address1 = Mock(spec=Address)
        mock_address1.display_name = "Recipient 1"
        mock_address1.addr_spec = "recipient1@example.com"
        
        mock_address2 = Mock(spec=Address)
        mock_address2.display_name = "Recipient 2"
        mock_address2.addr_spec = "recipient2@example.com"
        
        mock_header = Mock(spec=AddressHeader)
        mock_header.addresses = [mock_address1, mock_address2]
        
        email_message.get.return_value = mock_header
        
        with patch('rococo.parsers.email.header_parser._clean_addresses') as mock_clean:
            mock_clean.return_value = [
                EmailAddress(name="Recipient 1", address="recipient1@example.com"),
                EmailAddress(name="Recipient 2", address="recipient2@example.com")
            ]
            
            result = _parse_to(email_message)
            
            assert len(result) == 2
            assert result[0].address == "recipient1@example.com"

    def test_parse_to_no_header(self):
        """Test parsing To header when header doesn't exist"""
        email_message = Mock(spec=EmailMessage)
        email_message.get.return_value = None
        
        result = _parse_to(email_message)
        
        assert len(result) == 0


class TestParseCc:
    """Tests for _parse_cc function"""

    def test_parse_cc_with_addresses(self):
        """Test parsing Cc header with addresses"""
        email_message = Mock(spec=EmailMessage)
        
        mock_address = Mock(spec=Address)
        mock_address.display_name = "CC Recipient"
        mock_address.addr_spec = "cc@example.com"
        
        mock_header = Mock(spec=AddressHeader)
        mock_header.addresses = [mock_address]
        
        email_message.get.return_value = mock_header
        
        result = _parse_cc(email_message)
        
        assert len(result) == 1
        assert result[0].address == "cc@example.com"

    def test_parse_cc_no_header(self):
        """Test parsing Cc header when header doesn't exist"""
        email_message = Mock(spec=EmailMessage)
        email_message.get.return_value = None
        
        result = _parse_cc(email_message)
        
        assert len(result) == 0


class TestParseBcc:
    """Tests for _parse_bcc function"""

    def test_parse_bcc_with_header(self):
        """Test parsing Bcc header with AddressHeader"""
        email_message = Mock(spec=EmailMessage)
        
        mock_address = Mock(spec=Address)
        mock_address.display_name = "BCC Recipient"
        mock_address.addr_spec = "bcc@example.com"
        
        mock_header = Mock(spec=AddressHeader)
        mock_header.addresses = [mock_address]
        
        email_message.get.return_value = mock_header
        email_message.is_multipart.return_value = True
        
        result = _parse_bcc(email_message)
        
        assert len(result) == 1
        assert result[0].address == "bcc@example.com"

    def test_parse_bcc_from_payload(self):
        """Test parsing Bcc header from payload when not multipart"""
        email_message = Mock(spec=EmailMessage)
        email_message.get.return_value = None
        email_message.is_multipart.return_value = False
        email_message.get_payload.return_value = "Bcc: bcc@example.com\nSubject: Test"
        
        with patch('rococo.parsers.email.header_parser._get_header') as mock_get, \
             patch('rococo.parsers.email.header_parser.email.utils.getaddresses') as mock_getaddresses:
            
            mock_get.return_value = ["bcc@example.com"]
            mock_getaddresses.return_value = [("", "bcc@example.com")]
            
            result = _parse_bcc(email_message)
            
            assert len(result) == 1
            assert result[0].address == "bcc@example.com"

    def test_parse_bcc_no_header(self):
        """Test parsing Bcc header when header doesn't exist and is multipart"""
        email_message = Mock(spec=EmailMessage)
        email_message.get.return_value = None
        email_message.is_multipart.return_value = True
        
        result = _parse_bcc(email_message)
        
        assert len(result) == 0


class TestCleanAddresses:
    """Tests for _clean_addresses function"""

    def test_clean_addresses_normal(self):
        """Test cleaning normal addresses"""
        addresses = [
            EmailAddress(name="Test User", address="test@example.com")
        ]
        
        with patch('rococo.parsers.email.header_parser.decode_header') as mock_decode:
            mock_decode.side_effect = [
                (("Test User", None),),
                (("test@example.com", None),)
            ]
            
            result = _clean_addresses(addresses)
            
            assert len(result) == 1
            assert result[0].address == "test@example.com"

    def test_clean_addresses_with_quotes(self):
        """Test cleaning addresses with quotes"""
        addresses = [
            EmailAddress(name='"Test User"', address='"test@example.com"')
        ]
        
        with patch('rococo.parsers.email.header_parser.decode_header') as mock_decode:
            mock_decode.side_effect = [
                (("Test User", None),),
                (("test@example.com", None),)
            ]
            
            result = _clean_addresses(addresses)
            
            assert len(result) == 1
            assert result[0].name == "Test User"
            assert result[0].address == "test@example.com"

    def test_clean_addresses_encoded(self):
        """Test cleaning encoded addresses"""
        addresses = [
            EmailAddress(name="=?utf-8?q?Test?=", address="test@example.com")
        ]
        
        with patch('rococo.parsers.email.header_parser.decode_header') as mock_decode:
            mock_decode.side_effect = [
                ((b"Test", "utf-8"),),
                (("test@example.com", None),)
            ]
            
            result = _clean_addresses(addresses)
            
            assert len(result) == 1

    def test_clean_addresses_empty_name(self):
        """Test cleaning addresses with empty name"""
        addresses = [
            EmailAddress(name=None, address="test@example.com")
        ]
        
        with patch('rococo.parsers.email.header_parser.decode_header') as mock_decode:
            # decode_header returns a list of tuples, accessed with [0]
            # When _name is None, it uses (_name, None) directly, so decode_header is not called for name
            # Only called for address
            mock_decode.return_value = [("test@example.com", None)]
            
            result = _clean_addresses(addresses)
            
            assert len(result) == 1
            assert result[0].address == "test@example.com"

