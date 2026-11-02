"""
Google Drive & Google Slides conversion and readback verification module.
"""

import os
import sys
from typing import Dict, Any, Optional, Tuple, List

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


# Minimal OAuth Scope required for creating and modifying app-created files
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleSlidesUploader:
    """Handles OAuth desktop flow, Drive PPTX import to Google Slides, and readback validation."""

    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds: Optional[Credentials] = None
        self.drive_service = None
        self.slides_service = None

    def authenticate(self) -> bool:
        """Authenticate using local OAuth Desktop flow with minimal drive.file scope."""
        if not GOOGLE_API_AVAILABLE:
            print("ERROR: Google API client libraries not installed. Install with: pip install .[google]", file=sys.stderr)
            return False

        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                print(f"WARN: Failed to load existing token.json: {e}", file=sys.stderr)
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"WARN: Token refresh failed: {e}. Re-authenticating.", file=sys.stderr)
                    self.creds = None

            if not self.creds:
                if not os.path.exists(self.credentials_path):
                    print(f"ERROR: Google OAuth credentials file '{self.credentials_path}' not found.", file=sys.stderr)
                    print("Please download credentials.json (Desktop App) from Google Cloud Console.", file=sys.stderr)
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Save token for next runs
            with open(self.token_path, "w", encoding="utf-8") as token_file:
                token_file.write(self.creds.to_json())

        self.drive_service = build("drive", "v3", credentials=self.creds)
        self.slides_service = build("slides", "v1", credentials=self.creds)
        return True

    def upload_and_convert(
        self,
        pptx_path: str,
        presentation_name: Optional[str] = None,
        drive_folder_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Upload PPTX file to Google Drive and convert to native Google Slides.
        Returns (presentation_id, web_view_link, error_message).
        """
        if not self.drive_service:
            if not self.authenticate():
                return (None, None, "Google authentication failed or credentials missing.")

        if not os.path.exists(pptx_path):
            return (None, None, f"PPTX file not found: {pptx_path}")

        name = presentation_name or os.path.splitext(os.path.basename(pptx_path))[0]

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.presentation"  # Trigger Google Drive automatic conversion
        }
        if drive_folder_id:
            file_metadata["parents"] = [drive_folder_id]

        media = MediaFileUpload(
            pptx_path,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            resumable=True
        )

        try:
            file_resource = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink"
            ).execute()

            pres_id = file_resource.get("id")
            link = file_resource.get("webViewLink")
            return (pres_id, link, None)
        except Exception as e:
            return (None, None, f"Google Drive upload error: {e}")

    def validate_google_slides(self, presentation_id: str) -> Dict[str, Any]:
        """
        Read back Google Slides structure via Slides API to verify editable shapes and slide count.
        """
        if not self.slides_service:
            if not self.authenticate():
                return {"status": "FAIL", "error": "Slides service not authenticated"}

        try:
            pres = self.slides_service.presentations().get(presentationId=presentation_id).execute()
            slides = pres.get("slides", [])
            slide_count = len(slides)

            shape_count = 0
            image_count = 0
            text_element_count = 0

            for s in slides:
                for pe in s.get("pageElements", []):
                    if "shape" in pe:
                        shape_count += 1
                        shape_obj = pe["shape"]
                        if "text" in shape_obj:
                            text_element_count += 1
                    elif "image" in pe:
                        image_count += 1

            is_valid = slide_count > 0 and (shape_count + text_element_count > 0)
            return {
                "status": "PASS" if is_valid else "FAIL",
                "presentation_id": presentation_id,
                "title": pres.get("title", ""),
                "slide_count": slide_count,
                "shape_elements": shape_count,
                "text_elements": text_element_count,
                "image_elements": image_count,
                "is_editable": is_valid
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "error": f"Failed to read back Google Slides: {e}"
            }
