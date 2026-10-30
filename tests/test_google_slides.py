"""
Test Google Slides API Integration, OAuth Flow Handling, and Readback Validation (Mock & Structural).
"""

import pytest
from unittest.mock import MagicMock, patch

from html2slides.google_slides import GoogleSlidesUploader, GOOGLE_API_AVAILABLE


def test_google_slides_uploader_initialization():
    uploader = GoogleSlidesUploader(credentials_path="test_cred.json", token_path="test_token.json")
    assert uploader.credentials_path == "test_cred.json"
    assert uploader.token_path == "test_token.json"


@pytest.mark.skipif(not GOOGLE_API_AVAILABLE, reason="google-api-client not available")
def test_google_slides_validation_structure():
    uploader = GoogleSlidesUploader()
    uploader.slides_service = MagicMock()
    uploader.authenticate = MagicMock(return_value=True)

    # Mock Presentations.get response
    mock_pres_response = {
        "presentationId": "test_id_123",
        "title": "Enterprise Solution Deck",
        "slides": [
            {
                "pageElements": [
                    {"shape": {"text": {"textElements": [{"textRun": {"content": "Title"}}]}}},
                    {"shape": {"text": {"textElements": [{"textRun": {"content": "Card text"}}]}}},
                    {"image": {}}
                ]
            }
        ]
    }
    uploader.slides_service.presentations().get().execute.return_value = mock_pres_response

    result = uploader.validate_google_slides("test_id_123")
    assert result["status"] == "PASS"
    assert result["slide_count"] == 1
    assert result["shape_elements"] == 2
    assert result["text_elements"] == 2
    assert result["image_elements"] == 1
    assert result["is_editable"] is True
