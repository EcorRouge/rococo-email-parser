import pytest
from unittest.mock import Mock, MagicMock
from bs4 import BeautifulSoup
from email.message import EmailMessage

from rococo.parsers.email.body_parser import (
    _is_reply_separator,
    _append_to_body,
    _extract_gmail_quote,
    _extract_o365_quote,
    _extract_outlook_quote,
    _replace_cid_images,
)


class TestIsReplySeparator:
    """Tests for _is_reply_separator function"""

    def test_forwarded_message_pattern(self):
        """Test detection of forwarded message pattern"""
        line = "---------- Forwarded message ----------"
        assert _is_reply_separator(line) is True

    def test_forwarded_message_with_dashes(self):
        """Test forwarded message with different dash count"""
        line = "--- Forwarded message"
        assert _is_reply_separator(line) is True

    def test_reply_header_pattern(self):
        """Test detection of reply header pattern"""
        line = "On Jan 14, 2024 at 3:05 PM -0800, Test User <test@example.com>, wrote:"
        assert _is_reply_separator(line) is True

    def test_reply_header_variation(self):
        """Test reply header with different format"""
        line = "On 2024-01-14 at 10:30 AM, John Doe, wrote:"
        assert _is_reply_separator(line) is True

    def test_quote_pattern_single(self):
        """Test detection of single quote pattern"""
        line = "> This is quoted text"
        assert _is_reply_separator(line) is True

    def test_quote_pattern_nested(self):
        """Test detection of nested quote pattern"""
        line = "> > Nested quote"
        assert _is_reply_separator(line) is True

    def test_quote_pattern_with_spaces(self):
        """Test quote pattern with spaces"""
        line = ">  >  > Triple nested with spaces"
        assert _is_reply_separator(line) is True

    def test_non_separator_line(self):
        """Test that regular text line is not detected as separator"""
        line = "This is just a regular line of text"
        assert _is_reply_separator(line) is False

    def test_empty_line(self):
        """Test that empty line is not detected as separator"""
        line = ""
        assert _is_reply_separator(line) is False

    def test_line_with_forwarded_but_not_at_start(self):
        """Test line containing 'Forwarded message' but not at start"""
        line = "This contains Forwarded message but not at start"
        assert _is_reply_separator(line) is False


class TestAppendToBody:
    """Tests for _append_to_body function"""

    def test_append_to_empty_body(self):
        """Test appending to empty body (no newline prefix)"""
        body = ""
        line = "First line"
        result = _append_to_body(body, line)
        assert result == "First line"
        assert "\n" not in result

    def test_append_to_non_empty_body(self):
        """Test appending to non-empty body (with newline prefix)"""
        body = "First line"
        line = "Second line"
        result = _append_to_body(body, line)
        assert result == "First line\nSecond line"
        assert "\n" in result

    def test_append_multiple_lines(self):
        """Test appending multiple lines"""
        body = "Line 1"
        line = "Line 2"
        result = _append_to_body(body, line)
        result = _append_to_body(result, "Line 3")
        assert result == "Line 1\nLine 2\nLine 3"

    def test_append_empty_line(self):
        """Test appending empty line"""
        body = "Existing content"
        line = ""
        result = _append_to_body(body, line)
        assert result == "Existing content\n"


class TestExtractGmailQuote:
    """Tests for _extract_gmail_quote function"""

    def test_extract_gmail_quote_present(self):
        """Test extraction when Gmail quote div is present"""
        html = """
        <div>Current message</div>
        <div class="gmail_quote">
            <div>Previous message content</div>
            <p>More previous content</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_gmail_quote(soup)
        
        assert result is not None
        assert "Previous message content" in result
        assert "More previous content" in result
        # Verify div is decomposed
        assert soup.find('div', {'class': 'gmail_quote'}) is None

    def test_extract_gmail_quote_not_present(self):
        """Test when Gmail quote div is not present"""
        html = """
        <div>Just regular content</div>
        <p>No gmail quote here</p>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_gmail_quote(soup)
        
        assert result is None

    def test_extract_gmail_quote_empty_soup(self):
        """Test with empty soup"""
        soup = BeautifulSoup("", "html.parser")
        result = _extract_gmail_quote(soup)
        assert result is None

    def test_extract_gmail_quote_removes_from_soup(self):
        """Test that extracted quote is removed from soup"""
        html = """
        <div>Current</div>
        <div class="gmail_quote">Previous</div>
        """
        soup = BeautifulSoup(html, "html.parser")
        _extract_gmail_quote(soup)
        
        # Verify it's gone
        assert soup.find('div', {'class': 'gmail_quote'}) is None
        # But current content remains
        assert soup.find('div', string='Current') is not None


class TestExtractO365Quote:
    """Tests for _extract_o365_quote function"""

    def test_extract_o365_quote_present(self):
        """Test extraction when O365 quote div is present"""
        html = """
        <div>Current message</div>
        <div name="messageReplySection">
            <div>O365 previous message</div>
            <span>Additional content</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_o365_quote(soup)
        
        assert result is not None
        assert "O365 previous message" in result
        assert "Additional content" in result
        # Verify div is decomposed
        assert soup.find('div', {'name': 'messageReplySection'}) is None

    def test_extract_o365_quote_not_present(self):
        """Test when O365 quote div is not present"""
        html = """
        <div>Regular content</div>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_o365_quote(soup)
        
        assert result is None

    def test_extract_o365_quote_empty_soup(self):
        """Test with empty soup"""
        soup = BeautifulSoup("", "html.parser")
        result = _extract_o365_quote(soup)
        assert result is None

    def test_extract_o365_quote_removes_from_soup(self):
        """Test that extracted quote is removed from soup"""
        html = """
        <div>Current</div>
        <div name="messageReplySection">Previous</div>
        """
        soup = BeautifulSoup(html, "html.parser")
        _extract_o365_quote(soup)
        
        assert soup.find('div', {'name': 'messageReplySection'}) is None
        assert soup.find('div', string='Current') is not None


class TestExtractOutlookQuote:
    """Tests for _extract_outlook_quote function"""

    def test_extract_outlook_quote_present(self):
        """Test extraction when Outlook marker div is present"""
        html = """
        <div>Current message</div>
        <div id="appendonsend">
            <p>Outlook previous message</p>
        </div>
        <div>Sibling 1</div>
        <span>Sibling 2</span>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_outlook_quote(soup)
        
        assert result is not None
        assert "Outlook previous message" in result
        assert "Sibling 1" in result
        assert "Sibling 2" in result
        # Verify marker div is decomposed
        assert soup.find('div', {'id': 'appendonsend'}) is None

    def test_extract_outlook_quote_not_present(self):
        """Test when Outlook marker div is not present"""
        html = """
        <div>Regular content</div>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_outlook_quote(soup)
        
        assert result is None

    def test_extract_outlook_quote_empty_soup(self):
        """Test with empty soup"""
        soup = BeautifulSoup("", "html.parser")
        result = _extract_outlook_quote(soup)
        assert result is None

    def test_extract_outlook_quote_with_siblings(self):
        """Test that siblings are included and decomposed"""
        html = """
        <div>Current</div>
        <div id="appendonsend">Marker</div>
        <p>Sibling paragraph</p>
        <span>Sibling span</span>
        """
        soup = BeautifulSoup(html, "html.parser")
        result = _extract_outlook_quote(soup)
        
        assert "Marker" in result
        assert "Sibling paragraph" in result
        assert "Sibling span" in result
        # Verify marker and siblings are decomposed
        assert soup.find('div', {'id': 'appendonsend'}) is None

    def test_extract_outlook_quote_sibling_decompose_exception(self):
        """Test that exceptions during sibling decomposition are handled"""
        html = """
        <div id="appendonsend">Marker</div>
        """
        soup = BeautifulSoup(html, "html.parser")
        marker_div = soup.find('div', {'id': 'appendonsend'})
        
        # Create a mock sibling that raises exception on decompose
        mock_sibling = Mock()
        mock_sibling.decompose = Mock(side_effect=Exception("Decompose failed"))
        marker_div.next_siblings = [mock_sibling]
        
        # Should not raise exception
        result = _extract_outlook_quote(soup)
        assert result is not None


class TestReplaceCidImages:
    """Tests for _replace_cid_images function"""

    def test_replace_cid_image_single(self):
        """Test replacing a single CID image"""
        html = '<img src="cid:image123">'
        soup = BeautifulSoup(html, "html.parser")
        
        # Create mock email message
        email_message = Mock()
        attachment = Mock()
        attachment.is_attachment.return_value = True
        attachment.get.return_value = "<image123>"
        attachment.get_filename.return_value = "image.png"
        attachment.get_content_subtype.return_value = "png"
        attachment.get_payload.return_value = "base64encodeddata"
        
        email_message.walk.return_value = [attachment]
        
        _replace_cid_images(soup, email_message)
        
        img_tag = soup.find("img")
        assert img_tag is not None
        assert img_tag["src"].startswith("data:image/png;base64,")
        assert "base64encodeddata" in img_tag["src"]

    def test_replace_cid_image_multiple(self):
        """Test replacing multiple CID images"""
        html = '''
        <img src="cid:image1">
        <img src="cid:image2">
        '''
        soup = BeautifulSoup(html, "html.parser")
        
        email_message = Mock()
        
        attachment1 = Mock()
        attachment1.is_attachment.return_value = True
        attachment1.get.return_value = "<image1>"
        attachment1.get_filename.return_value = "img1.jpg"
        attachment1.get_payload.return_value = "data1"
        
        attachment2 = Mock()
        attachment2.is_attachment.return_value = True
        attachment2.get.return_value = "<image2>"
        attachment2.get_filename.return_value = "img2.gif"
        attachment2.get_payload.return_value = "data2"
        
        email_message.walk.return_value = [attachment1, attachment2]
        
        _replace_cid_images(soup, email_message)
        
        img_tags = soup.find_all("img")
        assert len(img_tags) == 2
        assert img_tags[0]["src"].startswith("data:image/jpg;base64,")
        assert img_tags[1]["src"].startswith("data:image/gif;base64,")

    def test_replace_cid_image_no_cid_images(self):
        """Test when no CID images are present"""
        html = '<img src="https://example.com/image.png">'
        soup = BeautifulSoup(html, "html.parser")
        
        email_message = Mock()
        email_message.walk.return_value = []
        
        original_html = str(soup)
        _replace_cid_images(soup, email_message)
        
        # Should remain unchanged
        assert str(soup) == original_html

    def test_replace_cid_image_with_content_id_header(self):
        """Test CID replacement using Content-ID header"""
        html = '<img src="cid:myimage">'
        soup = BeautifulSoup(html, "html.parser")
        
        email_message = Mock()
        attachment = Mock()
        attachment.is_attachment.return_value = False
        attachment.get.return_value = "<myimage>"
        attachment.get_filename.return_value = None
        attachment.get_content_subtype.return_value = "jpeg"
        attachment.get_payload.return_value = "imagedata"
        
        email_message.walk.return_value = [attachment]
        
        _replace_cid_images(soup, email_message)
        
        img_tag = soup.find("img")
        assert img_tag["src"].startswith("data:image/jpeg;base64,")

    def test_replace_cid_image_no_filename_uses_subtype(self):
        """Test that content subtype is used when filename is missing"""
        html = '<img src="cid:image123">'
        soup = BeautifulSoup(html, "html.parser")
        
        email_message = Mock()
        attachment = Mock()
        attachment.is_attachment.return_value = True
        attachment.get.return_value = "<image123>"
        attachment.get_filename.return_value = None
        attachment.get_content_subtype.return_value = "png"
        attachment.get_payload.return_value = "data"
        
        email_message.walk.return_value = [attachment]
        
        _replace_cid_images(soup, email_message)
        
        img_tag = soup.find("img")
        assert "data:image/png;base64," in img_tag["src"]

    def test_replace_cid_image_cid_not_found(self):
        """Test when CID doesn't match any attachment"""
        html = '<img src="cid:notfound">'
        soup = BeautifulSoup(html, "html.parser")
        
        email_message = Mock()
        attachment = Mock()
        attachment.is_attachment.return_value = True
        attachment.get.return_value = "<differentcid>"
        
        email_message.walk.return_value = [attachment]
        
        original_src = soup.find("img")["src"]
        _replace_cid_images(soup, email_message)
        
        # Should remain unchanged
        assert soup.find("img")["src"] == original_src

    def test_replace_cid_image_skips_non_matching_attachments(self):
        """Test that non-matching attachments are skipped"""
        html = '<img src="cid:target">'
        soup = BeautifulSoup(html, "html.parser")
        
        email_message = Mock()
        
        attachment1 = Mock()
        attachment1.is_attachment.return_value = True
        attachment1.get.return_value = "<other>"
        
        attachment2 = Mock()
        attachment2.is_attachment.return_value = True
        attachment2.get.return_value = "<target>"
        attachment2.get_filename.return_value = "target.png"
        attachment2.get_payload.return_value = "targetdata"
        
        email_message.walk.return_value = [attachment1, attachment2]
        
        _replace_cid_images(soup, email_message)
        
        img_tag = soup.find("img")
        assert "targetdata" in img_tag["src"]

